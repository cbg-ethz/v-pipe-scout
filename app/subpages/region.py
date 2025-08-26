import streamlit as st
import pandas as pd

from datetime import datetime

from interface import MutationType
from api.wiseloculus import WiseLoculusLapis
from visualize.mutations import mutations_over_time
from utils.config import get_wiseloculus_url


pd.set_option('future.no_silent_downcasting', True)


# Get server configuration from centralized config
server_ip = get_wiseloculus_url()
wiseLoculus = WiseLoculusLapis(server_ip)


def app():
    st.title("Region Explorer")
    st.write("This page allows you to visualize a custom set or genomic range of mutations over time.")
    st.write("This feature may be useful for positions of interest or primer design and redesign.")
    st.markdown("---")
    
    # select mutation type - nucleotide or amino acid, mutli-selcted default to nucleotide
    mutation_type = st.radio(
        "Select mutation type:",
        options=["Nucleotide", "Amino Acid"],
        index=0  # Default to Nucleotide
    )
    mutation_type_value = MutationType.NUCLEOTIDE if mutation_type == "Nucleotide" else MutationType.AMINO_ACID

    # select mode - seleced mutations or genomic range
    mode = st.radio(
        "Select mode:",
        options=["Custom Mutation Set", "Genomic Ranges"],
        index=0  # Default to "Custom Mutation Set"
    )

    # allow input by comma-separated list of mutations as free text that is then validated
    if mode == "Custom Mutation Set":
        st.write("### Input Mutations")
        st.write("Enter a comma-separated list of mutations (e.g., C43T, G96A, T456C).")
        st.write("Mutations should be in nucleotide format (e.g., A123T), you may also skip the reference base (e.g., 123T, 456-).")
        mutation_input = st.text_area("Mutations:", value="C43T, G96A, T456C", height=100)
        # Split input into a list and strip whitespace
        mutations = [mut.strip() for mut in mutation_input.split(",") if mut.strip()]
        # Validate mutations --> let's implemen a simple regex validation of nucleotide mutations and amino acids in process/mutations.py
        # if not valid show warning, but proceed with valid ones



    # Apply the lambda function to each element in the mutations list
    formatted_mutations = mutations

    st.markdown("---")
    # Allow the user to choose a date range
    st.write("Choose your data to inspect:")
    # Get dynamic date range from API with bounds to enforce limits
    default_start, default_end, min_date, max_date = wiseLoculus.get_cached_date_range_with_bounds("resistance_mutations")
    date_range_input = st.date_input(
        "Select a date range:", 
        [default_start, default_end],
        min_value=min_date,
        max_value=max_date
    )

    # Ensure date_range is a tuple with two elements
    if len(date_range_input) != 2:
        st.error("Please select a valid date range with a start and end date.")
        return

    start_date = datetime.fromisoformat(date_range_input[0].strftime('%Y-%m-%d'))
    end_date = datetime.fromisoformat(date_range_input[1].strftime('%Y-%m-%d'))

    date_range = (start_date, end_date)

    ## Fetch locations from API
    default_locations = [
        "Zürich (ZH)",
    ]  # Define default locations
    
    # Fetch locations using cached session state
    if "locations" not in st.session_state:
        st.session_state.locations = wiseLoculus.fetch_locations(default_locations)
    locations = st.session_state.locations

    location = st.selectbox("Select Location:", locations)

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
            counts_df, freq_df, coverage_freq_df = wiseLoculus.mutations_over_time_dfs(formatted_mutations, mutation_type_value, date_range, location)
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
            st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    app()