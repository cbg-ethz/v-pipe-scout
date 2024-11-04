# Use the official Python image from the Docker Hub
FROM python:3.9-slim

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install the required packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port Streamlit runs on
EXPOSE 8080

# Run the Streamlit application
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]