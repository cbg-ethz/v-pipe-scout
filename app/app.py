import streamlit as st
import logging
import os
from streamlit_theme import st_theme

import subpages.index as index
import subpages.resistance_mut_silo as resistance_mut_silo
import subpages.dynamic_mutations as dynamic_mutations
import subpages.signature_explorer as signature_explorer
import subpages.abundance_estimator as abundance_estimator
import subpages.background as background
from utils.system_health import initialize_health_monitoring, display_global_system_status

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == "__main__":
    st.set_page_config(
        page_title="V-Pipe Scout",
        page_icon="https://cbg-ethz.github.io/V-pipe/favicon-32x32.png",
        layout="wide"
    )

    # --- Google Analytics (GA4) injection using .env only (cookieless via Consent Mode v2) ---
    GA_ID = os.environ.get("GA_MEASUREMENT_ID")
    if GA_ID:
        import streamlit.components.v1 as components
        ga_html = f"""
                <script>
                    // Consent Mode v2: deny analytics/ad storage to avoid analytics cookies (cookieless pings only)
                    window.dataLayer = window.dataLayer || [];
                    function gtag(){{dataLayer.push(arguments);}}
                    gtag('consent', 'default', {{
                        'ad_storage': 'denied',
                        'analytics_storage': 'denied',
                        'ad_user_data': 'denied',
                        'ad_personalization': 'denied',
                        'functionality_storage': 'denied',
                        'security_storage': 'granted'
                    }});
                </script>
                <script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
                <script>
                    gtag('js', new Date());
                    gtag('config', '{GA_ID}', {{
                        'anonymize_ip': true,
                        'allow_google_signals': false,
                        'send_page_view': true
                    }});
                </script>
                """
        components.html(f"<div style='display:none'>{ga_html}</div>", height=0, scrolling=False)
    # --- end GA injection ---
    
    # Initialize health monitoring session state
    initialize_health_monitoring()
    
    # Create navigation with proper URLs for subpages, but hide the default navigation UI
    # to replace it with a custom navigation system in the sidebar for a more tailored user experience.
    # Page configurations
    PAGE_CONFIGS = [
        {"app": index.app, "title": "Home", "icon": "🏠", "default": True, "url_path": None},
        {"app": resistance_mut_silo.app, "title": "Resistance Mutations", "icon": "🧬", "url_path": "resistance"},
        {"app": dynamic_mutations.app, "title": "Dynamic Mutation Heatmap", "icon": "🧮", "url_path": "dynamic-mutations"},
        {"app": background.app, "title": "Untracked Mutations", "icon": "👀", "url_path": "background"},
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
        # Get current theme and display appropriate logo
        theme = st_theme()
        
        # Display theme-appropriate logo
        if theme and theme.get('base') == 'dark':
            # Dark theme - use inverted logo
            st.image("images/logo/v-pipe-scout-inverted.png", use_container_width=True)
        else:
            # Light theme or unknown theme - use regular logo
            st.image("images/logo/v-pipe-scout.png", use_container_width=True)
        
        
        # Create custom navigation links using page_link
        for page in pages:
            st.page_link(page, label=page.title)
        
        # Display API status only when there are issues
        display_global_system_status()
    
    # Run the current page
    current_page.run()