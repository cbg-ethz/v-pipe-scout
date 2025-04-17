from matplotlib import pyplot as plt
import numpy as np
import streamlit as st
import yaml
import pandas as pd
import logging
import aiohttp
import asyncio
import seaborn as sns
import streamlit.components.v1 as components
from cojac.sig_generate import listfilteredmutations

from common import fetch_locations, parse_url_hostname


# Load configuration from config.yaml
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

server_ip = config.get('server', {}).get('lapis_address', 'http://default_ip:8000')

async def fetch_data(session, mutation, date_range):
    payload = {
        "aminoAcidMutations": [mutation],
        "sampling_dateFrom": date_range[0].strftime('%Y-%m-%d'),
        "sampling_dateTo": date_range[1].strftime('%Y-%m-%d'),
        "fields": ["sampling_date"]
    }

    async with session.post(
        f'{server_ip}/sample/aggregated',
        headers={
            'accept': 'application/json',
            'Content-Type': 'application/json'
        },
        json=payload
    ) as response:
        if response.status == 200:
            data = await response.json()
            return {"mutation": mutation,
                    "data": data.get('data', [])}
        else:
            logging.error(f"Failed to fetch data for mutation {mutation}.")
            logging.error(f"Status code: {response.status}")
            logging.error(await response.text())
            return {"mutation": mutation,
                    "data": None}

async def fetch_all_data(mutations, date_range):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_data(session, mutation, date_range) for mutation in mutations]
        return await asyncio.gather(*tasks)
    





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

    def fetch_mutations():
        try:
            muts = listfilteredmutations(variantQuery, min_abundance, min_coverage, min_abundance_del)
            if not muts:
                st.session_state['mutations'] = []
                st.session_state['mutation_df'] = pd.DataFrame()
                st.error("No mutations found. This may be due to an invalid query or a server error. Please check your query and try again.\nIf you see errors in the console, please review the details or contact support.")
                return
            if isinstance(muts, set):
                muts = list(muts)
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
    variantQuery = st.text_input("Enter your variant query (e.g., LP.8, B.1.617.2):", "B.1.1.7", key='variantQuery')
    st.text("(advanced queries e.g.: 'BA.5* | nextcladePangoLineage:BA.5* | nextstrainClade:22B' are also supported)")
    sequence_type = st.selectbox("Select Sequence Type:", ["Nucleotides"])
    sequence_type_value = "amino acid" if sequence_type == "Amino Acids" else "nucleotide"
    min_abundance = st.slider("Select the minimal abundance % of substitutions:", 0.0, 1.0, 0.8, key='min_abundance')
    min_abundance_del = st.slider("Select the minimal abundance % of deletions:", 0.0, 1.0, 0.8, key='min_abundance_del')
    min_coverage = st.slider("Select the minimal coverage of mutation – no of seqeunces:", 0, 1000, 100, key='min_coverage')

    # --- Debounce: update last_change on any input change ---
    changed = False
    for k in ['variantQuery', 'min_abundance', 'min_abundance_del', 'min_coverage']:
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
    if not st.session_state['mutation_df'].empty:
        st.info(f"{len(st.session_state['mutation_df'])} signature mutations found.")
        edited_df = st.data_editor(
            st.session_state['mutation_df'],
            num_rows="dynamic",
            use_container_width=True,
            key='mutation_editor',
            disabled=["Mutation"],
        )
        st.session_state['mutation_df'] = edited_df
        selected_mutations = edited_df[edited_df['Selected']]['Mutation'].tolist()
    else:
        st.info("No mutations found. Adjust your filters or add mutations manually.")

    st.markdown("---")

    ## Add a subheader: Make dynamic plot of this

    st.subheader("Dynamic Mutations-over-time of Signature Mutations")
    st.markdown("#### on Read Level")

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

    # location = "Zürich (ZH)"
    # sequence_type_value = "amino acid"

    # formatted_mutations_str = str(formatted_mutations).replace("'", '"')

    # # strip of the part before the ":"
    # formatted_mutations_no_gene_str = str(list([mut.split(':')[1] for mut in formatted_mutations])).replace("'",'"')

    # st.write(formatted_mutations_no_gene_str)
    # st.write(start_date)
    # st.write(end_date)
    
    # ll = ["ORF1a:T103L", "ORF1a:N126K", "ORF1a:P252L", "ORF1a:R3561V", "S:E990A", "ORF1a:G143S"]
    # ll_str = str(ll).replace("'", '"')
    # st.write(ll_str)

    # # fetch the counts for SE990A
    # async def fetch_single_mutation(mutation, date_range):
    #     async with aiohttp.ClientSession() as session:
    #         return await fetch_data(session, mutation, date_range)

    # data_mut = asyncio.run(fetch_single_mutation("ORF1a:G143S", date_range)) # Assuming S gene based on context, adjust if needed

    # st.write("Data for ORF1a:G143S:")
    # st.write(data_mut)

    # # Use the dynamically generated list of mutations string
    # # The formatted_mutations_str variable already contains the string representation
    # # of the list with double quotes, e.g., '["ORF1a:T103L", "ORF1a:N126K"]'
    # # The lapisFilter uses double curly braces {{ and }} to escape the literal
    # # curly braces needed for the JSON object within the f-string.
    # components.html(
    #     f"""
    #     <html>
    #     <head>
    #     <script type="module" src="https://unpkg.com/@genspectrum/dashboard-components@latest/standalone-bundle/dashboard-components.js"></script>
    #     <link rel="stylesheet" href="https://unpkg.com/@genspectrum/dashboard-components@latest/dist/style.css" />
    #     </head>
    #         <body>
    #         <!-- Component documentation: https://genspectrum.github.io/dashboard-components/?path=/docs/visualization-mutations-over-time--docs -->
    #         <gs-app lapis="{server_ip}">
    #             <gs-mutations-over-time
    #             lapisFilter='{{"sampling_dateFrom":"{start_date}", "sampling_dateTo": "{end_date}", "location_name": "{location}"}}'
    #             sequenceType='{sequence_type_value}'
    #             views='["grid"]'
    #             width='100%'
    #             height='100%'
    #             granularity='day'
    #             displayMutations='{formatted_mutations_str}'
    #             lapisDateField='sampling_date'
    #             initialMeanProportionInterval='{{"min":0.00,"max":1.0}}'
    #             pageSizes='[50, 30, 20, 10]'
    #             />
    #         </gs-app>
    #         </head>
    #         <body>
    #         </body>
    #     </html>
    # """,
    #     height=1000,
    # )

    #  displayMutations='{formatted_mutations_str}'
if __name__ == "__main__":
    app()