import streamlit as st
import pandas as pd
import pathlib
from datetime import date

from datetime import datetime

from interface import MutationType
from api.wiseloculus import WiseLoculusLapis
from visualize.mutations import mutations_over_time
from utils.config import get_wiseloculus_url
from utils.url_state import create_url_state_manager
from components.mutation_plot_component import render_mutation_plot_component

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
    
    date_range_in = st.date_input(
        "Select a date range:", 
        [url_start_date, url_end_date],
        min_value=min_date,
        max_value=max_date
    )

    # Ensure date_range is a tuple with two elements
    if len(date_range_in) != 2:
        st.error("Please select a valid date range with a start and end date.")
        return

    start_date = datetime.fromisoformat(date_range_in[0].strftime('%Y-%m-%d'))
    end_date = datetime.fromisoformat(date_range_in[1].strftime('%Y-%m-%d'))
    date_range = (start_date, end_date)
    
    # Save date range to URL
    url_state.save_to_url(start_date=date_range[0], end_date=date_range[1])

    
    locations = wiseLoculus.fetch_locations()
    location = st.selectbox("Select Location:", locations)

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
            mutation_type = MutationType.AMINO_ACID
            
            # Configure the component for dynamic mutations
            plot_config = {
                'show_frequency_filtering': True,
                'show_date_options': True,
                'show_download': True,
                'show_summary_stats': True,
                'default_min_frequency': 0.01,
                'default_max_frequency': 1.0,
                'plot_title': f"Resistance Mutations Over Time",
                'enable_empty_date_toggle': True,
                'show_mutation_count': True
            }
            
            # Use the mutation plot component
            result = render_mutation_plot_component(
                wiseLoculus=wiseLoculus,
                mutations=formatted_mutations,
                sequence_type=mutation_type,
                date_range=date_range,
                location=location,
                config=plot_config,
                session_prefix="proportion_"
            )
            
            if result is None:
                st.info("💡 Try adjusting the date range, location, or minimum proportion.")
            else:
                st.success(f"Successfully analyzed {len(result['filtered_mutations'])} mutations.")
        except Exception as e:
            st.error(f"⚠️ Error fetching mutation data: {str(e)}")
            st.info("This could be due to API connectivity issues. Please try again later.")

if __name__ == "__main__":
    app()