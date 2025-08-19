import streamlit as st
import pandas as pd
import logging 
import asyncio
from datetime import datetime

from interface import MutationType
from api.wiseloculus import WiseLoculusLapis
from components.mutation_plot_component import render_mutation_plot_component
from utils.config import get_wiseloculus_url

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Get server configuration from centralized config
server_ip = get_wiseloculus_url()

wiseLoculus = WiseLoculusLapis(server_ip)

def app():

    ## Add a title
    st.title("Search by Proportion")

    ## Add a subheader
    st.markdown("### Explore mutations over time by proportion")

    st.write("Explore all mutations found and filter by proportions. Notice that this is a heavy operation and may take a while to load.")

    ## select dat range
    st.write("Select a date range:")
    # Get dynamic date range from API with bounds to enforce limits
    default_start, default_end, min_date, max_date = wiseLoculus.get_cached_date_range_with_bounds("dynamic_mutations")
    date_range = st.date_input(
        "Select a date range:", 
        [default_start, default_end],
        min_value=min_date,
        max_value=max_date
    )

    ## Add a horizontal line
    st.markdown("---")

    ## Fetch locations from API
    default_locations = ["Zürich (ZH)", "Lugano (TI)", "Chur (GR)"] # Define default locations
    # Fetch locations using the new function
    locations = wiseLoculus.fetch_locations(default_locations)

    location = st.selectbox("Select Location:", locations)

    # Amino Acids or Nucleotides
    sequence_type = st.selectbox("Select Sequence Type:", ["Nucleotides", "Amino Acids"])

    # the sequence type selection determines the default value for min_proportion
    if sequence_type == "Nucleotides":
        default_min_proportion = 0.10
    elif sequence_type == "Amino Acids":
        default_min_proportion = 0.30
    else:
        default_min_proportion = 0.05
    

    # text box with min_proportion – mutaiton has to occure at least once to this proportion to show up
    min_proportion = st.number_input(
        "Minimum Proportion of Mutation to fetch (the lower the longer the loading time)",
        min_value=0.01,
        max_value=1.0,
        value=default_min_proportion,  # Default value
        step=0.01,
        help="Set the minimum proportion of mutation to fetch in the heatmap."
    )

    # Add performance warning before the button
    st.warning("⚠️ **Performance Notice**: Loading this plot may take up to a minute for proportions below 10%. A major speedup will be implemented soon to improve loading times.")

    # Add button to trigger data fetching
    if st.button("Fetch Mutation Data"):
        if len(date_range) == 2:
            start_date = datetime.strptime(str(date_range[0]), "%Y-%m-%d")
            end_date = datetime.strptime(str(date_range[1]), "%Y-%m-%d")

            sequence_type_value = "amino acid" if sequence_type == "Amino Acids" else "nucleotide"

            # Fetch all mutations for the given parameters
            st.write("### Mutation Analysis by Proportion")
            st.write("Analyzing all mutations found in the selected timeframe and location.")
            
            try:
                mutation_type = MutationType.NUCLEOTIDE if sequence_type_value == "nucleotide" else MutationType.AMINO_ACID
                # Get all nucleotide mutations in the timeframe
                mutations_in_timeframe_df = asyncio.run(wiseLoculus.sample_mutations(
                    type=mutation_type,
                    date_range=(start_date, end_date),
                    location_name=location,
                    min_proportion=min_proportion  # Lower threshold to get more mutations
                ))

                if mutations_in_timeframe_df.empty or 'mutation' not in mutations_in_timeframe_df.columns:
                    st.warning("⚠️ No mutations found for the selected parameters.")
                    st.info("Try adjusting the date range or location.")
                    return
                
                mutations_list = mutations_in_timeframe_df['mutation'].tolist()
                
                # Configure the component for dynamic mutations
                plot_config = {
                    'show_frequency_filtering': True,
                    'show_date_options': True,
                    'show_download': True,
                    'show_summary_stats': True,
                    'default_min_frequency': min_proportion,
                    'default_max_frequency': 1.0,
                    'plot_title': f"{sequence_type} Mutations by Proportion Over Time",
                    'enable_empty_date_toggle': True,
                    'show_mutation_count': True
                }
                
                # Use the mutation plot component
                result = render_mutation_plot_component(
                    wiseLoculus=wiseLoculus,
                    mutations=mutations_list,
                    sequence_type=sequence_type_value,
                    date_range=(start_date, end_date),
                    location=location,
                    config=plot_config,
                    session_prefix="dynamic_"
                )
                
            except Exception as e:
                st.error(f"⚠️ Error fetching mutation data: {str(e)}")
                st.info("This could be due to API connectivity issues. Please try again later.")
        else:
            st.warning("Please select a valid date range with both start and end dates.")


if __name__ == "__main__":
    app()