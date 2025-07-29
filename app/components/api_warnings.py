"""API Warning Components for displaying health status warnings in Streamlit."""

import streamlit as st
from typing import Dict, Optional
from api.health_check import ApiHealthResult, HealthStatus


def display_api_warnings(health_results: Dict[str, ApiHealthResult]) -> None:
    """
    Display API health warnings at the top of a page.
    
    Args:
        health_results: Dictionary with API names as keys and health results as values
    """
    # Count issues
    critical_apis = []
    warning_apis = []
    
    for api_name, result in health_results.items():
        if result.status == HealthStatus.CRITICAL:
            critical_apis.append((api_name, result))
        elif result.status == HealthStatus.WARNING:
            warning_apis.append((api_name, result))
    
    # Display critical warnings first
    if critical_apis:
        with st.container():
            st.error("🔴 **API Service Issues Detected**")
            for api_name, result in critical_apis:
                api_display_name = _get_api_display_name(api_name)
                
                with st.expander(f"❌ {api_display_name} - Service Unavailable", expanded=False):
                    st.write(f"**Status:** {result.status.value.title()}")
                    if result.error_message:
                        st.write(f"**Error:** {result.error_message}")
                    if result.response_time_ms:
                        st.write(f"**Response Time:** {result.response_time_ms:.0f}ms")
                    if result.status_code:
                        st.write(f"**HTTP Status:** {result.status_code}")
                    
                    # Provide specific guidance based on API
                    if api_name == 'wiseloculus':
                        st.info("📢 **Impact:** Location data, mutation analysis, and wastewater data features may not work properly.")
                    elif api_name == 'covspectrum':
                        st.info("📢 **Impact:** Variant signature creation and global mutation data may be unavailable.")
    
    # Display warning-level issues
    if warning_apis:
        with st.container():
            st.warning("🟡 **API Performance Issues**")
            for api_name, result in warning_apis:
                api_display_name = _get_api_display_name(api_name)
                
                with st.expander(f"⚠️ {api_display_name} - Slow Response", expanded=False):
                    st.write(f"**Status:** {result.status.value.title()}")
                    if result.response_time_ms:
                        st.write(f"**Response Time:** {result.response_time_ms:.0f}ms (slower than expected)")
                    if result.error_message:
                        st.write(f"**Details:** {result.error_message}")
                    
                    st.info("📢 **Impact:** Features may work but with slower response times.")


def display_compact_api_status(health_results: Dict[str, ApiHealthResult]) -> None:
    """
    Display a compact API status indicator in the sidebar ONLY when there are issues.
    
    Args:
        health_results: Dictionary with API names as keys and health results as values
    """
    overall_status = _get_overall_status(health_results)
    
    # Only show status if there are issues (not healthy)
    if overall_status == HealthStatus.WARNING:
        st.sidebar.warning("🟡 API Performance Issues")
        _show_compact_details(health_results)
    elif overall_status == HealthStatus.CRITICAL:
        st.sidebar.error("🔴 API Service Issues")
        _show_compact_details(health_results)
    elif overall_status == HealthStatus.UNKNOWN:
        st.sidebar.info("❓ API Status Unknown")
        _show_compact_details(health_results)
    # When overall_status == HealthStatus.HEALTHY, show nothing


def _show_compact_details(health_results: Dict[str, ApiHealthResult]) -> None:
    """Show compact details in sidebar only for non-healthy APIs."""
    issues_found = False
    details_content = []
    
    for api_name, result in health_results.items():
        if result.status != HealthStatus.HEALTHY:  # Only show problematic APIs
            api_display_name = _get_api_display_name(api_name)
            status_icon = _get_status_icon(result.status)
            
            details_content.append(f"{status_icon} **{api_display_name}**")
            if result.response_time_ms:
                details_content.append(f"   Response: {result.response_time_ms:.0f}ms")
            if result.error_message and len(result.error_message) < 50:
                details_content.append(f"   Error: {result.error_message}")
            issues_found = True
    
    # Only show expander if there are issues to display
    if issues_found:
        with st.sidebar.expander("API Status Details"):
            for content in details_content:
                st.write(content)


def display_page_specific_warnings(health_results: Dict[str, ApiHealthResult], required_apis: list) -> bool:
    """
    Display warnings specific to page requirements and return if page can function.
    
    Args:
        health_results: Dictionary with API names as keys and health results as values
        required_apis: List of API names required for this page to function
        
    Returns:
        bool: True if page can function with current API status
    """
    unavailable_required = []
    slow_required = []
    
    for api_name in required_apis:
        if api_name in health_results:
            result = health_results[api_name]
            if result.status == HealthStatus.CRITICAL:
                unavailable_required.append(api_name)
            elif result.status == HealthStatus.WARNING:
                slow_required.append(api_name)
    
    if unavailable_required:
        st.error(f"🚫 **Page Functionality Limited**")
        st.write("The following required services are unavailable:")
        for api_name in unavailable_required:
            api_display_name = _get_api_display_name(api_name)
            st.write(f"• {api_display_name}")
        st.write("Some features on this page may not work until these services are restored.")
        return False
    
    if slow_required:
        st.warning("⏳ **Slower Performance Expected**")
        st.write("Some services are responding slowly. Page functionality may be delayed.")
    
    return True


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


def _get_status_icon(status: HealthStatus) -> str:
    """Get icon for status."""
    icons = {
        HealthStatus.HEALTHY: "🟢",
        HealthStatus.WARNING: "🟡", 
        HealthStatus.CRITICAL: "🔴",
        HealthStatus.UNKNOWN: "❓"
    }
    return icons.get(status, "❓")


def _get_api_display_name(api_name: str) -> str:
    """Get user-friendly display name for API."""
    display_names = {
        'wiseloculus': 'WISE-CovSpectrum API',
        'covspectrum': 'CovSpectrum API',
    }
    return display_names.get(api_name, api_name.title())


def show_health_check_info() -> None:
    """Show information about the health check system."""
    with st.expander("ℹ️ About API Health Monitoring"):
        st.write("""
        **V-Pipe Scout** monitors the health of external APIs to ensure optimal functionality:
        
        **🟢 Healthy:** API responding normally (< 2 seconds)
        **🟡 Warning:** API responding slowly (> 2 seconds) or minor issues
        **🔴 Critical:** API unavailable or major errors
        
        **APIs Monitored:**
        - **WISE-CovSpectrum API:** Provides wastewater mutation data and location information
        - **CovSpectrum API:** Provides global variant definitions and mutation signatures
        
        Health status is cached for 60 seconds to avoid excessive API calls.
        """)


def display_retry_button(api_name: str, on_retry_callback=None) -> bool:
    """
    Display a retry button for failed API calls.
    
    Args:
        api_name: Name of the API to retry
        on_retry_callback: Optional callback function to execute on retry
        
    Returns:
        bool: True if retry button was clicked
    """
    api_display_name = _get_api_display_name(api_name)
    
    if st.button(f"🔄 Retry {api_display_name}", key=f"retry_{api_name}"):
        if on_retry_callback:
            on_retry_callback()
        st.rerun()
        return True
    return False
