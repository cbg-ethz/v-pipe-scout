"""Global pytest configuration."""

import os
import pytest


def pytest_collection_modifyitems(config, items):
    """Automatically skip tests marked with 'skip_in_ci' when running in CI environments."""
    # Check if we're running in a CI environment
    ci_environments = [
        'CI',           # Generic CI environment variable
        'GITHUB_ACTIONS',  # GitHub Actions
        'TRAVIS',       # Travis CI
        'JENKINS_URL',  # Jenkins
        'CIRCLECI',     # CircleCI
        'GITLAB_CI',    # GitLab CI
    ]
    
    is_ci = any(os.getenv(env_var) for env_var in ci_environments)
    
    if is_ci:
        skip_ci_marker = pytest.mark.skip(reason="Skipped in CI environment (live API test)")
        for item in items:
            if "skip_in_ci" in item.keywords:
                item.add_marker(skip_ci_marker)