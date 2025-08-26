"""
URL State Manager for V-Pipe Scout Streamlit App

This module provides utilities for managing session state through URL query parameters,
enabling users to share application configurations via URL.

Features:
- Serialize/deserialize various data types (strings, lists, dates, booleans)
- URL-safe encoding/decoding
- Backward compatibility (URLs without params still work)
- Selective parameter inclusion to keep URLs manageable
"""

import streamlit as st
import json
import base64
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote, unquote


class URLStateManager:
    """Manages application state through URL query parameters."""
    
    def __init__(self, page_prefix: str = ""):
        """
        Initialize URL state manager.
        
        Args:
            page_prefix: Optional prefix for parameters to avoid conflicts between pages
        """
        self.page_prefix = page_prefix
    
    def _get_param_key(self, key: str) -> str:
        """Get the full parameter key with optional page prefix."""
        return f"{self.page_prefix}_{key}" if self.page_prefix else key
    
    def _encode_value(self, value: Any) -> str:
        """
        Encode a value for URL storage.
        
        Args:
            value: Value to encode (supports str, list, date, bool, int, float)
            
        Returns:
            URL-safe encoded string
        """
        if value is None:
            return ""
        
        # Handle different data types
        if isinstance(value, (list, tuple)):
            # For lists, join with comma (works well for simple string lists)
            if all(isinstance(item, str) for item in value):
                return ",".join(value)
            else:
                # For complex lists, use JSON encoding
                json_str = json.dumps(list(value))
                return base64.urlsafe_b64encode(json_str.encode()).decode()
        
        elif isinstance(value, date):
            return value.isoformat()
        
        elif isinstance(value, bool):
            return "true" if value else "false"
        
        elif isinstance(value, (int, float)):
            return str(value)
        
        else:
            # For strings and other types, convert to string
            return str(value)
    
    def _decode_value(self, encoded_value: str, value_type: type) -> Any:
        """
        Decode a value from URL storage.
        
        Args:
            encoded_value: URL-encoded string
            value_type: Expected type of the decoded value
            
        Returns:
            Decoded value
        """
        if not encoded_value:
            return None
        
        try:
            if value_type == list:
                # Try simple comma-separated first
                if "," in encoded_value and not encoded_value.startswith("eyJ"):  # not base64 JSON
                    return encoded_value.split(",")
                else:
                    # Try base64 JSON decoding
                    try:
                        json_str = base64.urlsafe_b64decode(encoded_value.encode()).decode()
                        return json.loads(json_str)
                    except:
                        # Fallback to comma-separated
                        return encoded_value.split(",") if "," in encoded_value else [encoded_value]
            
            elif value_type == date:
                return datetime.fromisoformat(encoded_value).date()
            
            elif value_type == bool:
                return encoded_value.lower() == "true"
            
            elif value_type == int:
                return int(encoded_value)
            
            elif value_type == float:
                return float(encoded_value)
            
            else:
                # String or other types
                return encoded_value
                
        except (ValueError, TypeError, json.JSONDecodeError):
            # Return None for invalid values
            return None
    
    def save_to_url(self, **params) -> None:
        """
        Save parameters to URL query string.
        
        Args:
            **params: Key-value pairs to save to URL
        """
        current_params = dict(st.query_params)
        
        for key, value in params.items():
            param_key = self._get_param_key(key)
            if value is not None:
                current_params[param_key] = self._encode_value(value)
            elif param_key in current_params:
                # Remove parameter if value is None
                del current_params[param_key]
        
        # Update query params (this will update the URL)
        st.query_params.update(current_params)
    
    def load_from_url(self, key: str, default: Any = None, value_type: type = str) -> Any:
        """
        Load a parameter from URL query string.
        
        Args:
            key: Parameter key
            default: Default value if parameter not found
            value_type: Expected type of the parameter
            
        Returns:
            Parameter value or default
        """
        param_key = self._get_param_key(key)
        encoded_value = st.query_params.get(param_key)
        
        if encoded_value is None:
            return default
        
        decoded_value = self._decode_value(encoded_value, value_type)
        return decoded_value if decoded_value is not None else default
    
    def clear_url_params(self, keys: Optional[List[str]] = None) -> None:
        """
        Clear parameters from URL.
        
        Args:
            keys: List of specific keys to clear. If None, clears all parameters with page prefix.
        """
        current_params = dict(st.query_params)
        
        if keys is None:
            # Clear all parameters with page prefix
            if self.page_prefix:
                keys_to_remove = [k for k in current_params.keys() 
                                 if k.startswith(f"{self.page_prefix}_")]
            else:
                keys_to_remove = list(current_params.keys())
        else:
            keys_to_remove = [self._get_param_key(key) for key in keys]
        
        for key in keys_to_remove:
            if key in current_params:
                del current_params[key]
        
        st.query_params.clear()
        st.query_params.update(current_params)


def create_url_state_manager(page_name: str) -> URLStateManager:
    """
    Create a URL state manager for a specific page.
    
    Args:
        page_name: Name of the page (used as prefix)
        
    Returns:
        URLStateManager instance
    """
    return URLStateManager(page_prefix=page_name)


# Convenience functions for common use cases
def save_date_range_to_url(start_date: date, end_date: date, page_name: str = "") -> None:
    """Save date range to URL."""
    manager = URLStateManager(page_name)
    manager.save_to_url(start_date=start_date, end_date=end_date)


def load_date_range_from_url(default_start: date, default_end: date, page_name: str = "") -> tuple:
    """Load date range from URL."""
    manager = URLStateManager(page_name)
    start_date = manager.load_from_url("start_date", default_start, date)
    end_date = manager.load_from_url("end_date", default_end, date)
    return start_date, end_date


def save_location_to_url(location: str, page_name: str = "") -> None:
    """Save location to URL."""
    manager = URLStateManager(page_name)
    manager.save_to_url(location=location)


def load_location_from_url(default_location: str = "", page_name: str = "") -> str:
    """Load location from URL."""
    manager = URLStateManager(page_name)
    return manager.load_from_url("location", default_location, str)


def save_variants_to_url(variants: List[str], page_name: str = "") -> None:
    """Save variant list to URL."""
    manager = URLStateManager(page_name)
    manager.save_to_url(variants=variants)


def load_variants_from_url(default_variants: List[str] = None, page_name: str = "") -> List[str]:
    """Load variant list from URL."""
    manager = URLStateManager(page_name)
    return manager.load_from_url("variants", default_variants or [], list)


def save_frequency_thresholds_to_url(min_freq: float, max_freq: float, page_name: str = "") -> None:
    """Save frequency thresholds to URL."""
    manager = URLStateManager(page_name)
    manager.save_to_url(min_frequency=min_freq, max_frequency=max_freq)


def load_frequency_thresholds_from_url(default_min: float = 0.01, default_max: float = 1.0, page_name: str = "") -> tuple:
    """Load frequency thresholds from URL."""
    manager = URLStateManager(page_name)
    min_freq = manager.load_from_url("min_frequency", default_min, float)
    max_freq = manager.load_from_url("max_frequency", default_max, float)
    return min_freq, max_freq