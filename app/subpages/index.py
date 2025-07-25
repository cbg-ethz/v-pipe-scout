import streamlit as st
from streamlit_theme import st_theme
from utils.system_info import get_version_info, get_system_info
from utils.system_health import get_system_health_status

def app():
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
    
    # Debug Information Section (Collapsible)
    st.markdown("---")
    with st.expander("🛠️ Debug Information", expanded=False):
        st.markdown("### System Information")
        
        # Version Information (simplified)
        from utils.system_info import get_version_info, get_system_info
        from utils.system_health import get_system_health_status
        
        version_info = get_version_info()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Version Information:**")
            if version_info['version']:
                st.code(f"Version: {version_info['version']}")
            
            if version_info['build_date']:
                st.text(f"Built: {version_info['build_date']}")
            
            # Show source of version info
            st.caption(f"Source: {version_info['source']}")
        
        with col2:
            st.markdown("**System Status:**")
            system_info = get_system_info()
            if system_info['python_version']:
                st.text(f"Python: {system_info['python_version']}")
            st.text(f"Current Time: {system_info['current_time']}")
        
        # API Health Status
        st.markdown("**API Health Status:**")
        health_results = get_system_health_status()
        
        for api_name, result in health_results.items():
            status_emoji = "✅" if result.is_healthy else "⚠️" if result.is_available else "❌"
            st.text(f"{status_emoji} {api_name.title()}: {result.status.value}")
            
            if result.response_time_ms:
                st.text(f"   Response Time: {result.response_time_ms:.1f}ms")
            if result.error_message:
                st.text(f"   Error: {result.error_message}")
            if result.last_checked:
                import datetime
                check_time = datetime.datetime.fromtimestamp(result.last_checked)
                st.text(f"   Last Checked: {check_time.strftime('%H:%M:%S')}")
