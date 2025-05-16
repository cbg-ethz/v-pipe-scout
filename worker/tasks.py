import time
import json
import os
import redis
from celery import Celery

# Initialize Celery
app = Celery(
    'tasks',
    broker=os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
)

# Initialize Redis client for storing progress updates
redis_client = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'redis'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    db=0
)

@app.task(bind=True)
def long_running_task(self, n_iterations, sleep_time):
    """
    A simple long-running task that simulates work by sleeping.
    Updates progress in Redis to allow the frontend to track status.
    """
    task_id = self.request.id
    progress_key = f"task_progress:{task_id}"
    
    # Initialize result container
    result = {
        "iterations_completed": 0,
        "total_iterations": n_iterations,
        "results": []
    }
    
    # Process each iteration
    for i in range(n_iterations):
        # Simulate work
        time.sleep(sleep_time)
        
        # Calculate some dummy result
        iteration_result = {
            "iteration": i + 1,
            "timestamp": time.time(),
            "value": (i + 1) * sleep_time
        }
        
        # Add to results
        result["results"].append(iteration_result)
        result["iterations_completed"] = i + 1
        
        # Update progress in Redis
        progress_data = {
            "current": i + 1,
            "total": n_iterations,
            "status": f"Processing iteration {i + 1}/{n_iterations}",
            "partial_results": result["results"]
        }
        
        redis_client.set(
            progress_key,
            json.dumps(progress_data),
            ex=3600  # Expire after 1 hour
        )
    
    # Task completed
    progress_data = {
        "current": n_iterations,
        "total": n_iterations,
        "status": "Completed",
        "partial_results": result["results"]
    }
    
    redis_client.set(
        progress_key,
        json.dumps(progress_data),
        ex=3600  # Expire after 1 hour
    )
    
    return result
