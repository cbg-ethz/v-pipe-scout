"""Implements the Wiseloculus API Queries."""

import logging
import aiohttp
import asyncio
import json # Added for json.dumps
from typing import Optional, List, Tuple, Any # Added Optional, List, Tuple, Any
from datetime import datetime # Added datetime for type hinting date_range
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

    async def fetch_single_mutation(self, mutation: str, mutation_type: str, date_range: Tuple[datetime, datetime], location_name: Optional[str] = None) -> dict[str, Any]:
        """
        Fetches data for a single mutation, specifying its type and optional location.
        """
        async with aiohttp.ClientSession() as session:
            return await self.fetch_sample_aggregated(session, mutation, mutation_type, date_range, location_name)

    async def fetch_all_data(self, mutations: List[str], mutation_type: str, date_range: Tuple[datetime, datetime], location_name: Optional[str] = None) -> List[dict[str, Any]]:
        """
        Fetches data for a list of mutations, specifying their type and optional location.
        """
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_sample_aggregated(session, m, mutation_type, date_range, location_name) for m in mutations]
            return await asyncio.gather(*tasks)
