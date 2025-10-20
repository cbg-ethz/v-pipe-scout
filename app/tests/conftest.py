"""Test configuration for app tests."""

import os
import sys
import pytest
from unittest.mock import patch

# Add parent directory (app/) to Python path so we can import modules directly
# This allows tests to use imports like "from components.mutation_plot_component import ..."
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def fix_streamlit_issues():
    """Fix various Streamlit testing issues.
    
    This addresses multiple issues where Streamlit components receive
    MagicMock objects instead of proper values during testing:
    - Logging formatter receiving MagicMock objects instead of strings
    - Theme functions receiving MagicMock objects instead of JSON strings
    """
    # Set environment variables to provide proper logging configuration
    original_log_level = os.environ.get('STREAMLIT_LOG_LEVEL')
    original_log_format = os.environ.get('STREAMLIT_LOG_FORMAT')
    
    # Set proper logging configuration
    os.environ['STREAMLIT_LOG_LEVEL'] = 'WARNING'
    os.environ['STREAMLIT_LOG_FORMAT'] = '%(asctime)s %(levelname)s: %(message)s'
    
    # Mock the problematic components
    with patch('streamlit.logger.setup_formatter') as mock_setup, \
         patch('streamlit_theme.st_theme') as mock_theme:
        
        # Make setup_formatter do nothing to avoid the MagicMock issue
        mock_setup.return_value = None
        
        # Make st_theme return a proper theme dictionary instead of MagicMock
        mock_theme.return_value = {'base': 'light'}
        
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