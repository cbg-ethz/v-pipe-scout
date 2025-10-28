import streamlit as st
import pandas as pd
import logging 
import asyncio
from datetime import datetime, date

from interface import MutationType
from api.wiseloculus import WiseLoculusLapis
from components.mutation_plot_component import render_mutation_plot_component
from utils.config import get_wiseloculus_url
from utils.url_state import create_url_state_manager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Get server configuration from centralized config
server_ip = get_wiseloculus_url()

wiseLoculus = WiseLoculusLapis(server_ip)

def app():
    # Initialize URL state manager for this page
    url_state = create_url_state_manager("proportion")

    ## Add a title
    st.title("Search by Proportion")

    ## Add a subheader
    st.markdown("### Explore mutations over time by proportion")

    st.write("Explore all mutations found and filter by proportions. Notice that this is a heavy operation and may take a while to load.")

    ## select dat range
    st.write("Select a date range:")
    # Get dynamic date range from API with bounds to enforce limits
    default_start, default_end, min_date, max_date = wiseLoculus.get_cached_date_range_with_bounds("dynamic_mutations")
    
    # Load date range from URL or use defaults
    url_start_date = url_state.load_from_url("start_date", default_start, date)
    url_end_date = url_state.load_from_url("end_date", default_end, date)
    
    date_range = st.date_input(
        "Select a date range:", 
        [url_start_date, url_end_date],
        min_value=min_date,
        max_value=max_date
    )
    
    # Save date range to URL
    if len(date_range) == 2:
        url_state.save_to_url(start_date=date_range[0], end_date=date_range[1])

    ## Add a horizontal line
    st.markdown("---")

    ## Fetch locations from API
    default_locations = ["Zürich (ZH)", "Lugano (TI)", "Chur (GR)"] # Define default locations
    # Fetch locations using the new function
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

    # Amino Acids or Nucleotides
    url_sequence_type = url_state.load_from_url("sequence_type", "Nucleotides", str)
    sequence_type_options = ["Nucleotides", "Amino Acids"]
    sequence_type_index = sequence_type_options.index(url_sequence_type) if url_sequence_type in sequence_type_options else 0
    sequence_type = st.selectbox("Select Sequence Type:", sequence_type_options, index=sequence_type_index)
    
    # Save sequence type to URL
    url_state.save_to_url(sequence_type=sequence_type)

    # the sequence type selection determines the default value for min_proportion
    if sequence_type == "Nucleotides":
        default_min_proportion = 0.2
    elif sequence_type == "Amino Acids":
        default_min_proportion = 0.4
    else:
        default_min_proportion = 0.05
    

    # text box with min_proportion – mutaiton has to occure at least once to this proportion to show up
    url_min_proportion = url_state.load_from_url("min_proportion", default_min_proportion, float)
    min_proportion = st.number_input(
        "Minimum Proportion of Mutation to fetch (the lower the longer the loading time)",
        min_value=0.01,
        max_value=1.0,
        value=url_min_proportion,  # Default value from URL or computed default
        step=0.01,
        help="Set the minimum proportion of mutation to fetch in the heatmap."
    )
    
    # Save min proportion to URL
    url_state.save_to_url(min_proportion=min_proportion)

    # Add performance warning
    st.warning("⚠️ **Performance Notice**: Loading this plot may take up to a minute for proportions below 15% due to the high number of datapoints to fetch.")

    # Check if all necessary parameters are available
    if date_range and len(date_range) == 2 and location and min_proportion:
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
                locationName=location,
                min_proportion=min_proportion  # Lower threshold to get more mutations
            ))


            if mutations_in_timeframe_df.empty or 'mutation' not in mutations_in_timeframe_df.columns:
                st.warning("⚠️ No mutations found for the selected parameters.")
                st.info("Try adjusting the date range or location.")
            else:
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
                    sequence_type=mutation_type,
                    date_range=(start_date, end_date),
                    location=location,
                    config=plot_config,
                    session_prefix="proportion_",
                    url_state_manager=url_state
                )
                
                if result is None:
                    st.info("💡 Try adjusting the date range, location, or minimum proportion.")
                else:
                    st.success(f"Successfully analyzed {len(result['filtered_mutations'])} mutations.")
                
        except Exception as e:
            st.error(f"⚠️ Error fetching mutation data: {str(e)}")
            st.info("This could be due to API connectivity issues. Please try again later.")
    else:
        st.info("Please configure all parameters above to display the mutation analysis.")
        if not date_range or len(date_range) != 2:
            st.info("• Please select a complete date range")
        if not location:
            st.info("• Please select a location")
        if not min_proportion:
            st.info("• Please set a minimum proportion value")


if __name__ == "__main__":
    app()