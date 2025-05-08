import streamlit as st
import yaml
import pandas as pd
import streamlit.components.v1 as components

from api.wiseloculus import WiseLoculusLapis
from api.covspectrum import CovSpectrumLapis
from components.variant_signature_component import render_signature_composer


# Load configuration from config.yaml
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

wise_server_ip = config.get('server', {}).get('lapis_address', 'http://default_ip:8000')
cov_sprectrum_api = config.get('server', {}).get('cov_spectrum_api', 'https://lapis.cov-spectrum.org')
    
wiseLoculus = WiseLoculusLapis(wise_server_ip)
covSpectrum = CovSpectrumLapis(cov_sprectrum_api)

def app():

    st.title("Variant Signature Explorer")
    st.subheader("Explore the variant signatures in the wastewater data.")
    st.write("First make a variant definition based on live queries to CovSpectrum.")
    st.write("Then explore the variant signature in the wastewater data, on read level.")


    # Configure the component with full functionality
    component_config = {
        'show_nucleotides_only': False,
        'slim_table': False,
        'show_distributions': True,
        'show_download': True,
        'show_plot': True,
        'title': "Variant Signature Explorer",
        'show_title': True,
        'show_description': True
    }

    # Render the variant signature component
    selected_mutations, sequence_type_value= render_signature_composer(
        covSpectrum,
        component_config,
        session_prefix="compact_"  # Use a prefix to avoid session state conflicts
    )

    st.markdown("---")

    st.subheader("Dynamic Mutations-over-time of Signature Mutations")
    st.markdown("#### on Read Level")
    st.write("Are these global signatures, already observed in the wastewater data? - Check the plot below.")
    st.write("The data is fetched from the WISE-CovSpectrum API and currently contains demo data for Feb-Mar 2025.")

    #### #3) Select the date range
    date_range = st.date_input("Select a date range:", [pd.to_datetime("2025-02-10"), pd.to_datetime("2025-03-08")])

    start_date = date_range[0].strftime('%Y-%m-%d')
    end_date = date_range[1].strftime('%Y-%m-%d')
    #### #4) Select the location
    default_locations = ["Zürich (ZH)"]  # Define default locations
    locations = wiseLoculus.fetch_locations(default_locations)
    location = st.selectbox("Select Location:", locations)


    # Check if all necessary parameters are available
    if selected_mutations and date_range and len(date_range) == 2 and location:

        st.write("NOTE: currently the below GenSpectrum Plot does not show mutations that have zero proportion in the selected date range.")
        st.write("Absence of the mutation, does not mean no coverage – this ISSUE is currently being considered.")

        # Use the dynamically generated list of mutations string
        # The formatted_mutations_str variable already contains the string representation
        # of the list with double quotes, e.g., '["ORF1a:T103L", "ORF1a:N126K"]'
        # The lapisFilter uses double curly braces {{ and }} to escape the literal
        # curly braces needed for the JSON object within the f-string.
        display_mutations = str(selected_mutations).replace("'", '"')
        components.html(
            f"""
            <html>
            <head>
            <script type="module" src="https://unpkg.com/@genspectrum/dashboard-components@latest/standalone-bundle/dashboard-components.js"></script>
            <link rel="stylesheet" href="https://unpkg.com/@genspectrum/dashboard-components@latest/dist/style.css" />
            </head>
                <body>
                <!-- Component documentation: https://genspectrum.github.io/dashboard-components/?path=/docs/visualization-mutations-over-time--docs -->
                <gs-app lapis="{wise_server_ip}">
                    <gs-mutations-over-time
                    lapisFilter='{{"sampling_dateFrom":"{start_date}", "sampling_dateTo": "{end_date}", "location_name": "{location}"}}'
                    sequenceType='{sequence_type_value}'
                    views='["grid"]'
                    width='100%'
                    height='100%'
                    granularity='day'
                    displayMutations='{display_mutations}'
                    lapisDateField='sampling_date'
                    initialMeanProportionInterval='{{"min":0.00,"max":1.0}}'
                    pageSizes='[50, 30, 20, 10]'
                    />
                </gs-app>
                </head>
                <body>
                </body>
            </html>
        """,
            height=1500,
        )
    else:
        st.warning("Please select mutations, a valid date range, and a location to display the plot.")


if __name__ == "__main__":
    app()