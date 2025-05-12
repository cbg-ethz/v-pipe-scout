import streamlit as st
import subpages.index as index
import subpages.resistance_mut_silo as resistance_mut_silo
import subpages.dynamic_mutations as dynamic_mutations
import subpages.signature_explorer as signature_explorer
import subpages.variant_signature_composer as variant_signature_composer
import subpages.download_count_cov as download_count_cov

if __name__ == "__main__":
    st.set_page_config(
        page_title="V-Pipe Online",
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
        {"app": variant_signature_composer.app, "title": "Variant Signature Composer", "icon": "🧩", "url_path": "signature-composer"},
        {"app": download_count_cov.app, "title": "Download Mutation Counts and Coverage", "icon": "⬇️", "url_path": "download-count-coverage"}
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