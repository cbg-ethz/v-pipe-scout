"""
Tests for URL State Manager
"""

import pytest
import sys
from pathlib import Path
from datetime import date
from unittest.mock import MagicMock, patch
import json
import base64

# Add the app directory to the path for imports
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from utils.url_state import URLStateManager, create_url_state_manager, load_date_range_from_url_with_validation
import pandas as pd


class TestURLStateManager:
    """Test URLStateManager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = URLStateManager("test")
    
    def test_get_param_key(self):
        """Test parameter key generation with prefix."""
        assert self.manager._get_param_key("key") == "test_key"
        
        manager_no_prefix = URLStateManager("")
        assert manager_no_prefix._get_param_key("key") == "key"
    
    def test_encode_decode_string(self):
        """Test string encoding and decoding."""
        value = "test_string"
        encoded = self.manager._encode_value(value)
        decoded = self.manager._decode_value(encoded, str)
        assert decoded == value
    
    def test_encode_decode_list(self):
        """Test list encoding and decoding."""
        # Simple string list
        value = ["item1", "item2", "item3"]
        encoded = self.manager._encode_value(value)
        decoded = self.manager._decode_value(encoded, list)
        assert decoded == value
        
        # Complex list with mixed types
        value = ["item1", 123, True]
        encoded = self.manager._encode_value(value)
        decoded = self.manager._decode_value(encoded, list)
        assert decoded == value
    
    def test_encode_decode_date(self):
        """Test date encoding and decoding."""
        value = date(2024, 1, 15)
        encoded = self.manager._encode_value(value)
        decoded = self.manager._decode_value(encoded, date)
        assert decoded == value
    
    def test_encode_decode_bool(self):
        """Test boolean encoding and decoding."""
        assert self.manager._encode_value(True) == "true"
        assert self.manager._encode_value(False) == "false"
        assert self.manager._decode_value("true", bool) is True
        assert self.manager._decode_value("false", bool) is False
    
    def test_encode_decode_numbers(self):
        """Test number encoding and decoding."""
        # Integer
        value = 42
        encoded = self.manager._encode_value(value)
        decoded = self.manager._decode_value(encoded, int)
        assert decoded == value
        
        # Float
        value = 3.14
        encoded = self.manager._encode_value(value)
        decoded = self.manager._decode_value(encoded, float)
        assert decoded == value
    
    def test_encode_none(self):
        """Test handling of None values."""
        encoded = self.manager._encode_value(None)
        assert encoded == ""
    
    def test_decode_invalid_values(self):
        """Test handling of invalid encoded values."""
        # Invalid date
        assert self.manager._decode_value("invalid_date", date) is None
        
        # Invalid number
        assert self.manager._decode_value("not_a_number", int) is None
        
        # Boolean decoding always returns a boolean (True for "true", False for anything else)
        assert self.manager._decode_value("maybe", bool) is False
        assert self.manager._decode_value("true", bool) is True
    
    @patch('streamlit.query_params')
    def test_save_to_url(self, mock_query_params):
        """Test saving parameters to URL."""
        mock_query_params.__iter__.return_value = iter({})
        mock_query_params.get.return_value = None
        mock_dict = {}
        
        # Create a mock update method  
        update_mock = MagicMock()
        mock_query_params.update = update_mock
        
        self.manager.save_to_url(
            test_string="hello",
            test_list=["a", "b"],
            test_date=date(2024, 1, 15),
            test_bool=True
        )
        
        # Check that update was called
        update_mock.assert_called_once()
    
    @patch('streamlit.query_params')
    def test_load_from_url(self, mock_query_params):
        """Test loading parameters from URL."""
        mock_query_params.get.side_effect = lambda k: {
            "test_string": "hello",
            "test_list": "a,b,c",
            "test_date": "2024-01-15",
            "test_bool": "true",
            "test_int": "42"
        }.get(k)
        
        assert self.manager.load_from_url("string", "default") == "hello"
        assert self.manager.load_from_url("list", [], list) == ["a", "b", "c"]
        assert self.manager.load_from_url("date", None, date) == date(2024, 1, 15)
        assert self.manager.load_from_url("bool", False, bool) is True
        assert self.manager.load_from_url("int", 0, int) == 42
        
        # Test default values
        assert self.manager.load_from_url("nonexistent", "default") == "default"


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @patch('streamlit.query_params')
    def test_create_url_state_manager(self, mock_query_params):
        """Test creating URL state manager."""
        manager = create_url_state_manager("test_page")
        assert manager.page_prefix == "test_page"
    
    @patch('utils.url_state.URLStateManager')
    def test_save_date_range_to_url(self, mock_manager_class):
        """Test date range saving convenience function."""
        from utils.url_state import save_date_range_to_url
        
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)
        
        save_date_range_to_url(start, end, "test_page")
        
        mock_manager_class.assert_called_with("test_page")
        mock_manager.save_to_url.assert_called_with(start_date=start, end_date=end)
    
    @patch('utils.url_state.URLStateManager')
    def test_load_date_range_from_url(self, mock_manager_class):
        """Test date range loading convenience function."""
        from utils.url_state import load_date_range_from_url
        
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.load_from_url.side_effect = [
            date(2024, 1, 1),  # start_date
            date(2024, 1, 31)  # end_date
        ]
        
        default_start = date(2024, 2, 1)
        default_end = date(2024, 2, 28)
        
        start, end = load_date_range_from_url(default_start, default_end, "test_page")
        
        assert start == date(2024, 1, 1)
        assert end == date(2024, 1, 31)
        
        mock_manager_class.assert_called_with("test_page")
        assert mock_manager.load_from_url.call_count == 2


class TestDateRangeValidation:
    """Test load_date_range_from_url_with_validation functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = MagicMock(spec=URLStateManager)
        self.default_start = date(2024, 1, 10)
        self.default_end = date(2024, 1, 20)
        self.min_date = date(2024, 1, 1)
        self.max_date = date(2024, 1, 31)

    def test_dates_within_bounds(self):
        """Test that dates within bounds are returned as is."""
        self.manager.load_from_url.side_effect = [
            date(2024, 1, 15),  # start_date
            date(2024, 1, 25)   # end_date
        ]

        start, end, adjusted = load_date_range_from_url_with_validation(
            self.manager, self.default_start, self.default_end, self.min_date, self.max_date
        )

        assert start == date(2024, 1, 15)
        assert end == date(2024, 1, 25)
        assert adjusted is False

    def test_dates_clamped_to_bounds(self):
        """Test that dates outside bounds are clamped."""
        self.manager.load_from_url.side_effect = [
            date(2023, 12, 31), # start_date (before min)
            date(2024, 2, 1)    # end_date (after max)
        ]

        start, end, adjusted = load_date_range_from_url_with_validation(
            self.manager, self.default_start, self.default_end, self.min_date, self.max_date
        )

        assert start == self.min_date
        assert end == self.max_date
        assert adjusted is True

    def test_start_after_end_adjustment(self):
        """Test that start date is adjusted if it's after end date."""
        self.manager.load_from_url.side_effect = [
            date(2024, 1, 25),  # start_date
            date(2024, 1, 15)   # end_date
        ]

        start, end, adjusted = load_date_range_from_url_with_validation(
            self.manager, self.default_start, self.default_end, self.min_date, self.max_date
        )

        # Start and end should be swapped
        assert start == date(2024, 1, 15)
        assert end == date(2024, 1, 25)
        assert adjusted is True

    def test_pandas_timestamp_conversion(self):
        """Test that Pandas Timestamps are converted to date objects."""
        self.manager.load_from_url.side_effect = [
            pd.Timestamp("2024-01-15"),  # start_date
            pd.Timestamp("2024-01-25")   # end_date
        ]
        
        # Also test with Timestamp bounds
        min_ts = pd.Timestamp("2024-01-01")
        max_ts = pd.Timestamp("2024-01-31")

        start, end, adjusted = load_date_range_from_url_with_validation(
            self.manager, self.default_start, self.default_end, min_ts, max_ts
        )

        assert isinstance(start, date)
        assert not isinstance(start, pd.Timestamp)
        assert isinstance(end, date)
        assert not isinstance(end, pd.Timestamp)
        assert start == date(2024, 1, 15)
        assert end == date(2024, 1, 25)
        assert adjusted is False

    def test_edge_cases(self):
        """Test edge cases like both dates out of bounds in opposite directions."""
        # Case 1: Both dates before min
        self.manager.load_from_url.side_effect = [
            date(2023, 1, 1),   # start_date
            date(2023, 1, 5)    # end_date
        ]
        
        start, end, adjusted = load_date_range_from_url_with_validation(
            self.manager, self.default_start, self.default_end, self.min_date, self.max_date
        )
        
        assert start == self.min_date
        assert end == self.min_date
        assert adjusted is True
        
        # Case 2: Both dates after max
        self.manager.load_from_url.side_effect = [
            date(2024, 2, 1),   # start_date
            date(2024, 2, 5)    # end_date
        ]
        
        start, end, adjusted = load_date_range_from_url_with_validation(
            self.manager, self.default_start, self.default_end, self.min_date, self.max_date
        )
        
        assert start == self.max_date
        assert end == self.max_date
        assert adjusted is True


if __name__ == "__main__":
    pytest.main([__file__])