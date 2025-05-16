import streamlit as st
import json
import os
import time  
from celery import Celery
import redis

# Initialize Celery
celery_app = Celery(
    'tasks',
    broker=os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
)

# Initialize Redis client for checking task status
redis_client = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'redis'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    db=0
)


def app():
        
    st.title('Streamlit with Celery and Redis')
    st.write('This is a simple example of using Celery with Redis to handle background tasks in Streamlit.')
    # Initialize task list in session state
    if 'tasks_info' not in st.session_state:
        st.session_state['tasks_info'] = []

    # Input for task parameters
    st.subheader('Task Parameters')
    n_iterations = st.slider('Number of iterations', 1, 10, 5)
    sleep_time = st.slider('Sleep time per iteration (seconds)', 1, 5, 2)

    # Button to start a new task
    # Only submit when there is at least one free slot to avoid duplicate appends on rerun
    if st.button('Start Task'):
        # Submit the task to Celery
        task = celery_app.send_task(
            'tasks.long_running_task',
            args=[n_iterations, sleep_time],
            kwargs={}
        )
        # Append new task info (avoid duplicates)
        if not any(info['id'] == task.id for info in st.session_state['tasks_info']):
            st.session_state['tasks_info'].append({
                'id': task.id,
                'n_iterations': n_iterations,
                'sleep_time': sleep_time
            })
        st.success(f'Task submitted with ID: {task.id}')

    # Display all submitted tasks and their status
    for info in st.session_state['tasks_info']:
        task_id = info['id']
        with st.expander(f"Task {task_id} (iter={info['n_iterations']}, sleep={info['sleep_time']})"):
            status_placeholder = st.empty()
            progress_bar = st.progress(0)
            results_placeholder = st.empty()
            task_result = celery_app.AsyncResult(task_id)
            if task_result.ready():
                status_placeholder.success('Task completed!')
                progress_bar.progress(100)
                results_placeholder.json(task_result.get())
            else:
                # Check for progress updates in Redis
                progress_key = f"task_progress:{task_id}"
                progress_data = redis_client.get(progress_key)
                if progress_data:
                    progress_info = json.loads(progress_data)
                    current = progress_info.get('current', 0)
                    total = progress_info.get('total', 1)
                    status = progress_info.get('status', 'Processing')
                    progress_bar.progress(int(100 * current / total) if total > 0 else 0)
                    status_placeholder.info(f"Status: {status} ({current}/{total})")
                    partial = progress_info.get('partial_results', [])
                    if partial:
                        results_placeholder.json(partial)
                else:
                    status_placeholder.info('Task pending or starting...')
    # Auto-refresh if any task is still in progress
    if any(not celery_app.AsyncResult(info['id']).ready() for info in st.session_state['tasks_info']):
        time.sleep(2)
        st.rerun()


    st.markdown("---")

    st.subheader('Simple Task, no progress, only show task is in queue')
    # Single Config Task: track queued, processing, and done states
    st.subheader('Single Config Task')
    # Initialize single task state
    if 'single_task_id' not in st.session_state:
        st.session_state['single_task_id'] = None

    # Button to start a single task
    if st.button('Run Single Task'):
        task = celery_app.send_task(
            'tasks.long_running_task',
            args=[n_iterations, sleep_time],
            kwargs={}
        )
        st.session_state['single_task_id'] = task.id
        st.success(f'Single task submitted with ID: {task.id}')

    # Display status of the single task
    if st.session_state['single_task_id']:
        task_id = st.session_state['single_task_id']
        task_result = celery_app.AsyncResult(task_id)
        # Map Celery states to user-friendly labels
        status_map = {
            'PENDING': 'Queued',
            'STARTED': 'Processing',
            'SUCCESS': 'Done',
            'FAILURE': 'Failed'
        }
        current_state = task_result.status
        label = status_map.get(current_state, current_state)
        # Use a placeholder to avoid stacking status messages on each rerun
        status_slot = st.empty()
        status_slot.info(f'Task {task_id} status: {label}')
        if current_state == 'SUCCESS':
            # Display result once when done
            result = task_result.get()
            result_slot = st.empty()
            result_slot.json(result)
        elif current_state in ('PENDING', 'STARTED'):
            # Auto-refresh until task completes
            time.sleep(2)
            st.rerun()
    