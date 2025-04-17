import streamlit as st
import yaml
import pandas as pd
import logging
import streamlit.components.v1 as components

from common import fetch_locations, parse_url_hostname
import requests


# Load configuration from config.yaml
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

server_ip = config.get('server', {}).get('lapis_address', 'http://default_ip:8000')
cov_sprectrum_api = config.get('server', {}).get('cov_spectrum_api', 'https://lapis.cov-spectrum.org')
    

def app():
    st.title("Variant Signature Composer")

    st.write("This page allows you to visualize signature mutations for different variants over time.")
    st.write("We query CovSpectrum for the defining mutations of the variants.")

    st.write("The user may adjust the choices of how variants signatures are defined.")
    st.markdown("---")
    st.markdown("### Variant Signature Composer")

    # --- Debounce logic using session state ---
    import time
    if 'last_change' not in st.session_state:
        st.session_state['last_change'] = time.time()
    if 'mutations' not in st.session_state:
        st.session_state['mutations'] = []
    if 'mutation_df' not in st.session_state:
        st.session_state['mutation_df'] = pd.DataFrame()

    def fetch_mutations_api(variantQuery, sequence_type, min_abundance):
        base_url = f"{cov_sprectrum_api}/open/v2/sample/"
        params = (
            f"variantQuery={variantQuery}"
            f"&minProportion={min_abundance}"
            f"&limit=1000"
            f"&downloadAsFile=false"
        )
        if sequence_type == "Nucleotides":
            url = f"{base_url}nucleotideMutations?{params}"
        else:
            url = f"{base_url}aminoAcidMutations?{params}"
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])

    # Save the last fetched DataFrame for plotting
    def fetch_mutations():
        try:
            mutation_data = fetch_mutations_api(variantQuery, sequence_type, min_abundance)
            df = pd.DataFrame(mutation_data)
            st.session_state['last_fetched_df'] = df.copy()
            if df.empty:
                st.session_state['mutations'] = []
                st.session_state['mutation_df'] = pd.DataFrame()
                st.error("No mutations found. This may be due to an invalid query or a server error. Please check your query and try again.\nIf you see errors in the console, please review the details or contact support.")
                return
            # Filter by min_coverage
            df = df[df['coverage'] >= min_coverage]
            muts = df['mutation'].tolist()
            st.session_state['mutations'] = muts
            st.session_state['mutation_df'] = pd.DataFrame({
                'Mutation': muts,
                'Selected': [True]*len(muts)
            })
        except Exception as e:
            st.session_state['mutations'] = []
            st.session_state['mutation_df'] = pd.DataFrame()
            st.error(f"Failed to fetch mutations. Please check your query and try again.\nError details: {e}")

    # --- UI controls ---
    variantQuery = st.text_input(
        "Enter your variant query (e.g., LP.8, B.1.617.2):", "LP.8", key='variantQuery')
    sequence_type = st.selectbox("Select Sequence Type:", ["Nucleotides", "Amino Acids"])
    sequence_type_value = "amino acid" if sequence_type == "Amino Acids" else "nucleotide"
    min_abundance = st.slider(
        "Minimal Proportion (fraction of clinical sequences with this mutation in this variant):",
        0.0, 1.0, 0.8, key='min_abundance',
        help="This is the minimal fraction of clinical sequences assigned to this variant that must have the mutation for it to be included."
    )
    min_coverage = st.slider("Select the minimal coverage of mutation – no of sequences:", 0, 250, 15, key='min_coverage')

    # --- Debounce: update last_change on any input change ---
    changed = False
    for k in ['variantQuery', 'min_abundance', 'min_coverage']:
        if st.session_state.get(k) != st.session_state.get(f'_prev_{k}'):
            st.session_state[f'_prev_{k}'] = st.session_state.get(k)
            st.session_state['last_change'] = time.time()
            changed = True

    # --- Debounce logic: fetch after 500ms idle ---
    if changed:
        st.session_state['debounce_triggered'] = False
    if not st.session_state.get('debounce_triggered', False):
        if time.time() - st.session_state['last_change'] > 0.5:
            fetch_mutations()
            st.session_state['debounce_triggered'] = True

    # --- Manual fetch button ---
    if st.button("Fetch Mutations"):
        fetch_mutations()
        st.session_state['debounce_triggered'] = True

    st.markdown(
        """
        Below are the mutations found for your selected variant and filters.\
        You can deselect mutations you don’t want to include, or add extra ones by adding a new row in the table below.
        """
    )

    # --- Data editor for mutation selection ---
    selected_mutations = None
    if not st.session_state['mutation_df'].empty:
        # Try to get the last fetched DataFrame for extra columns
        df = st.session_state.get('last_fetched_df', pd.DataFrame())
        # Merge coverage and proportion columns if available
        mutation_df = st.session_state['mutation_df']
        if not df.empty and 'mutation' in df.columns:
            # Only keep relevant columns
            cols = ['mutation']
            if 'coverage' in df.columns:
                cols.append('coverage')
            if 'proportion' in df.columns:
                cols.append('proportion')
            extra = df[cols].rename(columns={'mutation': 'Mutation'})
            # Merge on Mutation
            merged = pd.merge(mutation_df, extra, on='Mutation', how='left')
            # Reorder columns for display
            display_cols = ['Mutation', 'Selected']
            if 'coverage' in merged.columns:
                display_cols.append('coverage')
            if 'proportion' in merged.columns:
                display_cols.append('proportion')
            merged = merged[display_cols]
        else:
            merged = mutation_df
        st.info(f"{len(merged)} signature mutations found.")
        edited_df = st.data_editor(
            merged,
            num_rows="dynamic",
            use_container_width=True,
            key='mutation_editor',
            disabled=["Mutation", "coverage", "proportion"] if 'coverage' in merged.columns or 'proportion' in merged.columns else ["Mutation"],
        )
        st.session_state['mutation_df'] = edited_df[[c for c in edited_df.columns if c in ['Mutation', 'Selected']]]
        selected_mutations = edited_df[edited_df['Selected']]['Mutation'].tolist()
    else:
        st.info("No mutations found. Adjust your filters or add mutations manually.")

    # --- Only show coverage/proportion plots after first query ---
    if 'last_fetched_df' in st.session_state:
        st.markdown('---')
        st.subheader('Coverage and Proportion Distributions')
        import matplotlib.pyplot as plt
        import numpy as np
        # Try to use the last mutation DataFrame if available
        mutation_df = st.session_state.get('mutation_df', pd.DataFrame())
        # Use the original DataFrame if available (for coverage/proportion columns)
        if 'mutation_data_df' in st.session_state:
            df = st.session_state['mutation_data_df']
        else:
            df = None
        # Try to get the DataFrame from the last fetch
        if df is None or df.empty:
            if 'last_fetched_df' in st.session_state:
                df = st.session_state['last_fetched_df']
        if df is None or df.empty:
            df = mutation_df
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
        plotted = False
        if not df.empty:
            if 'coverage' in df.columns:
                axes[0].hist(df['coverage'].dropna(), bins=20, color='skyblue', edgecolor='black')
                axes[0].set_title('Coverage Distribution')
                axes[0].set_xlabel('Coverage')
                axes[0].set_ylabel('Count')
                plotted = True
            else:
                axes[0].set_visible(False)
            if 'proportion' in df.columns:
                axes[1].hist(df['proportion'].dropna(), bins=20, color='orange', edgecolor='black')
                axes[1].set_title('Proportion Distribution')
                axes[1].set_xlabel('Proportion (fraction of clinical sequences with this mutation in this variant)')
                axes[1].set_ylabel('Count')
                plotted = True
            else:
                axes[1].set_visible(False)
        if not plotted:
            fig.delaxes(axes[1])
            fig.delaxes(axes[0])
            fig, ax = plt.subplots(figsize=(5, 2))
            ax.text(0.5, 0.5, 'No coverage or proportion data available.', ha='center', va='center')
            ax.axis('off')
            st.pyplot(fig)
        else:
            st.pyplot(fig)
        

        st.markdown("---")

            
        # --- Option to download mutation signature as YAML ---
        if not st.session_state['mutation_df'].empty and selected_mutations:
            import io
            import yaml as pyyaml
            # Prepare YAML content
            yaml_dict = {variantQuery: selected_mutations}
            yaml_str = pyyaml.dump(yaml_dict, sort_keys=False, allow_unicode=True)
            yaml_bytes = io.BytesIO(yaml_str.encode('utf-8'))
            st.download_button(
                label="Download mutation signature as YAML",
                data=yaml_bytes,
                file_name=f"{variantQuery}_signature.yaml",
                mime="application/x-yaml"
            )

    st.markdown("---")

    ## Add a subheader: Make dynamic plot of this

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
    # TODO: remove the next two lines
    address_no_port = parse_url_hostname(server_ip)
    location_url = f'{address_no_port}/sample/aggregated?fields=location_name&limit=100&dataFormat=JSON&downloadAsFile=false'
    locations = fetch_locations(location_url, default_locations)
    location = st.selectbox("Select Location:", locations)

   
    # Check if all necessary parameters are available
    if selected_mutations and date_range and len(date_range) == 2 and location:
        # Use the dynamically generated list of mutations string
        # The formatted_mutations_str variable already contains the string representation
        # of the list with double quotes, e.g., '["ORF1a:T103L", "ORF1a:N126K"]'
        # The lapisFilter uses double curly braces {{ and }} to escape the literal
        # curly braces needed for the JSON object within the f-string.
        display_mutations = str(st.session_state['mutations']).replace("'", '"')
        components.html(
            f"""
            <html>
            <head>
            <script type="module" src="https://unpkg.com/@genspectrum/dashboard-components@latest/standalone-bundle/dashboard-components.js"></script>
            <link rel="stylesheet" href="https://unpkg.com/@genspectrum/dashboard-components@latest/dist/style.css" />
            </head>
                <body>
                <!-- Component documentation: https://genspectrum.github.io/dashboard-components/?path=/docs/visualization-mutations-over-time--docs -->
                <gs-app lapis="{server_ip}">
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