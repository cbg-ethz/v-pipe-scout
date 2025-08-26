import numpy as np
import streamlit as st
import pandas as pd
import asyncio
import pathlib
from datetime import datetime, date
from typing import List

from interface import MutationType
from api.wiseloculus import WiseLoculusLapis
from api.signatures import get_variant_list, get_variant_names, VariantList
from components.mutation_plot_component import render_mutation_plot_component
from utils.config import get_wiseloculus_url
from utils.url_state import create_url_state_manager

pd.set_option('future.no_silent_downcasting', True)


# Get server configuration from centralized config
server_ip = get_wiseloculus_url()
wiseLoculus = WiseLoculusLapis(server_ip)


@st.cache_data(ttl=3600)  # Cache for 1 hour
def cached_get_variant_list() -> VariantList:
    """Cached version of get_variant_list to avoid repeated API calls."""
    return get_variant_list()

@st.cache_data(ttl=3600)  # Cache for 1 hour
def cached_get_variant_names() -> List[str]:
    """Cached version of get_variant_names to avoid repeated API calls."""
    return get_variant_names()

def app():
    # Initialize URL state manager for this page
    url_state = create_url_state_manager("untracked")

    
    st.title("Untracked Mutations")
    st.subheader("Explore Mutations currently not in any Variant Signature we track")
    st.write("This page allows you to visualize untracked mutations in wastewater samples that are not part of any known variant signature.")
    
    # Add explanatory note as requested
    st.info("**What are Untracked Mutations?** These are mutations currently not part of any variant definition used, or ever used, for wastewater monitoring.")
    
    # Add link to the VOC repository as requested
    st.write("For updates on Variants of Concern, see our [variant definitions repository](https://github.com/cbg-ethz/cowwid/tree/master/voc).")
    
    st.write("Are we missing something? Please let us know on [GitHub](https://github.com/cbg-ethz/cowwid/issues)")
    st.markdown("---")
    # Allow the user to choose a date range
    st.write("Choose your data to inspect:")
    # Get dynamic date range from API with bounds to enforce limits
    default_start, default_end, min_date, max_date = wiseLoculus.get_cached_date_range_with_bounds("background_mutations")
    
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

    start_date = datetime.strptime(str(date_range[0]), "%Y-%m-%d")
    end_date = datetime.strptime(str(date_range[1]),"%Y-%m-%d")
    

    ## Fetch locations from API
    default_locations = []  
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

    # Add button to trigger data fetching
    if date_range and len(date_range) == 2 and location:
        with st.spinner("Fetching mutation data..."):
            try:
                mutations_in_timeframe_df = asyncio.run(wiseLoculus.sample_mutations(
                    type=MutationType.NUCLEOTIDE,
                    date_range=(
                        start_date,
                        end_date
                    ),
                    location_name=location
                ))

                # Handle case where no mutations were found or API call failed
                if mutations_in_timeframe_df.empty:
                    st.info("ℹ️ No mutations found for the selected date range and location.")
                    st.write("This could be due to:")
                    st.write("• No mutations present in the specified time period")
                    st.write("• The selected location having no data for this date range")
                    mutations_in_timeframe = []  # Empty list as fallback
                elif 'mutation' not in mutations_in_timeframe_df.columns:
                    st.error("⚠️ Unexpected data format received from the API. Please try again or contact support.")
                    st.info("The API response doesn't contain the expected mutation data structure.")
                    mutations_in_timeframe = []  # Empty list as fallback
                else:
                    mutations_in_timeframe = mutations_in_timeframe_df['mutation'].to_list()  
            except Exception as e:
                st.error(f"Error fetching mutations: {str(e)}")
                mutations_in_timeframe = []
    else:
        mutations_in_timeframe = []

    # Get the available variant names from the signatures API (cached)
    available_variants = cached_get_variant_names()
    
    # Create a collapsible section for variant selection
    with st.expander("🔧 Advanced: Select known variants to exclude", expanded=False):
        st.write("By default, all known variant signatures are excluded from untracked mutations. You can customize which variants to exclude here.")
        
        # Load variant selection from URL or use default
        url_variants = url_state.load_from_url("variants", cached_get_variant_names(), list)
        
        # Create a multi-select box for variants
        selected_curated_variants = st.multiselect(
            "Select known variants to exclude.",
            options=available_variants,
            default=url_variants,
            help="Select from the list of known variants. The signature mutations of these variants have been curated by the V-Pipe team"
        )
        
        # Save variant selection to URL
        url_state.save_to_url(variants=selected_curated_variants)
   
    # Add performance warning
    st.warning("⚠️ **Performance Notice**: Loading this plot may take up to a minute due to the high number of datapoints to fetch.")

    
    # Only process if mutations_in_timeframe is defined and has data
    if 'mutations_in_timeframe' in locals() and mutations_in_timeframe:
        # from selected_curated_variants get each variant's signature mutations
        all_curated_variants = cached_get_variant_list()
        
        # Filter to only the selected variants and extract their signature mutations
        selected_signature_mutations = [
            mutation 
            for variant in all_curated_variants.variants
            if variant.name in selected_curated_variants
            for mutation in variant.signature_mutations
        ]

        # remove duplicates from selected_signature_mutations
        selected_signature_mutations = list(set(selected_signature_mutations))

        # Calculate untracked mutations (all mutations minus the signature mutations)
        background_mutations = [
            mutation for mutation in mutations_in_timeframe
            if mutation not in selected_signature_mutations
        ]

        # TODO: add a venn diragram here to visualize the overlap, once the better venn diagram library is available
        st.write(f"Total mutations in timeframe: {len(mutations_in_timeframe)}")
        st.write(f"Signature mutations to exclude: {len(selected_signature_mutations)}")
        st.write(f"Untracked mutations to analyze: {len(background_mutations)}")

        # Use the mutation plot component
        if background_mutations:
            # Configure the component for untracked mutations
            plot_config = {
                'show_frequency_filtering': True,
                'show_date_options': True,
                'show_download': True,
                'show_summary_stats': True,
                'default_min_frequency': 0.01,
                'default_max_frequency': 1.0,
                'plot_title': "Untracked Mutations Over Time",
                'enable_empty_date_toggle': True,
                'show_mutation_count': False  # We already show this above
            }
            
            # Add description
            st.write("Shows the untracked mutations (not in variant signatures) over time in wastewater for the selected date range.")
            
            # Use the component
            result = render_mutation_plot_component(
                wiseLoculus=wiseLoculus,
                mutations=background_mutations,
                sequence_type=MutationType.NUCLEOTIDE,
                date_range=(start_date, end_date),
                location=location,
                config=plot_config,
                session_prefix="background_"
            )
            
            if result is None:
                st.info("💡 Try adjusting the date range, location, or variant exclusions.")
        else:
            st.warning("⚠️ No untracked mutations available for analysis. This could be due to:")
            st.write("• API connection issues preventing mutation data fetch")
            st.write("• No mutations found in the selected time range and location")
            st.write("• All detected mutations were excluded as variant signatures")
            st.info("💡 Try adjusting the date range, location, or variant exclusions.")

if __name__ == "__main__":
    app()