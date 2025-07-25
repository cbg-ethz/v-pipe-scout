import streamlit as st
from streamlit_theme import st_theme
from monitoring.system_health import setup_page_health_monitoring

def app():
    # Setup page with health checks - home page doesn't require specific APIs but shows warnings
    page_can_function, health_results = setup_page_health_monitoring(
        page_title="Home",
        required_apis=[],  # No specific APIs required for home page
        show_sidebar_status=False  # Sidebar status is shown globally
    )
    
    st.title("POC: Rapid Variant Abundance Estimation 1-Month")
    
    # Get current theme and display appropriate POC image
    theme = st_theme()
    
    # Display theme-appropriate POC image
    if theme and theme.get('base') == 'dark':
        # Dark theme - use inverted image
        st.image("images/index/POC_Rapid_Variant_Abundance_1Month_inverted.png", caption="POC Technical Setup")
    else:
        # Light theme or unknown theme - use regular image
        st.image("images/index/POC_Rapid_Variant_Abundance_1Month.png", caption="POC Technical Setup")
    
    st.write("## Overview")
    st.write("This is a Proof-Of-Concept for the FAIR-CBG Grant Objective: Fast querying of short reads.")
    
    st.markdown("**QUERY all 24.5 Mio Reads instantly as you access.**")
    
    st.write("We show 1 Month of full depth wastewater sequencing data for Zürich.")
    
    st.write("The data was enriched with amino acid alignments, to enable the querying of resistance mutations.")
    
    st.write("To get this running, heavy data wrangling and new pre-processing was required in the database SILO.")
    
    st.write("This demo is done on Sars-Cov-2 data for Swiss wastewater samples.")

    st.write("## Demo")
    st.markdown("""
    This demo most remarkably shows the integration of CovSpectrum and expert-defined variant definitions, 
    to enable the on-demand estimation of variant abundances. 
    Essentially, making the question of "**Is this variant present?**" practically rapidly solvable.           

    - *Resistance mutations*: Custom frontend to look up known amino acid mutations.
    - *Dynamic mutation heatmap (AA)*: Amino acid mutations hijacking the clinical GenSpectrum frontend.
    - *Dynamic mutation heatmap (Nuc)*: Nucleotide mutations hijacking the clinical GenSpectrum frontend.
    - *Explore variant signatures*: See variant-specific mutations over time.
    - *Explore Background Mutations*: See the mutations not currently accounted for in the variant signatures we track.
    - *Rapid variant abundance*: Estimate variant abundance over time for an interactively defined set of variants.
    """)
    
    st.write("## Setup")
    st.markdown("""
    - V-Pipe nucleotide alignments are processed and wrangled on EULER.
    - Data is ingested in SILO running on a Dev Server of cEvo group.
    - This frontend runs on an ETHZ DBSSE machine.
    - Variant abundance estimation, is also done in coorinated fashion on the same machine.
    """)
    
    st.write("## Technical Challenges")
    st.write("The difficulty of this demo lies in the enormous number of reads to make instantaneously available.")
    
    st.write("This requires heavy memory for the database to run:")
    st.markdown("**24.5 Mio Reads × 2.5 GB/Mio Reads = 61.25 GB of RAM**")
    
    st.info("This project is under heavy development.")
