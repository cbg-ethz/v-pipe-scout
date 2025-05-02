import streamlit as st
import pages.index as index
import pages.variant_deconv as variant_deconv
import pages.resistance_mut_silo as resistance_mut_silo
import pages.dynamic_mutations as dynamic_mutations
import pages.variant_signature_compose as variant_signature_compose

PAGES = {
    "Home": {"module": index}, 
    "Resistance Mutations": {"module": resistance_mut_silo},
    "Dynamic Mutation Heatmap": {"module": dynamic_mutations},
    "Variant Signature Composer": {"module": variant_signature_compose},
    
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