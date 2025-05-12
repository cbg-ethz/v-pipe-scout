from matplotlib import pyplot as plt
import numpy as np
import streamlit as st
import pandas as pd
import asyncio
import yaml
import streamlit.components.v1 as components
import plotly.graph_objects as go # Added

from api.wiseloculus import WiseLoculusLapis

# Load configuration from config.yaml
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)


server_ip = config.get('server', {}).get('lapis_address', 'http://default_ip:8000')
wiseLoculus = WiseLoculusLapis(server_ip)


def fetch_reformat_data(formatted_mutations, date_range):
    mutation_type = "aminoAcid"  # as we care about amino acid mutations, as in resistance mutations
    all_data = asyncio.run(wiseLoculus.fetch_all_data(formatted_mutations,mutation_type, date_range))

    # get dates from date_range
    dates = pd.date_range(date_range[0], date_range[1]).strftime('%Y-%m-%d')

    # make a dataframe with the dates as columns and the mutations as rows
    df = pd.DataFrame(index=formatted_mutations, columns=list(dates))

    # fill the dataframe with the data
    for data in all_data:
        if data['data']:
            for d in data['data']:
                df.at[data['mutation'], d['sampling_date']] = d['count']

    return df


def plot_resistance_mutations(df):
    """Plot resistance mutations over time as a heatmap using Plotly."""

    # Replace None with np.nan and remove commas from numbers, then convert to float
    df_processed = df.replace({None: np.nan, ',': ''}, regex=True).astype(float)

    # Create hover text
    hover_text = []
    for mutation in df_processed.index:
        row_hover_text = []
        for date in df_processed.columns:
            count = df_processed.loc[mutation, date]
            if pd.isna(count):
                text = f"Mutation: {mutation}<br>Date: {date}<br>Status: No data"
            else:
                text = f"Mutation: {mutation}<br>Date: {date}<br>Count: {count:.1f}"
            row_hover_text.append(text)
        hover_text.append(row_hover_text)

    # Determine dynamic height
    height = max(400, len(df_processed.index) * 20 + 100) # Base height + per mutation + padding for title/axes

    # Determine dynamic left margin based on mutation label length
    max_len_mutation_label = 0
    if not df_processed.index.empty: # Check if index is not empty
        max_len_mutation_label = max(len(str(m)) for m in df_processed.index)
    
    margin_l = max(80, max_len_mutation_label * 7 + 30) # Min margin or calculated, adjust multiplier as needed


    fig = go.Figure(data=go.Heatmap(
        z=df_processed.values,
        x=df_processed.columns,
        y=df_processed.index,
        colorscale='Blues',
        showscale=True,
        colorbar=dict(title='Count', orientation='h', y=1.05, x=0.5, xanchor='center', yanchor='bottom'),
        hoverongaps=False, # Do not show hover for gaps (NaNs)
        text=hover_text,
        hoverinfo='text'
    ))

    # Customize layout
    num_cols = len(df_processed.columns)
    tick_indices = []
    tick_labels = []
    if num_cols > 0:
        tick_indices = [df_processed.columns[0]]
        if num_cols > 1:
            tick_indices.append(df_processed.columns[num_cols // 2])
        if num_cols > 2 and num_cols //2 != num_cols -1 : # Avoid duplicate if middle is last
             tick_indices.append(df_processed.columns[-1])
        tick_labels = [str(label) for label in tick_indices]


    fig.update_layout(
        title='Resistance Mutations Over Time',
        xaxis=dict(
            title='Date',
            side='bottom',
            tickmode='array',
            tickvals=tick_indices,
            ticktext=tick_labels,
            tickangle=45,
        ),
        yaxis=dict(
            title='Mutation',
            autorange='reversed' # Show mutations from top to bottom as in original df
        ),
        height=height,
        plot_bgcolor='lightpink',  # NaN values will appear as this background color
        margin=dict(l=margin_l, r=20, t=80, b=100),  # Adjust margins
    )
    
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

    st.write("Note that mutation sets `3CLpro` and `RdRP`refer to mature proteins, " \
    "thus the mutations are in the ORF1a and ORF1b genes, respectively and translated here.")

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
            fig = plot_resistance_mutations(df)
            st.plotly_chart(fig, use_container_width=True)
    

    ### Debugging ###
    st.write("### Debugging")
    st.write("This section shows the raw data for the mutations.")
    ## make textboxed top select two mutations
    mutation1 = st.text_input("Mutation 1", "ORF1b:D475Y")
    mutation2 = st.text_input("Mutation 2", "ORF1b:E793A")
    st.write("Fetching data for mutations:")
    st.write(mutation1)
    st.write(mutation2)
    mutation_type = "aminoAcid"  # as we care about amino acid mutations, as in resistance mutations
    data_mut1 = asyncio.run(wiseLoculus.fetch_single_mutation(mutation1, mutation_type, date_range))
    data_mut2 = asyncio.run(wiseLoculus.fetch_single_mutation(mutation2, mutation_type, date_range))
    st.write("Data for mutation 1:")
    st.write(data_mut1)
    st.write("Data for mutation 2:")
    st.write(data_mut2)


    st.write('making calls to `sample/aggregated` endpoint for each mutation filtering for `aminoAcidMutations`: ["ORF1b:D475Y"]')
if __name__ == "__main__":
    app()