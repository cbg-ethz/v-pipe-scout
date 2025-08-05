import streamlit as st
from streamlit_theme import st_theme
from utils.system_info import get_version_info, get_system_info
from utils.system_health import get_system_health_status

def app():
    st.title("POC: Rapid Interactive Wastewater-based Viral Variant Detection")
    
    # Get current theme and display appropriate POC image
    theme = st_theme()
    
    # Display theme-appropriate POC image
    if theme and theme.get('base') == 'dark':
        # Dark theme - use inverted image
        st.image("images/index/POC_DeployForInternal_inverted.png", caption="POC Technical Setup")
    else:
        # Light theme or unknown theme - use regular image
        st.image("images/index/POC_DeployForInternal.png", caption="POC Technical Setup")
    
    st.write("## Overview")
    st.write("This is a Proof-Of-Concept for the FAIR-CBG Grant Objective: Fast querying of short reads.")
    
    st.write("We show the most recent 1 month of Swiss wastewater sequencing data for Sars-Cov-2, at 6 wastewater treatment plants.")
    
    st.write("The data was enriched with amino acid alignments, to enable the querying of resistance mutations.")

    st.success("**First-ever:** Real-time, interactive querying of more than 108 million short seqeuning reads in aligment in seconds in the browser.")
    st.warning("This project is still experimental and we claim no responsibility for the correctness of the data shown here.")

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
    
    st.write("## Technical Challenges")
    st.write("The difficulty of this demo lies in the enormous number of reads to make instantaneously available.")
    
    st.write("This requires heavy memory for the database to run:")
    st.markdown("**27 Mio Reads × 2.5 GB/Mio Reads = 67.5 GB of RAM**")
    st.markdown("**4 weeks x 67.5 GB/week =  270 GB of RAM**")

    # Debug Information Section (Collapsible)
    st.markdown("---")
    with st.expander("🛠️ Debug Information", expanded=False):
        st.markdown("### System Information")
        
        # Version Information (simplified)
        
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
