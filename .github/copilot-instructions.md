# V-Pipe Scout: GitHub Copilot Instructions

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

V-Pipe Scout is a Streamlit-based interactive web application for rapid viral variant detection from wastewater sequencing data, with a Celery worker backend for background processing. The application uses Docker Compose orchestration with Redis as message broker.

## Working Effectively

### Bootstrap and Setup
- **ALWAYS start here for any fresh clone:**
  - `./setup.sh` - Creates .env with secure Redis password (takes < 1 second)
  - Review `app/config.yaml` for LAPIS server configuration
  - The application runs on port 9001 when using Docker Compose

### Development Environment Setup
- **Frontend development** (Streamlit app):
  - `conda env create -f app/environment.yml` - takes 2-3 minutes. NEVER CANCEL. Set timeout to 10+ minutes.
  - `conda activate v-pipe-scout-app`
  - Test: `conda run -n v-pipe-scout-app streamlit run app/app.py --server.port=8888`

- **Worker development** (Celery background tasks):
  - `conda env create -f worker/environment.yml` - takes 1-2 minutes, may fail on slow networks. NEVER CANCEL. Set timeout to 10+ minutes.
  - If pip dependencies fail due to network issues, manually install: `conda run -n v-pipe-scout-worker pip install redis celery`
  - `conda activate v-pipe-scout-worker`

### Docker Deployment (Recommended)
- `docker compose up --build` - NEVER CANCEL: Build takes 5-15 minutes depending on network. Set timeout to 30+ minutes.
- Docker may fail on networks with SSL/conda issues - use conda environments as fallback
- Application accessible at http://localhost:9001
- Services: Redis (internal), Streamlit frontend (port 9001), Celery worker

### Testing
- **Frontend tests**: `conda run -n v-pipe-scout-app pytest` - takes 8-10 seconds
- **Worker tests**: `conda run -n v-pipe-scout-worker pytest` - may require manual redis installation
- **Full test suite**: `pytest` from repository root (uses both environments)
- **Deployment validation**: `bash scripts/test-deployment.sh` - takes < 1 second

## Validation Requirements

### ALWAYS test end-to-end scenarios after making changes:
1. **Application startup validation**:
   - Start application via Docker Compose or conda environment
   - Verify Streamlit UI loads at http://localhost:9001 or http://localhost:8888
   - Check no console errors in browser developer tools

2. **Core functionality validation**:
   - Navigate through main subpages: Background, Dynamic Mutations, Resistance Mutations, Signature Explorer, Abundance Estimator, Task Runner
   - Test basic form interactions and button clicks
   - Verify Redis connectivity (background tasks should queue properly)

3. **Build and test validation**:
   - Run full test suite: `pytest` (frontend + worker tests)
   - Validate deployment script: `bash scripts/test-deployment.sh`

## Build Timing Expectations

**CRITICAL - NEVER CANCEL these operations:**
- Conda environment creation: 2-10 minutes (network dependent)
- Docker Compose build: 5-30 minutes (network dependent) 
- Frontend tests: 8-10 seconds
- Worker tests: 5-15 seconds (if dependencies available)
- Deployment script test: < 1 second
- Application startup: 10-30 seconds

## Common Network Issues

- **Docker build failures**: Conda SSL/certificate issues common in CI environments
  - Fallback: Use local conda environments instead of Docker
  - Document as "Docker build may fail due to network limitations - use conda environments"

- **Worker pip dependencies**: PyPI timeouts may prevent redis/celery installation
  - Workaround: `conda run -n v-pipe-scout-worker pip install redis celery` manually
  - Document timeout expectations and retry instructions

## Key Project Components

### Frontend (`app/` directory)
- **Main app**: `app.py` - Streamlit entry point
- **Subpages**: `subpages/` - Individual pages (background.py, dynamic_mutations.py, resistance_mut_silo.py, signature_explorer.py, abundance.py, task_runner.py, index.py)
- **Core components**: `components/` - Reusable UI components
- **Configuration**: `config.yaml` - LAPIS server settings
- **Environment**: `environment.yml` - Python 3.12, Streamlit 1.47, pandas, matplotlib, plotly

### Worker (`worker/` directory)
- **Tasks**: `tasks.py` - Celery task definitions  
- **Deconvolution**: `deconvolve.py` - Core analysis logic
- **Environment**: `environment.yml` - Python 3.12, pandas, scipy, lollipop, celery, redis

### Infrastructure
- **Docker**: `docker-compose.yml` - Redis, Streamlit frontend, Celery worker
- **Setup**: `setup.sh` - Environment configuration with Redis password
- **Deployment**: `scripts/auto-deploy.sh` - Production auto-deployment
- **CI/CD**: `.github/workflows/` - Separate frontend tests, worker tests, Docker validation

## Deployment and Production

### Automatic Deployment
- Script: `scripts/auto-deploy.sh` 
- Test: `scripts/test-deployment.sh`
- Manual deployment: `git pull && docker compose down && docker compose up -d --build`
- Production URL: http://dev.vpipe.ethz.ch (ETH network only)

### Monitoring
- Log files: `deployment.log` in repository root
- Service status: `docker compose ps`
- Service logs: `docker compose logs`

## Development Workflow

### Making Changes
1. **Always run existing tests first** to understand baseline
2. **Make minimal changes** to address specific requirements
3. **Test incrementally** - frontend tests after frontend changes, worker tests after worker changes
4. **Validate manually** by running application and testing user workflows
5. **Run deployment test** before final commit

### File Structure to Know
```
├── app/                    # Streamlit frontend
│   ├── app.py             # Main entry point
│   ├── subpages/          # Individual pages
│   ├── components/        # UI components  
│   ├── config.yaml        # LAPIS configuration
│   └── environment.yml    # Frontend dependencies
├── worker/                # Celery worker
│   ├── tasks.py          # Background tasks
│   ├── deconvolve.py     # Analysis logic
│   └── environment.yml   # Worker dependencies
├── scripts/              # Deployment and utility scripts
├── .github/workflows/    # CI/CD pipelines
└── docker-compose.yml    # Container orchestration
```

### Always Test These Commands Before Documenting:
- Environment setup: `./setup.sh`
- Docker build: `docker compose up --build` (with 30+ minute timeout)
- Frontend tests: `conda run -n v-pipe-scout-app pytest`
- Application startup: `streamlit run app/app.py` or Docker access via port 9001
- Deployment validation: `bash scripts/test-deployment.sh`

## Architecture Notes
- **Frontend**: Streamlit app handles UI and user interactions
- **Worker**: Celery processes background computational tasks (viral variant analysis)
- **Redis**: Message broker for task queue and results storage
- **LAPIS**: External API for genomic sequence data (configured in app/config.yaml)
- **Data flow**: UI → Celery tasks → Redis → Results display

**Remember**: This is a proof-of-concept focused on SARS-CoV-2 viral variant detection, with plans to expand to RSV and Influenza. The application enables mutation-level exploration and variant abundance estimation for wastewater surveillance.