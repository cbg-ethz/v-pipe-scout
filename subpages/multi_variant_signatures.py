"""This page allosw to compose the list of variants and their respectirve mutational signatures.
    Steps: 
    1. Select the variants of interest with their respective signature mutations / or load a pre-defined signature mutation set
        1.1 For a variant, search for the signature mutaitons
        1.2 Or load a pre-defined signature mutation set
    2. Build the mutation-variant matrix
    3. Visualize the mutation-variant matrix
    4. Export and download the mutation-variant matrix and var_dates.yaml
"""

import streamlit as st

def app():
    st.title("Multi Variant Signature Composer")

    st.write("This page will create the mutation-variant matrix.")
    st.write("This is one of the inputs to Lollipop")

    st.markdown("---")



if __name__ == "__main__":
    app()