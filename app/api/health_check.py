"""API Health Check Module for monitoring API status and availability."""

import asyncio
import aiohttp
import requests
import logging
import time
from enum import Enum
from typing import Dict, Optional, NamedTuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """API Health Status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class ApiHealthResult:
    """Result of an API health check."""
    status: HealthStatus
    response_time_ms: Optional[float]
    error_message: Optional[str] = None
    last_checked: Optional[float] = None
    status_code: Optional[int] = None

    @property
    def is_healthy(self) -> bool:
        """Check if API is healthy."""
        return self.status == HealthStatus.HEALTHY

    @property
    def is_available(self) -> bool:
        """Check if API is available (healthy or warning)."""
        return self.status in [HealthStatus.HEALTHY, HealthStatus.WARNING]


class ApiHealthChecker:
    """Centralized API health checking service."""
    
    def __init__(self, timeout_seconds: float = 5.0, cache_duration_seconds: float = 60.0):
        """
        Initialize the health checker.
        
        Args:
            timeout_seconds: Timeout for health check requests
            cache_duration_seconds: How long to cache health results
        """
        self.timeout = timeout_seconds
        self.cache_duration = cache_duration_seconds
        self._cache: Dict[str, ApiHealthResult] = {}

    def _is_cache_valid(self, result: ApiHealthResult) -> bool:
        """Check if cached result is still valid."""
        if result.last_checked is None:
            return False
        return (time.time() - result.last_checked) < self.cache_duration

    def _get_cached_result(self, api_name: str) -> Optional[ApiHealthResult]:
        """Get cached result if valid."""
        if api_name in self._cache:
            result = self._cache[api_name]
            if self._is_cache_valid(result):
                return result
        return None

    def _cache_result(self, api_name: str, result: ApiHealthResult) -> None:
        """Cache health check result."""
        result.last_checked = time.time()
        self._cache[api_name] = result

    async def check_wiseloculus_health(self, server_url: str) -> ApiHealthResult:
        """
        Check WiseLoculus API health.
        
        Args:
            server_url: The WiseLoculus server URL
            
        Returns:
            ApiHealthResult with status and details
        """
        api_name = f"wiseloculus_{server_url}"
        
        # Check cache first
        cached = self._get_cached_result(api_name)
        if cached:
            return cached

        start_time = time.time()
        
        try:
            # Use a simple endpoint that should always be available
            health_endpoint = f"{server_url.rstrip('/')}/sample/aggregated"
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                # Simple health check with minimal payload
                payload = {
                    "fields": ["location_name"],
                    "limit": 1,
                    "orderBy": "location_name",
                    "dataFormat": "JSON"
                }
                
                async with session.get(health_endpoint, params=payload) as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        # Check if we get valid JSON response
                        try:
                            data = await response.json()
                            if isinstance(data, dict) and 'data' in data:
                                status = HealthStatus.HEALTHY if response_time < 2000 else HealthStatus.WARNING
                                result = ApiHealthResult(
                                    status=status,
                                    response_time_ms=response_time,
                                    status_code=response.status
                                )
                            else:
                                result = ApiHealthResult(
                                    status=HealthStatus.WARNING,
                                    response_time_ms=response_time,
                                    error_message="Invalid response format",
                                    status_code=response.status
                                )
                        except Exception as e:
                            result = ApiHealthResult(
                                status=HealthStatus.WARNING,
                                response_time_ms=response_time,
                                error_message=f"JSON parsing error: {str(e)}",
                                status_code=response.status
                            )
                    else:
                        result = ApiHealthResult(
                            status=HealthStatus.CRITICAL,
                            response_time_ms=response_time,
                            error_message=f"HTTP {response.status}: {await response.text()}",
                            status_code=response.status
                        )
                        
        except asyncio.TimeoutError:
            result = ApiHealthResult(
                status=HealthStatus.CRITICAL,
                response_time_ms=None,
                error_message=f"Timeout after {self.timeout}s"
            )
        except Exception as e:
            result = ApiHealthResult(
                status=HealthStatus.CRITICAL,
                response_time_ms=None,
                error_message=f"Connection error: {str(e)}"
            )

        self._cache_result(api_name, result)
        return result

    def check_covspectrum_health(self, server_url: str) -> ApiHealthResult:
        """
        Check CovSpectrum API health.
        
        Args:
            server_url: The CovSpectrum server URL
            
        Returns:
            ApiHealthResult with status and details
        """
        api_name = f"covspectrum_{server_url}"
        
        # Check cache first
        cached = self._get_cached_result(api_name)
        if cached:
            return cached

        start_time = time.time()
        
        try:
            # Use a simple endpoint that should always be available
            health_endpoint = f"{server_url.rstrip('/')}/open/v2/sample/nucleotideMutations"
            
            # Simple health check with minimal parameters - use empty query which should be valid
            params = {
                "minProportion": 0.5,
                "limit": 1,
                "downloadAsFile": "false"
            }
            
            response = requests.get(
                health_endpoint,
                params=params,
                timeout=self.timeout,
                headers={'accept': 'application/json'}
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, dict) and 'data' in data:
                        status = HealthStatus.HEALTHY if response_time < 2000 else HealthStatus.WARNING
                        result = ApiHealthResult(
                            status=status,
                            response_time_ms=response_time,
                            status_code=response.status_code
                        )
                    else:
                        result = ApiHealthResult(
                            status=HealthStatus.WARNING,
                            response_time_ms=response_time,
                            error_message="Invalid response format",
                            status_code=response.status_code
                        )
                except Exception as e:
                    result = ApiHealthResult(
                        status=HealthStatus.WARNING,
                        response_time_ms=response_time,
                        error_message=f"JSON parsing error: {str(e)}",
                        status_code=response.status_code
                    )
            else:
                result = ApiHealthResult(
                    status=HealthStatus.CRITICAL,
                    response_time_ms=response_time,
                    error_message=f"HTTP {response.status_code}: {response.text}",
                    status_code=response.status_code
                )
                
        except requests.exceptions.Timeout:
            result = ApiHealthResult(
                status=HealthStatus.CRITICAL,
                response_time_ms=None,
                error_message=f"Timeout after {self.timeout}s"
            )
        except Exception as e:
            result = ApiHealthResult(
                status=HealthStatus.CRITICAL,
                response_time_ms=None,
                error_message=f"Connection error: {str(e)}"
            )

        self._cache_result(api_name, result)
        return result

    async def check_all_apis_health(self, wise_url: str, covspectrum_url: str) -> Dict[str, ApiHealthResult]:
        """
        Check health of all APIs concurrently.
        
        Args:
            wise_url: WiseLoculus server URL
            covspectrum_url: CovSpectrum server URL
            
        Returns:
            Dictionary with API names as keys and health results as values
        """
        # Check WiseLoculus asynchronously
        wise_task = self.check_wiseloculus_health(wise_url)
        
        # Check CovSpectrum synchronously (in executor to avoid blocking)
        loop = asyncio.get_event_loop()
        covspectrum_task = loop.run_in_executor(None, self.check_covspectrum_health, covspectrum_url)
        
        # Wait for both to complete
        wise_result, covspectrum_result = await asyncio.gather(wise_task, covspectrum_task)
        
        return {
            'wiseloculus': wise_result,
            'covspectrum': covspectrum_result
        }


# Global health checker instance
_health_checker = ApiHealthChecker()


async def check_api_health(wise_url: str, covspectrum_url: str) -> Dict[str, ApiHealthResult]:
    """
    Convenience function to check API health.
    
    Args:
        wise_url: WiseLoculus server URL
        covspectrum_url: CovSpectrum server URL
        
    Returns:
        Dictionary with API health results
    """
    return await _health_checker.check_all_apis_health(wise_url, covspectrum_url)


def get_cached_health_status(wise_url: str, covspectrum_url: str) -> Dict[str, Optional[ApiHealthResult]]:
    """
    Get cached health status without making new requests.
    
    Args:
        wise_url: WiseLoculus server URL
        covspectrum_url: CovSpectrum server URL
        
    Returns:
        Dictionary with cached health results (None if not cached or expired)
    """
    wise_cached = _health_checker._get_cached_result(f"wiseloculus_{wise_url}")
    covspectrum_cached = _health_checker._get_cached_result(f"covspectrum_{covspectrum_url}")
    
    return {
        'wiseloculus': wise_cached,
        'covspectrum': covspectrum_cached
    }
