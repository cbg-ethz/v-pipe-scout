"""Implements the Wiseloculus API Queries."""

import logging
import aiohttp
import asyncio
from .lapis import Lapis

class WiseLoculusLapis(Lapis):
    async def fetch_data(self, session, mutation, date_range):
        payload = {
            "aminoAcidMutations": [mutation],
            "sampling_dateFrom": date_range[0].strftime('%Y-%m-%d'),
            "sampling_dateTo": date_range[1].strftime('%Y-%m-%d'),
            "fields": ["sampling_date"]
        }
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
                logging.error(f"Failed to fetch data for mutation {mutation}.")
                logging.error(f"Status code: {response.status}")
                logging.error(await response.text())
                return {"mutation": mutation, "data": None}

    async def fetch_single_mutation(self, mutation, date_range):
        async with aiohttp.ClientSession() as session:
            return await self.fetch_data(session, mutation, date_range)

    async def fetch_all_data(self, mutations, date_range):
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_data(session, mutation, date_range) for mutation in mutations]
            return await asyncio.gather(*tasks)