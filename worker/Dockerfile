FROM continuumio/miniconda3:latest

WORKDIR /app

# Copy requirements file
COPY environment.yml .

# Create the conda environment from environment.yml
RUN conda env create -f environment.yml

# Install Celery worker dependencies within the conda environment
RUN conda run -n v-pipe-scout-backend pip install --no-cache-dir \
    celery==5.3.6 redis==5.0.1 watchdog==3.0.0

# Copy all worker files (scripts, configs, and data)
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the Celery worker using the conda environment
CMD ["conda", "run", "--no-capture-output", "-n", "v-pipe-scout-backend", \
     "celery", "-A", "tasks", "worker", "--loglevel=info"]
