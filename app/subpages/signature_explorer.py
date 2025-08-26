import streamlit as st
from datetime import datetime

from api.wiseloculus import WiseLoculusLapis
from api.covspectrum import CovSpectrumLapis
from interface import MutationType
from components.variant_signature_component import render_signature_composer
from components.mutation_plot_component import render_mutation_plot_component
from utils.config import get_wiseloculus_url, get_covspectrum_url


# Get server configuration from centralized config
wise_server_ip = get_wiseloculus_url()
cov_spectrum_api = get_covspectrum_url()
    
wiseLoculus = WiseLoculusLapis(wise_server_ip)
covSpectrum = CovSpectrumLapis(cov_spectrum_api)

def app():

    st.title("Variant Signature Explorer")
    st.subheader("Explore variant signatures in the wastewater data.")
    st.write("First make a variant definition based on live queries to CovSpectrum.")
    st.write("Then explore the variant signature in the wastewater data, on read level.")


    # Configure the component with full functionality
    component_config = {
        'show_nucleotides_only': False,
        'slim_table': False,
        'show_distributions': True,
        'show_download': True,
        'show_plot': True,
        'title': "Variant Signature Explorer",
        'show_title': True,
        'show_description': True
    }

    # Render the variant signature component
    signature_result = render_signature_composer(
        covSpectrum,
        component_config,
        session_prefix="compact_"  # Use a prefix to avoid session state conflicts
    )
    
    # Handle the case where no mutations are selected yet
    if signature_result is None:
        selected_mutations = []
        sequence_type_value = "nucleotide"
    else:
        selected_mutations, sequence_type_value = signature_result

    st.markdown("---")

    st.subheader("Dynamic Mutations-over-time of Signature Mutations")
    st.markdown("#### on Read Level")
    st.write("Are these global signatures, already observed in the wastewater data? - Check the plot below.")
    st.write("The data is fetched from the WISE-CovSpectrum API and currently contains demo data for Feb-Mar 2025.")

    #### #3) Select the date range
    # Get dynamic date range from API with bounds to enforce limits
    default_start, default_end, min_date, max_date = wiseLoculus.get_cached_date_range_with_bounds("signature_explorer")
    date_range = st.date_input(
        "Select a date range:", 
        [default_start, default_end],
        min_value=min_date,
        max_value=max_date
    )
    #### #4) Select the location
    default_locations = ["Zürich (ZH)"]  # Define default locations
    locations = wiseLoculus.fetch_locations(default_locations)
    location = st.selectbox("Select Location:", locations)

    # Check if all necessary parameters are available
    if selected_mutations and date_range and len(date_range) == 2 and location:

        # Convert date objects to datetime objects
        start_date = datetime.combine(date_range[0], datetime.min.time())
        end_date = datetime.combine(date_range[1], datetime.min.time())

        st.write("Exploring the signature mutations in wastewater data for the selected parameters.")
        
        # Configure the component for signature mutations
        plot_config = {
            'show_frequency_filtering': True,
            'show_date_options': True,
            'show_download': True,
            'show_summary_stats': True,
            'default_min_frequency': 0.01,
            'default_max_frequency': 1.0,
            'plot_title': f"Signature Mutations Over Time ({sequence_type_value.title()})",
            'enable_empty_date_toggle': True,
            'show_mutation_count': True
        }
        
        # Use the mutation plot component
        result = render_mutation_plot_component(
            wiseLoculus=wiseLoculus,
            mutations=selected_mutations,
            sequence_type=MutationType.NUCLEOTIDE, # Signature mutations are always nucleotide
            date_range=(start_date, end_date),
            location=location,
            config=plot_config,
            session_prefix="signature_"
        )
        
        if result is None:
            st.info("💡 Try adjusting the date range, location, or signature mutations.")
        else:
            st.success(f"Successfully analyzed {len(result['filtered_mutations'])} signature mutations.")
    else:
        st.warning("Please select mutations, a valid date range, and a location to display the analysis.")
        if not selected_mutations:
            st.info("• No mutations selected from the signature composer above")
        if not date_range or len(date_range) != 2:
            st.info("• Please select a complete date range")
        if not location:
            st.info("• Please select a location")


if __name__ == "__main__":
    app()