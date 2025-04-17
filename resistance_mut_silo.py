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
    
def fetch_reformat_data(formatted_mutations, date_range):
    all_data = asyncio.run(fetch_all_data(formatted_mutations, date_range))

    # get dates from date_range
    dates = pd.date_range(date_range[0], date_range[1]).strftime('%Y-%m-%d')

    # get all unique dates
    # dates = set()
    # for data in all_data:
    #     if data['data']:
    #         for d in data['data']:
    #             dates.add(d['date'])


    # make a dataframe with the dates as columns and the mutations as rows
    df = pd.DataFrame(index=formatted_mutations, columns=list(dates))

    # fill the dataframe with the data
    for data in all_data:
        if data['data']:
            for d in data['data']:
                df.at[data['mutation'], d['sampling_date']] = d['count']

    return df


def plot_heatmap(df):
    # Replace None with np.nan and remove commas from numbers
    df = df.replace({None: np.nan, ',': ''}, regex=True).astype(float)

    # Create a colormap with a custom color for NaN values
    cmap = sns.color_palette("Blues", as_cmap=True)
    cmap.set_bad(color='#FFCCCC')  # Set NaN values to a fainter red color

    # Adjust the plot size based on the number of rows in the dataframe
    height = max(8, len(df) * 0.3)  # Minimum height of 8, with 0.5 units per row
    fig, ax = plt.subplots(figsize=(15, height))

    annot = True if df.shape[0] * df.shape[1] <= 100 else False  # Annotate only if the plot is small enough
    sns.heatmap(df, cmap=cmap, ax=ax, cbar_kws={'label': 'Occurrence Frequency', 'orientation': 'horizontal'}, 
                linewidths=.5, linecolor='lightgrey', annot=annot, fmt=".1f", 
                annot_kws={"size": 10}, mask=df.isnull(), cbar=True, cbar_ax=fig.add_axes([0.15, 0.90, 0.7, 0.02]))

    # Set axis labels
    ax.set_xticks([0, len(df.columns) // 2, len(df.columns) - 1])
    ax.set_xticklabels([df.columns[0], df.columns[len(df.columns) // 2], df.columns[-1]], rotation=45)
    return fig



def app():
    st.title("Resistance Mutations from Wastewater Data")

    st.write("This page allows you to visualize the numer of observed resistance mutations over time.")
    st.write("The data is fetched from the WISE-CovSpectrum API and currently cointains demo data for Feb-Mar 2025.")

    st.write("The sets of resistance mutations are provide from Stanfords Coronavirus Antivirial & Reistance Database. Last updated 05/14/2024")

    st.write("This is a demo frontend to later make the first queries to SILO for wastewater data.")

    # make a horizontal line
    st.markdown("---")

    st.write("Select from the following resistance mutation sets:")

    # TODO: currently hardcoded, should be fetched from the server
    options = {
        "3CLpro Inhibitors": 'data/3CLpro_inhibitors_datasheet.csv',
        "RdRP Inhibitors": 'data/RdRP_inhibitors_datasheet.csv',
        "Spike mAbs": 'data/spike_mAbs_datasheet.csv'
    }

    selected_option = st.selectbox("Select a resistance mutation set:", options.keys())

    df = pd.read_csv(options[selected_option])

    gene_name =  {
        "3CLpro Inhibitors": "ORF1a",
        "RdRP Inhibitors": "ORF1b",
        "Spike mAbs": "S"
    }

    # get the gene name
    gene = gene_name[selected_option]

    # Get the list of mutations for the selected set
    mutations = df['Mutation'].tolist()
    # Lambda function to format the mutation list, from S24L to S:24L
    format_mutation = lambda x: f"{gene}:{x[0]}{x[1:]}"
    #format_mutation = lambda x: f"{x[0]}:{x[1:]}"
    # Apply the lambda function to each element in the mutations list
    formatted_mutations = [format_mutation(mutation) for mutation in mutations]

    if st.button("Show Mutations"):
        st.write(f"Selected mutations:")
        st.write(formatted_mutations)
    

    # Allow the user to choose a date range
    st.write("Select a date range:")
    date_range = st.date_input("Select a date range:", [pd.to_datetime("2025-02-10"), pd.to_datetime("2025-03-08")])

    if st.button("Fetch Data"):
        st.write("Fetching data...")
        df = fetch_reformat_data(formatted_mutations, date_range)
        
        # Check if the dataframe is all NaN
        if df.isnull().all().all():
            st.error("The fetched data contains only NaN values. Please try a different date range or mutation set.")
        else:
            # Plot the heatmap
            fig = plot_heatmap(df)
            st.pyplot(fig)

    start_date = date_range[0].strftime('%Y-%m-%d')
    end_date = date_range[1].strftime('%Y-%m-%d')

    location = "Zürich (ZH)"
    sequence_type_value = "amino acid"

    formatted_mutations_str = str(formatted_mutations).replace("'", '"')

    # strip of the part before the ":"
    formatted_mutations_no_gene_str = str(list([mut.split(':')[1] for mut in formatted_mutations])).replace("'",'"')

    st.write(formatted_mutations_no_gene_str)
    st.write(start_date)
    st.write(end_date)
    
    ll = ["ORF1a:T103L", "ORF1a:N126K", "ORF1a:P252L", "ORF1a:R3561V", "S:E990A", "ORF1a:G143S"]
    ll_str = str(ll).replace("'", '"')
    st.write(ll_str)

    # fetch the counts for SE990A
    async def fetch_single_mutation(mutation, date_range):
        async with aiohttp.ClientSession() as session:
            return await fetch_data(session, mutation, date_range)

    data_mut = asyncio.run(fetch_single_mutation("ORF1a:G143S", date_range)) # Assuming S gene based on context, adjust if needed

    st.write("Data for ORF1a:G143S:")
    st.write(data_mut)

    # Use the dynamically generated list of mutations string
    # The formatted_mutations_str variable already contains the string representation
    # of the list with double quotes, e.g., '["ORF1a:T103L", "ORF1a:N126K"]'
    # The lapisFilter uses double curly braces {{ and }} to escape the literal
    # curly braces needed for the JSON object within the f-string.
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
                displayMutations='{formatted_mutations_str}'
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
        height=1000,
    )

    #  displayMutations='{formatted_mutations_str}'
if __name__ == "__main__":
    app()