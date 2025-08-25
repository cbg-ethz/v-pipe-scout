import streamlit as st
import pandas as pd
import asyncio
import pathlib
from datetime import date

from interface import MutationType
from api.wiseloculus import WiseLoculusLapis
from visualize.mutations import mutations_over_time
from utils.config import get_wiseloculus_url
from utils.url_state import create_url_state_manager

pd.set_option('future.no_silent_downcasting', True)


# Get server configuration from centralized config
server_ip = get_wiseloculus_url()
wiseLoculus = WiseLoculusLapis(server_ip)


def app():
    # Initialize URL state manager for this page
    url_state = create_url_state_manager("resistance")
    
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

    # Load selected option from URL or use default
    default_option = url_state.load_from_url("resistance_set", "3CLpro Inhibitors", str)
    selected_option = st.selectbox("Select a resistance mutation set:", 
                                   options.keys(), 
                                   index=list(options.keys()).index(default_option) if default_option in options else 0)
    
    # Save selected option to URL
    url_state.save_to_url(resistance_set=selected_option)

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
    # Get dynamic date range from API with bounds to enforce limits
    default_start, default_end, min_date, max_date = wiseLoculus.get_cached_date_range_with_bounds("resistance_mutations")
    
    # Load date range from URL or use defaults
    url_start_date = url_state.load_from_url("start_date", default_start, date)
    url_end_date = url_state.load_from_url("end_date", default_end, date)
    
    date_range = st.date_input(
        "Select a date range:", 
        [url_start_date, url_end_date],
        min_value=min_date,
        max_value=max_date
    )

    # Ensure date_range is a tuple with two elements
    if len(date_range) != 2:
        st.error("Please select a valid date range with a start and end date.")
        return

    # Save date range to URL
    url_state.save_to_url(start_date=date_range[0], end_date=date_range[1])

    start_date = date_range[0].strftime('%Y-%m-%d')
    end_date = date_range[1].strftime('%Y-%m-%d')

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    

    ## Fetch locations from API
    default_locations = [
        "Zürich (ZH)",
    ]  # Define default locations
    # Fetch locations using the fetch_locations function
    locations = wiseLoculus.fetch_locations(default_locations)

    # Load location from URL or use default
    default_location = locations[0] if locations else ""
    url_location = url_state.load_from_url("location", default_location, str)
    
    # Make sure the URL location is still valid
    if url_location not in locations:
        url_location = default_location
    
    location_index = locations.index(url_location) if url_location in locations else 0
    location = st.selectbox("Select Location:", locations, index=location_index)
    
    # Save location to URL
    url_state.save_to_url(location=location)
    
    st.markdown("---")
    st.write("### Resistance Mutations Over Time")
    st.write("Shows the mutations over time in wastewater for the selected date range.")

    # Add radio button for showing/hiding dates with no data
    url_show_empty = url_state.load_from_url("show_empty", "Show all dates", str)
    show_empty_dates = st.radio(
        "Date display options:",
        options=["Show all dates", "Skip dates with no coverage"],
        index=0 if url_show_empty == "Show all dates" else 1
    )
    
    # Save radio button selection to URL
    url_state.save_to_url(show_empty=show_empty_dates)

    with st.spinner("Fetching resistance mutation data..."):
        try:
            # Get data using the mutations_over_time function
            mutations_over_time_df = asyncio.run(wiseLoculus.mutations_over_time(
                mutations=formatted_mutations,
                mutation_type=MutationType.AMINO_ACID,
                date_range=(start_date, end_date),
                location_name=location
            ))

            # Transform the data to match mutations_over_time_dfs signature:
            # 1. counts_df and freq_df: mutations as rows, dates as columns
            # 2. coverage_freq_df: keep the MultiIndex structure for compatibility
            
            # Reset index to access mutation and sampling_date as columns
            df_reset = mutations_over_time_df.reset_index()
            
            # Create the expected format: mutations as index, dates as columns
            counts_df = df_reset.pivot(index='mutation', columns='sampling_date', values='count')
            freq_df = df_reset.pivot(index='mutation', columns='sampling_date', values='frequency')
            
            # Keep the original MultiIndex structure for coverage_freq_df for compatibility with visualization
            coverage_freq_df = mutations_over_time_df

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
                coverage_freq_df,  # Now using the original MultiIndex structure
                title="Proportion of Resistance Mutations Over Time"
            )
            st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    app()