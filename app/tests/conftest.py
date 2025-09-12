"""Test configuration for app tests."""

import os
import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def fix_streamlit_logging():
    """Fix Streamlit logging configuration issues during testing.
    
    This addresses the issue where Streamlit's logging formatter receives
    MagicMock objects instead of proper string formats during testing.
    """
    # Set environment variables to provide proper logging configuration
    original_log_level = os.environ.get('STREAMLIT_LOG_LEVEL')
    original_log_format = os.environ.get('STREAMLIT_LOG_FORMAT')
    
    # Set proper logging configuration
    os.environ['STREAMLIT_LOG_LEVEL'] = 'WARNING'
    os.environ['STREAMLIT_LOG_FORMAT'] = '%(asctime)s %(levelname)s: %(message)s'
    
    # Mock the problematic logging configuration parts
    with patch('streamlit.logger.setup_formatter') as mock_setup:
        # Make setup_formatter do nothing to avoid the MagicMock issue
        mock_setup.return_value = None
        yield
    
    # Restore original environment
    if original_log_level is not None:
        os.environ['STREAMLIT_LOG_LEVEL'] = original_log_level
    else:
        os.environ.pop('STREAMLIT_LOG_LEVEL', None)
        
    if original_log_format is not None:
        os.environ['STREAMLIT_LOG_FORMAT'] = original_log_format
    else:
        os.environ.pop('STREAMLIT_LOG_FORMAT', None)