import streamlit as st
import pandas as pd
import pathlib

from datetime import datetime

from interface import MutationType
from api.wiseloculus import WiseLoculusLapis
from visualize.mutations import mutations_over_time
from utils.config import get_wiseloculus_url
from components.mutation_plot_component import render_mutation_plot_component

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
    date_range_in = st.date_input(
        "Select a date range:", 
        [default_start, default_end],
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
    
    locations = wiseLoculus.fetch_locations()
    location = st.selectbox("Select Location:", locations)
    
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