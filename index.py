import streamlit as st

def app():
    st.title("POC: Fast Short Read Querying 1-Month")
    
    st.image("images/1Month_POC_FastQueryReads.png", caption="POC Technical Setup")
    
    st.write("## Overview")
    st.write("This is a Proof-Of-Concept for the FAIR-CBG Grant Objective: Fast querying of short reads.")
    
    st.markdown("**QUERY all 24.5 Mio Reads instantly as you access.**")
    
    st.write("We show 1 Month of full depth wastewater sequencing data for Zürich.")
    
    st.write("The data was enriched with amino acid alignments, to enable the querying of resistance mutations.")
    
    st.write("To get this running, heavy data wrangling and new pre-processing was required in the database SILO.")
    
    st.write("This demo is done on Sars-Cov-2 data for Swiss wastewater samples.")

    st.write("## Demo")
    st.markdown("""
    - *Resistance Mutations*: custom frontend to look up known amino acid mutations
    - *Dynamic Mutation Heatmap AA*: Amino Acid Mutations hijacking clinical GenSpectrum Frontend
    - *Dynamic Mutation Heatmap Nuc*: Nucliotides Mutations hijacking clinical GenSpectrum Frontend
    """)
    
    st.write("## Setup")
    st.markdown("""
    - V-Pipe nucleotide alignments are processed and wrangled on EULER.
    - Data is ingested in SILO running on a Dev Server of cEvo group.
    - This frontend runs on an ETHZ DBSSE machine.
    """)
    
    st.write("## Technical Challenges")
    st.write("The difficulty of this demo lies in the enormous number of reads to make instantaneously available.")
    
    st.write("This requires heavy memory for the database to run:")
    st.markdown("**24.5 Mio Reads × 2.5 GB/Mio Reads = 61.25 GB of RAM**")
    
    st.info("This project is under heavy development.")
