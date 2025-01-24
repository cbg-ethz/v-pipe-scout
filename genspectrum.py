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
            <gs-app lapis="https://lapis.cov-spectrum.org/open/v2">
                <gs-mutations-over-time
                lapisFilter='{"region":"Europe","country":"Switzerland","dateFrom":"2024-01-23","nextcladePangoLineage":"JN.1*"}'
                sequenceType='amino acid'
                views='["grid"]'
                width='100%'
                height='100%'
                granularity='week'
                lapisDateField='date'
                />
            </gs-app>
                        <!-- Component documentation: https://genspectrum.github.io/dashboard-components/?path=/docs/visualization-mutations-over-time--docs -->
            <gs-app lapis="http://localhost:8080/2">
                <gs-mutations-over-time
                lapisFilter='{"sampling_dateFrom":"2024-08-23", "sampling_dateTo": "2024-10-23"}'
                sequenceType='amino acid'
                views='["grid"]'
                width='100%'
                height='100%'
                granularity='week'
                lapisDateField='sampling_date'
                />
            </gs-app>

            </head>
            <body>
            </body>
        </html>
    """,
        height=600,
    )

    ## Allow for user input by Gene

    ### Let user select a Data Range

    ### Allow for user input by Proportions

    ### Allow for Choice of Nucliotides // Amino Acids

    ### Make Query for list of mutations wiht Such proportions
    ### Ensure this list is not to large to be displayed

    date_range = [pd.to_datetime("2024-09-30"), pd.to_datetime("2024-10-16")]
    gene = ["ORF1a"]
    proportions = [0.05, 0.5]
    sequence_type = "amino acid"

    data = asyncio.run(fetch_data())

    # Display the data
    st.write(data)


### For each mutation in the list get the counts of the mutation over time

### Display the counts of the mutation over time



if __name__ == "__main__":
    app()