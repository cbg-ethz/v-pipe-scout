# Use Python slim base image
FROM python:3.13-slim

# Set the working directory
WORKDIR /app

# Install uv
RUN pip install uv

# Copy pyproject.toml and uv.lock first to leverage Docker cache
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen --no-install-project

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
CMD ["uv", "run", "streamlit", "run", "app.py", "--server.port=8000", "--server.address=0.0.0.0"]