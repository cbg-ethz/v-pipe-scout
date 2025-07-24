import numpy as np
import streamlit as st
import pandas as pd
import asyncio
import yaml
import streamlit.components.v1 as components
import plotly.graph_objects as go 
import pathlib

from interface import MutationType
from api.wiseloculus import WiseLoculusLapis

pd.set_option('future.no_silent_downcasting', True)


# Load configuration from config.yaml
CONFIG_PATH = pathlib.Path(__file__).parent.parent / "config.yaml"
with open(CONFIG_PATH, 'r') as file:
    config = yaml.safe_load(file)


server_ip = config.get('server', {}).get('lapis_address', 'http://default_ip:8000')
wiseLoculus = WiseLoculusLapis(server_ip)


def plot_resistance_mutations(freq_df, counts_df=None, coverage_freq_df=None):
    """Plot resistance mutations over time as a heatmap using Plotly.
    
    Args:
        freq_df: DataFrame with mutations as rows, dates as columns, and frequency values
        counts_df: DataFrame with mutations as rows, dates as columns, and count values (for hover info)
        coverage_freq_df: Optional MultiIndex DataFrame with detailed coverage and frequency data
    """

    # Replace None with np.nan and remove commas from numbers
    df_processed = freq_df.replace({None: np.nan, ',': ''}, regex=True).infer_objects(copy=False).astype(float)

    # Create enhanced hover text
    hover_text = []
    for mutation in df_processed.index:
        row_hover_text = []
        for date in df_processed.columns:
            frequency = df_processed.loc[mutation, date]
            
            # Try to get additional data from other sources
            count = None
            coverage = None
            
            # First try to get count from counts_df if provided
            if counts_df is not None and not counts_df.empty:
                count = counts_df.loc[mutation, date] if not pd.isna(counts_df.loc[mutation, date]) else None
            
            # Then try to get additional data from coverage_freq_df
            if coverage_freq_df is not None and not coverage_freq_df.empty:
                try:
                    if mutation in coverage_freq_df.index.get_level_values('mutation'):
                        mutation_data = coverage_freq_df.loc[mutation]
                        if date in mutation_data.index:
                            coverage_val = mutation_data.loc[date, 'coverage']
                            
                            # If count is still None, try to get it from coverage_freq_df
                            if count is None:
                                count_val = mutation_data.loc[date, 'count']
                                count = count_val if count_val != 'NA' else None
                            
                            # Handle 'NA' values for coverage
                            coverage = coverage_val if coverage_val != 'NA' else None
                except (KeyError, IndexError):
                    pass  # Data not available for this mutation/date combination
            
            # Build hover text
            if pd.isna(frequency):
                text = f"Mutation: {mutation}<br>Date: {date}<br>Status: No data"
            else:
                text = f"Mutation: {mutation}<br>Date: {date}<br>Proportion: {frequency * 100:.1f}%"
                if count is not None:
                    text += f"<br>Count: {float(count):.0f}"
                if coverage is not None:
                    text += f"<br>Coverage: {float(coverage):.0f}"
            
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
        z=df_processed.values,  # Now using frequency values
        x=df_processed.columns,
        y=df_processed.index,
        colorscale='Blues',
        showscale=False,  # Hide color bar as requested
        hoverongaps=True, # Show hover for gaps (NaNs)
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
        title="Proportion of Resistance Mutations Over Time",
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
    st.markdown("---")
    st.write("Select from the following resistance mutation sets:")
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

    st.markdown("---")
    # Allow the user to choose a date range
    st.write("Choose your data to inspect:")
    date_range = st.date_input("Select a date range:", [pd.to_datetime("2025-02-10"), pd.to_datetime("2025-03-08")])

    # Ensure date_range is a tuple with two elements
    if len(date_range) != 2:
        st.error("Please select a valid date range with a start and end date.")
        return

    start_date = date_range[0].strftime('%Y-%m-%d')
    end_date = date_range[1].strftime('%Y-%m-%d')
    

    ## Fetch locations from API
    default_locations = [
        "Zürich (ZH)",
    ]  # Define default locations
    # Fetch locations using the fetch_locations function
    locations = wiseLoculus.fetch_locations(default_locations)

    location = st.selectbox("Select Location:", locations)
    
    sequence_type_value = "amino acid"

    formatted_mutations_str = str(formatted_mutations).replace("'", '"')

    st.markdown("---")
    st.write("### Resistance Mutations Over Time")
    st.write("Shows the mutations over time in wastewater for the selected date range.")

    # Add radio button for showing/hiding dates with no data
    show_empty_dates = st.radio(
        "Date display options:",
        options=["Show all dates", "Skip dates with no coverage"],
        index=0  # Default to showing all dates (off)
    )

    with st.spinner("Fetching resistance mutation data..."):
        counts_df, freq_df, coverage_freq_df = wiseLoculus.mutations_over_time_dfs(formatted_mutations, MutationType.AMINO_ACID, date_range, location)


    # Only skip NA dates if the option is selected
    if show_empty_dates == "Skip dates with no coverage":
        plot_counts_df = counts_df.dropna(axis=1, how='all')
        plot_freq_df = freq_df.dropna(axis=1, how='all')
    else:
        plot_counts_df = counts_df
        plot_freq_df = freq_df

    if not freq_df.empty:
        if freq_df.isnull().all().all():
            st.error("The fetched data contains only NaN values. Please try a different date range or mutation set.")
        else:
            fig = plot_resistance_mutations(plot_freq_df, plot_counts_df, coverage_freq_df)
            st.plotly_chart(fig, use_container_width=True)

    st.write("### GenSpectrum Dashboard Dynamic Mutations Over Time")
    st.write("In the long term, GenSpectrum will provide a dashboard to visualize the mutations over time.")
    st.write("Yet currently, the below component only shows mutations above an unknown threshold.")
    st.write("This is under investigation and will be addresed by the GenSpectrum team.")

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

if __name__ == "__main__":
    app()