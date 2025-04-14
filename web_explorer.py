import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import yaml
import requests # Add requests import
import logging # Import the logging module

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Load configuration from config.yaml
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

server_ip = config.get('server', {}).get('lapis_address', 'http://default_ip:8000')


def app():
    
    ## Add a title
    st.title("POC: Fast Short Read Querying 1-Month")
    st.markdown("## Dynamic Mutation Heatmap Amino Acids")  

    ## Add a subheader
    st.markdown("### This page allows you to explore mutations over time by gene and proportion.")
    
    ## select dat range
    st.write("Select a date range:")
    date_range = st.date_input("Select a date range:", [pd.to_datetime("2025-02-10"), pd.to_datetime("2025-03-8")])

    ## Add a horizontal line
    st.markdown("---")

    start_date = date_range[0].strftime("%Y-%m-%d")
    end_date = date_range[1].strftime("%Y-%m-%d")


    ## Fetch locations from API
    locations = ["Zürich (ZH)", "Lugano (TI)", "Chur (GR)"] # Start with default/fallback
    try:
        location_url = 'http://88.198.54.174/sample/aggregated?fields=location_name&limit=100&dataFormat=JSON&downloadAsFile=false'
        logging.info(f"Attempting to fetch locations from: {location_url}")
        st.info(f"Attempting to fetch locations from API...") # User-facing info
        response = requests.get(location_url, headers={'accept': 'application/json'})
        response.raise_for_status() # Raise an exception for bad status codes
        location_data = response.json()
        fetched_locations = [item['location_name'] for item in location_data.get('data', []) if 'location_name' in item]

        if fetched_locations:
            locations = fetched_locations
            logging.info(f"Successfully fetched locations: {locations}")
            st.success("Successfully fetched locations from API.") # User-facing success
        else:
            logging.warning("API call successful but returned no locations. Using default values.")
            st.warning("Could not fetch locations from API (empty list returned), using default values.") # User-facing warning
            # locations remains the default list initialized before the try block
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching locations: {e}", exc_info=True)
        st.error(f"Error fetching locations: {e}. Using default values.") # User-facing error
        # locations remains the default list initialized before the try block
    except Exception as e: # Catch potential JSON decoding errors or other issues
        logging.error(f"An unexpected error occurred during location fetching: {e}", exc_info=True)
        st.error(f"An unexpected error occurred: {e}. Using default values.") # User-facing error
        # locations remains the default list initialized before the try block

    location = st.selectbox("Select Location:", locations)

    # Amino Acids or Nuclitides
    
    sequence_type = st.selectbox("Select Sequence Type:", ["Amino Acids", "Nucleotides"])

    sequence_type_value = "amino acid" if sequence_type == "Amino Acids" else "nucleotide"

    components.html(
        f"""
        <html>
        <head>
        <script type="module" src="https://unpkg.com/@genspectrum/dashboard-components@latest/standalone-bundle/dashboard-components.js"></script>
        <link rel="stylesheet" href="https://unpkg.com/@genspectrum/dashboard-components@latest/dist/style.css" />
        </head>
            <body>
            <!-- Component documentation: https://genspectrum.github.io/dashboard-components/?path=/docs/visualization-mutations-over-time--docs -->
            <gs-app lapis="{server_ip}">
                <gs-mutations-over-time
                lapisFilter='{{"sampling_dateFrom":"{start_date}", "sampling_dateTo": "{end_date}", "location_name": "{location}"}}'
                sequenceType='{sequence_type_value}'
                views='["grid"]'
                width='100%'
                height='100%'
                granularity='day'
                lapisDateField='sampling_date'
                pageSizes='[50, 30, 20, 10]'
                />
            </gs-app>
            </head>
            <body>
            </body>
        </html>
    """,
        height=4000,
    )


if __name__ == "__main__":
    app()