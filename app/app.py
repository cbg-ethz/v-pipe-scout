import streamlit as st
import logging

import subpages.index as index
import subpages.resistance_mut_silo as resistance_mut_silo
import subpages.dynamic_mutations as dynamic_mutations
import subpages.signature_explorer as signature_explorer
import subpages.abundance_estimator as abundance_estimator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == "__main__":
    st.set_page_config(
        page_title="V-Pipe Scout",
        page_icon="https://cbg-ethz.github.io/V-pipe/favicon-32x32.png",
        layout="wide"
    )
    
    # Create navigation with proper URLs for subpages, but hide the default navigation UI
    # to replace it with a custom navigation system in the sidebar for a more tailored user experience.
    # Page configurations
    PAGE_CONFIGS = [
        {"app": index.app, "title": "Home", "icon": "🏠", "default": True, "url_path": None},
        {"app": resistance_mut_silo.app, "title": "Resistance Mutations", "icon": "🧬", "url_path": "resistance"},
        {"app": dynamic_mutations.app, "title": "Dynamic Mutation Heatmap", "icon": "🧮", "url_path": "dynamic-mutations"},
        {"app": signature_explorer.app, "title": "Variant Signature Explorer", "icon": "🔍", "url_path": "signature-explorer"},
        {"app": abundance_estimator.app, "title": "Variant Abundances", "icon": "🧩", "url_path": "abundance-estimator"}
    ]
    
    # Create pages dynamically from configurations
    pages = [
        st.Page(
            config["app"],
            title=config["title"],
            icon=config["icon"],
            default=config.get("default", False),
            url_path=config.get("url_path")
        )
        for config in PAGE_CONFIGS
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