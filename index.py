import streamlit as st

def app():
    st.title("V-Pipe @ BioHack24 !")
    
    st.write("Welcome to V-Pipe, the pipeline processing viral next-generation sequencing data and analyzing mixed virus populations.")
    st.write("Identify emerging viral mutations and variants in Swiss wastewater samples.")
    st.write("Identify the emergence of new variants on the fly!")

    # Leave some space
    st.write("")
    # Head to mutation frequency
    st.write("Head to the Mutation Frequency page to visualize the mutations emerging.")
    st.write("If you identify new mutations arising, head to the Variant Deconvolution page and check on the fly.")

    st.write("This demo is done on Sars-Cov-2 data for Swiss wastewater samples.")
