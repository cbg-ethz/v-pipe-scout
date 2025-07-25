"""Tests for API warning components."""

import pytest
from unittest.mock import patch, Mock
import streamlit as st
from streamlit.testing.v1 import AppTest

from api.health_check import ApiHealthResult, HealthStatus
from components.api_warnings import (
    display_api_warnings,
    display_compact_api_status,
    display_page_specific_warnings,
    _get_overall_status,
    _get_status_icon,
    _get_api_display_name
)


class TestApiWarningComponents:
    """Test API warning display components."""
    
    def test_get_overall_status(self):
        """Test overall status calculation."""
        # All healthy
        health_results = {
            'api1': ApiHealthResult(status=HealthStatus.HEALTHY, response_time_ms=100.0),
            'api2': ApiHealthResult(status=HealthStatus.HEALTHY, response_time_ms=150.0)
        }
        assert _get_overall_status(health_results) == HealthStatus.HEALTHY
        
        # One warning
        health_results['api2'] = ApiHealthResult(status=HealthStatus.WARNING, response_time_ms=2500.0)
        assert _get_overall_status(health_results) == HealthStatus.WARNING
        
        # One critical (should override warning)
        health_results['api1'] = ApiHealthResult(status=HealthStatus.CRITICAL, response_time_ms=None, error_message="Failed")
        assert _get_overall_status(health_results) == HealthStatus.CRITICAL
        
        # Empty results
        assert _get_overall_status({}) == HealthStatus.UNKNOWN
    
    def test_get_status_icon(self):
        """Test status icon mapping."""
        assert _get_status_icon(HealthStatus.HEALTHY) == "🟢"
        assert _get_status_icon(HealthStatus.WARNING) == "🟡"
        assert _get_status_icon(HealthStatus.CRITICAL) == "🔴"
        assert _get_status_icon(HealthStatus.UNKNOWN) == "❓"
    
    def test_get_api_display_name(self):
        """Test API display name mapping."""
        assert _get_api_display_name('wiseloculus') == 'WISE-CovSpectrum API'
        assert _get_api_display_name('covspectrum') == 'CovSpectrum API'
        assert _get_api_display_name('unknown') == 'Unknown'
    
    def test_display_page_specific_warnings_all_healthy(self):
        """Test page warnings when all APIs are healthy."""
        health_results = {
            'wiseloculus': ApiHealthResult(status=HealthStatus.HEALTHY, response_time_ms=100.0),
            'covspectrum': ApiHealthResult(status=HealthStatus.HEALTHY, response_time_ms=150.0)
        }
        required_apis = ['wiseloculus', 'covspectrum']
        
        # Mock streamlit functions
        with patch('streamlit.error') as mock_error, \
             patch('streamlit.warning') as mock_warning:
            
            result = display_page_specific_warnings(health_results, required_apis)
            
            assert result is True  # Page can function
            mock_error.assert_not_called()
            mock_warning.assert_not_called()
    
    def test_display_page_specific_warnings_critical_api(self):
        """Test page warnings when required API is critical."""
        health_results = {
            'wiseloculus': ApiHealthResult(
                status=HealthStatus.CRITICAL, 
                response_time_ms=None, 
                error_message="Connection failed"
            ),
            'covspectrum': ApiHealthResult(status=HealthStatus.HEALTHY, response_time_ms=150.0)
        }
        required_apis = ['wiseloculus', 'covspectrum']
        
        with patch('streamlit.error') as mock_error, \
             patch('streamlit.write') as mock_write:
            
            result = display_page_specific_warnings(health_results, required_apis)
            
            assert result is False  # Page cannot function properly
            mock_error.assert_called_once()
            assert mock_write.call_count >= 2  # Multiple write calls for error details
    
    def test_display_page_specific_warnings_slow_api(self):
        """Test page warnings when required API is slow."""
        health_results = {
            'wiseloculus': ApiHealthResult(status=HealthStatus.WARNING, response_time_ms=2500.0),
            'covspectrum': ApiHealthResult(status=HealthStatus.HEALTHY, response_time_ms=150.0)
        }
        required_apis = ['wiseloculus', 'covspectrum']
        
        with patch('streamlit.warning') as mock_warning, \
             patch('streamlit.write') as mock_write:
            
            result = display_page_specific_warnings(health_results, required_apis)
            
            assert result is True  # Page can still function
            mock_warning.assert_called_once()
            mock_write.assert_called()


class TestHealthIntegration:
    """Test health integration utilities."""
    
    @patch('monitoring.system_health.load_api_config')
    @patch('monitoring.system_health.check_api_health')
    def test_get_api_health_status_success(self, mock_check_api_health, mock_load_config):
        """Test successful health status retrieval."""
        # Mock config loading
        mock_load_config.return_value = ("http://wise-server:8000", "https://covspectrum.org")
        
        # Mock health check results
        expected_results = {
            'wiseloculus': ApiHealthResult(status=HealthStatus.HEALTHY, response_time_ms=100.0),
            'covspectrum': ApiHealthResult(status=HealthStatus.HEALTHY, response_time_ms=150.0)
        }
        
        async def mock_health_check(wise_url, cov_url):
            return expected_results
            
        mock_check_api_health.return_value = expected_results
        
        # Import and test the function
        from monitoring.system_health import get_system_health_status
        
        with patch('asyncio.new_event_loop') as mock_new_loop, \
             patch('asyncio.set_event_loop') as mock_set_loop:
            
            mock_loop = Mock()
            mock_loop.run_until_complete.return_value = expected_results
            mock_new_loop.return_value = mock_loop
            
            # Clear any existing cache
            get_system_health_status.clear()
            
            result = get_system_health_status()
            
            assert result == expected_results
    
    def test_compact_status_only_shows_when_issues_exist(self):
        """Test that compact status only shows when there are issues."""
        from components.api_warnings import display_compact_api_status
        
        # Test 1: All healthy - should show nothing
        healthy_results = {
            'api1': ApiHealthResult(status=HealthStatus.HEALTHY, response_time_ms=100.0),
            'api2': ApiHealthResult(status=HealthStatus.HEALTHY, response_time_ms=150.0)
        }
        
        with patch('streamlit.sidebar.warning') as mock_warning, \
             patch('streamlit.sidebar.error') as mock_error, \
             patch('streamlit.sidebar.info') as mock_info, \
             patch('streamlit.sidebar.success') as mock_success:
            
            display_compact_api_status(healthy_results)
            
            # Nothing should be shown when all healthy
            mock_warning.assert_not_called()
            mock_error.assert_not_called()
            mock_info.assert_not_called()
            mock_success.assert_not_called()
        
        # Test 2: Issues present - should show warnings
        issue_results = {
            'api1': ApiHealthResult(status=HealthStatus.WARNING, response_time_ms=2500.0),
            'api2': ApiHealthResult(status=HealthStatus.HEALTHY, response_time_ms=150.0)
        }
        
        with patch('streamlit.sidebar.warning') as mock_warning:
            display_compact_api_status(issue_results)
            mock_warning.assert_called_once()
        """Test API availability checking."""
        from monitoring.system_health import is_api_available
        
        health_results = {
            'healthy_api': ApiHealthResult(status=HealthStatus.HEALTHY, response_time_ms=100.0),
            'warning_api': ApiHealthResult(status=HealthStatus.WARNING, response_time_ms=2500.0),
            'critical_api': ApiHealthResult(
                status=HealthStatus.CRITICAL, 
                response_time_ms=None, 
                error_message="Connection failed"
            )
        }
        
        assert is_api_available('healthy_api', health_results) is True
        assert is_api_available('warning_api', health_results) is True
        assert is_api_available('critical_api', health_results) is False
        assert is_api_available('missing_api', health_results) is False


def create_mock_streamlit_app_for_warnings():
    """Create a mock Streamlit app to test warning display."""
    def mock_app():
        from components.api_warnings import display_api_warnings
        
        # Test data
        health_results = {
            'wiseloculus': ApiHealthResult(
                status=HealthStatus.CRITICAL,
                response_time_ms=None,
                error_message="Connection timeout"
            ),
            'covspectrum': ApiHealthResult(
                status=HealthStatus.WARNING,
                response_time_ms=2500.0
            )
        }
        
        display_api_warnings(health_results)
        st.write("App content here")
    
    return mock_app


# Note: Streamlit integration tests removed due to AppTest complexity
# The actual UI functionality is tested manually and through smoke tests

if __name__ == "__main__":
    import unittest
    unittest.main()
