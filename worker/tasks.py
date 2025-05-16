import time
import json
import os
import redis
import pandas as pd
from celery import Celery
from deconvolve import devconvolve

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

@app.task(bind=True)
def run_deconvolve(self, mutation_counts_df, mutation_variant_matrix_df, 
                   bootstraps=None, bandwidth=None, regressor=None, 
                   regressor_params=None, deconv_params=None):
    """
    A task that runs the deconvolve function with progress tracking.
    
    Args:
        mutation_counts_df (pd.DataFrame): DataFrame containing mutation counts data (required)
        mutation_variant_matrix_df (pd.DataFrame): DataFrame containing mutation variant matrix data (required)
        bootstraps (int, optional): Number of bootstrap iterations
        bandwidth (int, optional): Bandwidth parameter for kernel
        regressor (str, optional): Regressor type
        regressor_params (dict, optional): Parameters for the regressor
        deconv_params (dict, optional): Parameters for deconvolution
    """
    
    task_id = self.request.id
    progress_key = f"task_progress:{task_id}"
    
    # Initialize progress tracking
    progress_data = {
        "current": 0,
        "total": 5,  # We'll track progress in 5 stages
        "status": "Preparing input data",
        "partial_results": None
    }
    
    redis_client.set(
        progress_key,
        json.dumps(progress_data),
        ex=3600  # Expire after 1 hour
    )
    
    try:
        # Update progress
        progress_data["current"] = 1
        progress_data["status"] = f"Preparing deconvolution (bootstraps={bootstraps if bootstraps is not None else 'default'})"
        redis_client.set(progress_key, json.dumps(progress_data), ex=3600)
        
        # Function to update progress
        def update_progress(stage, message):
            progress_data["current"] = stage
            progress_data["status"] = message
            redis_client.set(progress_key, json.dumps(progress_data), ex=3600)
        
        # Convert serialized DataFrames back to pandas DataFrames
        try:
            # Add debug info about the input types
            update_progress(1.5, f"Input types: mutation_counts_df: {type(mutation_counts_df)}, mutation_variant_matrix_df: {type(mutation_variant_matrix_df)}")
            
            # Check if inputs are already DataFrames or need to be deserialized
            if isinstance(mutation_counts_df, pd.DataFrame) and isinstance(mutation_variant_matrix_df, pd.DataFrame):
                update_progress(2, "Inputs are already DataFrames, no parsing needed")
            else:
                # Try to load serialized DataFrames using pickle or JSON
                try:
                    # Try pickle first if inputs are byte strings
                    import pickle
                    import base64
                    if isinstance(mutation_counts_df, str) and isinstance(mutation_variant_matrix_df, str):
                        # If they're base64 encoded pickle strings
                        try:
                            mutation_counts_df = pickle.loads(base64.b64decode(mutation_counts_df))
                            mutation_variant_matrix_df = pickle.loads(base64.b64decode(mutation_variant_matrix_df))
                            update_progress(2, f"Successfully unpickled DataFrames, shapes: {mutation_counts_df.shape}, {mutation_variant_matrix_df.shape}")
                        except:
                            # Fall back to JSON if pickle fails
                            mutation_counts_df = pd.read_json(mutation_counts_df, orient='split')
                            mutation_variant_matrix_df = pd.read_json(mutation_variant_matrix_df, orient='split')
                            update_progress(2, f"Successfully parsed JSON DataFrames, shapes: {mutation_counts_df.shape}, {mutation_variant_matrix_df.shape}")
                except Exception as e:
                    update_progress(2, f"Error parsing DataFrames with both pickle and JSON methods: {str(e)}")
                    raise ValueError(f"Failed to deserialize DataFrames: {str(e)}")
        except Exception as e:
            update_progress(2, f"Error processing DataFrames: {str(e)}")
            raise ValueError(f"Failed to process DataFrames: {str(e)}")
        
        # Create kwargs dict with required parameters and optional parameters if provided
        kwargs = {
            'mutation_counts_df': mutation_counts_df,
            'mutation_variant_matrix_df': mutation_variant_matrix_df
        }
        
        # Add optional parameters only if they're not None
        if bootstraps is not None:
            kwargs['bootstraps'] = bootstraps
        if bandwidth is not None:
            kwargs['bandwidth'] = bandwidth
        if regressor is not None:
            kwargs['regressor'] = regressor
        if regressor_params is not None:
            kwargs['regressor_params'] = regressor_params
        if deconv_params is not None:
            kwargs['deconv_params'] = deconv_params
            
        # Run the deconvolution with only the provided parameters
        # devconvolve will use its default values for any missing parameters
        update_progress(3, "Running deconvolution algorithm")
        deconvolved_data = devconvolve(**kwargs)
        
        # Update progress after deconvolution is complete
        update_progress(4, "Processing results")
        
        # Stage 5: Finalize results
        progress_data["current"] = 5
        progress_data["total"] = 5
        progress_data["status"] = "Completed"
        progress_data["partial_results"] = {"summary": "Deconvolution completed successfully"}
        redis_client.set(progress_key, json.dumps(progress_data), ex=3600)
        
        return deconvolved_data
        
    except Exception as e:
        # If there's an error, report it
        error_message = str(e)
        progress_data["status"] = f"Error: {error_message}"
        redis_client.set(progress_key, json.dumps(progress_data), ex=3600)
        raise
