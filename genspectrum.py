import streamlit as st
import streamlit.components.v1 as components
import aiohttp
import asyncio
import logging
import yaml

import pandas as pd

LAPIS_URL = "http://localhost:8080/"


# Load configuration from config.yaml
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

server_ip = config.get('server', {}).get('lapis_address', 'http://default_ip:8000')

async def fetch_data():
    url = 'http://localhost:8080/sample/aminoAcidMutations'
    params = {
        'sampling_dateFrom': '2024-08-23',
        'sampling_dateTo': '2024-10-23',
        'minProportion': 0.5,
        'orderBy': 'proportion',
        'limit': 100,
        'downloadAsFile': 'false'
    }
    headers = {
        'accept': 'application/json'
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                logging.error(f"Failed to fetch data. Status code: {response.status}")

# To run the async function
# asyncio.run(fetch_data())

def app():
    # bootstrap 4 collapse example
    components.html(
        """
        <html>
        <head>
        <script type="module" src="https://unpkg.com/@genspectrum/dashboard-components@latest/standalone-bundle/dashboard-components.js"></script>
        <link rel="stylesheet" href="https://unpkg.com/@genspectrum/dashboard-components@latest/dist/style.css" />
        </head>
            <body>
            <!-- Component documentation: https://genspectrum.github.io/dashboard-components/?path=/docs/visualization-mutations-over-time--docs -->
            <gs-app lapis="http://localhost:8080">
                <gs-mutations-over-time
                lapisFilter='{"sampling_dateFrom":"2024-09-25", "sampling_dateTo": "2024-10-23"}'
                sequenceType='amino acid'
                views='["grid"]'
                width='100%'
                height='100%'
                granularity='day'
                lapisDateField='sampling_date'
                />
            </gs-app>
            </head>
            <body>
            </body>
        </html>
    """,
        height=3000,
    )


if __name__ == "__main__":
    app()