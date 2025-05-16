import streamlit as st
import json
import os
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

    # Input for task parameters
    st.subheader('Task Parameters')
    n_iterations = st.slider('Number of iterations', 1, 10, 5)
    sleep_time = st.slider('Sleep time per iteration (seconds)', 1, 5, 2)

    # Button to start a new task
    if st.button('Start Task'):
        # Submit the task to Celery
        task = celery_app.send_task(
            'tasks.long_running_task',
            args=[n_iterations, sleep_time],
            kwargs={}
        )
        
        # Store the task ID in session state for later reference
        st.session_state['task_id'] = task.id
        st.success(f'Task submitted with ID: {task.id}')

    # Check task status and display results
    if 'task_id' in st.session_state:
        task_id = st.session_state['task_id']
        st.subheader('Task Status')
        
        # Status placeholder
        status_placeholder = st.empty()
        
        # Progress bar placeholder
        progress_bar = st.progress(0)
        
        # Results placeholder
        results_placeholder = st.empty()
        
        # Check if task is completed
        task_result = celery_app.AsyncResult(task_id)
        
        if task_result.ready():
            status_placeholder.success('Task completed!')
            progress_bar.progress(100)
            result = task_result.get()
            results_placeholder.json(result)
        else:
            # Check for progress updates in Redis
            progress_key = f"task_progress:{task_id}"
            progress_data = redis_client.get(progress_key)
            
            if progress_data:
                progress_info = json.loads(progress_data)
                current = progress_info.get('current', 0)
                total = progress_info.get('total', 1)
                status = progress_info.get('status', 'Processing')
                
                # Update progress bar
                progress_percent = int(100 * current / total) if total > 0 else 0
                progress_bar.progress(progress_percent)
                
                # Update status
                status_placeholder.info(f"Status: {status} ({current}/{total})")
                
                # Show partial results if available
                partial_results = progress_info.get('partial_results', [])
                if partial_results:
                    results_placeholder.json(partial_results)
            else:
                status_placeholder.info('Task is pending or in progress...')
        
        # Add a button to refresh the status
        if st.button('Refresh Status'):
            st.rerun()
