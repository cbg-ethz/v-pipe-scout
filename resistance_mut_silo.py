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
        "3CLpro Inhibitors": 'data/translated_3CLpro_in_ORF1a_mutations.csv',
        "RdRP Inhibitors": 'data/translated_RdRp_in_ORF1a_ORF1b_mutations.csv',
        "Spike mAbs": 'data/translated_Spike_in_S_mutations.csv'
    }

    selected_option = st.selectbox("Select a resistance mutation set:", options.keys())

    df = pd.read_csv(options[selected_option])

    
    # Get the list of mutations for the selected set
    mutations = df['Mutation'].tolist()
    # Apply the lambda function to each element in the mutations list
    formatted_mutations = mutations
    

    # Allow the user to choose a date range
    st.write("Select a date range:")
    date_range = st.date_input("Select a date range:", [pd.to_datetime("2025-02-10"), pd.to_datetime("2025-03-08")])


    start_date = date_range[0].strftime('%Y-%m-%d')
    end_date = date_range[1].strftime('%Y-%m-%d')

    location = "Zürich (ZH)"
    sequence_type_value = "amino acid"

    formatted_mutations_str = str(formatted_mutations).replace("'", '"')

    ### GenSpectrum Dashboard Component ###

    st.write("### GenSpectrum Dashboard Dynamic Mutation Heatmap")
    st.write("This component only shows mutations above an unknown threshold.")
    st.write("This is under investigation.")

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
            <body>
            
            </body>
        </html>
    """,
        height=500,
    )

    ### Python plot ###
    st.write("### Python Plot")
    st.write("This plot shows the mutations over time.")

    if st.button("Making Python Plot - manual API calls"):
        st.write("Fetching data...")
        df = fetch_reformat_data(formatted_mutations, date_range)
        
        # Check if the dataframe is all NaN
        if df.isnull().all().all():
            st.error("The fetched data contains only NaN values. Please try a different date range or mutation set.")
        else:
            # Plot the heatmap
            fig = plot_heatmap(df)
            st.pyplot(fig)
    

    # fetch the counts for SE990A
    async def fetch_single_mutation(mutation, date_range):
        async with aiohttp.ClientSession() as session:
            return await fetch_data(session, mutation, date_range)

    ### Debugging ###
    st.write("### Debugging")
    st.write("This section shows the raw data for the mutations.")
    ## make textboxed top select two mutations
    mutation1 = st.text_input("Mutation 1", "ORF1b:D475Y")
    mutation2 = st.text_input("Mutation 2", "ORF1b:E793A")
    st.write("Fetching data for mutations:")
    st.write(mutation1)
    st.write(mutation2)
    data_mut1 = asyncio.run(fetch_single_mutation(mutation1, date_range))
    data_mut2 = asyncio.run(fetch_single_mutation(mutation2, date_range))
    st.write("Data for mutation 1:")
    st.write(data_mut1)
    st.write("Data for mutation 2:")
    st.write(data_mut2)


    st.write('making calls to `sample/aggregated` endpoint for each mutation filtering for `aminoAcidMutations`: ["ORF1b:D475Y"]')
if __name__ == "__main__":
    app()