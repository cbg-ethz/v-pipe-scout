"""System health monitoring and integration for Streamlit pages."""

import streamlit as st
import asyncio
import yaml
import pathlib
from typing import Dict, Optional, Tuple, List
from api.health_check import check_api_health, get_cached_health_status, ApiHealthResult, HealthStatus
from components.api_warnings import display_api_warnings, display_compact_api_status


def load_api_config() -> Tuple[str, str]:
    """
    Load API configuration from config.yaml.
    
    Returns:
        Tuple of (wise_url, covspectrum_url)
    """
    try:
        # Handle different possible working directories
        config_paths = [
            pathlib.Path("config.yaml"),
            pathlib.Path("app/config.yaml"),
            pathlib.Path(__file__).parent.parent / "config.yaml"
        ]
        
        config = None
        for config_path in config_paths:
            if config_path.exists():
                with open(config_path, 'r') as file:
                    config = yaml.safe_load(file)
                break
        
        if config is None:
            st.error("Could not find config.yaml file")
            return "http://default_ip:8000", "https://lapis.cov-spectrum.org"
        
        wise_url = config.get('server', {}).get('lapis_address', 'http://default_ip:8000')
        covspectrum_url = config.get('server', {}).get('cov_spectrum_api', 'https://lapis.cov-spectrum.org')
        
        return wise_url, covspectrum_url
        
    except Exception as e:
        st.error(f"Error loading configuration: {e}")
        return "http://default_ip:8000", "https://lapis.cov-spectrum.org"


@st.cache_data(ttl=30)  # Cache for 30 seconds
def get_system_health_status() -> Dict[str, ApiHealthResult]:
    """
    Get current API health status with caching.
    
    Returns:
        Dictionary with API health results
    """
    wise_url, covspectrum_url = load_api_config()
    
    # First check if we have recent cached results
    cached_results = get_cached_health_status(wise_url, covspectrum_url)
    
    # If we have all cached results, return them
    if all(result is not None for result in cached_results.values()):
        return {k: v for k, v in cached_results.items() if v is not None}
    
    # Otherwise, perform health checks
    try:
        # Run async health check
        try:
            # Check if an event loop is already running
            loop = asyncio.get_running_loop()
            # If running, use asyncio.run_coroutine_threadsafe
            future = asyncio.run_coroutine_threadsafe(
                check_api_health(wise_url, covspectrum_url), loop
            )
            health_results = future.result()
        except RuntimeError:
            # If no event loop is running, use asyncio.run
            health_results = asyncio.run(check_api_health(wise_url, covspectrum_url))
        return health_results
    except Exception as e:
        st.error(f"Error checking API health: {e}")
        # Return dummy results indicating unknown status
        from api.health_check import ApiHealthResult, HealthStatus
        return {
            'wiseloculus': ApiHealthResult(
                status=HealthStatus.UNKNOWN,
                response_time_ms=None,
                error_message=f"Health check failed: {str(e)}"
            ),
            'covspectrum': ApiHealthResult(
                status=HealthStatus.UNKNOWN,
                response_time_ms=None,
                error_message=f"Health check failed: {str(e)}"
            )
        }


def setup_page_health_monitoring(page_title: str, required_apis: Optional[List[str]] = None, show_sidebar_status: bool = True) -> Tuple[bool, Dict[str, ApiHealthResult]]:
    """
    Setup a page with API health monitoring and warnings.
    
    Args:
        page_title: Title of the page (used for error messages)
        required_apis: List of API names required for this page ['wiseloculus', 'covspectrum']
        show_sidebar_status: Whether to show compact status in sidebar
        
    Returns:
        Tuple of (page_can_function, health_results)
    """
    if required_apis is None:
        required_apis = ['wiseloculus', 'covspectrum']
    
    # Get health status
    health_results = get_system_health_status()
    
    # Show sidebar status if requested
    if show_sidebar_status:
        display_compact_api_status(health_results)
    
    # Display main warnings
    display_api_warnings(health_results)
    
    # Check if page can function with current API status
    from components.api_warnings import display_page_specific_warnings
    page_can_function = display_page_specific_warnings(health_results, required_apis)
    
    return page_can_function, health_results


def refresh_health_status():
    """Force refresh of health status by clearing cache."""
    # Clear the Streamlit cache for health status
    get_system_health_status.clear()
    
    # Also clear the internal health checker cache
    from api.health_check import _health_checker
    _health_checker._cache.clear()


def initialize_health_monitoring():
    """Initialize session state variables for health monitoring."""
    if 'health_monitoring_enabled' not in st.session_state:
        st.session_state.health_monitoring_enabled = True
    
    if 'last_health_check' not in st.session_state:
        st.session_state.last_health_check = None
    
    if 'health_warnings_dismissed' not in st.session_state:
        st.session_state.health_warnings_dismissed = set()


def is_api_available(api_name: str, health_results: Dict[str, ApiHealthResult]) -> bool:
    """
    Check if a specific API is available (healthy or warning status).
    
    Args:
        api_name: Name of the API to check
        health_results: Dictionary with API health results
        
    Returns:
        bool: True if API is available for use
    """
    if api_name not in health_results:
        return False
    
    return health_results[api_name].is_available


def show_system_status_debug() -> None:
    """Show debug information about system status (for development)."""
    # Add separator for debug section
    st.sidebar.markdown("---")
    
    if st.sidebar.checkbox("Show System Debug Info", key="system_debug"):
        health_results = get_system_health_status()
        
        st.sidebar.write("**Current System Health Status:**")
        for api_name, result in health_results.items():
            with st.sidebar.expander(f"Debug: {api_name}"):
                st.json({
                    'status': result.status.value,
                    'response_time_ms': result.response_time_ms,
                    'error_message': result.error_message,
                    'last_checked': result.last_checked,
                    'status_code': result.status_code,
                    'is_healthy': result.is_healthy,
                    'is_available': result.is_available
                })
        
        if st.sidebar.button("Force Refresh Health Status"):
            refresh_health_status()
            st.rerun()


def display_global_system_status() -> None:
    """Display global system status in sidebar only when there are issues."""
    try:
        health_results = get_system_health_status()
        
        # Check if there are any issues before showing anything
        overall_status = _get_overall_status(health_results)
        
        if overall_status != HealthStatus.HEALTHY:
            # Only show the API Status section when there are problems
            st.sidebar.markdown("---")
            st.sidebar.markdown("**API Status**")
            display_compact_api_status(health_results)
            
    except Exception as e:
        # Always show errors
        st.sidebar.markdown("---")
        st.sidebar.markdown("**API Status**")
        st.sidebar.error(f"Health check failed: {str(e)}")


def _get_overall_status(health_results: Dict[str, ApiHealthResult]) -> HealthStatus:
    """Determine overall system status."""
    if not health_results:
        return HealthStatus.UNKNOWN
    
    statuses = [result.status for result in health_results.values()]
    
    if HealthStatus.CRITICAL in statuses:
        return HealthStatus.CRITICAL
    elif HealthStatus.WARNING in statuses:
        return HealthStatus.WARNING
    elif all(status == HealthStatus.HEALTHY for status in statuses):
        return HealthStatus.HEALTHY
    else:
        return HealthStatus.UNKNOWN
