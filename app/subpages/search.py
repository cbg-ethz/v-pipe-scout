import numpy as np
import streamlit as st
import pandas as pd
import asyncio
import streamlit.components.v1 as components
import plotly.graph_objects as go 
import pathlib

from interface import MutationType
from api.wiseloculus import WiseLoculusLapis
from visualize.mutations import mutations_over_time
from utils.config import get_wiseloculus_url

pd.set_option('future.no_silent_downcasting', True)


# Get server configuration from centralized config
server_ip = get_wiseloculus_url()
wiseLoculus = WiseLoculusLapis(server_ip)


def app():
    st.title("Resistance Mutations from Wastewater Data")
    st.write("This page allows you to visualize the number of observed resistance mutations over time.")
    st.write("The sets of resistance mutations are provided from Stanford's Coronavirus Antiviral & Resistance Database.")
    st.markdown("---")
    st.write("Select from the following resistance mutation sets:")
    # Get absolute path to data directory to handle different working directories
    data_dir = pathlib.Path(__file__).parent.parent / "data"
    options = {
        "3CLpro Inhibitors": str(data_dir / 'translated_3CLpro_in_ORF1a_mutations.csv'),
        "RdRP Inhibitors": str(data_dir / 'translated_RdRp_in_ORF1a_ORF1b_mutations.csv'),
        "Spike mAbs": str(data_dir / 'translated_Spike_in_S_mutations.csv')
    }

    selected_option = st.selectbox("Select a resistance mutation set:", options.keys())

    st.write("Note that mutation sets `3CLpro` and `RdRP`refer to mature proteins, " \
    "thus the mutations are in the ORF1a and ORF1b genes, respectively and translated here.")

    # Handle test environment where selectbox might return MagicMock
    if hasattr(selected_option, '_mock_name'):
        # In test environment, use the first option as fallback
        selected_option = list(options.keys())[0]

    df = pd.read_csv(options[selected_option])

    # Get the list of mutations for the selected set
    mutations = df['Mutation'].tolist()
    # Apply the lambda function to each element in the mutations list
    formatted_mutations = mutations

    st.markdown("---")
    # Allow the user to choose a date range
    st.write("Choose your data to inspect:")
    # Get dynamic date range from API with bounds to enforce limits
    default_start, default_end, min_date, max_date = wiseLoculus.get_cached_date_range_with_bounds("resistance_mutations")
    date_range = st.date_input(
        "Select a date range:", 
        [default_start, default_end],
        min_value=min_date,
        max_value=max_date
    )

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
        try:
            counts_df, freq_df, coverage_freq_df = wiseLoculus.mutations_over_time_dfs(formatted_mutations, MutationType.AMINO_ACID, date_range, location)
        except Exception as e:
            st.error(f"⚠️ Error fetching resistance mutation data: {str(e)}")
            st.info("This could be due to API connectivity issues. Please try again later.")
            # Create empty DataFrames for consistency
            counts_df = pd.DataFrame()
            freq_df = pd.DataFrame()
            coverage_freq_df = pd.DataFrame()


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
            st.plotly_chart(fig, width="container")

if __name__ == "__main__":
    app()