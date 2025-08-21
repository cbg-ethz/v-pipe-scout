"""Implements the Wiseloculus API Queries."""

import logging
import aiohttp
import asyncio
from typing import Optional, List, Tuple, Any
from datetime import datetime

import pandas as pd

from .lapis import Lapis
from .exceptions import APIError
from interface import MutationType

from process.mutations import get_symbols_for_mutation_type

# Constants for fallback date range
FALLBACK_START_DATE, FALLBACK_END_DATE = datetime(2025, 1, 1), datetime(2025, 12, 31)

class WiseLoculusLapis(Lapis):
    """Wise-Loculus Instance API"""

    async def fetch_sample_aggregated(
            self,
            session: aiohttp.ClientSession, 
            mutation: str, 
            mutation_type: MutationType, 
            date_range: Tuple[datetime, datetime], 
            location_name: Optional[str] = None
            ) -> dict[str, Any]:
        """
        Fetches aggregated sample data for a given mutation, type, date range, and optional location.
        """
        payload: dict[str, Any] = { 
            "sampling_dateFrom": date_range[0].strftime('%Y-%m-%d'),
            "sampling_dateTo": date_range[1].strftime('%Y-%m-%d'),
            "fields": ["sampling_date"],
            "orderBy": ["sampling_date"]  # API expects array, not string
        }

        if mutation_type == MutationType.AMINO_ACID:
            payload["aminoAcidMutations"] = [mutation]
        elif mutation_type == MutationType.NUCLEOTIDE:
            payload["nucleotideMutations"] = [mutation]
        else:
            logging.error(f"Unknown mutation type: {mutation_type}")
            return {"mutation": mutation, "data": None, "error": "Unknown mutation type"}

        if location_name:
            payload["location_name"] = location_name  

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
                    logging.error(f"Failed to fetch data for mutation {mutation} (type: {mutation_type}, location: {location_name}).")
                    logging.error(f"Status code: {response.status}")
                    logging.error(await response.text())
                    return {"mutation": mutation, "data": None, "status_code": response.status, "error_details": await response.text()}
        except Exception as e:
            logging.error(f"Connection error fetching data for mutation {mutation}: {e}")
            return {"mutation": mutation, "data": None, "error": str(e)}

    async def fetch_mutation_counts(
            self, 
            mutations: List[str], 
            mutation_type: MutationType, 
            date_range: Tuple[datetime, datetime], 
            location_name: Optional[str] = None
            ) -> List[dict[str, Any]]:
        """
        Fetches the mutation counts for a list of mutations, specifying their type and optional location.
        """
        # validate mutation_type
        if mutation_type not in [MutationType.AMINO_ACID, MutationType.NUCLEOTIDE]:
            raise ValueError(f"Unsupported mutation type: {mutation_type}")

        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_sample_aggregated(session, m, mutation_type, date_range, location_name) for m in mutations]
            return await asyncio.gather(*tasks, return_exceptions=True)  # return_exceptions to avoid failing the entire batch
        
    async def _fetch_coverage_for_mutation(
            self, 
            session: aiohttp.ClientSession,
            mutation: str,
            mutation_type: MutationType,
            date_range: Tuple[datetime, datetime],
            location_name: Optional[str]
        ) -> Tuple[dict[str, int], dict[str, dict]]:
        """
        Fetches coverage data for all possible symbols at a mutation position.
        Returns (coverage_data, stratified_results).
        """
        symbols = get_symbols_for_mutation_type(mutation_type)
        mutation_base = mutation[:-1]  # Everything except the last character
        
        # Fetch data for all possible symbols at this position
        coverage_tasks = [
            self.fetch_sample_aggregated(session, f"{mutation_base}{symbol}", mutation_type, date_range, location_name)
            for symbol in symbols
        ]
        coverage_results = await asyncio.gather(*coverage_tasks)

        # Parse coverage_results to extract total counts for each symbol
        coverage_data = {
            symbol: sum(entry['count'] for entry in item['data']) if item['data'] else 0
            for symbol, item in zip(symbols, coverage_results)
        }

        # Stratify results by sampling_date
        stratified_results = {}
        for symbol, item in zip(symbols, coverage_results):
            if item['data']:
                for entry in item['data']:
                    date = entry['sampling_date']
                    count = entry['count']
                    if date not in stratified_results:
                        stratified_results[date] = {"counts": {s: 0 for s in symbols}, "coverage": 0}
                    stratified_results[date]["counts"][symbol] += count
                    stratified_results[date]["coverage"] += count

        return coverage_data, stratified_results

    def _calculate_mutation_result(
            self, 
            mutation: str, 
            coverage_data: dict[str, int], 
            stratified_results: dict[str, dict]
        ) -> dict[str, Any]:
        """
        Calculates the final result for a mutation including overall and stratified statistics.
        """
        target_symbol = mutation[-1]
        total_coverage = sum(coverage_data.values())
        frequency = coverage_data.get(target_symbol, 0) / total_coverage if total_coverage > 0 else 0

        # Calculate frequency for the target symbol on each date
        for date, data in stratified_results.items():
            data["frequency"] = data["counts"].get(target_symbol, 0) / data["coverage"] if data["coverage"] > 0 else 0

        # Build stratified data with proper NA handling
        stratified_data = [
            {
                "sampling_date": date,
                "coverage": data["coverage"],
                "frequency": data["frequency"] if data["coverage"] > 0 else "NA",
                "count": data["counts"].get(target_symbol, 0) if data["coverage"] > 0 else "NA"
            }
            for date, data in stratified_results.items()
        ]

        return {
            "mutation": mutation,
            "coverage": total_coverage,
            "frequency": frequency,
            "counts": coverage_data,
            "stratified": stratified_data
        }

    async def fetch_mutation_counts_and_coverage(
            self, 
            mutations: List[str], 
            mutation_type: MutationType, 
            date_range: Tuple[datetime, datetime], 
            location_name: Optional[str] = None
        ) -> List[dict[str, Any]]:
        """
        Fetches the mutation counts and coverage for a list of mutations, specifying their type and optional location.

        Note Amino Acid mutations require gene:change name "ORF1a:V3449I" while nucleotide mutations can be in the form "A123T".
        """
  
        try:
            timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout
            async with aiohttp.ClientSession(timeout=timeout) as session:
                combined_results = []

                for mutation in mutations:
                    # Fetch coverage data for all possible symbols at this position
                    coverage_data, stratified_results = await self._fetch_coverage_for_mutation(
                        session, mutation, mutation_type, date_range, location_name
                    )
                    
                    # Calculate and append the result for this mutation
                    mutation_result = self._calculate_mutation_result(mutation, coverage_data, stratified_results)
                    combined_results.append(mutation_result)

                return combined_results
        except Exception as e:
            logging.error(f"Error fetching mutation counts and coverage: {e}")
            # Return empty results for all mutations
            return [{"mutation": mutation, "coverage": 0, "frequency": 0, "counts": {}, "stratified": []} for mutation in mutations]
        
    
    async def fetch_counts_coverage_freq(self, mutations: List[str], mutation_type : MutationType, date_range: Tuple[datetime, datetime], location_name: str) -> pd.DataFrame:
        """Fetches mutation counts, coverage, and frequency for a list of nucleotide mutations over a date range.

        Args:
            mutations (list): List of nucleotide mutations to fetch data for.
            date_range (tuple): Tuple containing start and end dates for the data range.

        Returns:
            pd.DataFrame: A MultiIndex DataFrame with mutation and sampling_date as the index, and count, coverage, and frequency as columns.
        """

        try:
            all_data = await self.fetch_mutation_counts_and_coverage(mutations, mutation_type, date_range, location_name)

            # Debug logging
            logging.debug(f"fetch_counts_coverage_freq: Received {len(all_data)} mutation results")

            # Flatten the data into a list of records
            records = []
            for mutation_data in all_data:
                mutation = mutation_data["mutation"]
                stratified_data = mutation_data.get("stratified", [])
                logging.debug(f"Mutation {mutation}: {len(stratified_data)} stratified entries")
                
                for stratified in stratified_data:
                    records.append({
                        "mutation": mutation,
                        "sampling_date": stratified["sampling_date"],
                        "count": stratified["count"],
                        "coverage": stratified["coverage"],
                        "frequency": stratified["frequency"]
                    })

            logging.debug(f"Created {len(records)} records from API data")

            # Create a DataFrame from the records
            df = pd.DataFrame(records)

            # Only set MultiIndex if we have data and the required columns exist
            if not df.empty and "mutation" in df.columns and "sampling_date" in df.columns:
                df.set_index(["mutation", "sampling_date"], inplace=True)
            else:
                # Create empty DataFrame with proper MultiIndex structure
                df = pd.DataFrame(columns=["count", "coverage", "frequency"])
                df.index = pd.MultiIndex.from_tuples([], names=["mutation", "sampling_date"])

            # Return the DataFrame
            return df
        except Exception as e:
            logging.error(f"Error fetching mutation counts and coverage: {e}")
            # Return empty DataFrame with proper MultiIndex structure
            df = pd.DataFrame(columns=["count", "coverage", "frequency"])
            df.index = pd.MultiIndex.from_tuples([], names=["mutation", "sampling_date"])
            return df

    async def sample_mutations(
            self, 
            type: MutationType,
            date_range: Tuple[datetime, datetime], 
            location_name: Optional[str] = None,
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
            "sampling_dateFrom": date_range[0].strftime('%Y-%m-%d'),
            "sampling_dateTo": date_range[1].strftime('%Y-%m-%d'),
            "location_name": location_name,
            "minProportion": min_proportion, 
            "orderBy": "proportion",
            "limit": 10000,  # Adjust limit as needed
            "dataFormat": "JSON",
            "downloadAsFile": "false"
        }

        # Add mutation filters if provided
        if nucleotide_mutations:
            payload["nucleotideMutations"] = nucleotide_mutations
        if amino_acid_mutations:
            payload["aminoAcidMutations"] = amino_acid_mutations

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
    

    async def mutations_over_time_fallback(
        self, 
        formatted_mutations: List[str], 
        mutation_type: MutationType, 
        date_range: Tuple[datetime, datetime], 
        location_name: str
    ) -> pd.DataFrame:
        """
        Fetch mutation data using the fallback fetch_counts_coverage_freq method.
        Returns a MultiIndex DataFrame compatible with mutations_over_time.
        
        Args:
            formatted_mutations: List of mutation strings (e.g., ['A123T', 'C456G'] for nucleotides 
                               or ['ORF1a:V3449I'] for amino acids)
            mutation_type: Type of mutations (MutationType.NUCLEOTIDE or MutationType.AMINO_ACID)
            date_range: Tuple of (start_date, end_date) as datetime objects
            location_name: Name of the location to filter by
            
        Returns:
            pd.DataFrame: MultiIndex DataFrame with (mutation, sampling_date) as index 
                         and count, coverage, frequency as columns
            
        Raises:
            TypeError: If formatted_mutations is not a list of strings
            ValueError: If formatted_mutations is empty or contains invalid mutation formats
        """
        # Type validation
        if not isinstance(formatted_mutations, list):
            raise TypeError(f"formatted_mutations must be a list of strings, got {type(formatted_mutations).__name__}: {formatted_mutations}")
        
        if not formatted_mutations:
            # Return empty DataFrame with proper MultiIndex structure when no mutations provided
            logging.warning("No mutations provided to mutations_over_time_fallback, returning empty DataFrame")
            empty_coverage_df = pd.DataFrame(columns=["count", "coverage", "frequency"])
            empty_coverage_df.index = pd.MultiIndex.from_tuples([], names=["mutation", "sampling_date"])
            return empty_coverage_df
            
        if not all(isinstance(m, str) for m in formatted_mutations):
            raise TypeError(f"All elements in formatted_mutations must be strings, got: {[type(m).__name__ for m in formatted_mutations]}")
        
        # Basic format validation for mutations
        for mutation in formatted_mutations:
            if not mutation.strip():  # Check for empty or whitespace-only strings
                raise ValueError(f"Invalid mutation format: empty or whitespace-only string")
            
            if mutation_type == MutationType.NUCLEOTIDE:
                # Nucleotide mutations should be like "A123T" - at least 3 characters
                if len(mutation) < 3:
                    raise ValueError(f"Invalid nucleotide mutation format: '{mutation}'. Expected format like 'A123T'")
            elif mutation_type == MutationType.AMINO_ACID:
                # Amino acid mutations should contain ":" for gene:mutation format
                if ":" not in mutation:
                    raise ValueError(f"Invalid amino acid mutation format: '{mutation}'. Expected format like 'ORF1a:V3449I'")

        # Fetch comprehensive data using the existing async method
        coverage_freq_df = await self.fetch_counts_coverage_freq(
            formatted_mutations, mutation_type, date_range, location_name
        )
        
        return coverage_freq_df

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
                    params={'fields': 'sampling_date'},
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
                            if 'sampling_date' in entry:
                                try:
                                    date_obj = datetime.strptime(entry['sampling_date'], '%Y-%m-%d')
                                    dates.append(date_obj)
                                except ValueError as e:
                                    logging.warning(f"Invalid date format: {entry['sampling_date']}: {e}")
                        
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
            location_name: str
        ) -> dict[str, Any]:
        """
        Helper method for fetching mutations over time data from component endpoints.
        
        Args:
            endpoint: The API endpoint name (e.g., "aminoAcidMutationsOverTime")
            mutation_type_name: Display name for logging (e.g., "amino acid")
            mutations: List of mutations
            date_ranges: List of date range tuples
            location_name: Location name to filter by
            
        Returns:
            Dict containing the API response with mutations, dateRanges, and data matrix
        """
        payload = {
            "filters": {
                "location_name": location_name
            },
            "includeMutations": mutations,
            "dateRanges": [
                {
                    "dateFrom": date_range[0].strftime('%Y-%m-%d'),
                    "dateTo": date_range[1].strftime('%Y-%m-%d')
                }
                for date_range in date_ranges
            ],
            "dateField": "sampling_date"
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
            location_name: str
        ) -> dict[str, Any]:
        """
        Fetches amino acid mutations over time for a given location and specific date ranges.
        Returns counts and coverage for each mutation and date range.
        
        Args:
            mutations: List of amino acid mutations in format ["S:N501Y", "N:N8N"]
            date_ranges: List of date range tuples [(start_date, end_date), ...]
            location_name: Location name to filter by
            
        Returns:
            Dict containing the API response with mutations, dateRanges, and data matrix
        """
        return await self._component_mutations_over_time(
            endpoint="aminoAcidMutationsOverTime",
            mutation_type_name="amino acid",
            mutations=mutations,
            date_ranges=date_ranges,
            location_name=location_name
        )

    async def component_nucleotideMutationsOverTime(
            self, 
            mutations: List[str], 
            date_ranges: List[Tuple[datetime, datetime]],
            location_name: str
        ) -> dict[str, Any]:
        """
        Fetches nucleotide mutations over time for a given location and specific date ranges.
        Returns counts and coverage for each mutation and date range.
        
        Args:
            mutations: List of nucleotide mutations in format ["A5341C", "C34G"]
            date_ranges: List of date range tuples [(start_date, end_date), ...]
            location_name: Location name to filter by
            
        Returns:
            Dict containing the API response with mutations, dateRanges, and data matrix
        """
        return await self._component_mutations_over_time(
            endpoint="nucleotideMutationsOverTime",
            mutation_type_name="nucleotide",
            mutations=mutations,
            date_ranges=date_ranges,
            location_name=location_name
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
            location_name: str,
            interval: str = "daily"
        ) -> pd.DataFrame:
        """
        Fetches mutation counts, coverage, and frequency using component endpoints for specified time intervals.

        Args:
            mutations (List[str]): List of mutations to fetch data for.
            mutation_type (MutationType): Type of mutations (NUCLEOTIDE or AMINO_ACID).
            date_range (Tuple[datetime, datetime]): Tuple containing start and end dates for the data range.
            location_name (str): Location name to filter by.
            interval (str): Time interval - "daily" (default), "weekly", or "monthly".

        Returns:
            pd.DataFrame: A MultiIndex DataFrame with mutation and sampling_date as the index, 
                         and count, coverage, and frequency as columns.
        """
        try:
            # Generate date ranges based on the specified interval
            date_ranges = self._generate_date_ranges(date_range, interval)
            
            # Choose the appropriate component endpoint based on mutation type
            if mutation_type == MutationType.AMINO_ACID:
                api_data = await self.component_aminoAcidMutationsOverTime(mutations, date_ranges, location_name)
            elif mutation_type == MutationType.NUCLEOTIDE:
                api_data = await self.component_nucleotideMutationsOverTime(mutations, date_ranges, location_name)
            else:
                raise ValueError(f"Unsupported mutation type: {mutation_type}")

            # Parse the API response (no need to check for "error" key anymore as we raise APIError)
            records = []
            api_data_content = api_data.get("data", {})
            api_mutations = api_data_content.get("mutations", [])
            api_date_ranges = api_data_content.get("dateRanges", [])
            data_matrix = api_data_content.get("data", [])

            # Debug logging
            logging.debug(f"mutations_over_time: Received {len(api_mutations)} mutations, {len(api_date_ranges)} date ranges")

            # Process the data matrix
            for i, mutation in enumerate(api_mutations):
                for j, date_range_info in enumerate(api_date_ranges):
                    if i < len(data_matrix) and j < len(data_matrix[i]):
                        mutation_data = data_matrix[i][j]
                        
                        # Extract count and coverage from the API response
                        count = mutation_data.get("count", 0)
                        coverage = mutation_data.get("coverage", 0)
                        
                        # Calculate frequency from count and coverage
                        frequency = count / coverage if coverage > 0 else pd.NA
                        
                        # For interval-based data, use the start date as the sampling_date
                        # or use the midpoint for better representation
                        start_date = pd.to_datetime(date_range_info["dateFrom"])
                        end_date = pd.to_datetime(date_range_info["dateTo"])
                        
                        if interval == "daily":
                            sampling_date = start_date.strftime('%Y-%m-%d')
                        else:
                            # Use midpoint for weekly/monthly intervals
                            midpoint = start_date + (end_date - start_date) / 2
                            sampling_date = midpoint.strftime('%Y-%m-%d')
                        
                        # Add all records, even those with coverage = 0
                        # This allows us to see when data is missing vs when mutations don't exist
                        records.append({
                            "mutation": mutation,
                            "sampling_date": sampling_date,
                            "count": count,
                            "coverage": coverage,
                            "frequency": frequency
                        })

            logging.debug(f"Created {len(records)} records from component API data")

            # Create DataFrame from records
            df = pd.DataFrame(records)

            # Set MultiIndex if we have data
            if not df.empty and "mutation" in df.columns and "sampling_date" in df.columns:
                df.set_index(["mutation", "sampling_date"], inplace=True)
            else:
                # Create empty DataFrame with proper MultiIndex structure
                df = pd.DataFrame(columns=["count", "coverage", "frequency"])
                df.index = pd.MultiIndex.from_tuples([], names=["mutation", "sampling_date"])
            return df

        except APIError as api_error:
            # Handle API failures by falling back to the slower legacy method
            logging.warning(f"APIError encountered in mutations_over_time: {api_error}")
            logging.info("Switching to fallback method (mutations_over_time_fallback) - this may be slower")
            
            try:
                df = await self.mutations_over_time_fallback(
                    formatted_mutations=mutations,
                    mutation_type=mutation_type,
                    date_range=date_range,
                    location_name=location_name
                )
                
                # Add a marker to indicate fallback was used - components can detect this
                if hasattr(df, 'attrs'):
                    df.attrs['fallback_used'] = True
                    df.attrs['fallback_reason'] = f"Primary API failed: {str(api_error)}"
                
                logging.info("Successfully retrieved data using fallback method")
                return df
                
            except Exception as fallback_error:
                logging.error(f"Fallback method also failed: {fallback_error}")
                # If fallback also fails, return empty DataFrame
                df = pd.DataFrame(columns=["count", "coverage", "frequency"])
                df.index = pd.MultiIndex.from_tuples([], names=["mutation", "sampling_date"])
                if hasattr(df, 'attrs'):
                    df.attrs['fallback_used'] = True
                    df.attrs['fallback_failed'] = True
                    df.attrs['fallback_reason'] = f"Primary API failed: {str(api_error)}, Fallback failed: {str(fallback_error)}"
                return df
        except Exception as e:
            logging.error(f"Error in mutations_over_time: {e}")
            # Return empty DataFrame with proper MultiIndex structure
            df = pd.DataFrame(columns=["count", "coverage", "frequency"])
            df.index = pd.MultiIndex.from_tuples([], names=["mutation", "sampling_date"])
            return df

