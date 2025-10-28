"""
Test the multi-location functionality.
"""
import pytest
import pandas as pd
from unittest.mock import AsyncMock, MagicMock
import asyncio
from datetime import datetime
import sys
import os

# Add the parent directory to the path so we can import from app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock streamlit to avoid import issues in tests
import sys
from unittest.mock import MagicMock
sys.modules['streamlit'] = MagicMock()

from utils.multi_location import fetch_multi_location_data, validate_location_data
from interface import MutationType


class TestMultiLocationUtils:
    
    @pytest.fixture
    def mock_wiseLoculus(self):
        """Create a mock WiseLoculus client."""
        mock_client = MagicMock()
        
        # Create sample data for different locations
        def create_sample_data(location):
            dates = pd.date_range('2024-01-01', periods=5, freq='D')
            mutations = ['C241T', 'A23403G', 'C3037T']
            
            data = []
            for date in dates:
                for mutation in mutations:
                    data.append({
                        'count': 10 + hash(f"{location}{mutation}{date}") % 20,
                        'coverage': 100 + hash(f"{location}{mutation}{date}") % 50,
                        'frequency': 0.1 + (hash(f"{location}{mutation}{date}") % 10) / 100
                    })
            
            df = pd.DataFrame(data)
            # Create MultiIndex with mutation and samplingDate
            index_tuples = [(mut, date) for date in dates for mut in mutations]
            df.index = pd.MultiIndex.from_tuples(index_tuples, names=['mutation', 'samplingDate'])
            
            return df
        
        # Mock the async method
        async def mock_mutations_over_time(mutations, mutation_type, date_range, location, interval="daily"):
            if location == "FailLocation":
                raise Exception("Network error")
            return create_sample_data(location)
        
        mock_client.mutations_over_time = mock_mutations_over_time
        return mock_client
    
    @pytest.mark.asyncio
    async def test_single_location_fetch(self, mock_wiseLoculus):
        """Test fetching data for a single location."""
        mutations = ['C241T', 'A23403G']
        date_range = (datetime(2024, 1, 1), datetime(2024, 1, 5))
        locations = ['Location1']
        
        # Mock streamlit components
        with pytest.MonkeyPatch().context() as m:
            m.setattr('streamlit.write', lambda x: None)
            m.setattr('streamlit.container', lambda: MagicMock())
            
            result = await fetch_multi_location_data(
                mock_wiseLoculus,
                mutations,
                MutationType.NUCLEOTIDE,
                date_range,
                locations
            )
        
        assert len(result) == 1
        assert 'Location1' in result
        assert not result['Location1'].empty
        assert 'count' in result['Location1'].columns
        assert 'coverage' in result['Location1'].columns
    
    @pytest.mark.asyncio 
    async def test_multi_location_fetch(self, mock_wiseLoculus):
        """Test fetching data for multiple locations."""
        mutations = ['C241T', 'A23403G']
        date_range = (datetime(2024, 1, 1), datetime(2024, 1, 5))
        locations = ['Location1', 'Location2', 'Location3']
        
        # Mock streamlit components
        with pytest.MonkeyPatch().context() as m:
            m.setattr('streamlit.write', lambda x: None)
            m.setattr('streamlit.container', lambda: MagicMock())
            m.setattr('streamlit.columns', lambda x: [MagicMock() for _ in range(x)])
            
            result = await fetch_multi_location_data(
                mock_wiseLoculus,
                mutations,
                MutationType.NUCLEOTIDE,
                date_range,
                locations
            )
        
        assert len(result) == 3
        for location in locations:
            assert location in result
            assert not result[location].empty
    
    @pytest.mark.asyncio
    async def test_fetch_with_failures(self, mock_wiseLoculus):
        """Test fetching data when some locations fail."""
        mutations = ['C241T']
        date_range = (datetime(2024, 1, 1), datetime(2024, 1, 5))
        locations = ['Location1', 'FailLocation', 'Location3']
        
        # Mock streamlit components
        with pytest.MonkeyPatch().context() as m:
            m.setattr('streamlit.write', lambda x: None)
            m.setattr('streamlit.container', lambda: MagicMock())
            m.setattr('streamlit.columns', lambda x: [MagicMock() for _ in range(x)])
            m.setattr('streamlit.success', lambda x: None)
            m.setattr('streamlit.warning', lambda x: None)
            
            result = await fetch_multi_location_data(
                mock_wiseLoculus,
                mutations,
                MutationType.NUCLEOTIDE,
                date_range,
                locations
            )
        
        # Should have 2 successful locations (excluding FailLocation)
        assert len(result) == 2
        assert 'Location1' in result
        assert 'Location3' in result
        assert 'FailLocation' not in result
    
    def test_validate_location_data(self):
        """Test location data validation."""
        # Create test data with some issues
        good_data = pd.DataFrame({
            'count': [10, 20, 30],
            'coverage': [100, 200, 300],
            'frequency': [0.1, 0.2, 0.3]
        })
        
        bad_data = pd.DataFrame({
            'count': [10, -5, 30],  # Negative count
            'coverage': [100, 200, -50],  # Negative coverage
            'frequency': [0.1, 0.2, 0.3]
        })
        
        empty_data = pd.DataFrame()
        
        location_data = {
            'GoodLocation': good_data,
            'BadLocation': bad_data,
            'EmptyLocation': empty_data
        }
        
        cleaned = validate_location_data(location_data)
        
        # Should keep good location
        assert 'GoodLocation' in cleaned
        
        # Should clean bad location (fix negative values)
        assert 'BadLocation' in cleaned
        assert (cleaned['BadLocation']['count'] >= 0).all()
        assert (cleaned['BadLocation']['coverage'] >= 0).all()
        
        # Should exclude empty location
        assert 'EmptyLocation' not in cleaned
    

if __name__ == "__main__":
    pytest.main([__file__, "-v"])