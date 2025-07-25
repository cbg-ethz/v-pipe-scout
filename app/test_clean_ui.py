"""Test script to verify clean UI when APIs are healthy."""

import streamlit as st
from unittest.mock import patch
from api.health_check import ApiHealthResult, HealthStatus
from utils.system_health import display_global_system_status

def test_clean_ui():
    st.title("Clean UI Test")
    st.write("This page tests that API status only appears when there are issues.")
    
    # Mock healthy API results
    healthy_results = {
        'wiseloculus': ApiHealthResult(status=HealthStatus.HEALTHY, response_time_ms=100.0),
        'covspectrum': ApiHealthResult(status=HealthStatus.HEALTHY, response_time_ms=150.0)
    }
    
    # Patch the health status to return healthy results
    with patch('utils.system_health.get_system_health_status') as mock_health:
        mock_health.return_value = healthy_results
        
        st.write("✅ All APIs are healthy - sidebar should be clean (no API status section)")
        
        # This should not add anything to the sidebar when APIs are healthy
        display_global_system_status()
    
    st.write("If you don't see an 'API Status' section in the sidebar, the clean UI is working correctly!")

if __name__ == "__main__":
    test_clean_ui()
