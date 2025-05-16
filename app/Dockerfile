# Use Miniconda3 as the base image
FROM continuumio/miniconda3:latest

# Set the working directory
WORKDIR /app

# Copy environment.yml first to leverage Docker cache
COPY environment.yml .

# Create the conda environment
RUN conda env create -f environment.yml

# Make sure conda environment is activated by default
SHELL ["/bin/bash", "-c"]

# Activate the environment and ensure it's used for subsequent commands
ENV PATH=/opt/conda/envs/v-pipe-scout-app/bin:$PATH

# Copy the rest of the application code
COPY . .

# Expose the port Streamlit runs on
EXPOSE 8000

# Run the Streamlit application
CMD ["conda", "run", "-n", "v-pipe-scout-app", "streamlit", "run", "app.py", "--server.port=8000", "--server.address=0.0.0.0"]