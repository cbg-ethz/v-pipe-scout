"""System information utilities."""

import subprocess
import os
from typing import Dict, Optional
import datetime


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
