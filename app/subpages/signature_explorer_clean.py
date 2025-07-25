import streamlit as st
import yaml
import pandas as pd
import streamlit.components.v1 as components

from api.wiseloculus import WiseLoculusLapis
from api.covspectrum import CovSpectrumLapis
from components.variant_signature_component import render_signature_composer


# Load configuration from config.yaml
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

wise_server_ip = config.get('server', {}).get('lapis_address', 'http://default_ip:8000')
cov_sprectrum_api = config.get('server', {}).get('cov_spectrum_api', 'https://lapis.cov-spectrum.org')
    
wiseLoculus = WiseLoculusLapis(wise_server_ip)
covSpectrum = CovSpectrumLapis(cov_sprectrum_api)

def app():
    st.title("Variant Signature Explorer")
    st.subheader("Explore the variant signatures in the wastewater data.")
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
    selected_mutations, sequence_type_value= render_signature_composer(
        covSpectrum,
        component_config,
        session_prefix="compact_"  # Use a prefix to avoid session state conflicts
    )

    st.markdown("---")

    st.subheader("Dynamic Mutations-over-time of Signature Mutations")
    st.markdown("#### on Read Level")
    st.write("Are these global signatures, already observed in the wastewater data? - Check the plot below.")
    st.write("The data is fetched from the WISE-CovSpectrum API and currently contains demo data for Feb-Mar 2025.")

    if selected_mutations is not None and len(selected_mutations) > 0:
        st.write(f"**Selected Mutations:** {', '.join(selected_mutations) if selected_mutations else 'None'}")

        if len(selected_mutations) > 10:
            st.warning("⚠️ Large number of mutations selected. This may take longer to process.")

        # Display mutations in a nice format
        mutations_df = pd.DataFrame({
            'Mutation': selected_mutations,
            'Type': [sequence_type_value] * len(selected_mutations)
        })
        st.dataframe(mutations_df, use_container_width=True)

        # Fetch and display mutation data over time
        try:
            with st.spinner("Fetching mutation data from WiseLoculus..."):
                mutation_data = wiseLoculus.fetch_mutation_counts_and_coverage(
                    mutations=selected_mutations,
                    sequence_type=sequence_type_value
                )

            if not mutation_data.empty:
                st.success(f"✅ Found data for {len(mutation_data)} time points")
                
                # Display the time series data
                st.subheader("Mutation Frequencies Over Time")
                st.dataframe(mutation_data, use_container_width=True)
                
                # Simple line plot
                if len(mutation_data.columns) > 1:
                    try:
                        st.line_chart(mutation_data.set_index(mutation_data.columns[0]))
                    except Exception as e:
                        st.write("Raw data preview:")
                        st.write(mutation_data.head())
            else:
                st.warning("⚠️ No mutation data found for the selected mutations.")
                st.write("This could mean:")
                st.write("- The mutations are not present in the wastewater data")
                st.write("- The data is still being processed")
                st.write("- There may be a temporary issue with the data source")

        except Exception as e:
            st.error(f"❌ Error fetching mutation data: {str(e)}")
            st.write("Please try again or contact support if the issue persists.")

    else:
        st.info("👆 Please select mutations using the variant signature composer above to see their frequency over time in wastewater data.")

    # Additional information
    st.markdown("---")
    st.markdown("### About This Tool")
    st.write("""
    This tool allows you to:
    1. **Define variants** using live data from CovSpectrum
    2. **Explore mutations** in wastewater sequencing data
    3. **Visualize trends** over time at the read level
    
    The wastewater data comes from high-depth sequencing and provides insights into 
    variant prevalence in the community before they appear in clinical samples.
    """)

    # Debug information (can be removed in production)
    with st.expander("🔧 Debug Information"):
        st.write(f"**WiseLoculus Server:** {wise_server_ip}")
        st.write(f"**CovSpectrum API:** {cov_sprectrum_api}")
        st.write(f"**Selected Mutations:** {selected_mutations}")
        st.write(f"**Sequence Type:** {sequence_type_value}")
