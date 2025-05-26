"""Implements the Wiseloculus API Queries."""

import logging
import aiohttp
import asyncio
from typing import Optional, List, Tuple, Any 
from datetime import datetime

import pandas as pd

from .lapis import Lapis


class WiseLoculusLapis(Lapis):
    """Wise-Loculus Instance API"""

    async def fetch_sample_aggregated(
            self,
            session: aiohttp.ClientSession, 
            mutation: str, 
            mutation_type: str, 
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

        if mutation_type == "aminoAcid":
            payload["aminoAcidMutations"] = [mutation]
        elif mutation_type == "nucleotide":
            payload["nucleotideMutations"] = [mutation]
        else:
            logging.error(f"Unknown mutation type: {mutation_type}")
            return {"mutation": mutation, "data": None, "error": "Unknown mutation type"}

        if location_name:
            payload["location_name"] = location_name  

        logging.debug(f"Fetching sample aggregated with payload: {payload}")
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

    async def fetch_mutation_counts(
            self, 
            mutations: List[str], 
            mutation_type: str, 
            date_range: Tuple[datetime, datetime], 
            location_name: Optional[str] = None
            ) -> List[dict[str, Any]]:
        """
        Fetches the mutation counts for a list of mutations, specifying their type and optional location.
        """
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_sample_aggregated(session, m, mutation_type, date_range, location_name) for m in mutations]
            return await asyncio.gather(*tasks)
        

    async def fetch_mutation_counts_and_coverage(
            self, 
            mutations: List[str], 
            mutation_type: str, 
            date_range: Tuple[datetime, datetime], 
            location_name: Optional[str] = None
        ) -> List[dict[str, Any]]:
        """
        Fetches the mutation counts and coverage for a list of mutations, specifying their type and optional location.
        """

        if mutation_type not in ["nucleotide"]:
            logging.error(f"Unknown mutation type: {mutation_type}")
            raise NotImplementedError(f"Unknown mutation type: {mutation_type}")
        
        async with aiohttp.ClientSession() as session:
            combined_results = []

            for mutation in mutations:
                target_symbol = mutation[-1]  # The last character is the target nucleotide or amino acid
 
                if mutation_type == "aminoAcid":
                    amino_acids = ["A", "C", "D", "E", "F", "G", "H", "I", "K", 
                                    "L", "M", "N", "P", "Q", "R", "S", "T", 
                                    "V", "W", "Y"]
                    # For amino acid mutations, we need to fetch counts for all amino acids
                    coverage_tasks = [
                        self.fetch_sample_aggregated(session, f"{mutation[:-1]}{aa}", "aminoAcid", date_range, location_name)
                        for aa in amino_acids
                    ]
                    coverage_results = await asyncio.gather(*coverage_tasks)

                    # Parse coverage_results to extract counts for each nucleotide
                    coverage_data = {
                        nt: sum(entry['count'] for entry in item['data']) if item['data'] else 0
                        for nt, item in zip(amino_acids, coverage_results)
                    }
                    # Calculate total coverage
                    total_coverage = sum(coverage_data.values())

                    # Calculate frequency for the target nucleotide
                    frequency = coverage_data.get(target_symbol, 0) / total_coverage if total_coverage > 0 else 0

                    # Append the result for this mutation
                    combined_results.append({
                        "mutation": mutation,
                        "coverage": total_coverage,
                        "frequency": frequency,
                        "counts": coverage_data
                    })

                    # Stratify results by sampling_date
                    stratified_results = {}
                    for nt, item in zip(amino_acids, coverage_results):
                        for entry in item['data']:
                            date = entry['sampling_date']
                            count = entry['count']
                            if date not in stratified_results:
                                stratified_results[date] = {"counts": {n: 0 for n in amino_acids}, "coverage": 0}
                            stratified_results[date]["counts"][nt] += count
                            stratified_results[date]["coverage"] += count

                elif mutation_type == "nucleotide":
                    nucleotides = ['A', 'T', 'C', 'G']
                    # For nucleotide mutations, we fetch counts for A, T, C, G
                    # The mutation is expected to be in the format like "A456T"
                    coverage_tasks = [
                        self.fetch_sample_aggregated(session, f"{mutation[:-1]}{nt}", "nucleotide", date_range, location_name)
                        for nt in nucleotides
                    ]
                    coverage_results = await asyncio.gather(*coverage_tasks)

                    # Parse coverage_results to extract counts for each nucleotide
                    coverage_data = {
                        nt: sum(entry['count'] for entry in item['data']) if item['data'] else 0
                        for nt, item in zip(nucleotides, coverage_results)
                    }

                    # Calculate total coverage
                    total_coverage = sum(coverage_data.values())

                    # Calculate frequency for the target nucleotide
                    frequency = coverage_data.get(target_symbol, 0) / total_coverage if total_coverage > 0 else 0

                    # Append the result for this mutation
                    combined_results.append({
                        "mutation": mutation,
                        "coverage": total_coverage,
                        "frequency": frequency,
                        "counts": coverage_data
                    })

                    # Stratify results by sampling_date
                    stratified_results = {}
                    for nt, item in zip(nucleotides, coverage_results):
                        for entry in item['data']:
                            date = entry['sampling_date']
                            count = entry['count']
                            if date not in stratified_results:
                                stratified_results[date] = {"counts": {n: 0 for n in nucleotides}, "coverage": 0}
                            stratified_results[date]["counts"][nt] += count
                            stratified_results[date]["coverage"] += count
                else:
                    logging.error(f"Unknown mutation type: {mutation_type}")
                    raise NotImplementedError(f"Unknown mutation type: {mutation_type}")

                # Calculate frequency for the target nucleotide on each date
                for date, data in stratified_results.items():
                    data["frequency"] = data["counts"].get(target_symbol, 0) / data["coverage"] if data["coverage"] > 0 else 0

                # Append the stratified result for this mutation, ensuring NA for frequency and count if coverage is zero
                combined_results[-1]["stratified"] = [
                    {
                        "sampling_date": date,
                        "coverage": data["coverage"],
                        "frequency": data["frequency"] if data["coverage"] > 0 else "NA",
                        "count": data["counts"].get(target_symbol, 0) if data["coverage"] > 0 else "NA"
                    }
                    for date, data in stratified_results.items()
                ]

            return combined_results
        
    
    def fetch_counts_and_coverage_3D_df_nuc(self, mutations, date_range, location_name) -> pd.DataFrame:
        """Fetches mutation counts, coverage, and frequency for a list of nucleotide mutations over a date range.

        Args:
            mutations (list): List of nucleotide mutations to fetch data for.
            date_range (tuple): Tuple containing start and end dates for the data range.

        Returns:
            pd.DataFrame: A MultiIndex DataFrame with mutation and sampling_date as the index, and count, coverage, and frequency as columns.
        """
        mutation_type = "nucleotide"
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
