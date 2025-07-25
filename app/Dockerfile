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

# Generate version.py with build-time information
RUN BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") && \
    BASE_VERSION=$(grep -Po '(?<=^VERSION\s*=\s*").*(?=")' version.py 2>/dev/null || echo "0.1.0-alpha") && \
    echo "\"\"\"Version information for v-pipe-scout.\"\"\"" > version.py && \
    echo "" >> version.py && \
    echo "# Build-time version information" >> version.py && \
    echo "VERSION = \"${BASE_VERSION}\"" >> version.py && \
    echo "BUILD_DATE = \"${BUILD_DATE}\"" >> version.py && \
    echo "" >> version.py && \
    echo "# Generated at build time on $(date)" >> version.py

# Expose the port Streamlit runs on
EXPOSE 8000

# Run the Streamlit application
CMD ["conda", "run", "-n", "v-pipe-scout-app", "streamlit", "run", "app.py", "--server.port=8000", "--server.address=0.0.0.0"]