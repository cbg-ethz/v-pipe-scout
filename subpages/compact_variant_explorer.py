"""
Example page demonstrating how to use the variant signature composer component
in a compact format with nucleotides only.
"""

import streamlit as st
import yaml
import pandas as pd
from api.covspectrum import CovSpectrumLapis
from components.variant_signature_component import render_signature_composer

def app():
    st.title("Compact Variant Signature Explorer")
    st.write("This page demonstrates how to use the variant signature component in a compact format.")

    # Load configuration from config.yaml
    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)

    server_ip = config.get('server', {}).get('lapis_address', 'http://default_ip:8000')
    cov_spectrum_api = config.get('server', {}).get('cov_spectrum_api', 'https://lapis.cov-spectrum.org')
    
    cov_spectrum = CovSpectrumLapis(cov_spectrum_api)

    # Configure the component for a compact display
    compact_config = {
        'show_nucleotides_only': True,  # Only show nucleotides option
        'slim_table': True,             # Use a simplified table
        'show_distributions': False,    # Don't show the distribution plots
        'show_download': True,          # Allow downloading as YAML
        'show_title': False,            # Don't show the title (we already have a page title)
        'show_description': False,      # Don't show the description
        'default_variant': 'LP.8'       # Default variant to query
    }

    # Render the variant signature component
    selected_mutations = render_signature_composer(
        cov_spectrum,
        cov_spectrum_api,
        compact_config,
        session_prefix="compact_"  # Use a prefix to avoid session state conflicts
    )

    # Display selected mutations if any
    if selected_mutations:
        st.success(f"Selected {len(selected_mutations)} mutations")
        st.write("Selected mutations:", selected_mutations)

if __name__ == "__main__":
    app()
