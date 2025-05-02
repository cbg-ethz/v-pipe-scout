"""Implements LAPIS API Queries. """

import logging
import requests
from urllib.parse import urlparse
import streamlit as st

class Lapis:
    def __init__(self, server_ip):
        self.server_ip = server_ip

    @staticmethod
    def parse_url_hostname(url_string):
        """Parses a URL string and returns the scheme and hostname."""
        try:
            parsed_url = urlparse(url_string)
            if parsed_url.hostname:
                address_no_port = f"{parsed_url.scheme}://{parsed_url.hostname}"
                logging.info(f"Parsed URL: {url_string}, Address without port: {address_no_port}")
                return address_no_port
            else:
                logging.warning(f"Could not parse hostname from {url_string}. Returning original.")
                return url_string # Fallback to the original URL
        except Exception as e:
            logging.error(f"Error parsing URL {url_string}: {e}", exc_info=True)
            return url_string # Fallback in case of any parsing error

    def fetch_locations(self, default_locations):
        """Fetches locations from the API endpoint."""
        address_no_port = self.parse_url_hostname(self.server_ip)
        location_url = f'{address_no_port}/sample/aggregated?fields=location_name&limit=100&dataFormat=JSON&downloadAsFile=false'
        try:
            logging.info(f"Attempting to fetch locations from: {location_url}")
            st.toast("Attempting to fetch locations from API...", icon="🔄") # Temporary toast
            response = requests.get(location_url, headers={'accept': 'application/json'})
            response.raise_for_status() # Raise an exception for bad status codes
            location_data = response.json()
            fetched_locations = [item['location_name'] for item in location_data.get('data', []) if 'location_name' in item]
            if fetched_locations:
                logging.info(f"Successfully fetched locations: {fetched_locations}")
                st.toast("Successfully fetched locations from API.", icon="✅") # Temporary toast
                return fetched_locations
            else:
                logging.warning("API call successful but returned no locations. Using default values.")
                st.warning("Could not fetch locations from API (empty list returned), using default values.") # User-facing warning
                return default_locations
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching locations: {e}", exc_info=True)
            st.error(f"Error fetching locations: {e}. Using default values.") # User-facing error
            return default_locations
        except Exception as e: # Catch potential JSON decoding errors or other issues
            logging.error(f"An unexpected error occurred during location fetching: {e}", exc_info=True)
            st.error(f"An unexpected error occurred: {e}. Using default values.") # User-facing error
            return default_locations