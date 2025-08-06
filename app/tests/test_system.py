"""Simple tests for system functionality."""

import unittest
from unittest.mock import Mock, patch
import requests


class TestSystemInfo(unittest.TestCase):
    """Test system info functionality."""

    def test_version_info_import(self):
        """Test that version info can be imported and called."""
        from utils.system_info import get_version_info
        
        version_info = get_version_info()
        
        # Should return a dict with expected keys
        expected_keys = ['version', 'build_date', 'source']
        for key in expected_keys:
            self.assertIn(key, version_info)
        
        # Version should be a string
        self.assertIsInstance(version_info['version'], str)
        self.assertIn('source', version_info)

    def test_system_info_import(self):
        """Test that system info can be imported and called."""
        from utils.system_info import get_system_info
        
        system_info = get_system_info()
        
        # Should return a dict with expected keys
        expected_keys = ['python_version', 'current_time']
        for key in expected_keys:
            self.assertIn(key, system_info)
        
        # Should have current time as ISO string
        self.assertIsInstance(system_info['current_time'], str)


class TestHealthCheck(unittest.TestCase):
    """Simple health check tests."""

    def test_health_check_import(self):
        """Test that health check components can be imported."""
        from api.health_check import ApiHealthChecker, HealthStatus, ApiHealthResult
        
        # Should be able to create instances
        checker = ApiHealthChecker(timeout_seconds=5.0)
        self.assertIsNotNone(checker)
        
        # Test enum values
        self.assertEqual(HealthStatus.HEALTHY.value, 'healthy')
        self.assertEqual(HealthStatus.CRITICAL.value, 'critical')

    def test_covspectrum_health_basic(self):
        """Test basic CovSpectrum health check structure."""
        from api.health_check import ApiHealthChecker, HealthStatus
        
        checker = ApiHealthChecker(timeout_seconds=5.0)
        
        # Mock a successful response
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": []}
            mock_get.return_value = mock_response
            
            with patch('time.time', side_effect=[0.0, 0.1, 0.2]):  # Start, end, cache time
                result = checker.check_covspectrum_health("https://test.example.com")
                
            self.assertEqual(result.status, HealthStatus.HEALTHY)
            self.assertTrue(result.is_healthy)
            self.assertIsNotNone(result.response_time_ms)


if __name__ == '__main__':
    unittest.main()
