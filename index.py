import streamlit as st

def app():
    st.title("V-Pipe @ BioHack24 !")
    
    col1, col2 = st.columns([1, 1])  # Create two equal columns

    with col1:
        # Add an image from a URL and center it
        st.write("<div style='text-align: center;'>", unsafe_allow_html=True)
        st.image("images/cbg.jpeg", width=140)
        st.write("</div>", unsafe_allow_html=True)

    with col2:
        # Add an image from a local file and center it
        st.write("<div style='text-align: center;'>", unsafe_allow_html=True)
        st.image("images/vpipe.png", width=100, use_column_width=True)
        st.write("</div>", unsafe_allow_html=True)

    st.write("Welcome to V-Pipe, a pipeline for variant calling and annotation.")
    st.write("Identify emerging viral mutations and vairants in swiss wasteater samples.")
    st.write("Identify emergence of new variants on the fly!")

    # leave some pace
    st.write("")
    # head to mutation frequency
    st.write("Head to the Mutation Frequency page to visualize the mutations emerging.")
    st.write("If you identify a new mutations arising, head to the Variant Deconvultion page and check on the fly.")
