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


def plot_resistance_mutations(freq_df, counts_df=None, coverage_freq_df=None):
    """Plot resistance mutations over time as a heatmap using Plotly.
    
    Args:
        freq_df: DataFrame with mutations as rows, dates as columns, and frequency values
        counts_df: DataFrame with mutations as rows, dates as columns, and count values (for hover info)
        coverage_freq_df: Optional MultiIndex DataFrame with detailed coverage and frequency data
    """

    # Replace None with np.nan and remove commas from numbers
    df_processed = freq_df.replace({None: np.nan, ',': ''}, regex=True).infer_objects(copy=False).astype(float)

    # Create enhanced hover text
    hover_text = []
    for mutation in df_processed.index:
        row_hover_text = []
        for date in df_processed.columns:
            frequency = df_processed.loc[mutation, date]
            
            # Try to get additional data from other sources
            count = None
            coverage = None
            
            # First try to get count from counts_df if provided
            if counts_df is not None and not counts_df.empty:
                count = counts_df.loc[mutation, date] if not pd.isna(counts_df.loc[mutation, date]) else None
            
            # Then try to get additional data from coverage_freq_df
            if coverage_freq_df is not None and not coverage_freq_df.empty:
                try:
                    if mutation in coverage_freq_df.index.get_level_values('mutation'):
                        mutation_data = coverage_freq_df.loc[mutation]
                        if date in mutation_data.index:
                            coverage_val = mutation_data.loc[date, 'coverage']
                            
                            # If count is still None, try to get it from coverage_freq_df
                            if count is None:
                                count_val = mutation_data.loc[date, 'count']
                                count = count_val if count_val != 'NA' else None
                            
                            # Handle 'NA' values for coverage
                            coverage = coverage_val if coverage_val != 'NA' else None
                except (KeyError, IndexError):
                    pass  # Data not available for this mutation/date combination
            
            # Build hover text
            if pd.isna(frequency):
                text = f"Mutation: {mutation}<br>Date: {date}<br>Status: No data"
            else:
                text = f"Mutation: {mutation}<br>Date: {date}<br>Proportion: {frequency * 100:.1f}%"
                if count is not None:
                    text += f"<br>Count: {float(count):.0f}"
                if coverage is not None:
                    text += f"<br>Coverage: {float(coverage):.0f}"
            
            row_hover_text.append(text)
        hover_text.append(row_hover_text)

    # Determine dynamic height
    height = max(400, len(df_processed.index) * 20 + 100) # Base height + per mutation + padding for title/axes

    # Determine dynamic left margin based on mutation label length
    max_len_mutation_label = 0
    if not df_processed.index.empty: # Check if index is not empty
        max_len_mutation_label = max(len(str(m)) for m in df_processed.index)
    
    margin_l = max(80, max_len_mutation_label * 7 + 30) # Min margin or calculated, adjust multiplier as needed


    fig = go.Figure(data=go.Heatmap(
        z=df_processed.values,  # Now using frequency values
        x=df_processed.columns,
        y=df_processed.index,
        colorscale='Blues',
        showscale=False,  # Hide color bar as requested
        hoverongaps=True, # Show hover for gaps (NaNs)
        text=hover_text,
        hoverinfo='text'
    ))

    # Customize layout
    num_cols = len(df_processed.columns)
    tick_indices = []
    tick_labels = []
    if num_cols > 0:
        tick_indices = [df_processed.columns[0]]
        if num_cols > 1:
            tick_indices.append(df_processed.columns[num_cols // 2])
        if num_cols > 2 and num_cols //2 != num_cols -1 : # Avoid duplicate if middle is last
             tick_indices.append(df_processed.columns[-1])
        tick_labels = [str(label) for label in tick_indices]

    fig.update_layout(
        title="Proportion of Resistance Mutations Over Time",
        xaxis=dict(
            title='Date',
            side='bottom',
            tickmode='array',
            tickvals=tick_indices,
            ticktext=tick_labels,
            tickangle=45,
        ),
        yaxis=dict(
            title='Mutation',
            autorange='reversed' # Show mutations from top to bottom as in original df
        ),
        height=height,
        plot_bgcolor='lightpink',  # NaN values will appear as this background color
        margin=dict(l=margin_l, r=20, t=80, b=100),  # Adjust margins
    )
    return fig


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
    
    # 1.1) Which mutations appear at least once with a fraction of MIN_FREQ 
    #  in the data range and location?   

    
    # 1.2) Which mutations are not in any variant signature we track?


    # 2) For these mutations, fetch the counts and frequencies over time, for the given date range and location.



if __name__ == "__main__":
    app()