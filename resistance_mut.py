import streamlit as st
import requests
import yaml
import pandas as pd
import logging

# Load configuration from config.yaml
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

server_ip = config.get('server', {}).get('ip_address', 'http://default_ip:8000')

def fetch_data(mutation, date_range):
    payload = {
        "aminoAcidMutations": [mutation],
        "dateFrom": date_range[0].strftime('%Y-%m-%d'),
        "dateTo": date_range[1].strftime('%Y-%m-%d'),
        "fields": ["date"]
    }

    response = requests.post(
        'https://lapis.cov-spectrum.org/open/v2/sample/aggregated',
        headers={
            'accept': 'application/json',
            'Content-Type': 'application/json'
        },
        json=payload
    )

    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Failed to fetch data for mutation {mutation}.")
        logging.error(f"Status code: {response.status_code}")
        logging.error(response.text)
        return None

def app():
    st.title("Resistance Mutations")

    st.write("This page allows you to run the Lollipop variant deconvolution tool with custom variant definitions.")

    st.write("Select from the following resistance mutation sets:")

    # TODO: currently hardcoded, should be fetched from the server
    options = {
        "3CLpro Inhibitors": 'data/3CLpro_inhibitors_datasheet.csv',
        "RdRP Inhibitors": 'data/RdRP_inhibitors_datasheet.csv',
        "Spike mAbs": 'data/spike_mAbs_datasheet.csv'
    }

    selected_option = st.selectbox("Select a resistance mutation set:", options.keys())

    df = pd.read_csv(options[selected_option])

    # Get the list of mutations for the selected set
    mutations = df['Mutation'].tolist()
    # Lambda function to format the mutation list, from S24L to S:24L
    format_mutation = lambda x: f"{x[0]}:{x[1:]}"
    # Apply the lambda function to each element in the mutations list
    formatted_mutations = [format_mutation(mutation) for mutation in mutations]

    st.write(f"Selected mutations: {formatted_mutations}")

    # Allow the user to choose a date range
    st.write("Select a date range:")
    date_range = st.date_input("Select a date range:", [pd.to_datetime("2022-01-01"), pd.to_datetime("2024-01-01")])

    if st.button("Fetch Data"):
        all_data = {}
        successful_fetches = 0
        for mutation in formatted_mutations:
            data = fetch_data(mutation, date_range)
            if data:
                all_data[mutation] = data
                successful_fetches += 1
        
        st.write(all_data)

        # next make df out of it / catch the case where change was found but no data was returned

if __name__ == "__main__":
    app()