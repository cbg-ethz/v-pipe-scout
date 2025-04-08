import streamlit as st
import index
import resistance_mut_silo
import web_explorer

PAGES = {
    "Home": {"module": index}, 
    "Resistance Mutations": {"module": resistance_mut_silo},
    "Dynamic Mutation Heatmap": {"module": web_explorer},
    
}

def sidebar():

    st.sidebar.image("images/V-Pipe_SILO_logo.png", caption="")
    st.sidebar.title("Navigation")
    selection = st.sidebar.radio("Explore the data using", list(PAGES.keys()))  # Changed to selectbox
    return selection

if __name__ == "__main__":
    st.set_page_config(
        page_title="V-Pipe Online", 
        page_icon="https://cbg-ethz.github.io/V-pipe/favicon-32x32.png",
        layout="wide"  # Set default to wide mode
    )
    selection = sidebar()
    page = PAGES[selection]["module"]
    page.app()