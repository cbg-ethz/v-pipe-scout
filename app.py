import streamlit as st
import subpages.index as index
import subpages.resistance_mut_silo as resistance_mut_silo
import subpages.dynamic_mutations as dynamic_mutations
import subpages.signature_explorer as signature_explorer
import subpages.variant_signature_composer as variant_signature_composer

if __name__ == "__main__":
    st.set_page_config(
        page_title="V-Pipe Online",
        page_icon="https://cbg-ethz.github.io/V-pipe/favicon-32x32.png",
        layout="wide"
    )
    
    # Create navigation with proper URLs for subpages, but hide the default navigation UI
    # to replace it with a custom navigation system in the sidebar for a more tailored user experience.
    pages = [
        st.Page(index.app, title="Home", icon="🏠", default=True),
        st.Page(resistance_mut_silo.app, title="Resistance Mutations", icon="🧬", url_path="resistance"),
        st.Page(dynamic_mutations.app, title="Dynamic Mutation Heatmap", icon="🧮", url_path="dynamic-mutations"),
        st.Page(signature_explorer.app, title="Variant Signature Explorer", icon="🔍", url_path="signature-explorer"),
        st.Page(variant_signature_composer.app, title="Variant Signature Composer", icon="🧩", url_path="signature-composer")
    ]
    
    # Get the current page but hide the navigation UI
    current_page = st.navigation(pages, position="hidden")
    
    # Display the logo and create custom navigation in the sidebar
    with st.sidebar:
        # Display the logo above navigation
        st.image("images/V-Pipe_SILO_logo.png", caption="")
        st.title("Navigation")
        
        # Create custom navigation links using page_link
        for page in pages:
            st.page_link(page, label=f"{page.icon} {page.title}" if page.icon else page.title)
    
    # Run the current page
    current_page.run()