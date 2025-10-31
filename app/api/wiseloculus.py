"""Implements the Wiseloculus API Queries."""

import logging
import aiohttp
import asyncio
from typing import Optional, List, Tuple, Any
from datetime import datetime, timedelta

import pandas as pd

from .lapis import Lapis
from .exceptions import APIError
from .lapis_fields import (
    SAMPLING_DATE, SAMPLING_DATE_FROM, SAMPLING_DATE_TO,
    LOCATION_NAME, AMINO_ACID_MUTATIONS, NUCLEOTIDE_MUTATIONS,
    FIELDS, ORDER_BY, MIN_PROPORTION, LIMIT, DATA_FORMAT, DOWNLOAD_AS_FILE,
    FILTERS, INCLUDE_MUTATIONS, DATE_RANGES, DATE_FROM, DATE_TO, DATE_FIELD,
    DATA, MUTATIONS, COUNT, COVERAGE, PROPORTION,
    DF_SAMPLING_DATE, DF_MUTATION, DF_COUNT, DF_COVERAGE, DF_FREQUENCY
)
from interface import MutationType

# Constants for fallback date range
# When API fails, use the last 3 months instead of an entire year to avoid huge API calls
def get_fallback_date_range() -> Tuple[datetime, datetime]:
    """
    Returns fallback date range of the last 3 months from today.
    This avoids excessively large API calls when the API date range query fails.
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)  # Approximately 3 months
    return start_date, end_date

FALLBACK_START_DATE, FALLBACK_END_DATE = get_fallback_date_range()

class WiseLoculusLapis(Lapis):
    """Wise-Loculus Instance API"""

    # TODO: phase out
    async def fetch_sample_aggregated(
            self,
            session: aiohttp.ClientSession, 
            mutation: str, 
            mutation_type: MutationType, 
            date_range: Tuple[datetime, datetime], 
            locationName: Optional[str] = None
            ) -> dict[str, Any]:
        """
        Fetches aggregated sample data for a given mutation, type, date range, and optional location.
        """
        payload: dict[str, Any] = { 
            SAMPLING_DATE_FROM: date_range[0].strftime('%Y-%m-%d'),
            SAMPLING_DATE_TO: date_range[1].strftime('%Y-%m-%d'),
            FIELDS: [SAMPLING_DATE],
            ORDER_BY: [SAMPLING_DATE]  # API expects array, not string
        }

        if mutation_type == MutationType.AMINO_ACID:
            payload[AMINO_ACID_MUTATIONS] = [mutation]
        elif mutation_type == MutationType.NUCLEOTIDE:
            payload[NUCLEOTIDE_MUTATIONS] = [mutation]
        else:
            logging.error(f"Unknown mutation type: {mutation_type}")
            return {"mutation": mutation, "data": None, "error": "Unknown mutation type"}

        if locationName:
            payload[LOCATION_NAME] = locationName  

        logging.debug(f"Fetching sample aggregated with payload: {payload}")
        try:
            async with session.post(
                f'{self.server_ip}/sample/aggregated',
                headers={
                    'accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {"mutation": mutation, "data": data.get('data', [])}
                else:
                    logging.error(f"Failed to fetch data for mutation {mutation} (type: {mutation_type}, location: {locationName}).")
                    logging.error(f"Status code: {response.status}")
                    logging.error(await response.text())
                    return {"mutation": mutation, "data": None, "status_code": response.status, "error_details": await response.text()}
        except Exception as e:
            logging.error(f"Connection error fetching data for mutation {mutation}: {e}")
            return {"mutation": mutation, "data": None, "error": str(e)}

    # TODO: phase out
    async def fetch_mutation_counts(
            self, 
            mutations: List[str], 
            mutation_type: MutationType, 
            date_range: Tuple[datetime, datetime], 
            locationName: Optional[str] = None
            ) -> List[dict[str, Any]]:
        """
        Fetches the mutation counts for a list of mutations, specifying their type and optional location.
        """
        # validate mutation_type
        if mutation_type not in [MutationType.AMINO_ACID, MutationType.NUCLEOTIDE]:
            raise ValueError(f"Unsupported mutation type: {mutation_type}")

        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_sample_aggregated(session, m, mutation_type, date_range, locationName) for m in mutations]
            return await asyncio.gather(*tasks, return_exceptions=True)  # return_exceptions to avoid failing the entire batch
            

    async def sample_mutations(
            self, 
            type: MutationType,
            date_range: Tuple[datetime, datetime], 
            locationName: Optional[str] = None,
            min_proportion: float = 0.01,
            nucleotide_mutations: Optional[List[str]] = None,
            amino_acid_mutations: Optional[List[str]] = None,
        ) -> pd.DataFrame:
        """
        Fetches nucleotide mutations for a given date range and optional location.
        Fetches mutations (nucleotide or amino acid) for a given date range and optional location.
        Filters for sequences/reads with particular nucleotide or amino acid mutations, depending on the specified mutation type and provided filters.
        
        Returns a DataFrame with 
        Columns: ['mutation', 'count', 'coverage', 'proportion', 'sequenceName', 'mutationFrom', 'mutationTo', 'position']
        """

        payload = {
            SAMPLING_DATE_FROM: date_range[0].strftime('%Y-%m-%d'),
            SAMPLING_DATE_TO: date_range[1].strftime('%Y-%m-%d'),
            LOCATION_NAME: locationName,
            MIN_PROPORTION: min_proportion, 
            ORDER_BY: PROPORTION,
            LIMIT: 10000,  # Adjust limit as needed
            DATA_FORMAT: "JSON",
            DOWNLOAD_AS_FILE: "false"
        }

        # Add mutation filters if provided
        if nucleotide_mutations:
            payload[NUCLEOTIDE_MUTATIONS] = nucleotide_mutations
        if amino_acid_mutations:
            payload[AMINO_ACID_MUTATIONS] = amino_acid_mutations

        if type == MutationType.AMINO_ACID:
            endpoint = f'{self.server_ip}/sample/aminoAcidMutations'
        elif type == MutationType.NUCLEOTIDE:
            endpoint = f'{self.server_ip}/sample/nucleotideMutations'
        else:
            logging.error(f"Unknown mutation type: {type}")
            return pd.DataFrame()

        try:
            timeout = aiohttp.ClientTimeout(total=30) 
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    endpoint,
                    params=payload,
                    headers={'accept': 'application/json'}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        df = pd.DataFrame(data['data'])
                        return df
                    else:
                        logging.error(f"Failed to fetch nucleotide mutations: {response.status}")
                        return pd.DataFrame()
        except Exception as e:
            logging.error(f"Error fetching mutations: {e}")
            return pd.DataFrame()
    

    async def get_date_range(self) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Fetches all available sampling dates and returns the earliest and latest dates.
        
        Returns:
            Tuple[Optional[datetime], Optional[datetime]]: (earliest_date, latest_date) or (None, None) if no data
        """
        try:
            timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout for this query
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    f'{self.server_ip}/sample/aggregated',
                    params={FIELDS: SAMPLING_DATE},
                    headers={'accept': 'application/json'}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        sample_data = data.get('data', [])
                        
                        if not sample_data:
                            logging.warning("No sampling date data available")
                            return None, None
                        
                        # Extract all dates and convert to datetime objects
                        dates = []
                        for entry in sample_data:
                            if SAMPLING_DATE in entry:
                                try:
                                    date_obj = datetime.strptime(entry[SAMPLING_DATE], '%Y-%m-%d')
                                    dates.append(date_obj)
                                except ValueError as e:
                                    logging.warning(f"Invalid date format: {entry[SAMPLING_DATE]}: {e}")
                        
                        if not dates:
                            logging.warning("No valid sampling dates found")
                            return None, None
                        
                        earliest_date = min(dates)
                        latest_date = max(dates)
                        
                        logging.info(f"Date range: {earliest_date.strftime('%Y-%m-%d')} to {latest_date.strftime('%Y-%m-%d')}")
                        return earliest_date, latest_date
                        
                    else:
                        logging.error(f"Failed to fetch sampling dates: {response.status}")
                        logging.error(await response.text())
                        return None, None
                        
        except Exception as e:
            logging.error(f"Error fetching date range: {e}")
            return None, None

    def get_cached_date_range(self, cache_key: str = "default") -> Tuple[datetime, datetime]:
        """
        Get the date range with caching to avoid repeated API calls.
        Returns pandas Timestamps for compatibility with Streamlit date inputs.
        
        Args:
            cache_key: Unique key for this cache (allows multiple cached ranges)
            
        Returns:
            Tuple[datetime, datetime]: Start and end dates as pandas Timestamps
        """
        import streamlit as st
        import asyncio
        import pandas as pd
        
        # Create a unique session state key
        session_key = f"wiseloculus_date_range_{cache_key}"
        
        # Check if we already have cached date range
        if session_key in st.session_state:
            cached_range = st.session_state[session_key]
            logging.debug(f"Using cached date range for {cache_key}: {cached_range}")
            return cached_range
        
        # Fetch new date range
        try:
            earliest, latest = asyncio.run(self.get_date_range())
            
            if earliest and latest:
                # Convert to pandas Timestamps for Streamlit compatibility
                date_range = (pd.to_datetime(earliest), pd.to_datetime(latest))
                logging.info(f"Fetched date range for {cache_key}: {date_range[0].strftime('%Y-%m-%d')} to {date_range[1].strftime('%Y-%m-%d')}")
            else:
                # Fallback to default dates
                date_range = (pd.to_datetime(FALLBACK_START_DATE), pd.to_datetime(FALLBACK_END_DATE))
                logging.warning(f"API date range not available for {cache_key}, using defaults: {date_range}")
                
        except Exception as e:
            # Fallback to default dates
            date_range = (pd.to_datetime(FALLBACK_START_DATE), pd.to_datetime(FALLBACK_END_DATE))
            logging.warning(f"Error fetching date range for {cache_key}: {e}, using defaults")
        
        # Cache the result
        st.session_state[session_key] = date_range
        return date_range

    def get_cached_date_range_with_bounds(self, cache_key: str = "default") -> Tuple[datetime, datetime, datetime, datetime]:
        """
        Get the date range with bounds for enforcing min/max in date inputs.
        
        Args:
            cache_key: Unique key for this cache
            
        Returns:
            Tuple[datetime, datetime, datetime, datetime]: (start_date, end_date, min_date, max_date)
        """
        start_date, end_date = self.get_cached_date_range(cache_key)
        
        # Use the same dates as bounds to enforce API limits
        # Add a small buffer for edge cases (1 day on each side)
        import pandas as pd
        buffer = pd.Timedelta(days=1)
        min_date = start_date - buffer
        max_date = end_date + buffer
        
        return start_date, end_date, min_date, max_date
    

    async def _component_mutations_over_time(
            self,
            endpoint: str,
            mutation_type_name: str,
            mutations: List[str], 
            date_ranges: List[Tuple[datetime, datetime]],
            locationName: str
        ) -> dict[str, Any]:
        """
        Helper method for fetching mutations over time data from component endpoints.
        
        Args:
            endpoint: The API endpoint name (e.g., "aminoAcidMutationsOverTime")
            mutation_type_name: Display name for logging (e.g., "amino acid")
            mutations: List of mutations
            date_ranges: List of date range tuples
            locationName: Location name to filter by
            
        Returns:
            Dict containing the API response with mutations, dateRanges, and data matrix
        """
        payload = {
            FILTERS: {
                LOCATION_NAME: locationName
            },
            INCLUDE_MUTATIONS: mutations,
            DATE_RANGES: [
                {
                    DATE_FROM: date_range[0].strftime('%Y-%m-%d'),
                    DATE_TO: date_range[1].strftime('%Y-%m-%d')
                }
                for date_range in date_ranges
            ],
            DATE_FIELD: SAMPLING_DATE
        }

        logging.debug(f"Fetching {mutation_type_name} mutations over time with payload: {payload}")
        
        try:
            timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout (consistent with other API calls)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f'{self.server_ip}/component/{endpoint}',
                    headers={
                        'accept': 'application/json',
                        'Content-Type': 'application/json'
                    },
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    elif response.status == 500:
                        # Log the failed query for debugging
                        logging.error(f"Internal Server Error (500) for {mutation_type_name} mutations over time")
                        logging.error(f"Failed POST query: {self.server_ip}/component/{endpoint}")
                        logging.error(f"Payload: {payload}")
                        error_text = await response.text()
                        logging.error(f"Server response: {error_text}")
                        
                        # Raise custom APIError for better frontend handling
                        raise APIError(
                            f"Internal Server Error: The backend API server is experiencing issues. This is not an application error.",
                            status_code=500,
                            details=error_text,
                            payload=payload
                        )
                    else:
                        logging.error(f"Failed to fetch {mutation_type_name} mutations over time.")
                        logging.error(f"Status code: {response.status}")
                        error_text = await response.text()
                        logging.error(error_text)
                        raise APIError(
                            f"API request failed with status {response.status}",
                            status_code=response.status,
                            details=error_text,
                            payload=payload
                        )
        except APIError:
            # Re-raise our custom APIError
            raise
        except Exception as e:
            logging.error(f"Connection error fetching {mutation_type_name} mutations over time: {e}")
            raise APIError(
                f"Connection error: {str(e)}",
                details=str(e),
                payload=payload
            )

    async def component_aminoAcidMutationsOverTime(
            self, 
            mutations: List[str], 
            date_ranges: List[Tuple[datetime, datetime]],
            locationName: str
        ) -> dict[str, Any]:
        """
        Fetches amino acid mutations over time for a given location and specific date ranges.
        Returns counts and coverage for each mutation and date range.
        
        Args:
            mutations: List of amino acid mutations in format ["S:N501Y", "N:N8N"]
            date_ranges: List of date range tuples [(start_date, end_date), ...]
            locationName: Location name to filter by
            
        Returns:
            Dict containing the API response with mutations, dateRanges, and data matrix
        """
        return await self._component_mutations_over_time(
            endpoint="aminoAcidMutationsOverTime",
            mutation_type_name="amino acid",
            mutations=mutations,
            date_ranges=date_ranges,
            locationName=locationName
        )

    async def component_nucleotideMutationsOverTime(
            self, 
            mutations: List[str], 
            date_ranges: List[Tuple[datetime, datetime]],
            locationName: str
        ) -> dict[str, Any]:
        """
        Fetches nucleotide mutations over time for a given location and specific date ranges.
        Returns counts and coverage for each mutation and date range.
        
        Args:
            mutations: List of nucleotide mutations in format ["A5341C", "C34G"]
            date_ranges: List of date range tuples [(start_date, end_date), ...]
            locationName: Location name to filter by
            
        Returns:
            Dict containing the API response with mutations, dateRanges, and data matrix
        """
        return await self._component_mutations_over_time(
            endpoint="nucleotideMutationsOverTime",
            mutation_type_name="nucleotide",
            mutations=mutations,
            date_ranges=date_ranges,
            locationName=locationName
        )

    def _generate_date_ranges(
            self, 
            date_range: Tuple[datetime, datetime], 
            interval: str = "daily"
        ) -> List[Tuple[datetime, datetime]]:
        """
        Generate date ranges based on the specified interval.
        
        Args:
            date_range: Tuple of (start_date, end_date)
            interval: "daily", "weekly", or "monthly"
            
        Returns:
            List of date range tuples
        """
        start_date, end_date = date_range
        date_ranges = []
        
        if interval == "daily":
            current_date = start_date
            while current_date <= end_date:
                date_ranges.append((current_date, current_date))
                current_date += pd.Timedelta(days=1)
                
        elif interval == "weekly":
            current_date = start_date
            while current_date <= end_date:
                week_end = min(current_date + pd.Timedelta(days=6), end_date)
                date_ranges.append((current_date, week_end))
                current_date = week_end + pd.Timedelta(days=1)
                
        elif interval == "monthly":
            current_date = start_date
            while current_date <= end_date:
                # Get the last day of the current month
                if current_date.month == 12:
                    next_month = current_date.replace(year=current_date.year + 1, month=1, day=1)
                else:
                    next_month = current_date.replace(month=current_date.month + 1, day=1)
                month_end = min(next_month - pd.Timedelta(days=1), end_date)
                date_ranges.append((current_date, month_end))
                current_date = next_month
                
        else:
            raise ValueError(f"Unsupported interval: {interval}. Use 'daily', 'weekly', or 'monthly'")
            
        return date_ranges

    async def mutations_over_time(
            self, 
            mutations: List[str], 
            mutation_type: MutationType, 
            date_range: Tuple[datetime, datetime], 
            locationName: str,
            interval: str = "daily"
        ) -> pd.DataFrame:
        """
        Fetches mutation counts, coverage, and frequency using component endpoints for specified time intervals.

        Args:
            mutations (List[str]): List of mutations to fetch data for.
            mutation_type (MutationType): Type of mutations (NUCLEOTIDE or AMINO_ACID).
            date_range (Tuple[datetime, datetime]): Tuple containing start and end dates for the data range.
            locationName (str): Location name to filter by.
            interval (str): Time interval - "daily" (default), "weekly", or "monthly".

        Returns:
            pd.DataFrame: A MultiIndex DataFrame with mutation and samplingDate as the index, 
                         and count, coverage, and frequency as columns.
        """
        try:
            # Generate date ranges based on the specified interval
            date_ranges = self._generate_date_ranges(date_range, interval)
            
            # Choose the appropriate component endpoint based on mutation type
            if mutation_type == MutationType.AMINO_ACID:
                api_data = await self.component_aminoAcidMutationsOverTime(mutations, date_ranges, locationName)
            elif mutation_type == MutationType.NUCLEOTIDE:
                api_data = await self.component_nucleotideMutationsOverTime(mutations, date_ranges, locationName)
            else:
                raise ValueError(f"Unsupported mutation type: {mutation_type}")

            # Parse the API response (no need to check for "error" key anymore as we raise APIError)
            records = []
            api_data_content = api_data.get(DATA, {})
            api_mutations = api_data_content.get(MUTATIONS, [])
            api_date_ranges = api_data_content.get(DATE_RANGES, [])
            data_matrix = api_data_content.get(DATA, [])

            # Debug logging
            logging.debug(f"mutations_over_time: Received {len(api_mutations)} mutations, {len(api_date_ranges)} date ranges")

            # Process the data matrix
            for i, mutation in enumerate(api_mutations):
                for j, date_range_info in enumerate(api_date_ranges):
                    if i < len(data_matrix) and j < len(data_matrix[i]):
                        mutation_data = data_matrix[i][j]
                        
                        # Extract count and coverage from the API response
                        count = mutation_data.get(COUNT, 0)
                        coverage = mutation_data.get(COVERAGE, 0)
                        
                        # Calculate frequency from count and coverage
                        frequency = count / coverage if coverage > 0 else pd.NA
                        
                        # For interval-based data, use the start date as the samplingDate
                        # or use the midpoint for better representation
                        start_date = pd.to_datetime(date_range_info[DATE_FROM])
                        end_date = pd.to_datetime(date_range_info[DATE_TO])
                        
                        if interval == "daily":
                            samplingDate = start_date.strftime('%Y-%m-%d')
                        else:
                            # Use midpoint for weekly/monthly intervals
                            midpoint = start_date + (end_date - start_date) / 2
                            samplingDate = midpoint.strftime('%Y-%m-%d')
                        
                        # Add all records, even those with coverage = 0
                        # This allows us to see when data is missing vs when mutations don't exist
                        records.append({
                            DF_MUTATION: mutation,
                            DF_SAMPLING_DATE: samplingDate,
                            DF_COUNT: count,
                            DF_COVERAGE: coverage,
                            DF_FREQUENCY: frequency
                        })

            logging.debug(f"Created {len(records)} records from component API data")

            # Create DataFrame from records
            df = pd.DataFrame(records)

            # Check for and handle duplicates before setting MultiIndex
            if not df.empty and DF_MUTATION in df.columns and DF_SAMPLING_DATE in df.columns:
                # Check for duplicates
                duplicates = df.duplicated(subset=[DF_MUTATION, DF_SAMPLING_DATE], keep=False)
                if duplicates.any():
                    logging.warning(f"Found {duplicates.sum()} duplicate mutation-date combinations, removing duplicates")
                    # Keep first occurrence of each duplicate, preferring non-zero values
                    df = df.drop_duplicates(subset=[DF_MUTATION, DF_SAMPLING_DATE], keep='first')
                    logging.debug(f"After deduplication: {len(df)} records remain")
                
                df.set_index([DF_MUTATION, DF_SAMPLING_DATE], inplace=True)
            else:
                # Create empty DataFrame with proper MultiIndex structure
                df = pd.DataFrame(columns=[DF_COUNT, DF_COVERAGE, DF_FREQUENCY])
                df.index = pd.MultiIndex.from_tuples([], names=[DF_MUTATION, DF_SAMPLING_DATE])
            return df

        except APIError as api_error:
            # Log the API error and return empty DataFrame
            logging.error(f"APIError encountered in mutations_over_time: {api_error}")
            df = pd.DataFrame(columns=[DF_COUNT, DF_COVERAGE, DF_FREQUENCY])
            df.index = pd.MultiIndex.from_tuples([], names=[DF_MUTATION, DF_SAMPLING_DATE])
            return df
        except Exception as e:
            logging.error(f"Error in mutations_over_time: {e}")
            # Return empty DataFrame with proper MultiIndex structure
            df = pd.DataFrame(columns=[DF_COUNT, DF_COVERAGE, DF_FREQUENCY])
            df.index = pd.MultiIndex.from_tuples([], names=[DF_MUTATION, DF_SAMPLING_DATE])
            return df
