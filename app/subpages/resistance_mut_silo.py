import numpy as np
import streamlit as st
import pandas as pd
import asyncio
import yaml
import streamlit.components.v1 as components
import plotly.graph_objects as go 
import pathlib

from interface import MutationType
from api.wiseloculus import WiseLoculusLapis
from visualize.mutations import mutations_over_time

pd.set_option('future.no_silent_downcasting', True)


# Load configuration from config.yaml
CONFIG_PATH = pathlib.Path(__file__).parent.parent / "config.yaml"
with open(CONFIG_PATH, 'r') as file:
    config = yaml.safe_load(file)


server_ip = config.get('server', {}).get('lapis_address', 'http://default_ip:8000')
wiseLoculus = WiseLoculusLapis(server_ip)


def app():
    st.title("Resistance Mutations from Wastewater Data")
    st.write("This page allows you to visualize the numer of observed resistance mutations over time.")
    st.write("The data is fetched from the WISE-CovSpectrum API and currently cointains demo data for Feb-Mar 2025.")
    st.write("The sets of resistance mutations are provide from Stanfords Coronavirus Antivirial & Reistance Database. Last updated 05/14/2024")
    st.write("This is a demo frontend to later make the first queries to SILO for wastewater data.")
    st.markdown("---")
    st.write("Select from the following resistance mutation sets:")
    options = {
        "3CLpro Inhibitors": 'data/translated_3CLpro_in_ORF1a_mutations.csv',
        "RdRP Inhibitors": 'data/translated_RdRp_in_ORF1a_ORF1b_mutations.csv',
        "Spike mAbs": 'data/translated_Spike_in_S_mutations.csv'
    }

    selected_option = st.selectbox("Select a resistance mutation set:", options.keys())

    st.write("Note that mutation sets `3CLpro` and `RdRP`refer to mature proteins, " \
    "thus the mutations are in the ORF1a and ORF1b genes, respectively and translated here.")

    df = pd.read_csv(options[selected_option])

    # Get the list of mutations for the selected set
    mutations = df['Mutation'].tolist()
    # Apply the lambda function to each element in the mutations list
    formatted_mutations = mutations

    st.markdown("---")
    # Allow the user to choose a date range
    st.write("Choose your data to inspect:")
    date_range = st.date_input("Select a date range:", [pd.to_datetime("2025-02-10"), pd.to_datetime("2025-03-08")])

    # Ensure date_range is a tuple with two elements
    if len(date_range) != 2:
        st.error("Please select a valid date range with a start and end date.")
        return

    start_date = date_range[0].strftime('%Y-%m-%d')
    end_date = date_range[1].strftime('%Y-%m-%d')
    

    ## Fetch locations from API
    default_locations = [
        "Zürich (ZH)",
    ]  # Define default locations
    # Fetch locations using the fetch_locations function
    locations = wiseLoculus.fetch_locations(default_locations)

    location = st.selectbox("Select Location:", locations)
    
    sequence_type_value = "amino acid"

    formatted_mutations_str = str(formatted_mutations).replace("'", '"')

    st.markdown("---")
    st.write("### Resistance Mutations Over Time")
    st.write("Shows the mutations over time in wastewater for the selected date range.")

    # Add radio button for showing/hiding dates with no data
    show_empty_dates = st.radio(
        "Date display options:",
        options=["Show all dates", "Skip dates with no coverage"],
        index=0  # Default to showing all dates (off)
    )

    with st.spinner("Fetching resistance mutation data..."):
        counts_df, freq_df, coverage_freq_df = wiseLoculus.mutations_over_time_dfs(formatted_mutations, MutationType.AMINO_ACID, date_range, location)


    # Only skip NA dates if the option is selected
    if show_empty_dates == "Skip dates with no coverage":
        plot_counts_df = counts_df.dropna(axis=1, how='all')
        plot_freq_df = freq_df.dropna(axis=1, how='all')
    else:
        plot_counts_df = counts_df
        plot_freq_df = freq_df

    if not freq_df.empty:
        if freq_df.isnull().all().all():
            st.error("The fetched data contains only NaN values. Please try a different date range or mutation set.")
        else:
            fig = mutations_over_time(
                plot_freq_df, 
                plot_counts_df, 
                coverage_freq_df,
                title="Proportion of Resistance Mutations Over Time"
            )
            st.plotly_chart(fig, use_container_width=True)

    st.write("### GenSpectrum Dashboard Dynamic Mutations Over Time")
    st.write("In the long term, GenSpectrum will provide a dashboard to visualize the mutations over time.")
    st.write("Yet currently, the below component only shows mutations above an unknown threshold.")
    st.write("This is under investigation and will be addresed by the GenSpectrum team.")

    # Use the dynamically generated list of mutations string
    # The formatted_mutations_str variable already contains the string representation
    # of the list with double quotes, e.g., '["ORF1a:T103L", "ORF1a:N126K"]'
    # The lapisFilter uses double curly braces {{ and }} to escape the literal
    # curly braces needed for the JSON object within the f-string.
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
                displayMutations='{formatted_mutations_str}'
                lapisDateField='sampling_date'
                initialMeanProportionInterval='{{"min":0.00,"max":1.0}}'
                pageSizes='[50, 30, 20, 10]'
                />
            </gs-app>
            <body>
            
            </body>
        </html>
    """,
        height=500,
    )

if __name__ == "__main__":
    app()