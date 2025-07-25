"""Simple tests for core functionality."""

import unittest
from unittest.mock import Mock, patch
import requests


class TestSystemInfo(unittest.TestCase):
    """Test basic system info functionality."""

    def test_git_info_import(self):
        """Test that git info can be imported and called."""
        from utils.system_info import get_git_info
        
        git_info = get_git_info()
        
        # Should return a dict with expected keys
        expected_keys = ['commit_hash', 'commit_short', 'tag', 'branch', 'commit_date', 'commit_message', 'is_dirty']
        for key in expected_keys:
            self.assertIn(key, git_info)

    def test_system_info_import(self):
        """Test that system info can be imported and called."""
        from utils.system_info import get_system_info
        
        system_info = get_system_info()
        
        # Should return a dict with expected keys
        expected_keys = ['python_version', 'current_time', 'working_directory']
        for key in expected_keys:
            self.assertIn(key, system_info)


class TestHealthCheck(unittest.TestCase):
    """Simple health check tests."""

    def test_health_check_import(self):
        """Test that health check components can be imported."""
        from api.health_check import ApiHealthChecker, HealthStatus, ApiHealthResult
        
        # Should be able to create instances
        checker = ApiHealthChecker(timeout_seconds=1.0)
        self.assertIsNotNone(checker)
        
        # Test enum values
        self.assertEqual(HealthStatus.HEALTHY.value, 'healthy')
        self.assertEqual(HealthStatus.CRITICAL.value, 'critical')

    def test_covspectrum_health_basic(self):
        """Test basic CovSpectrum health check structure."""
        from api.health_check import ApiHealthChecker, HealthStatus
        
        checker = ApiHealthChecker(timeout_seconds=1.0)
        
        # Mock a successful response
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": []}
            mock_get.return_value = mock_response
            
            with patch('time.time', return_value=0.1):  # Fixed response time
                result = checker.check_covspectrum_health("https://test.example.com")
                
            self.assertEqual(result.status, HealthStatus.HEALTHY)
            self.assertTrue(result.is_healthy)
            self.assertIsNotNone(result.response_time_ms)


if __name__ == '__main__':
    unittest.main()
