import sys
from pathlib import Path

# Add the project root directory to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest
import pandas as pd
from worker.deconvolve import devconvolve

def test_deconvolve_function(mutation_counts_df, mutation_variant_matrix_df, expected_output_df):
    """Test the deconvolve function with sample data.
    
        This test only checks the shape and columns of the output DataFrame.
        It does not check the actual values in the DataFrame.
    """

    # Call the deconvolve function
    try:
        deconvolved_json = devconvolve(
                    mutation_counts_df=mutation_counts_df,
                    mutation_variant_matrix_df=mutation_variant_matrix_df,
                    bootstraps=10
                )
    except Exception as e:
        pytest.fail(f"Deconvolve function raised an exception: {e}")

    # Convert result to pandas dataframe
    deconvolved_df = pd.DataFrame.from_records(deconvolved_json)

    # Check if the output matches the expected output
    assert deconvolved_df.shape == expected_output_df.shape, "Output shape does not match expected shape"
    assert deconvolved_df.columns.tolist() == expected_output_df.columns.tolist(), "Output columns do not match expected columns"
    assert deconvolved_df.index.tolist() == expected_output_df.index.tolist(), "Output index does not match expected index"


