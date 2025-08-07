"""Implements the Wiseloculus API Queries."""

import logging
import aiohttp
import asyncio
from typing import Optional, List, Tuple, Any, Union
from datetime import datetime

import pandas as pd

from .lapis import Lapis
from interface import MutationType

from process.mutations import get_symbols_for_mutation_type



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
            "fields": ["sampling_date"]  
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
            timeout = aiohttp.ClientTimeout(total=5)  # 5 second timeout
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
        
    
    def fetch_counts_coverage_freq(self, mutations: List[str], mutation_type : MutationType, date_range: Tuple[datetime, datetime], location_name: str) -> pd.DataFrame:
        """Fetches mutation counts, coverage, and frequency for a list of nucleotide mutations over a date range.

        Args:
            mutations (list): List of nucleotide mutations to fetch data for.
            date_range (tuple): Tuple containing start and end dates for the data range.

        Returns:
            pd.DataFrame: A MultiIndex DataFrame with mutation and sampling_date as the index, and count, coverage, and frequency as columns.
        """

        try:
            all_data = asyncio.run(self.fetch_mutation_counts_and_coverage(mutations, mutation_type, date_range, location_name))

            # Flatten the data into a list of records
            records = []
            for mutation_data in all_data:
                mutation = mutation_data["mutation"]
                for stratified in mutation_data["stratified"]:
                    records.append({
                        "mutation": mutation,
                        "sampling_date": stratified["sampling_date"],
                        "count": stratified["count"],
                        "coverage": stratified["coverage"],
                        "frequency": stratified["frequency"]
                    })

            # Create a DataFrame from the records
            df = pd.DataFrame(records)

            # Set MultiIndex with mutation and sampling_date
            df.set_index(["mutation", "sampling_date"], inplace=True)

            # Return the DataFrame
            return df
        except Exception as e:
            logging.error(f"Error fetching mutation counts and coverage: {e}")
            # Return empty DataFrame with proper MultiIndex structure
            return pd.DataFrame(columns=["count", "coverage", "frequency"]).set_index(["mutation", "sampling_date"])

    async def sample_nucleotideMutations(
            self, 
            date_range: Tuple[datetime, datetime], 
            location_name: Optional[str] = None,
            min_proportion: float = 0.01,
        ) -> pd.DataFrame:
        """
        Fetches nucleotide mutations for a given date range and optional location.
        
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

        try:
            timeout = aiohttp.ClientTimeout(total=5)  # 5 second timeout
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    f'{self.server_ip}/sample/nucleotideMutations',
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
            logging.error(f"Error fetching nucleotide mutations: {e}")
            return pd.DataFrame()

    def mutations_over_time_dfs(
        self, 
        formatted_mutations: List[str], 
        mutation_type: MutationType, 
        date_range: Tuple[datetime, datetime], 
        location_name: str
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Fetch mutation data using the new fetch_counts_coverage_freq method.
        
        Args:
            formatted_mutations: List of mutation strings (e.g., ['A123T', 'C456G'] for nucleotides 
                               or ['ORF1a:V3449I'] for amino acids)
            mutation_type: Type of mutations (MutationType.NUCLEOTIDE or MutationType.AMINO_ACID)
            date_range: Tuple of (start_date, end_date) as datetime objects
            location_name: Name of the location to filter by
            
        Returns:
            Tuple of (counts_df, freq_df, coverage_freq_df) where:
            - counts_df: DataFrame with mutations as rows and dates as columns (with counts for backward compatibility)
            - freq_df: DataFrame with mutations as rows and dates as columns (with frequency values for plotting)
            - coverage_freq_df: MultiIndex DataFrame with detailed count, coverage, and frequency data
            
        Raises:
            TypeError: If formatted_mutations is not a list of strings
            ValueError: If formatted_mutations is empty or contains invalid mutation formats
        """
        # Type validation
        if not isinstance(formatted_mutations, list):
            raise TypeError(f"formatted_mutations must be a list of strings, got {type(formatted_mutations).__name__}: {formatted_mutations}")
        
        if not formatted_mutations:
            # Return empty DataFrames with proper structure when no mutations provided
            logging.warning("No mutations provided to mutations_over_time_dfs, returning empty DataFrames")
            dates = pd.date_range(date_range[0], date_range[1]).strftime('%Y-%m-%d')
            empty_counts_df = pd.DataFrame(columns=list(dates))
            empty_freq_df = pd.DataFrame(columns=list(dates))
            # Create empty MultiIndex DataFrame properly
            empty_coverage_df = pd.DataFrame(columns=["count", "coverage", "frequency"])
            empty_coverage_df.index = pd.MultiIndex.from_tuples([], names=["mutation", "sampling_date"])
            return empty_counts_df, empty_freq_df, empty_coverage_df
            
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

        # Fetch comprehensive data using the new method
        coverage_freq_df = self.fetch_counts_coverage_freq(
            formatted_mutations, mutation_type, date_range, location_name
        )
        
        # Get dates from date_range for consistency
        dates = pd.date_range(date_range[0], date_range[1]).strftime('%Y-%m-%d')
        
        # Create DataFrames with mutations as rows and dates as columns
        counts_df = pd.DataFrame(index=formatted_mutations, columns=list(dates))
        freq_df = pd.DataFrame(index=formatted_mutations, columns=list(dates))
        
        # Fill the counts and frequency DataFrames from the MultiIndex DataFrame
        if not coverage_freq_df.empty:
            for mutation in formatted_mutations:
                if mutation in coverage_freq_df.index.get_level_values('mutation'):
                    mutation_data = coverage_freq_df.loc[mutation]
                    for date in mutation_data.index:
                        # Handle 'NA' values from the API
                        count_val = mutation_data.loc[date, 'count']
                        freq_val = mutation_data.loc[date, 'frequency']
                        
                        if count_val != 'NA':
                            counts_df.at[mutation, date] = count_val
                        
                        if freq_val != 'NA':
                            freq_df.at[mutation, date] = freq_val
        
        return counts_df, freq_df, coverage_freq_df