import numpy as np
import streamlit as st
import pandas as pd
import asyncio
import yaml
import plotly.graph_objects as go 
import pathlib
from pydantic import BaseModel
from typing import List

from api.wiseloculus import WiseLoculusLapis
from interface import MutationType

from api.signatures import Variant as SignatureVariant
from api.signatures import VariantList as SignatureVariantList
from api.signatures import get_variant_list, get_variant_names

from datetime import datetime

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

# TODO: dublicate in resistance mutaitons, extract as utility function + typing here
def fetch_reformat_data(formatted_mutations, date_range, location_name=None):
    """
    Fetch mutation data using the new fetch_counts_coverage_freq method.
    Returns a tuple of (counts_df, freq_df, coverage_freq_df) where:
    - counts_df: DataFrame with mutations as rows and dates as columns (with counts for backward compatibility)
    - freq_df: DataFrame with mutations as rows and dates as columns (with frequency values for plotting)
    - coverage_freq_df: MultiIndex DataFrame with detailed count, coverage, and frequency data
    """
    mutation_type = MutationType.NUCLEOTIDE  # as we care about amino acid mutations, as in resistance mutations
    
    # Fetch comprehensive data using the new method
    coverage_freq_df = wiseLoculus.fetch_counts_coverage_freq(
        formatted_mutations, mutation_type, date_range, location_name
    )
    
    # Get dates from date_range for consistency
    dates = pd.date_range(date_range[0], date_range[1]).strftime('%Y-%m-%d')
    
    # Create DataFrames with mutations as rows and dates as columns
    counts_df = pd.DataFrame(index=formatted_mutations, columns=list(dates))
    freq_df = pd.DataFrame(index=formatted_mutations, columns=list(dates))
    
    # Fill the counts and frequency DataFrames from the MultiIndex DataFrame
    if not coverage_freq_df.empty:
        for mutation in formatted_mutations:
            if mutation in coverage_freq_df.index.get_level_values('mutation'):
                mutation_data = coverage_freq_df.loc[mutation]
                for date in mutation_data.index:
                    # Handle 'NA' values from the API
                    count_val = mutation_data.loc[date, 'count']
                    freq_val = mutation_data.loc[date, 'frequency']
                    
                    if count_val != 'NA':
                        counts_df.at[mutation, date] = count_val
                    
                    if freq_val != 'NA':
                        freq_df.at[mutation, date] = freq_val
    
    return counts_df, freq_df, coverage_freq_df


class Variant(BaseModel):
    """
    Model for a variant with its signature mutations.
    This is a simplified version of the Variant class from signatures.py.
    """
    name: str  # pangolin name
    signature_mutations: List[str]
    
    @classmethod
    def from_signature_variant(cls, signature_variant: SignatureVariant) -> "Variant":
        """Convert a signature Variant to our simplified Variant."""
        return cls(
            name=signature_variant.name,  # This is already the pangolin name
            signature_mutations=signature_variant.signature_mutations
        )


class VariantList(BaseModel):
    """Model for a simplified list of variants."""
    variants: List[Variant] = []
    
    @classmethod
    def from_signature_variant_list(cls, signature_variant_list: SignatureVariantList) -> "VariantList":
        """Convert a signature VariantList to our simplified VariantList."""
        variant_list = cls()
        for signature_variant in signature_variant_list.variants:
            variant_list.add_variant(Variant.from_signature_variant(signature_variant))
        return variant_list
        
    def add_variant(self, variant: Variant):
        self.variants.append(variant)
        
    def remove_variant(self, variant: Variant):
        self.variants.remove(variant)


@st.cache_data(ttl=3600)  # Cache for 1 hour
def cached_get_variant_list() -> SignatureVariantList:
    """Cached version of get_variant_list to avoid repeated API calls."""
    return get_variant_list()

@st.cache_data(ttl=3600)  # Cache for 1 hour
def cached_get_variant_names() -> List[str]:
    """Cached version of get_variant_names to avoid repeated API calls."""
    return get_variant_names()

def app():

    
    st.title("Background Mutations")
    st.subheader("Explore Mutations currently not in any Variant Signature we track")
    st.write("This page allows you to visualize the numer of observed mutations over time.")
    st.markdown("---")
    # Allow the user to choose a date range
    st.write("Choose your data to inspect:")
    date_range = st.date_input("Select a date range:", [pd.to_datetime("2025-02-10"), pd.to_datetime("2025-03-08")])

    # Ensure date_range is a tuple with two elements
    if len(date_range) != 2:
        st.error("Please select a valid date range with a start and end date.")
        return

    start_date = datetime.strptime(str(date_range[0]), "%Y-%m-%d")
    end_date = datetime.strptime(str(date_range[1]),"%Y-%m-%d")
    

    ## Fetch locations from API
    default_locations = [
        "Zürich (ZH)",
    ]  # Define default locations
    # Fetch locations using the fetch_locations function
    locations = wiseLoculus.fetch_locations(default_locations)

    location = st.selectbox("Select Location:", locations)

    mutations_in_timeframe_df =  asyncio.run(wiseLoculus.sample_nucleotideMutations(
        date_range=(
            start_date,
            end_date
        ),
        location_name="Zürich (ZH)"
    ))

    mutations_in_timeframe = mutations_in_timeframe_df['mutation'].to_list()  

    # Get the available variant names from the signatures API (cached)
    available_variants = cached_get_variant_names()
    
    # Create a multi-select box for variants
    selected_curated_variants = st.multiselect(
        "Select known variants of interest – curated by the V-Pipe team",
        options=available_variants,
        default=cached_get_variant_names(),
        help="Select from the list of known variants. The signature mutations of these variants have been curated by the V-Pipe team"
    )
    
    # from selected_curated_variants get each variant's signature mutations
    curated_variants = cached_get_variant_list()
    curated_variants = VariantList.from_signature_variant_list(curated_variants)
    curated_variants.variants = [
        variant for variant in curated_variants.variants
        if variant.name in selected_curated_variants
    ]
    # Extract the signature mutations from the selected curated variants
    selected_signature_mutations = [
        mutation for variant in curated_variants.variants
        for mutation in variant.signature_mutations
    ]

    # remove duplicates from selected_signature_mutations
    selected_signature_mutations = list(set(selected_signature_mutations))

    # Calculate background mutations (all mutations minus the signature mutations)
    background_mutations = [
        mutation for mutation in mutations_in_timeframe
        if mutation not in selected_signature_mutations
    ]

    st.write(f"Total mutations in timeframe: {len(mutations_in_timeframe)}")
    st.write(f"Signature mutations to exclude: {len(selected_signature_mutations)}")
    st.write(f"Background mutations to analyze: {len(background_mutations)}")

    # Show a spinner while fetching data - only for background mutations
    with st.spinner("Fetching mutation data for background mutations..."):
        counts_df, freq_df, coverage_freq_df =  wiseLoculus.mutations_over_time_dfs(
            background_mutations,  # Only fetch data for background mutations
            MutationType.NUCLEOTIDE,
            date_range=(start_date, end_date),
            location_name=location
        )
    
    # Display the visualization
    st.markdown("---")
    st.write("### Background Mutations Over Time")
    st.write("Shows the background mutations (not in variant signatures) over time in wastewater for the selected date range.")
    
    # Add radio button for showing/hiding dates with no data
    show_empty_dates = st.radio(
        "Date display options:",
        options=["Show all dates", "Skip dates with no coverage"],
        index=0  # Default to showing all dates
    )
    
    # Only skip NA dates if the option is selected
    if show_empty_dates == "Skip dates with no coverage":
        plot_counts_df = counts_df.dropna(axis=1, how='all')
        plot_freq_df = freq_df.dropna(axis=1, how='all')
    else:
        plot_counts_df = counts_df
        plot_freq_df = freq_df
    
    if not freq_df.empty and len(background_mutations) > 0:
        if freq_df.isnull().all().all():
            st.error("The fetched data contains only NaN values. Please try a different date range or select fewer variants to exclude.")
        else:
            fig = mutations_over_time(
                plot_freq_df, 
                plot_counts_df, 
                coverage_freq_df,
                title="Proportion of Background Mutations Over Time"
            )
            st.plotly_chart(fig, use_container_width=True)
    elif len(background_mutations) == 0:
        st.info("No background mutations found. All mutations in the selected timeframe are part of the selected variant signatures.")
    else:
        st.error("No data available for the selected parameters. Please try a different date range or location.")

if __name__ == "__main__":
    app()