"""Simple tests for the wiseloculus module."""

import pytest
from unittest.mock import patch
from datetime import datetime
from pathlib import Path
import sys

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
