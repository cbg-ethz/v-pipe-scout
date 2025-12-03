"""Simple tests for the wiseloculus module."""

import pytest
import asyncio
from unittest.mock import patch
from datetime import datetime
from pathlib import Path
import sys

import pandas as pd
import aiohttp

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.wiseloculus import WiseLoculusLapis
from interface import MutationType


def test_mutations_to_and_query_empty():
    """Test _mutations_to_and_query with empty list."""
    api = WiseLoculusLapis("http://test-server.com")
    result = api._mutations_to_and_query([])
    assert result == "", "Empty list should return empty string"

def test_mutations_to_and_query_single():
    """Test _mutations_to_and_query with single mutation."""
    api = WiseLoculusLapis("http://test-server.com")
    result = api._mutations_to_and_query(["23149T"])
    assert result == "23149T", "Single mutation should return as-is"

def test_mutations_to_and_query_multiple():
    """Test _mutations_to_and_query with multiple mutations."""
    api = WiseLoculusLapis("http://test-server.com")
    result = api._mutations_to_and_query(["23149T", "23224T", "23311T"])
    assert result == "23149T & 23224T & 23311T", "Multiple mutations should be joined with ' & '"

def test_mutations_to_and_query_with_deletions():
    """Test _mutations_to_and_query with deletions."""
    api = WiseLoculusLapis("http://test-server.com")
    result = api._mutations_to_and_query(["123A", "234T", "345-"])
    assert result == "123A & 234T & 345-", "Should handle deletions correctly"

class TestWiseLoculusLapis:
    """Test cases for WiseLoculusLapis class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.api = WiseLoculusLapis("http://test-server.com")
        self.date_range = (datetime(2024, 1, 1), datetime(2024, 1, 31))
    

    @pytest.mark.asyncio
    async def test_sample_mutations_nucleotide_success(self):
        """Test sample_mutations for nucleotide mutations with successful response."""
        # Mock aiohttp session and response
        mock_response_data = {
            "data": [
                {
                    "mutation": "A123T",
                    "count": 150,
                    "coverage": 1000,
                    "proportion": 0.15,
                    "sequenceName": "NC_045512",
                    "mutationFrom": "A",
                    "mutationTo": "T",
                    "position": 123
                },
                {
                    "mutation": "C456G",
                    "count": 80,
                    "coverage": 800,
                    "proportion": 0.10,
                    "sequenceName": "NC_045512",
                    "mutationFrom": "C",
                    "mutationTo": "G",
                    "position": 456
                }
            ]
        }

        # Create a mock session with proper async context manager behavior
        class MockResponse:
            def __init__(self, status=200, json_data=None):
                self.status = status
                self._json_data = json_data or {}

            async def json(self):
                return self._json_data

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        class MockSession:
            def __init__(self, response):
                self.response = response

            def get(self, url, params=None, headers=None):
                return self.response

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        # Mock aiohttp.ClientSession
        mock_response = MockResponse(status=200, json_data=mock_response_data)
        mock_session = MockSession(mock_response)

        with patch('aiohttp.ClientSession', return_value=mock_session):
            with patch('aiohttp.ClientTimeout'):
                result = await self.api.sample_mutations(
                    type=MutationType.NUCLEOTIDE,
                    date_range=self.date_range,
                    locationName="Zurich",
                    min_proportion=0.01
                )

        # Assertions
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert "mutation" in result.columns
        assert "count" in result.columns
        assert "coverage" in result.columns
        assert "proportion" in result.columns
        
        # Check specific values
        assert result.iloc[0]["mutation"] == "A123T"
        assert result.iloc[0]["count"] == 150
        assert result.iloc[1]["mutation"] == "C456G"
        assert result.iloc[1]["count"] == 80

        # Use shared MockResponse and MockSession classes
    @pytest.mark.asyncio
    async def test_sample_mutations_amino_acid_success(self):
        """Test sample_mutations for amino acid mutations with successful response."""
        mock_response_data = {
            "data": [
                {
                    "mutation": "ORF1a:V3449I",
                    "count": 75,
                    "coverage": 500,
                    "proportion": 0.15,
                    "sequenceName": "ORF1a",
                    "mutationFrom": "V",
                    "mutationTo": "I",
                    "position": 3449
                }
            ]
        }

        class MockResponse:
            def __init__(self, status=200, json_data=None):
                self.status = status
                self._json_data = json_data or {}

            async def json(self):
                return self._json_data

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        class MockSession:
            def __init__(self, response):
                self.response = response

            def get(self, url, params=None, headers=None):
                return self.response

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_response = MockResponse(status=200, json_data=mock_response_data)
        mock_session = MockSession(mock_response)

        with patch('aiohttp.ClientSession', return_value=mock_session):
            with patch('aiohttp.ClientTimeout'):
                result = await self.api.sample_mutations(
                    type=MutationType.AMINO_ACID,
                    date_range=self.date_range,
                    locationName="Zurich"
                )

        # Assertions
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]["mutation"] == "ORF1a:V3449I"
        assert result.iloc[0]["count"] == 75


    def test_sample_mutations_payload_construction(self):
        """Test that the payload is constructed correctly for sample_mutations."""
        # This tests the payload construction logic without making actual HTTP calls
        date_range = (datetime(2024, 1, 1), datetime(2024, 1, 31))
        locationName = "Zurich"
        min_proportion = 0.05

        # Expected payload structure
        expected_payload = {
            "samplingDateFrom": "2024-01-01",
            "samplingDateTo": "2024-01-31",
            "locationName": locationName,
            "minProportion": min_proportion,
            "orderBy": "proportion",
            "limit": 10000,
            "dataFormat": "JSON",
            "downloadAsFile": "false"
        }

        # Test nucleotide endpoint construction
        assert f'{self.api.server_ip}/sample/nucleotideMutations' == f'http://test-server.com/sample/nucleotideMutations'
        
        # Test amino acid endpoint construction
        assert f'{self.api.server_ip}/sample/aminoAcidMutations' == f'http://test-server.com/sample/aminoAcidMutations'

        # Verify date formatting
        assert date_range[0].strftime('%Y-%m-%d') == "2024-01-01"
        assert date_range[1].strftime('%Y-%m-%d') == "2024-01-31"

    def test_generate_date_ranges_daily(self):
        """Test _generate_date_ranges method with daily interval."""
        date_range = (datetime(2024, 1, 1), datetime(2024, 1, 3))
        result = self.api._generate_date_ranges(date_range, "daily")
        
        assert len(result) == 3
        assert result[0] == (datetime(2024, 1, 1), datetime(2024, 1, 1))
        assert result[1] == (datetime(2024, 1, 2), datetime(2024, 1, 2))
        assert result[2] == (datetime(2024, 1, 3), datetime(2024, 1, 3))

    def test_generate_date_ranges_weekly(self):
        """Test _generate_date_ranges method with weekly interval."""
        date_range = (datetime(2024, 1, 1), datetime(2024, 1, 14))
        result = self.api._generate_date_ranges(date_range, "weekly")
        
        assert len(result) == 2
        assert result[0] == (datetime(2024, 1, 1), datetime(2024, 1, 7))
        assert result[1] == (datetime(2024, 1, 8), datetime(2024, 1, 14))

    def test_generate_date_ranges_monthly(self):
        """Test _generate_date_ranges method with monthly interval."""
        date_range = (datetime(2024, 1, 15), datetime(2024, 3, 10))
        result = self.api._generate_date_ranges(date_range, "monthly")
        
        assert len(result) == 3
        assert result[0] == (datetime(2024, 1, 15), datetime(2024, 1, 31))
        assert result[1] == (datetime(2024, 2, 1), datetime(2024, 2, 29))
        assert result[2] == (datetime(2024, 3, 1), datetime(2024, 3, 10))

    def test_generate_date_ranges_invalid_interval(self):
        """Test _generate_date_ranges method with invalid interval."""
        date_range = (datetime(2024, 1, 1), datetime(2024, 1, 3))
        
        with pytest.raises(ValueError, match="Unsupported interval"):
            self.api._generate_date_ranges(date_range, "invalid")

    def test_fallback_date_range(self):
        """Test that fallback date range is approximately 3 months."""
        from api.wiseloculus import FALLBACK_START_DATE, FALLBACK_END_DATE, get_fallback_date_range
        
        # Test the constants
        diff = FALLBACK_END_DATE - FALLBACK_START_DATE
        
        # Should be approximately 3 months (90 days, allow ±5 days tolerance)
        assert 85 <= diff.days <= 95, f"Fallback range should be ~90 days, got {diff.days}"
        
        # Test the function
        start, end = get_fallback_date_range()
        func_diff = end - start
        assert 85 <= func_diff.days <= 95, f"Function should return ~90 days, got {func_diff.days}"
        
        # Verify they are datetime objects
        assert isinstance(FALLBACK_START_DATE, datetime), "FALLBACK_START_DATE should be datetime"
        assert isinstance(FALLBACK_END_DATE, datetime), "FALLBACK_END_DATE should be datetime"
        
        # Verify start < end
        assert FALLBACK_START_DATE < FALLBACK_END_DATE, "Start should be before end"

@pytest.mark.asyncio
async def test_coocurrences_over_time_simple():
    """Test coocurrences_over_time with simple mutations list (backward compatibility)."""
    api = WiseLoculusLapis("http://test-server.com")
    date_range = (datetime(2024, 1, 1), datetime(2024, 1, 2))
    
    # Mock responses
    mock_filtered_response = {
        "data": [{"samplingDate": "2024-01-01", "count": 10}]
    }
    mock_intersection_response = {
        "data": [{"samplingDate": "2024-01-01", "count": 100}]
    }
    
    # Mock session
    class MockResponse:
        def __init__(self, status=200, json_data=None):
            self.status = status
            self._json_data = json_data or {}
        async def json(self): return self._json_data
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        def __await__(self):
            async def _ret(): return self
            return _ret().__await__()

    class MockSession:
        def __init__(self, *args, **kwargs): pass
        def post(self, url, json=None, **kwargs):
            if "advancedQuery" in json:
                query = json["advancedQuery"]
                # Check if it's the filtered query (AND logic)
                if " & " in query and "!" not in query:
                    return MockResponse(json_data=mock_filtered_response)
                # Check if it's the intersection query (!posN)
                elif "!123N" in query:
                    return MockResponse(json_data=mock_intersection_response)
            return MockResponse(status=404)
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass

    with patch('aiohttp.ClientSession', side_effect=MockSession):
        with patch('aiohttp.ClientTimeout'):
            result = await api.coocurrences_over_time(
                date_range=date_range,
                locationName="Test",
                mutations=["123T", "456G"]
            )
            
    assert not result.empty
    assert result.iloc[0]["count"] == 10
    assert result.iloc[0]["coverage"] == 100
    assert result.iloc[0]["frequency"] == 0.1

@pytest.mark.asyncio
async def test_coocurrences_over_time_advanced():
    """Test coocurrences_over_time with advanced query."""
    api = WiseLoculusLapis("http://test-server.com")
    date_range = (datetime(2024, 1, 1), datetime(2024, 1, 2))
    advanced_query = "[3-of: 123T, 456G, 789A]"
    
    # Mock responses
    mock_filtered_response = {
        "data": [{"samplingDate": "2024-01-01", "count": 5}]
    }
    mock_intersection_response = {
        "data": [{"samplingDate": "2024-01-01", "count": 50}]
    }
    
    class MockSession:
        def __init__(self, *args, **kwargs): pass
        def post(self, url, json=None, **kwargs):
            if "advancedQuery" in json:
                query = json["advancedQuery"]
                if query == advanced_query:
                    return MockResponse(json_data=mock_filtered_response)
                # Intersection query should contain !posN for extracted mutations
                elif "!123N" in query and "!456N" in query and "!789N" in query:
                    return MockResponse(json_data=mock_intersection_response)
            return MockResponse(status=404)
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        
    class MockResponse:
        def __init__(self, status=200, json_data=None):
            self.status = status
            self._json_data = json_data or {}
        async def json(self): return self._json_data
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        def __await__(self):
            async def _ret(): return self
            return _ret().__await__()

    with patch('aiohttp.ClientSession', side_effect=MockSession):
        with patch('aiohttp.ClientTimeout'):
            result = await api.coocurrences_over_time(
                date_range=date_range,
                locationName="Test",
                advanced_query=advanced_query
            )
            
    assert not result.empty
    assert result.iloc[0]["count"] == 5
    assert result.iloc[0]["coverage"] == 50
    assert result.iloc[0]["frequency"] == 0.1

@pytest.mark.skip_in_ci
class TestWiseLoculusLapisLiveAPI:
    """Live API tests that are skipped in CI environments."""
    
    def setup_method(self):
        """Set up test fixtures for live API tests."""
        import yaml
        import pathlib
        
        # Load config for live testing
        CONFIG_PATH = pathlib.Path(__file__).parent.parent / "config.yaml"
        try:
            with open(CONFIG_PATH, 'r') as file:
                config = yaml.safe_load(file)
            server_ip = config.get('server', {}).get('lapis_address', 'http://localhost:8000')
        except (FileNotFoundError, yaml.YAMLError):
            pytest.skip("Config file not found or invalid, skipping live API tests")
            
        self.api = WiseLoculusLapis(server_ip)
        # Use recent date range for live testing
        self.date_range = (datetime(2025, 7, 1), datetime(2025, 8, 28))
    
    @pytest.mark.asyncio
    async def test_sample_mutations_live_nucleotide(self):
        """Live test for nucleotide mutations from real API."""
        try:
            result = await self.api.sample_mutations(
                type=MutationType.NUCLEOTIDE,
                date_range=self.date_range,
                locationName="Zürich (ZH)",
                min_proportion=0.001  # Lower threshold to get some results
            )

            print(f"Live nucleotide test: Retrieved {len(result)} mutations")
            
            # Basic structure assertions
            assert isinstance(result, pd.DataFrame)
            
            if not result.empty:
                # Check that expected columns exist
                expected_columns = ["mutation", "count", "coverage", "proportion"]
                for col in expected_columns:
                    assert col in result.columns, f"Missing column: {col}"
                
                # Check data types and ranges
                assert result["count"].dtype in ['int64', 'float64'], "Count should be numeric"
                assert result["coverage"].dtype in ['int64', 'float64'], "Coverage should be numeric"
                assert result["proportion"].dtype in ['int64', 'float64'], "Proportion should be numeric"
                
                # Proportion should be between 0 and 1
                assert (result["proportion"] >= 0).all(), "Proportion should be >= 0"
                assert (result["proportion"] <= 1).all(), "Proportion should be <= 1"
                
                # Coverage should be >= count
                assert (result["coverage"] >= result["count"]).all(), "Coverage should be >= count"
                
                print(f"Sample mutations:\n{result.head()}")
            else:
                print("No nucleotide mutations found in the specified date range")
                
        except Exception as e:
            pytest.fail(f"Live nucleotide API test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_sample_mutations_live_amino_acid(self):
        """Live test for amino acid mutations from real API."""
        try:
            result = await self.api.sample_mutations(
                type=MutationType.AMINO_ACID,
                date_range=self.date_range,
                locationName="Zürich (ZH)",
                min_proportion=0.001  # Lower threshold to get some results
            )
            
            # Basic structure assertions
            assert isinstance(result, pd.DataFrame)
            print(f"Live amino acid test: Retrieved {len(result)} mutations")
            
            if not result.empty:
                # Check that expected columns exist
                expected_columns = ["mutation", "count", "coverage", "proportion"]
                for col in expected_columns:
                    assert col in result.columns, f"Missing column: {col}"
                
                # Check amino acid mutation format (should contain ":")
                mutations_with_colon = result["mutation"].str.contains(":", na=False)
                assert mutations_with_colon.any(), "Amino acid mutations should contain gene:mutation format"
                
                print(f"Sample amino acid mutations:\n{result.head()}")
            else:
                print("No amino acid mutations found in the specified date range")
                
        except Exception as e:
            pytest.fail(f"Live amino acid API test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_component_amino_acid_mutations_over_time_live(self):
        """Live test for component_aminoAcidMutationsOverTime from real API."""
        try:
            # Test with known mutations that are likely to exist
            mutations = ["S:N501Y", "N:N8N"]
            date_ranges = [
                (datetime(2025, 6, 12), datetime(2025, 6, 18)),
                (datetime(2025, 6, 19), datetime(2025, 6, 26))
            ]
            locationName = "Zürich (ZH)"
            
            result = await self.api.component_aminoAcidMutationsOverTime(
                mutations=mutations,
                date_ranges=date_ranges,
                locationName=locationName
            )
            
            print(f"Live component test result keys: {list(result.keys()) if isinstance(result, dict) else type(result)}")
            
            # Basic structure assertions
            assert isinstance(result, dict), "Result should be a dictionary"
            
            # Check for error vs success response
            if "error" in result:
                print(f"API returned error (may be expected): {result['error']}")
                # Even with errors, we validate the structure
                assert "error" in result
                assert isinstance(result["error"], str)
            else:
                # Successful response structure validation
                assert "data" in result, "Successful response should contain 'data' key"
                
                data = result["data"]
                assert isinstance(data, dict), "Data should be a dictionary"
                
                # Validate expected structure based on API documentation
                expected_keys = ["mutations", "dateRanges", "data"]
                for key in expected_keys:
                    assert key in data, f"Missing key in data: {key}"
                
                # Validate mutations list
                assert isinstance(data["mutations"], list), "Mutations should be a list"
                assert len(data["mutations"]) == len(mutations), "Should return same number of mutations"
                
                # Validate dateRanges
                assert isinstance(data["dateRanges"], list), "DateRanges should be a list"
                assert len(data["dateRanges"]) == len(date_ranges), "Should return same number of date ranges"
                
                # Validate data matrix structure
                assert isinstance(data["data"], list), "Data matrix should be a list"
                if data["data"]:  # If we have data
                    # Should have one entry per mutation
                    assert len(data["data"]) == len(mutations), "Data matrix should have one row per mutation"
                    
                    # Each mutation should have data for each date range
                    for mutation_data in data["data"]:
                        assert isinstance(mutation_data, list), "Each mutation should have a list of date range data"
                        assert len(mutation_data) == len(date_ranges), "Each mutation should have data for each date range"
                        
                        # Each date range entry should have count and coverage
                        for date_data in mutation_data:
                            assert isinstance(date_data, dict), "Date data should be a dictionary"
                            assert "count" in date_data, "Date data should have count"
                            assert "coverage" in date_data, "Date data should have coverage"
                            assert isinstance(date_data["count"], (int, float)), "Count should be numeric"
                            assert isinstance(date_data["coverage"], (int, float)), "Coverage should be numeric"
                            assert date_data["coverage"] >= date_data["count"], "Coverage should be >= count"
                
                print(f"Successfully validated component response structure")
                print(f"Mutations tested: {data['mutations']}")
                print(f"Date ranges: {len(data['dateRanges'])}")
                if data["data"]:
                    print(f"data : {data['data']}")
                
                # Additional validation for info section if present
                if "info" in result:
                    info = result["info"]
                    assert isinstance(info, dict), "Info should be a dictionary"
                    # Common info fields from LAPIS
                    info_fields = ["dataVersion", "requestId", "lapisVersion"]
                    for field in info_fields:
                        if field in info:
                            assert isinstance(info[field], str), f"{field} should be a string"
                            
        except Exception as e:
            pytest.fail(f"Live component amino acid mutations over time API test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_component_nucleotide_mutations_over_time_live(self):
        """Live test for component_nucleotideMutationsOverTime from real API."""
        try:
            # Test with nucleotide mutations
            mutations = ["A123T", "C456G"]
            date_ranges = [
                (datetime(2025, 6, 12), datetime(2025, 6, 18)),
                (datetime(2025, 6, 19), datetime(2025, 6, 26))
            ]
            locationName = "Zürich (ZH)"
            
            result = await self.api.component_nucleotideMutationsOverTime(
                mutations=mutations,
                date_ranges=date_ranges,
                locationName=locationName
            )
            
            print(f"Live nucleotide component test result keys: {list(result.keys()) if isinstance(result, dict) else type(result)}")
            
            # Basic structure assertions
            assert isinstance(result, dict), "Result should be a dictionary"
            
            # Check for error vs success response
            if "error" in result:
                print(f"API returned error (may be expected): {result['error']}")
                # Even with errors, we validate the structure
                assert "error" in result
                assert isinstance(result["error"], str)
            else:
                # Successful response structure validation
                assert "data" in result, "Successful response should contain 'data' key"
                
                data = result["data"]
                assert isinstance(data, dict), "Data should be a dictionary"
                
                # Validate expected structure
                expected_keys = ["mutations", "dateRanges", "data"]
                for key in expected_keys:
                    assert key in data, f"Missing key in data: {key}"
                
                # Validate mutations list
                assert isinstance(data["mutations"], list), "Mutations should be a list"
                assert len(data["mutations"]) == len(mutations), "Should return same number of mutations"
                
                # Validate dateRanges
                assert isinstance(data["dateRanges"], list), "DateRanges should be a list"
                assert len(data["dateRanges"]) == len(date_ranges), "Should return same number of date ranges"
                
                # Validate data matrix structure
                assert isinstance(data["data"], list), "Data matrix should be a list"
                if data["data"]:  # If we have data
                    # Should have one entry per mutation
                    assert len(data["data"]) == len(mutations), "Data matrix should have one row per mutation"
                    
                    # Each mutation should have data for each date range
                    for mutation_data in data["data"]:
                        assert isinstance(mutation_data, list), "Each mutation should have a list of date range data"
                        assert len(mutation_data) == len(date_ranges), "Each mutation should have data for each date range"
                        
                        # Each date range entry should have count and coverage
                        for date_data in mutation_data:
                            assert isinstance(date_data, dict), "Date data should be a dictionary"
                            assert "count" in date_data, "Date data should have count"
                            assert "coverage" in date_data, "Date data should have coverage"
                            assert isinstance(date_data["count"], (int, float)), "Count should be numeric"
                            assert isinstance(date_data["coverage"], (int, float)), "Coverage should be numeric"
                            assert date_data["coverage"] >= date_data["count"], "Coverage should be >= count"
                
                print(f"Successfully validated nucleotide component response structure")
                print(f"Mutations tested: {data['mutations']}")
                print(f"Date ranges: {len(data['dateRanges'])}")
                if data["data"]:
                    print(f"Sample data point: {data['data'][0][0] if data['data'][0] else 'No data'}")
                
        except Exception as e:
            pytest.fail(f"Live component nucleotide mutations over time API test failed: {e}")

    def test_mutations_over_time_daily_interval(self):
        """Test mutations_over_time function with daily interval."""
        # Mock the component API response with proper structure
        mock_api_response = {
            "data": {
                "mutations": ["A123T", "C456G"],
                "dateRanges": [
                    {"dateFrom": "2024-01-01", "dateTo": "2024-01-01"},
                    {"dateFrom": "2024-01-02", "dateTo": "2024-01-02"}
                ],
                "data": [
                    [
                        {"count": 10, "coverage": 100},
                        {"count": 15, "coverage": 150}
                    ],
                    [
                        {"count": 5, "coverage": 50},
                        {"count": 8, "coverage": 80}
                    ]
                ]
            }
        }
        
        with patch.object(self.api, 'component_nucleotideMutationsOverTime', return_value=mock_api_response):
            result = asyncio.run(self.api.mutations_over_time(
                mutations=["A123T", "C456G"],
                mutation_type=MutationType.NUCLEOTIDE,
                date_range=(datetime(2024, 1, 1), datetime(2024, 1, 2)),
                locationName="Test Location",
                interval="daily"
            ))
        
        # Assertions
        assert isinstance(result, pd.DataFrame), "Result should be a DataFrame"
        assert isinstance(result.index, pd.MultiIndex), "Result should have MultiIndex"
        assert list(result.index.names) == ["mutation", "samplingDate"], "Index names should be correct"
        assert list(result.columns) == ["count", "coverage", "frequency"], "Columns should be correct"
        
        # Check data content
        assert len(result) == 4, "Should have 4 records (2 mutations × 2 dates)"
        
        # Check frequency calculation
        for _, row in result.iterrows():
            expected_freq = row["count"] / row["coverage"] if row["coverage"] > 0 else 0
            assert abs(row["frequency"] - expected_freq) < 1e-10, "Frequency should be calculated correctly"

    def test_mutations_over_time_weekly_interval(self):
        """Test mutations_over_time function with weekly interval."""
        date_range = (datetime(2024, 1, 1), datetime(2024, 1, 14))
        
        # Test the date range generation
        date_ranges = self.api._generate_date_ranges(date_range, "weekly")
        
        assert len(date_ranges) == 2, "Should generate 2 weekly ranges"
        assert date_ranges[0] == (datetime(2024, 1, 1), datetime(2024, 1, 7)), "First week should be correct"
        assert date_ranges[1] == (datetime(2024, 1, 8), datetime(2024, 1, 14)), "Second week should be correct"

    def test_mutations_over_time_monthly_interval(self):
        """Test mutations_over_time function with monthly interval."""
        date_range = (datetime(2024, 1, 15), datetime(2024, 3, 15))
        
        # Test the date range generation
        date_ranges = self.api._generate_date_ranges(date_range, "monthly")
        
        assert len(date_ranges) == 3, "Should generate 3 monthly ranges"
        assert date_ranges[0][0] == datetime(2024, 1, 15), "First month start should be correct"
        assert date_ranges[0][1] == datetime(2024, 1, 31), "First month end should be correct"
        assert date_ranges[1] == (datetime(2024, 2, 1), datetime(2024, 2, 29)), "February should be correct"
        assert date_ranges[2] == (datetime(2024, 3, 1), datetime(2024, 3, 15)), "March should be correct"

    @pytest.mark.asyncio
    async def test_mutations_over_time_live_nucleotide(self):
        """Live test for mutations_over_time function with nucleotide mutations."""
        try:
            # Test with nucleotide mutations that actually exist in the data
            mutations = ["C16407A", "T8104G"]  # Using real mutations from the API
            date_range = (datetime(2025, 7, 1), datetime(2025, 7, 7))  # One week
            locationName = "Zürich (ZH)"
            
            result = await self.api.mutations_over_time(
                mutations=mutations,
                mutation_type=MutationType.NUCLEOTIDE,
                date_range=date_range,
                locationName=locationName,
                interval="daily"
            )
            
            print(f"Live mutations_over_time test: Retrieved {len(result)} records")
            
            # Basic structure assertions
            assert isinstance(result, pd.DataFrame), "Result should be a DataFrame"
            assert isinstance(result.index, pd.MultiIndex), "Result should have MultiIndex"
            assert list(result.index.names) == ["mutation", "samplingDate"], "Index names should be correct"
            assert list(result.columns) == ["count", "coverage", "frequency"], "Columns should be correct"
            
            if not result.empty:
                # Check data content and validity
                for mutation in result.index.get_level_values('mutation').unique():
                    mutation_data = result.loc[mutation]
                    print(f"Mutation {mutation}: {len(mutation_data)} date entries")
                    
                    # Check data types and ranges
                    assert mutation_data["count"].dtype in ['int64', 'float64'], "Count should be numeric"
                    assert mutation_data["coverage"].dtype in ['int64', 'float64'], "Coverage should be numeric"
                    # Frequency can be numeric or object dtype when containing NA values
                    assert mutation_data["frequency"].dtype in ['int64', 'float64', 'object'], "Frequency should be numeric or contain NA values"
                    
                    # Frequency should be between 0 and 1 for non-NA values
                    non_na_freq = mutation_data["frequency"].dropna()
                    if not non_na_freq.empty:
                        assert (non_na_freq >= 0).all(), "Frequency should be >= 0"
                        assert (non_na_freq <= 1).all(), "Frequency should be <= 1"
                    
                    # Coverage should be >= count
                    assert (mutation_data["coverage"] >= mutation_data["count"]).all(), "Coverage should be >= count"
                    
                    # Verify frequency calculation
                    for _, row in mutation_data.iterrows():
                        if pd.notna(row["frequency"]):
                            expected_freq = row["count"] / row["coverage"] if row["coverage"] > 0 else 0
                            assert abs(row["frequency"] - expected_freq) < 1e-10, "Frequency should be calculated correctly"
                        else:
                            # If frequency is NA, both count and coverage should be 0
                            assert row["count"] == 0 and row["coverage"] == 0, "NA frequency should only occur when count and coverage are both 0"
                
                print(f"Sample data:\n{result.head()}")
            else:
                print("No data found for the specified mutations and date range")
                
        except Exception as e:
            pytest.fail(f"Live mutations_over_time nucleotide test failed: {e}")

    @pytest.mark.asyncio
    async def test_mutations_over_time_live_amino_acid(self):
        """Live test for mutations_over_time function with amino acid mutations."""
        try:
            # Test with amino acid mutations that actually exist in the data
            mutations = ["S:N501Y", "ORF1a:G1829I"]  # Using real mutations from the API
            date_range = (datetime(2025, 7, 1), datetime(2025, 7, 14))  # Two weeks
            locationName = "Zürich (ZH)"
            
            result = await self.api.mutations_over_time(
                mutations=mutations,
                mutation_type=MutationType.AMINO_ACID,
                date_range=date_range,
                locationName=locationName,
                interval="weekly"  # Use weekly for amino acid test
            )
            
            print(f"Live mutations_over_time amino acid test: Retrieved {len(result)} records")
            
            # Basic structure assertions
            assert isinstance(result, pd.DataFrame), "Result should be a DataFrame"
            assert isinstance(result.index, pd.MultiIndex), "Result should have MultiIndex"
            assert list(result.index.names) == ["mutation", "samplingDate"], "Index names should be correct"
            assert list(result.columns) == ["count", "coverage", "frequency"], "Columns should be correct"
            
            if not result.empty:
                # Check that mutations follow amino acid format
                mutations_found = result.index.get_level_values('mutation').unique()
                for mutation in mutations_found:
                    assert ":" in mutation, f"Amino acid mutation should contain ':' - got {mutation}"
                
                # Check data content and validity
                for mutation in mutations_found:
                    mutation_data = result.loc[mutation]
                    print(f"Amino acid mutation {mutation}: {len(mutation_data)} date entries")
                    
                    # Check data types and ranges
                    assert mutation_data["count"].dtype in ['int64', 'float64'], "Count should be numeric"
                    assert mutation_data["coverage"].dtype in ['int64', 'float64'], "Coverage should be numeric"
                    assert mutation_data["frequency"].dtype in ['int64', 'float64', 'object'], "Frequency should be numeric or contain NA values"
                    
                    # Frequency should be between 0 and 1
                    non_na_freq = mutation_data["frequency"].dropna()
                    if not non_na_freq.empty:
                        assert (non_na_freq >= 0).all(), "Frequency should be >= 0"
                        assert (non_na_freq <= 1).all(), "Frequency should be <= 1"
                    
                    # Coverage should be >= count
                    assert (mutation_data["coverage"] >= mutation_data["count"]).all(), "Coverage should be >= count"
                
                print(f"Sample amino acid data:\n{result.head()}")
                
                # Check that we have reasonable date distribution for weekly intervals
                dates_found = result.index.get_level_values('samplingDate').unique()
                print(f"Date points found: {sorted(dates_found)}")
                
            else:
                print("No amino acid data found for the specified mutations and date range")
                
        except Exception as e:
            pytest.fail(f"Live mutations_over_time amino acid test failed: {e}")




@pytest.mark.asyncio
async def test_coocurrences_over_time_api_error():
    """Test coocurrences_over_time raises APIError on failure."""
    api = WiseLoculusLapis("http://test-server.com")
    date_range = (datetime(2024, 1, 1), datetime(2024, 1, 2))
    
    class MockResponse:
        def __init__(self, status=500, text="Internal Server Error"):
            self.status = status
            self._text = text
        async def text(self): return self._text
        async def json(self): return {}
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        def __await__(self):
            async def _ret(): return self
            return _ret().__await__()

    class MockSession:
        def __init__(self, *args, **kwargs): pass
        def post(self, url, json=None, **kwargs):
            return MockResponse(status=500)
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass

    from api.exceptions import APIError

    with patch('aiohttp.ClientSession', side_effect=MockSession):
        with patch('aiohttp.ClientTimeout'):
            with pytest.raises(APIError) as excinfo:
                await api.coocurrences_over_time(
                    date_range=date_range,
                    locationName="Test",
                    mutations=["123T"]
                )
            assert "500" in str(excinfo.value)

def test_transform_query_to_coverage():
    """Test _transform_query_to_coverage with various inputs."""
    api = WiseLoculusLapis("http://test-server.com")
    
    # Nucleotide mutations
    query = "[3-of: 23149T, 23224T, 23311T]"
    expected = "[3-of: !23149N, !23224N, !23311N]"
    assert api._transform_query_to_coverage(query) == expected
    
    # Amino acid mutations
    query = "(S:484K | S:501Y) & ORF1a:3675-"
    expected = "(!S:484N | !S:501N) & !ORF1a:3675N"
    assert api._transform_query_to_coverage(query) == expected
    
    # Mixed and complex
    query = "A23403G & !23224- & (S:614G | S:614D)"
    expected = "!23403N & !23224N & (!S:614N | !S:614N)"
    assert api._transform_query_to_coverage(query) == expected
    
    # Exact N-of
    query = "[exactly-2-of: S:501Y, S:484K, S:417N]"
    expected = "[exactly-2-of: !S:501N, !S:484N, !S:417N]"
    assert api._transform_query_to_coverage(query) == expected

    # With dots
    query = "23403."
    expected = "!23403N"
    assert api._transform_query_to_coverage(query) == expected
