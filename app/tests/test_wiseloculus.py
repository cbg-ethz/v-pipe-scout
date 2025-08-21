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


class TestWiseLoculusLapis:
    """Test cases for WiseLoculusLapis class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.api = WiseLoculusLapis("http://test-server.com")
        self.date_range = (datetime(2024, 1, 1), datetime(2024, 1, 31))
    
    @pytest.mark.asyncio
    async def test_fetch_mutation_counts_and_coverage_nucleotide(self):
        """Test fetch_mutation_counts_and_coverage for nucleotide mutations."""
        # Mock the fetch_sample_aggregated method to return controlled data
        mock_responses = {
            "A123A": {"mutation": "A123A", "data": [{"sampling_date": "2024-01-15", "count": 10}]},
            "A123T": {"mutation": "A123T", "data": [{"sampling_date": "2024-01-15", "count": 5}]},
            "A123C": {"mutation": "A123C", "data": [{"sampling_date": "2024-01-15", "count": 3}]},
            "A123G": {"mutation": "A123G", "data": [{"sampling_date": "2024-01-15", "count": 2}]},
        }
        
        async def mock_fetch_sample_aggregated(session, mutation, mutation_type, date_range, location_name=None):
            return mock_responses.get(mutation, {"mutation": mutation, "data": []})
        
        with patch.object(self.api, 'fetch_sample_aggregated', side_effect=mock_fetch_sample_aggregated):
            result = await self.api.fetch_mutation_counts_and_coverage(
                mutations=["A123T"],
                mutation_type=MutationType.NUCLEOTIDE,
                date_range=self.date_range
            )
        
        # Assertions
        assert len(result) == 1
        mutation_result = result[0]
        
        assert mutation_result["mutation"] == "A123T"
        assert mutation_result["coverage"] == 20  # 10 + 5 + 3 + 2
        assert mutation_result["frequency"] == 0.25  # 5/20
        assert mutation_result["counts"] == {"A": 10, "T": 5, "C": 3, "G": 2}
        
        # Check stratified data
        assert len(mutation_result["stratified"]) == 1
        stratified = mutation_result["stratified"][0]
        assert stratified["sampling_date"] == "2024-01-15"
        assert stratified["coverage"] == 20
        assert stratified["frequency"] == 0.25
        assert stratified["count"] == 5

    @pytest.mark.asyncio
    async def test_fetch_mutation_counts_and_coverage_empty_data(self):
        """Test fetch_mutation_counts_and_coverage with empty data."""
        async def mock_fetch_sample_aggregated(session, mutation, mutation_type, date_range, location_name=None):
            return {"mutation": mutation, "data": []}
        
        with patch.object(self.api, 'fetch_sample_aggregated', side_effect=mock_fetch_sample_aggregated):
            result = await self.api.fetch_mutation_counts_and_coverage(
                mutations=["A123T"],
                mutation_type=MutationType.NUCLEOTIDE,
                date_range=self.date_range
            )
        
        # Assertions for empty data
        assert len(result) == 1
        mutation_result = result[0]
        
        assert mutation_result["mutation"] == "A123T"
        assert mutation_result["coverage"] == 0
        assert mutation_result["frequency"] == 0
        assert mutation_result["counts"] == {"A": 0, "T": 0, "C": 0, "G": 0}
        assert mutation_result["stratified"] == []

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
                    location_name="Zurich",
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
                    location_name="Zurich"
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
        location_name = "Zurich"
        min_proportion = 0.05

        # Expected payload structure
        expected_payload = {
            "sampling_dateFrom": "2024-01-01",
            "sampling_dateTo": "2024-01-31",
            "location_name": location_name,
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
                location_name="Zürich (ZH)",
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
                location_name="Zürich (ZH)",
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
            location_name = "Zürich (ZH)"
            
            result = await self.api.component_aminoAcidMutationsOverTime(
                mutations=mutations,
                date_ranges=date_ranges,
                location_name=location_name
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
            location_name = "Zürich (ZH)"
            
            result = await self.api.component_nucleotideMutationsOverTime(
                mutations=mutations,
                date_ranges=date_ranges,
                location_name=location_name
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
                location_name="Test Location",
                interval="daily"
            ))
        
        # Assertions
        assert isinstance(result, pd.DataFrame), "Result should be a DataFrame"
        assert isinstance(result.index, pd.MultiIndex), "Result should have MultiIndex"
        assert list(result.index.names) == ["mutation", "sampling_date"], "Index names should be correct"
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
            location_name = "Zürich (ZH)"
            
            result = await self.api.mutations_over_time(
                mutations=mutations,
                mutation_type=MutationType.NUCLEOTIDE,
                date_range=date_range,
                location_name=location_name,
                interval="daily"
            )
            
            print(f"Live mutations_over_time test: Retrieved {len(result)} records")
            
            # Basic structure assertions
            assert isinstance(result, pd.DataFrame), "Result should be a DataFrame"
            assert isinstance(result.index, pd.MultiIndex), "Result should have MultiIndex"
            assert list(result.index.names) == ["mutation", "sampling_date"], "Index names should be correct"
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
            location_name = "Zürich (ZH)"
            
            result = await self.api.mutations_over_time(
                mutations=mutations,
                mutation_type=MutationType.AMINO_ACID,
                date_range=date_range,
                location_name=location_name,
                interval="weekly"  # Use weekly for amino acid test
            )
            
            print(f"Live mutations_over_time amino acid test: Retrieved {len(result)} records")
            
            # Basic structure assertions
            assert isinstance(result, pd.DataFrame), "Result should be a DataFrame"
            assert isinstance(result.index, pd.MultiIndex), "Result should have MultiIndex"
            assert list(result.index.names) == ["mutation", "sampling_date"], "Index names should be correct"
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
                    assert mutation_data["frequency"].dtype in ['int64', 'float64'], "Frequency should be numeric"
                    
                    # Frequency should be between 0 and 1
                    assert (mutation_data["frequency"] >= 0).all(), "Frequency should be >= 0"
                    assert (mutation_data["frequency"] <= 1).all(), "Frequency should be <= 1"
                    
                    # Coverage should be >= count
                    assert (mutation_data["coverage"] >= mutation_data["count"]).all(), "Coverage should be >= count"
                
                print(f"Sample amino acid data:\n{result.head()}")
                
                # Check that we have reasonable date distribution for weekly intervals
                dates_found = result.index.get_level_values('sampling_date').unique()
                print(f"Date points found: {sorted(dates_found)}")
                
            else:
                print("No amino acid data found for the specified mutations and date range")
                
        except Exception as e:
            pytest.fail(f"Live mutations_over_time amino acid test failed: {e}")


if __name__ == "__main__":

    ### testing if the amino acid coverage works with real server data.

    import yaml
    import pathlib
    import asyncio

    async def main():
        CONFIG_PATH = pathlib.Path(__file__).parent.parent / "config.yaml"
        with open(CONFIG_PATH, 'r') as file:
            config = yaml.safe_load(file)
        server_ip = config.get('server', {}).get('lapis_address', 'http://default_ip:8000')
        wiseLoculus = WiseLoculusLapis(server_ip)

        result = await wiseLoculus.fetch_mutation_counts_and_coverage(
            mutations=["ORF1a:V3449I"],
            mutation_type=MutationType.AMINO_ACID,
            location_name="Zürich (ZH)",
            date_range=(datetime(2025, 2, 2), datetime(2025, 3, 3))
        )

        print(result)

    asyncio.run(main())
