# LAPIS/SILO API Field Centralization

## Overview

The LAPIS/SILO API field names are now centralized in dedicated constants modules to ensure that changes to the API field naming conventions require updates in only one location, rather than throughout the entire codebase.

## Location of Constants

### For the Frontend (Streamlit App)
**File**: `app/api/lapis_fields.py`

This module contains all API field name constants used by the Streamlit frontend application.

### For the Worker (Celery)
**File**: `worker/lapis_fields.py`

This module contains the same constants for the Celery worker. The files are kept separate to maintain independence between the app and worker, but they should be kept in sync.

## Available Constants

### API Request Fields
- `SAMPLING_DATE` - Field name for sampling date
- `SAMPLING_DATE_FROM` - Field name for date range start
- `SAMPLING_DATE_TO` - Field name for date range end
- `LOCATION_NAME` - Field name for location
- `AMINO_ACID_MUTATIONS` - Field name for amino acid mutations
- `NUCLEOTIDE_MUTATIONS` - Field name for nucleotide mutations
- `FIELDS`, `ORDER_BY`, `MIN_PROPORTION`, `LIMIT`, `DATA_FORMAT`, `DOWNLOAD_AS_FILE` - Other query parameters

### API Response Fields
- `COUNT`, `COVERAGE`, `PROPORTION`, `FREQUENCY` - Data fields in responses
- `MUTATION`, `SEQUENCE_NAME`, `POSITION` - Mutation-related fields
- `DATA`, `MUTATIONS`, `DATE_RANGES` - Component endpoint fields

### DataFrame Column Names
- `DF_SAMPLING_DATE`, `DF_MUTATION`, `DF_COUNT`, `DF_COVERAGE`, `DF_FREQUENCY` - Column names used in pandas DataFrames

## Usage Examples

### Importing in the Frontend

```python
from api.lapis_fields import SAMPLING_DATE, LOCATION_NAME, DF_MUTATION

# Use in API calls
payload = {
    SAMPLING_DATE_FROM: start_date.strftime('%Y-%m-%d'),
    SAMPLING_DATE_TO: end_date.strftime('%Y-%m-%d'),
    LOCATION_NAME: location
}

# Use in DataFrame operations
df = df_reset.pivot(index=DF_MUTATION, columns=DF_SAMPLING_DATE, values=DF_COUNT)
```

### Importing in the Worker

```python
from lapis_fields import DF_SAMPLING_DATE, DF_COUNT, DF_COVERAGE

# Use in data processing
select_command = [
    "xsv",
    "select",
    f"{DF_SAMPLING_DATE},{DF_COUNT},{DF_COVERAGE},mutation,pos,base,9-",
]
```

## When the API Changes

If the LAPIS/SILO API changes field names (e.g., from `samplingDate` to `sampling_date`), you only need to:

1. Update the constant value in `app/api/lapis_fields.py`
2. Update the same constant in `worker/lapis_fields.py`

**That's it!** All code using the constants will automatically use the new field names.

### Example

If the API changes from camelCase to snake_case:

```python
# Before
SAMPLING_DATE = "samplingDate"

# After
SAMPLING_DATE = "sampling_date"
```

This single change propagates through the entire codebase automatically.

## Migration History

Previously, field names like `samplingDate` and `locationName` were hardcoded in 100+ locations across the codebase. A simple API change required modifying all these locations, leading to:
- Risk of missing some occurrences
- Inconsistent updates
- Changes to Python variable names (violating naming conventions)
- Difficult code maintenance

The centralization solves all these issues by providing a single source of truth for API field names.

## Files Updated

The following files were updated to use centralized constants:

### Frontend (app/)
- `app/api/lapis.py` - Location fetching
- `app/api/wiseloculus.py` - Main API interaction layer
- `app/components/mutation_plot_component.py` - Mutation plotting component
- `app/tests/test_wiseloculus.py` - Test suite

### Worker
- `worker/deconvolve.py` - Data processing and deconvolution
- `worker/tasks.py` - Celery task definitions (uses locationName as Python variable)

## Best Practices

1. **Always import constants** - Never hardcode API field names as strings
2. **Keep files in sync** - When updating one constants file, update the other
3. **Use descriptive names** - Constants should clearly indicate what they represent
4. **Document changes** - When the API changes, document it in release notes
5. **Test after updates** - Run the full test suite after changing constants

## Testing

After changing constants, run:

```bash
# Frontend tests
conda run -n v-pipe-scout-app pytest app/tests/

# Worker tests  
conda run -n v-pipe-scout-worker pytest worker/tests/

# Full deployment validation
bash scripts/test-deployment.sh
```

## Future Improvements

Consider these potential enhancements:

1. **Shared constants** - Create a shared package for both app and worker
2. **API version support** - Support multiple API versions with different field names
3. **Runtime validation** - Validate that API responses use expected field names
4. **Auto-sync** - Script to automatically sync constants between files
