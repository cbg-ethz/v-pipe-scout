"""
Multi-location data fetching utilities for V-Pipe Scout.

This module provides functions to fetch mutation data from multiple locations
in parallel, with progress tracking and error handling.
"""

import asyncio
import logging
import pandas as pd
import streamlit as st
from typing import List, Tuple, Dict, Optional
from datetime import datetime

from api.wiseloculus import WiseLoculusLapis
from interface import MutationType

logger = logging.getLogger(__name__)


async def fetch_multi_location_data(
    wiseLoculus: WiseLoculusLapis,
    mutations: List[str],
    mutation_type: MutationType,
    date_range: Tuple[datetime, datetime],
    locations: List[str],
    interval: str = "daily"
) -> Dict[str, pd.DataFrame]:
    """
    Fetch mutation data for multiple locations in parallel.
    
    Args:
        wiseLoculus: The WiseLoculus API client
        mutations: List of mutations to fetch
        mutation_type: Type of mutations (nucleotide, amino acid, etc.)
        date_range: Tuple of (start_date, end_date)
        locations: List of location names to fetch data for
        interval: Time interval for data aggregation (default: "daily")
    
    Returns:
        Dict[location_name, DataFrame] - One DataFrame per location
        
    Raises:
        ValueError: If no data is retrieved for any location
    """
    
    if len(locations) == 1:
        # Single location - use existing optimized path
        st.write(f"📍 Fetching data for: {locations[0]}")
        result = await wiseLoculus.mutations_over_time(
            mutations, mutation_type, date_range, locations[0], interval
        )
        return {locations[0]: result}
    
    # Multiple locations - parallel processing
    st.write(f"🔄 Fetching data for {len(locations)} locations in parallel...")
    
    # Create progress containers for each location
    progress_container = st.container()
    location_progress = {}
    
    with progress_container:
        # Create a row of columns for progress indicators
        if len(locations) <= 4:
            # Show progress in columns if 4 or fewer locations
            progress_cols = st.columns(len(locations))
            for i, loc in enumerate(locations):
                with progress_cols[i]:
                    location_progress[loc] = st.empty()
                    location_progress[loc].info(f"📍 {loc}: Starting...")
        else:
            # Show progress in a single column if more than 4 locations
            for loc in locations:
                location_progress[loc] = st.empty()
                location_progress[loc].info(f"📍 {loc}: Starting...")
    
    async def fetch_with_progress(location: str):
        """Fetch data for a single location with progress updates."""
        try:
            location_progress[location].info(f"📍 {location}: Fetching data...")
            
            result = await wiseLoculus.mutations_over_time(
                mutations, mutation_type, date_range, location, interval
            )
            
            if result is not None and not result.empty:
                location_progress[location].success(f"✅ {location}: records retrieved")
                return location, result
            else:
                location_progress[location].warning(f"⚠️ {location}: No data found")
                return location, None
                
        except Exception as e:
            error_msg = str(e)
            # Truncate very long error messages for display
            if len(error_msg) > 100:
                error_msg = error_msg[:97] + "..."
            location_progress[location].error(f"❌ {location}: {error_msg}")
            logger.error(f"Failed to fetch data for {location}: {e}")
            return location, None
    
    # Execute all tasks concurrently
    tasks = [fetch_with_progress(loc) for loc in locations]
    
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        logger.error(f"Error in parallel data fetching: {e}")
        st.error(f"❌ Error during parallel data fetching: {str(e)}")
        raise
    
    # Process results
    location_data = {}
    successful_locations = []
    failed_locations = []
    
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Task failed with exception: {result}")
            continue
        
        # Ensure result is a tuple before unpacking
        if not isinstance(result, tuple) or len(result) != 2:
            logger.error(f"Unexpected result format: {result}")
            continue
            
        location, data = result
        if data is not None and not data.empty:
            location_data[location] = data
            successful_locations.append(location)
        else:
            failed_locations.append(location)
    
    # Clean up progress indicators after a brief delay to let users see final status
    await asyncio.sleep(1)  # Show final status for 1 second
    for progress_widget in location_progress.values():
        progress_widget.empty()
    
    # Show summary
    if successful_locations:
        st.success(f"✅ Successfully fetched data for {len(successful_locations)} locations: {', '.join(successful_locations)}")
    
    if failed_locations:
        st.warning(f"⚠️ Failed to fetch data for {len(failed_locations)} locations: {', '.join(failed_locations)}")
    
    if not location_data:
        raise ValueError("No data retrieved for any location")
    
    return location_data


def validate_location_data(location_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """
    Validate and clean location data.
    
    Args:
        location_data: Dictionary of location -> DataFrame
        
    Returns:
        Cleaned and validated location data
    """
    cleaned_data = {}
    
    for location, df in location_data.items():
        if df is None or df.empty:
            logger.warning(f"Empty data for location: {location}")
            continue
            
        # Validate expected columns
        required_columns = ['count', 'coverage']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            logger.warning(f"Missing columns {missing_columns} for location: {location}")
            continue
            
        # Check for valid data (non-negative counts and coverage)
        if (df['count'] < 0).any() or (df['coverage'] < 0).any():
            logger.warning(f"Invalid negative values found for location: {location}")
            # Clean negative values by setting them to 0
            df = df.copy()
            df['count'] = df['count'].clip(lower=0)
            df['coverage'] = df['coverage'].clip(lower=0)
        
        cleaned_data[location] = df
    
    return cleaned_data
