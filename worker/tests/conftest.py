import pytest
import pandas as pd
from pathlib import Path


# Fixtures for the deconvolution test

@pytest.fixture(scope="session")
def mutation_counts_df():
    """Fixture to load the mutation counts DataFrame."""
    file_path = Path(__file__).parent / "data/deconvolution/mutation_counts_coverage.csv"
    return pd.read_csv(file_path)

@pytest.fixture(scope="session")
def mutation_variant_matrix_df():
    """Fixture to load the mutation variant matrix DataFrame."""
    file_path = Path(__file__).parent / "data/deconvolution/mutation_variant_matrix.csv"
    return pd.read_csv(file_path)

@pytest.fixture(scope="session")
def expected_output_df():
    """Fixture to load the expected output DataFrame."""
    file_path = Path(__file__).parent / "data/deconvolution/deconvolution_expected.json"
    return pd.read_json(file_path)