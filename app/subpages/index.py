import streamlit as st
from streamlit_theme import st_theme
from utils.system_info import get_version_info, get_system_info
from utils.system_health import get_system_health_status
from api.wiseloculus import WiseLoculusLapis
from utils.config import get_wiseloculus_url

def app():
    st.title("Rapid Interactive Wastewater-based Viral Variant Detection")
    st.markdown("### First ever interactive querying of millions of short reads in the browser")
    st.markdown("#### Cutting weeks to minutes")
    
    # Get current theme and display appropriate POC image
    theme = st_theme()
    
    # Display theme-appropriate POC image

    # Dark theme - use inverted image
    st.image("images/index/welcome.png", caption="Illustration rapid browsing of millions of reads", width=600)

    
    st.write("## Overview")
    st.write("This is a Proof-Of-Concept for the FAIR-CBG Grant Objective: Fast querying of short reads.")
    
    st.write("We bring full transparency of Sars-Cov-2 mutations found Swiss wastewater sequencing data for the recent weeks to the browser.")
    
    st.write("Translation and amino acid alignment was performed to enable the direct querying for resistance mutations.")

    st.success("**First-ever:** Real-time, interactive querying of ~100 million short sequencing reads in alignment in seconds in the browser.")
    st.warning("This project is still experimental and we claim no responsibility for the correctness of the data shown here.")

    # Data Overview Section
    st.write("#### Current Dataset")
    
    # Initialize API client to fetch data info
    try:
        server_ip = get_wiseloculus_url()
        wiseLoculus = WiseLoculusLapis(server_ip)
        
        # Fetch date range and locations in a compact format
        with st.spinner("Fetching dataset information..."):
            date_start, date_end = wiseLoculus.get_cached_date_range("index_overview")
            locations = wiseLoculus.fetch_locations()
            
            if date_start and date_end and locations:
                duration = (date_end - date_start).days
                locations_str = ", ".join(locations)
                
                st.info(f"**{date_start.strftime('%Y-%m-%d')}** to **{date_end.strftime('%Y-%m-%d')}** ({duration} days) | "
                       f"**{len(locations)} locations:** {locations_str}")
            else:
                missing_parts = []
                if not (date_start and date_end):
                    missing_parts.append("date range")
                if not locations:
                    missing_parts.append("locations")
                st.warning(f"⚠️ Could not fetch: {', '.join(missing_parts)}")
                    
    except Exception as e:
        st.error(f"⚠️ Could not fetch dataset information: {str(e)}")
        # Fallback information
        st.info("**Fallback:** Swiss wastewater sequencing data from multiple treatment plants over recent weeks")

    st.write("## Capabilities")
    st.markdown("""
    This Proof-of-Concept most remarkably shows the integration of CovSpectrum and expert-defined variant definitions, 
    to enable the on-demand estimation of variant abundances. 
    Essentially, making the question of "**Is this variant present?**" practically rapidly solvable.

    The following features are available:           
    - *Resistance mutations*: Direct lookup of mature protein mutations known to confer resistance to antiviral drugs.
    - *Dynamic mutation heatmaps*: Search by minimal proportion in Amino acid mutations or Nucleotide mutations 
    - *Explore variant signatures*: Plot variant-specific mutations over time.
    - *Explore untracked mutations*: See the mutations not currently accounted for in the variant signatures we track.
    - *Rapid variant abundance*: Estimate variant abundance over time for an interactively defined set of variants.
    - *Region-specific mutations*: Explore mutations in specific genes or regions of the genome, userful for primer design.
    """)
    

    st.write("#### What does W-ASAP stand for?")
    st.markdown("""
    V-Pipe Scout is the first step toward a holistic Wastewater Analysis and Sharing Platform (W-ASAP) — a joint effort of the Computational Biology Group (CBG) and Computational Evolution Group (cEVO) at ETH Zürich.
    It is built on the [Loculus](https://loculus.org/) software and its high-performance SILO query engine, both developed by the cEVO Group.
    """)

    st.write("#### How are sequencing reads processed?")
    
    st.markdown("""
    **Quality Control & Preprocessing:**
    
    All preprocessing is performed using [V-Pipe](https://cbg-ethz.github.io/V-pipe/):
    - Filter reads shorter than 80% of intended length (250bp for SARS-CoV-2)
    - Remove reads with more than 4 N bases
    - Trim reads from both ends when quality score drops below 30
    - Discard reads when rolling mean quality score drops below 30 (sliding window of 10 bases)
    - Expected error rate: ~0.32% (Aviti sequencer) — [John et al., 2024](https://www.sciencedirect.com/science/article/pii/S0043135424013642?via%3Dihub)
    
    **Subsampling Strategy:**
    
    W-ASAP processes wastewater surveillance samples with highly variable read depths. To ensure consistent performance, we cap amplicon sequences at 4.5 million reads per sample through random subsampling, preserving Variant Allele Frequency and Haplotype Structure for reliable and predictable operations.
    
    For the full data for download, visit [db.wasap.genspectrum.org](https://db.wasap.genspectrum.org).
    
    **Nucleotide Alignment:**
    - Align reads to reference genome (Wuhan-Hu-1, NC_045512.2) using BWA
    - Performed as part of the V-Pipe workflow
    
    **Amino Acid Alignment:**
    - Translation and alignment performed using [DIAMOND](https://github.com/bbuchfink/diamond)
    - Integrated as part of [sr2silo](https://github.com/cbg-ethz/sr2silo)
    
    **Database Integration:**
    - Processed reads are wrangled into the [LAPIS](https://bmcbioinformatics.biomedcentral.com/articles/10.1186/s12859-023-05364-3) database format
    - Enables the interactive querying capabilities shown in this application
    """)

    st.write("#### Technical Challenges")
    st.write("The difficulty of this demo lies in the enormous number of reads to make instantaneously available.")
    
    st.write("This requires heavy memory for the database to run:")
    st.markdown("**27 Mio Reads × 2.5 GB/Mio Reads = 67.5 GB of RAM**")
    st.markdown("**4 weeks x 67.5 GB/week =  270 GB of RAM**")

    # Display theme-appropriate POC image
    if theme and theme.get('base') == 'dark':
        # Dark theme - use inverted image
        st.image("images/index/POC_DeployForInternal_inverted.png", caption="POC Technical Setup")
    else:
        # Light theme or unknown theme - use regular image
        st.image("images/index/POC_DeployForInternal.png", caption="POC Technical Setup")
    

    # LAPIS API Documentation Section (Collapsible)
    st.markdown("---")
    with st.expander("🔗 Try LAPIS API Yourself", expanded=False):
        st.markdown("### Direct Access to LAPIS API")
        
        # Get current LAPIS configuration
        try:
            lapis_url = get_wiseloculus_url()
            
            st.info(f"**Current LAPIS Server:** {lapis_url}")
            
            # Swagger UI link - hardcoded to correct URL
            swagger_url = f"{lapis_url}/swagger-ui/index.html"
            st.markdown(f"📋 **[Interactive API Documentation (Swagger UI)]({swagger_url})**")
            
            st.markdown("### Recommended Endpoints")
            st.markdown("""
            **Core Query Endpoints:**
            - **`/sample/aggregated`** - Aggregate samples by various fields (date, location, mutations)
            - **`/sample/details`** - Get detailed sample information with filtering
            - **`/sample/aminoAcidMutations`** - Query amino acid mutations across samples
            - **`/sample/nucleotideMutations`** - Query nucleotide mutations across samples
            
            **Time Series Endpoints:**
            - **`/sample/aggregated?groupByFields=date`** - Mutations over time data
            - **`/sample/aggregated?groupByFields=date,location`** - Location-specific time series
            """)
                
        except Exception as e:
            st.error(f"⚠️ Could not load LAPIS configuration: {str(e)}")
            st.info("Please check the configuration in `app/config.yaml` or contact administrators.")

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
