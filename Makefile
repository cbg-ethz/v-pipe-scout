# Makefile for v-pipe-scout
# This Makefile provides commands to set up and run the project

# Environment name
ENV_NAME = v-pipe-scout

# Default target
.PHONY: all
all: help

# Help message
.PHONY: help
help:
	@echo "V-Pipe Scout Frontend"
	@echo "=================================="
	@echo ""
	@echo "Available commands:"
	@echo "  make setup      - Create conda environment and install dependencies"
	@echo "  make run        - Run the Streamlit application"
	@echo "  make clean      - Remove the conda environment"
	@echo "  make update     - Update dependencies in existing environment"
	@echo "  make docker     - Build and run using Docker"
	@echo ""
	@echo "For first-time setup, run: make setup"

# Create conda environment and install dependencies
.PHONY: setup
setup:
	@echo "Creating conda environment '$(ENV_NAME)' from environment.yml..."
	@conda env create -f environment.yml
	@echo "Setup complete! Run 'make run' to start the application"

# Run the application
.PHONY: run
run:
	@{ \
		source $$(conda info --base)/etc/profile.d/conda.sh ; \
		conda activate $(ENV_NAME) ; \
		streamlit run app.py ; \
	}

# Clean up environment
.PHONY: clean
clean:
	@echo "Removing conda environment '$(ENV_NAME)'..."
	@conda env remove -n $(ENV_NAME)
	@echo "Environment removed."

# Update dependencies in existing environment
.PHONY: update
update:
	@echo "Updating conda environment '$(ENV_NAME)' from environment.yml..."
	@conda env update -n $(ENV_NAME) -f environment.yml

# Build and run using Docker
.PHONY: docker
docker:
	@echo "Building Docker image..."
	@docker build -t v-pipe-scout .
	@echo "Running Docker container..."
	@docker run -p 80:8000 v-pipe-scout
