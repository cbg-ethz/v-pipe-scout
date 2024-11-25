import json
from matplotlib import pyplot as plt
import numpy as np
import streamlit as st
import requests
import yaml
import pandas as pd
import logging
import aiohttp
import asyncio


# Load configuration from config.yaml
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

server_ip = config.get('server', {}).get('ip_address', 'http://default_ip:8000')

async def fetch_data(session, mutation, date_range):
    payload = {
        "aminoAcidMutations": [mutation],
        "dateFrom": date_range[0].strftime('%Y-%m-%d'),
        "dateTo": date_range[1].strftime('%Y-%m-%d'),
        "fields": ["date"]
    }

    async with session.post(
        'https://lapis.cov-spectrum.org/open/v2/sample/aggregated',
        headers={
            'accept': 'application/json',
            'Content-Type': 'application/json'
        },
        json=payload
    ) as response:
        if response.status == 200:
            data = await response.json()
            return {"mutation": mutation,
                    "data": data.get('data', [])}
        else:
            logging.error(f"Failed to fetch data for mutation {mutation}.")
            logging.error(f"Status code: {response.status}")
            logging.error(await response.text())
            return {"mutation": mutation,
                    "data": None}

async def fetch_all_data(mutations, date_range):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_data(session, mutation, date_range) for mutation in mutations]
        return await asyncio.gather(*tasks)
    
def plot_heatmap(df):

    # get the dates from the columns
    dates = df.columns

    # get the mutations from the index
    mutations = df.index.tolist()

    # 2. Heatmap Construction
    fig, ax = plt.subplots(figsize=(12, 8))
    # Replace None with np.nan and remove commas from numbers
    df = df.replace({None: np.nan, ',': ''}, regex=True).astype(float)
    
    # Create a colormap with a custom color for NaN values
    cmap = plt.cm.Blues
    cmap.set_bad(color='lightcoral')  # Set NaN values to light rose color

    im = ax.imshow(df.values, cmap=cmap)  # Use the custom colormap

    # Set axis labels
    ax.set_xticks([0, len(dates) // 2, len(dates) - 1])
    ax.set_xticklabels([dates[0], dates[len(dates) // 2], dates[-1]], rotation=45)
    ax.set_yticks(np.arange(len(mutations)))
    ax.set_yticklabels(mutations, fontsize=8)

    # Add colorbar
    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel("Occurrence Frequency", rotation=-90, va="bottom")

    return fig



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
        all_data = asyncio.run(fetch_all_data(formatted_mutations, date_range))

        # filter out mutations with no data
        all_data = [data for data in all_data if data['data']]

        # build a dataframe from the collected data
        # for each mutation make a row 
        # iterate through the data and add a column for each date with the number of samples
        mutation_data = []
        for data in all_data:
            mutation = data['mutation']
            mutation_data.append([mutation] + [d['count'] for d in data['data']])
        
        st.write("Data fetched from the server:")
        df = pd.DataFrame(mutation_data, columns=['Mutation'] + [d['date'] for d in all_data[0]['data']])
        # Set the first column as the index
        df.set_index(df.columns[0], inplace=True)
        st.write(df)

        st.write("df.values:", df.values)

        # Plot the heatmap
        fig = plot_heatmap(df)
        st.pyplot(fig)

if __name__ == "__main__":
    app()