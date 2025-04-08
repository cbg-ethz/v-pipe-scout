import streamlit as st

def app():
    st.title("POC: Fast Short Read Querying 1-Month")
    
    st.write("This ")

    # show the image images/1Month

    st.image("images/1Month_POC_FastQueryReads.png", caption="1-Month Image")

    # Leave some space
    st.write("")
    # Head to mutation frequency
    st.write("Head to the Mutation Frequency page to visualize the mutations emerging.")
    st.write("If you identify new mutations arising, head to the Variant Deconvolution page and check on the fly.")

    st.write("This demo is done on Sars-Cov-2 data for Swiss wastewater samples.")
