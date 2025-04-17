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
    st.title("Variant Signature Composer – View Variants Mutations Over Time")

    st.write("This page allows you to visualize signature mutations for different variants over time.")
    st.write("We query CovSpectrum for the defining mutations of the variants.")

    st.write("The user may adjust the choices of how variants signatures are defined.")

    # make a horizontal line
    st.markdown("---")

    ## Add a subheader: Variant Signature Composer

    #### #1) CovSpectrum Query - Select your Variant

    #### #2) Set your filters

    ###  #2.1) Select the minimal abundance of substitutions - default 0.8 

    ###  #2.2) Select the minimal abundance of deletions - default 0.8 

    ###  #2.3) Select the minimal coverage – number of seqeunces with that indel

    #### #4) show the mutations as a df with abundance and read no

    #### #5) provide funcitonality to edit the list of mutaitons


    st.markdown("---")

     ## Add a subheader: Make dynamic plot of this


  #### #3) Select the date range

    ###########################################

    # # get the gene name
    # gene = gene_name[selected_option]

    # # Get the list of mutations for the selected set
    # mutations = df['Mutation'].tolist()
    # # Lambda function to format the mutation list, from S24L to S:24L
    # format_mutation = lambda x: f"{gene}:{x[0]}{x[1:]}"
    # #format_mutation = lambda x: f"{x[0]}:{x[1:]}"
    # # Apply the lambda function to each element in the mutations list
    # formatted_mutations = [format_mutation(mutation) for mutation in mutations]


    # # Allow the user to choose a date range
    # st.write("Select a date range:")
    # date_range = st.date_input("Select a date range:", [pd.to_datetime("2025-02-10"), pd.to_datetime("2025-03-08")])

    # start_date = date_range[0].strftime('%Y-%m-%d')
    # end_date = date_range[1].strftime('%Y-%m-%d')

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