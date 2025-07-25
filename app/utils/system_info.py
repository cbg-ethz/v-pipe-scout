"""System information utilities."""

import subprocess
import os
from typing import Dict, Optional
import datetime


def get_version_info() -> Dict[str, Optional[str]]:
    """
    Get version information with fallback strategy:
    1. Try git information (development)
    2. Try build-time version info (Docker)
    3. Fall back to static version (default)
    
    Returns:
        Dictionary with version information
    """
    version_info = {
        'version': '1.0.0-unknown',
        'commit_hash': None,
        'commit_short': None,
        'tag': None,
        'build_date': None,
        'commit_date': None,
        'commit_message': None,
        'is_dirty': False,
        'source': 'fallback'
    }
    
    # Try build-time version info first (Docker production)
    try:
        from version import VERSION, BUILD_DATE, BUILD_COMMIT, BUILD_TAG
        if BUILD_COMMIT and BUILD_COMMIT != "unknown":
            version_info.update({
                'version': BUILD_TAG if BUILD_TAG else VERSION,
                'commit_hash': BUILD_COMMIT,
                'commit_short': BUILD_COMMIT[:8] if BUILD_COMMIT else None,
                'tag': BUILD_TAG if BUILD_TAG else None,
                'build_date': BUILD_DATE,
                'source': 'build'
            })
            return version_info
        elif VERSION:
            version_info.update({
                'version': VERSION,
                'build_date': BUILD_DATE,
                'source': 'static'
            })
    except ImportError:
        pass
    
    # Try git information (development environment)
    git_info = get_git_info()
    if git_info['commit_hash']:
        version_info.update(git_info)
        version_info['source'] = 'git'
        # Generate version from git info
        if git_info['tag']:
            version_info['version'] = git_info['tag']
        else:
            version_info['version'] = f"dev-{git_info['commit_short']}"
        return version_info
    
    return version_info


def get_git_info() -> Dict[str, Optional[str]]:
    """
    Get current git commit and tag information.
    
    Returns:
        Dictionary with git information including commit hash, tag, branch, and timestamp
    """
    git_info = {
        'commit_hash': None,
        'commit_short': None,
        'tag': None,
        'branch': None,
        'commit_date': None,
        'commit_message': None,
        'is_dirty': False
    }
    
    try:
        # Get current directory (should be in app/ folder)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.join(current_dir, '..', '..')
        
        # Get commit hash
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            git_info['commit_hash'] = result.stdout.strip()
            git_info['commit_short'] = result.stdout.strip()[:8]
        
        # Get current branch
        result = subprocess.run(
            ['git', 'branch', '--show-current'],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            git_info['branch'] = result.stdout.strip()
        
        # Get latest tag
        result = subprocess.run(
            ['git', 'describe', '--tags', '--abbrev=0'],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            git_info['tag'] = result.stdout.strip()
        
        # Get commit date
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%ci'],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            git_info['commit_date'] = result.stdout.strip()
        
        # Get commit message
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%s'],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            git_info['commit_message'] = result.stdout.strip()
        
        # Check if working directory is dirty
        result = subprocess.run(
            ['git', 'diff', '--quiet'],
            cwd=repo_root,
            capture_output=True,
            timeout=5
        )
        git_info['is_dirty'] = result.returncode != 0
        
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        # Git not available or timeout
        pass
    
    return git_info


def get_system_info() -> Dict[str, str]:
    """
    Get system information for debugging.
    
    Returns:
        Dictionary with system information
    """
    system_info = {
        'python_version': None,
        'current_time': datetime.datetime.now().isoformat(),
        'working_directory': os.getcwd(),
    }
    
    try:
        import sys
        system_info['python_version'] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    except Exception:
        pass
    
    return system_info
