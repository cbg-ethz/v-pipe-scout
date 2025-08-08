"""System information utilities."""

import os
from typing import Dict, Optional
import datetime


def get_version_info() -> Dict[str, Optional[str]]:
    """
    Get version information from version.py file.
    
    Returns:
        Dictionary with version information
    """
    version_info = {
        'version': '0.2.0-unknown',
        'build_date': None,
        'source': 'fallback'
    }
    
    # Try to read version from version.py
    try:
        from version import VERSION, BUILD_DATE
        version_info.update({
            'version': VERSION,
            'build_date': BUILD_DATE,
            'source': 'static'
        })
    except ImportError:
        # Fallback if version.py doesn't exist
        pass
    
    return version_info


def get_system_info() -> Dict[str, str]:
    """
    Get system information for debugging.
    
    Returns:
        Dictionary with system information
    """
    system_info = {
        'python_version': None,
        'current_time': datetime.datetime.now().isoformat(),
    }
    
    try:
        import sys
        system_info['python_version'] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    except Exception:
        pass
    
    return system_info
