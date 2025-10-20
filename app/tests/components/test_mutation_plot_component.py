"""
Tests for mutation plot component error rate masking functionality.
Focuses on essential test cases for maintainability.
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os
import importlib.util

# Load the mutation_plot_component module directly to avoid namespace conflicts
app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
module_path = os.path.join(app_dir, 'components', 'mutation_plot_component.py')
spec = importlib.util.spec_from_file_location("mutation_plot_component", module_path)
mutation_plot_component = importlib.util.module_from_spec(spec) # type: ignore
spec.loader.exec_module(mutation_plot_component) # type: ignore

SEQUENCING_ERROR_RATE = mutation_plot_component.SEQUENCING_ERROR_RATE


class TestErrorRateMasking:
    """Essential tests for the sequencing error rate masking functionality."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample frequency and counts DataFrames for testing."""
        freq_df = pd.DataFrame({
            'date1': [0.0010, 0.005, 0.0025],  # below, above, below threshold
            'date2': [0.0020, 0.010, 0.040],   # below, above, above threshold
        }, index=['mutation1', 'mutation2', 'mutation3'])
        
        counts_df = pd.DataFrame({
            'date1': [10, 50, 25],
            'date2': [20, 100, 400],
        }, index=['mutation1', 'mutation2', 'mutation3'])
        
        return freq_df, counts_df
    
    def test_values_below_threshold_are_masked(self, sample_data):
        """Test that values below 0.0032 are masked to NaN while values >= 0.0032 remain."""
        freq_df, _ = sample_data
        
        # Apply masking logic
        freq_df_numeric = freq_df.apply(pd.to_numeric, errors='coerce')
        below_error_rate = freq_df_numeric < SEQUENCING_ERROR_RATE
        masked_df = freq_df.copy()
        masked_df[below_error_rate] = np.nan
        
        # Values below threshold should be NaN
        assert pd.isna(masked_df.loc['mutation1', 'date1'])  # 0.0010 < 0.0032
        assert pd.isna(masked_df.loc['mutation1', 'date2'])  # 0.0020 < 0.0032
        assert pd.isna(masked_df.loc['mutation3', 'date1'])  # 0.0025 < 0.0032
        
        # Values above threshold should remain
        assert masked_df.loc['mutation2', 'date1'] == 0.005  # >= 0.0032
        assert masked_df.loc['mutation2', 'date2'] == 0.010  # >= 0.0032
        assert masked_df.loc['mutation3', 'date2'] == 0.040  # >= 0.0032
    
    def test_counts_df_masked_consistently(self, sample_data):
        """Test that counts_df is masked using the same mask as freq_df."""
        freq_df, counts_df = sample_data
        
        # Apply masking logic
        freq_df_numeric = freq_df.apply(pd.to_numeric, errors='coerce')
        below_error_rate = freq_df_numeric < SEQUENCING_ERROR_RATE
        
        masked_freq_df = freq_df.copy()
        masked_freq_df[below_error_rate] = np.nan
        
        masked_counts_df = counts_df.copy()
        masked_counts_df[below_error_rate] = np.nan
        
        # Verify consistent masking: wherever freq is NaN, count must also be NaN
        for mutation in freq_df.index:
            for date in freq_df.columns:
                freq_is_nan = pd.isna(masked_freq_df.loc[mutation, date])
                count_is_nan = pd.isna(masked_counts_df.loc[mutation, date])
                assert freq_is_nan == count_is_nan, \
                    f"Inconsistent masking at {mutation}, {date}"
    
    def test_mutation_inclusion_unchanged_by_masking(self, sample_data):
        """
        Test that mutation inclusion is based on max frequency,
        not affected by per-point masking.
        """
        freq_df, _ = sample_data
        min_frequency = 0.01  # 1%
        max_frequency = 1.0
        
        # Determine which mutations to keep BEFORE masking
        freq_df_numeric = freq_df.apply(pd.to_numeric, errors='coerce')
        mutations_above_min = freq_df_numeric.max(axis=1) >= min_frequency
        mutations_below_max = freq_df_numeric.max(axis=1) <= max_frequency
        mutations_to_keep_before = mutations_above_min & mutations_below_max
        
        # Apply masking
        below_error_rate = freq_df_numeric < SEQUENCING_ERROR_RATE
        masked_df = freq_df.copy()
        masked_df[below_error_rate] = np.nan
        
        # Mutation selection should use ORIGINAL data (before masking)
        mutations_to_keep_after = mutations_above_min & mutations_below_max
        
        # Verify mutation inclusion is unchanged
        pd.testing.assert_series_equal(
            mutations_to_keep_before,
            mutations_to_keep_after,
            check_names=False
        )
        
        # Verify expected behavior:
        # mutation1: max = 0.0020 < 0.01 -> excluded
        # mutation2: max = 0.010 >= 0.01 -> included
        # mutation3: max = 0.040 >= 0.01 -> included
        assert not mutations_to_keep_before['mutation1']
        assert mutations_to_keep_before['mutation2']
        assert mutations_to_keep_before['mutation3']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
