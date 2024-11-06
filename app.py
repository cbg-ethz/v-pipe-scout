import streamlit as st
import index
import mutation_freq
import variant_deconv

# No need for PIL now

PAGES = {
    "Home": {"module": index}, 
    "Mutation Frequency": {"module": mutation_freq},
    "Variant Deconvolution": {"module": variant_deconv},
}

def sidebar():
    st.sidebar.title("Navigation")
    selection = st.sidebar.radio("Go to", list(PAGES.keys()))  # No format_func
    return selection

if __name__ == "__main__":
    st.set_page_config(page_title="My Streamlit App", page_icon=":smiley:") 
    selection = sidebar()
    page = PAGES[selection]["module"]
    page.app()