"""
Centralized LAPIS/SILO API field name constants for the worker.

This module contains all API field names used to communicate with the LAPIS/SILO backend.
When the API changes field names, only this file needs to be updated instead of 
making changes throughout the codebase.

Field names follow the camelCase convention used by the LAPIS/SILO API.

Note: This is a copy of app/api/lapis_fields.py to maintain worker independence.
Both files should be kept in sync.
"""

# Date-related fields
SAMPLING_DATE = "samplingDate"
SAMPLING_DATE_FROM = "samplingDateFrom"
SAMPLING_DATE_TO = "samplingDateTo"
DATE_FIELD = "dateField"

# Location-related fields
LOCATION_NAME = "locationName"

# Mutation-related fields
AMINO_ACID_MUTATIONS = "aminoAcidMutations"
NUCLEOTIDE_MUTATIONS = "nucleotideMutations"

# General query fields
FIELDS = "fields"
ORDER_BY = "orderBy"
MIN_PROPORTION = "minProportion"
LIMIT = "limit"
DATA_FORMAT = "dataFormat"
DOWNLOAD_AS_FILE = "downloadAsFile"

# Data structure fields (used in responses)
COUNT = "count"
COVERAGE = "coverage"
PROPORTION = "proportion"
FREQUENCY = "frequency"
MUTATION = "mutation"
SEQUENCE_NAME = "sequenceName"
MUTATION_FROM = "mutationFrom"
MUTATION_TO = "mutationTo"
POSITION = "position"

# Component endpoint specific fields
FILTERS = "filters"
INCLUDE_MUTATIONS = "includeMutations"
DATE_RANGES = "dateRanges"
DATE_FROM = "dateFrom"
DATE_TO = "dateTo"
DATA = "data"
MUTATIONS = "mutations"


# DataFrame column names for internal use
# These are used for pandas DataFrame columns and may differ from API field names
# in certain contexts (e.g., when transforming API responses)
DF_SAMPLING_DATE = "samplingDate"
DF_MUTATION = "mutation"
DF_COUNT = "count"
DF_COVERAGE = "coverage"
DF_FREQUENCY = "frequency"
DF_LOCATION = "location"
