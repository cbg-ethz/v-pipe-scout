import streamlit as st
import time
import requests
from PIL import Image
from io import BytesIO
import base64
import yaml
import pandas as pd

# Load configuration from config.yaml
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

server_ip = config.get('server', {}).get('ip_address', 'http://default_ip:8000')

def app():
    st.title("Resistance Mutations")

    st.write("This page allows you to run the Lollipop variant deconvolution tool with a custom variant definitions.")

    # have three buttons for the three sets of mutations
    st.write("Select from the following resistance mutation sets:")

    # TODO: currently hardcoded, should be fetched from the server
    options = {
        "3CLpro Inhibitors": 'data/3CLpro_inhibitors_datasheet.csv',
        "RdRP Inhibitors": 'data/RdRP_inhibitors_datasheet.csv',
        "Spike mAbs": 'data/spike_mAbs_datasheet.csv'
    }

    selected_option = st.selectbox("Select a resistance mutation set:", options.keys())

    df = pd.read_csv(options[selected_option])

    st.write(df)

    # Define the POST request payload
    payload = {
        "aminoAcidMutations": ["S:144L"],
        "dateFrom": ["2022-02-18"],
        "dateTo": ["2024-11-01"],
        "fields": ["date"]
    }

    # Make the POST request
    response = requests.post(
        'https://lapis.cov-spectrum.org/open/v2/sample/aggregated',
        headers={
            'accept': 'application/json',
            'Content-Type': 'application/json'
        },
        json=payload
    )

    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()
        st.write("Data fetched from the server:")
        st.write(data)
    else:
        st.write("Failed to fetch data from the server.")
        st.write(f"Status code: {response.status_code}")
        st.write(response.text)
