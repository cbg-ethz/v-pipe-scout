import numpy as np
import streamlit as st
import pandas as pd
import asyncio
import yaml
import pathlib
from datetime import datetime
from typing import List

from interface import MutationType
from api.wiseloculus import WiseLoculusLapis
from api.signatures import get_variant_list, get_variant_names, VariantList
from visualize.mutations import mutations_over_time

pd.set_option('future.no_silent_downcasting', True)


# Load configuration from config.yaml
CONFIG_PATH = pathlib.Path(__file__).parent.parent / "config.yaml"
with open(CONFIG_PATH, 'r') as file:
    config = yaml.safe_load(file)


server_ip = config.get('server', {}).get('lapis_address', 'http://default_ip:8000')
wiseLoculus = WiseLoculusLapis(server_ip)


@st.cache_data(ttl=3600)  # Cache for 1 hour
def cached_get_variant_list() -> VariantList:
    """Cached version of get_variant_list to avoid repeated API calls."""
    return get_variant_list()

@st.cache_data(ttl=3600)  # Cache for 1 hour
def cached_get_variant_names() -> List[str]:
    """Cached version of get_variant_names to avoid repeated API calls."""
    return get_variant_names()

def app():

    
    st.title("Background Mutations")
    st.subheader("Explore Mutations currently not in any Variant Signature we track")
    st.write("This page allows you to visualize background mutations in wastewater samples that are not part of any known variant signature.")
    st.write("Are we misisng something? Please let us know on [GitHub](https://github.com/cbg-ethz/cowwid/issues)")
    st.markdown("---")
    # Allow the user to choose a date range
    st.write("Choose your data to inspect:")
    date_range = st.date_input("Select a date range:", [pd.to_datetime("2025-02-10"), pd.to_datetime("2025-03-08")])

    # Ensure date_range is a tuple with two elements
    if len(date_range) != 2:
        st.error("Please select a valid date range with a start and end date.")
        return

    start_date = datetime.strptime(str(date_range[0]), "%Y-%m-%d")
    end_date = datetime.strptime(str(date_range[1]),"%Y-%m-%d")
    

    ## Fetch locations from API
    default_locations = [
        "Zürich (ZH)",
    ]  # Define default locations
    # Fetch locations using the fetch_locations function
    locations = wiseLoculus.fetch_locations(default_locations)

    location = st.selectbox("Select Location:", locations)

    mutations_in_timeframe_df =  asyncio.run(wiseLoculus.sample_nucleotideMutations(
        date_range=(
            start_date,
            end_date
        ),
        location_name=location
    ))

    mutations_in_timeframe = mutations_in_timeframe_df['mutation'].to_list()  

    # Get the available variant names from the signatures API (cached)
    available_variants = cached_get_variant_names()
    
    # Create a collapsible section for variant selection
    with st.expander("🔧 Advanced: Select known variants to exclude", expanded=False):
        st.write("By default, all known variant signatures are excluded from background mutations. You can customize which variants to exclude here.")
        
        # Create a multi-select box for variants
        selected_curated_variants = st.multiselect(
            "Select known variants to exclude.",
            options=available_variants,
            default=cached_get_variant_names(),
            help="Select from the list of known variants. The signature mutations of these variants have been curated by the V-Pipe team"
        )
    
    # from selected_curated_variants get each variant's signature mutations
    all_curated_variants = cached_get_variant_list()
    
    # Filter to only the selected variants and extract their signature mutations
    selected_signature_mutations = [
        mutation 
        for variant in all_curated_variants.variants
        if variant.name in selected_curated_variants
        for mutation in variant.signature_mutations
    ]

    # remove duplicates from selected_signature_mutations
    selected_signature_mutations = list(set(selected_signature_mutations))

    # Calculate background mutations (all mutations minus the signature mutations)
    background_mutations = [
        mutation for mutation in mutations_in_timeframe
        if mutation not in selected_signature_mutations
    ]

    # TODO: add a venn diragram here to visualize the overlap, once the better venn diagram library is available
    st.write(f"Total mutations in timeframe: {len(mutations_in_timeframe)}")
    st.write(f"Signature mutations to exclude: {len(selected_signature_mutations)}")
    st.write(f"Background mutations to analyze: {len(background_mutations)}")

    # Show a spinner while fetching data - only for background mutations
    with st.spinner("Fetching mutation data for background mutations..."):
        counts_df, freq_df, coverage_freq_df =  wiseLoculus.mutations_over_time_dfs(
            background_mutations,  # Only fetch data for background mutations
            MutationType.NUCLEOTIDE,
            date_range=(start_date, end_date),
            location_name=location
        )

    # Add frequency filtering controls
    st.markdown("---")
    st.write("### Frequency Filtering")
    st.write("Filter mutations based on their frequency ranges to focus on mutations of interest.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        min_frequency = st.slider(
            "Minimum frequency threshold",
            min_value=0.0,
            max_value=1.0,
            value=0.01,  # Default value (1%)
            step=0.001,
            format="%.3f",
            help="Only show mutations that reach at least this frequency at some point in the timeframe."
        )
    
    with col2:
        max_frequency = st.slider(
            "Maximum frequency threshold", 
            min_value=0.0,
            max_value=1.0,
            value=1.0,  # Default value (100%)
            step=0.001,
            format="%.3f",
            help="Only show mutations that stay below this frequency throughout the timeframe."
        )
    
    # Validate that min <= max
    if min_frequency > max_frequency:
        st.error("Minimum frequency cannot be greater than maximum frequency.")
        return

    # Filter mutations based on frequency criteria
    # Convert freq_df to numeric, replacing non-numeric values with NaN
    freq_df_numeric = freq_df.replace({None: np.nan, ',': ''}, regex=True)
    freq_df_numeric = freq_df_numeric.apply(pd.to_numeric, errors='coerce')
    
    # Find mutations that meet the frequency criteria
    # Mutation must have at least one value >= min_frequency AND all non-NaN values <= max_frequency
    mutations_above_min = freq_df_numeric.max(axis=1) >= min_frequency
    mutations_below_max = freq_df_numeric.max(axis=1) <= max_frequency
    
    # Combine both conditions
    mutations_to_keep = mutations_above_min & mutations_below_max
    filtered_mutations = freq_df_numeric.index[mutations_to_keep].tolist()
    
    # Apply filtering to all DataFrames
    if len(filtered_mutations) > 0:
        freq_df_filtered = freq_df.loc[filtered_mutations]
        counts_df_filtered = counts_df.loc[filtered_mutations] 
        
        # Filter coverage_freq_df (MultiIndex DataFrame)
        if not coverage_freq_df.empty:
            existing_mutations_in_coverage = [
                mut for mut in filtered_mutations 
                if mut in coverage_freq_df.index.get_level_values('mutation')
            ]
            if existing_mutations_in_coverage:
                coverage_freq_df_filtered = coverage_freq_df.loc[existing_mutations_in_coverage]
            else:
                coverage_freq_df_filtered = coverage_freq_df.iloc[0:0]  # Empty with same structure
        else:
            coverage_freq_df_filtered = coverage_freq_df
            
        st.write(f"**Mutations after frequency filtering: {len(filtered_mutations)}** (was {len(background_mutations)})")
        st.write(f"Frequency range: {min_frequency:.3f} - {max_frequency:.3f}")
        
    else:
        st.warning(f"No mutations found within the frequency range {min_frequency:.3f} - {max_frequency:.3f}. Please adjust the frequency thresholds.")
        return



    # Display the visualization
    st.markdown("---")
    st.write("### Background Mutations Over Time")
    st.write("Shows the background mutations (not in variant signatures) over time in wastewater for the selected date range.")
    
    # Add radio button for showing/hiding dates with no data
    show_empty_dates = st.radio(
        "Date display options:",
        options=["Show all dates", "Skip dates with no coverage"],
        index=0  # Default to showing all dates
    )
    
    # Use the filtered DataFrames for plotting
    # Only skip NA dates if the option is selected
    if show_empty_dates == "Skip dates with no coverage":
        plot_counts_df = counts_df_filtered.dropna(axis=1, how='all')
        plot_freq_df = freq_df_filtered.dropna(axis=1, how='all')
    else:
        plot_counts_df = counts_df_filtered
        plot_freq_df = freq_df_filtered
    
    if not freq_df_filtered.empty and len(filtered_mutations) > 0:
        if freq_df_filtered.isnull().all().all():
            st.error("The fetched data contains only NaN values. Please try a different date range or adjust frequency filters.")
        else:
            fig = mutations_over_time(
                plot_freq_df, 
                plot_counts_df, 
                coverage_freq_df_filtered,
                title="Proportion of Background Mutations Over Time"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Add download section after the plot
            st.markdown("---")
            st.write("### 📥 Download Filtered Data")
            st.write("Download the filtered background mutation data for further analysis.")
            
            # Create a comprehensive dataset combining all information
            download_data = []
            
            for mutation in filtered_mutations:
                for date in freq_df_filtered.columns:
                    # Get frequency data
                    frequency = freq_df_filtered.loc[mutation, date] if not pd.isna(freq_df_filtered.loc[mutation, date]) else None
                    
                    # Get count data
                    count = counts_df_filtered.loc[mutation, date] if not pd.isna(counts_df_filtered.loc[mutation, date]) else None
                    
                    # Get coverage data from coverage_freq_df if available
                    coverage = None
                    if not coverage_freq_df_filtered.empty and mutation in coverage_freq_df_filtered.index.get_level_values('mutation'):
                        try:
                            mutation_data = coverage_freq_df_filtered.loc[mutation]
                            if date in mutation_data.index:
                                coverage_val = mutation_data.loc[date, 'coverage']
                                coverage = coverage_val if coverage_val != 'NA' else None
                        except (KeyError, IndexError):
                            pass
                    
                    # Add row to download data
                    download_data.append({
                        'mutation': mutation,
                        'date': date,
                        'frequency': frequency,
                        'count': count,
                        'coverage': coverage,
                        'location': location,
                        'min_frequency_threshold': min_frequency,
                        'max_frequency_threshold': max_frequency
                    })
            
            # Create DataFrame for download
            download_df = pd.DataFrame(download_data)
            
            # Display download options
            col1, col2 = st.columns(2)
            
            with col1:
                # CSV Download
                csv_data = download_df.to_csv(index=False)
                st.download_button(
                    label="📊 Download as CSV",
                    data=csv_data,
                    file_name=f'background_mutations_{location.replace(" ", "_")}_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.csv',
                    mime='text/csv',
                    help="Download the filtered background mutation data as a CSV file"
                )
            
            with col2:
                # JSON Download
                json_data = download_df.to_json(orient='records', date_format='iso', indent=2)
                st.download_button(
                    label="📋 Download as JSON",
                    data=json_data,
                    file_name=f'background_mutations_{location.replace(" ", "_")}_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.json',
                    mime='application/json',
                    help="Download the filtered background mutation data as a JSON file"
                )
            
            # Show preview of the data
            with st.expander("📖 Preview download data", expanded=False):
                st.write(f"**Data Preview** ({len(download_df)} rows)")
                st.dataframe(download_df.head(10), use_container_width=True)
                
                # Show summary statistics
                st.write("**Summary Statistics:**")
                summary_col1, summary_col2, summary_col3 = st.columns(3)
                
                with summary_col1:
                    st.metric("Total Records", len(download_df))
                
                with summary_col2:
                    st.metric("Unique Mutations", download_df['mutation'].nunique())
                
                with summary_col3:
                    st.metric("Date Range", f"{len(download_df['date'].unique())} days")
            
    elif len(filtered_mutations) == 0:
        st.info("No background mutations found matching the frequency criteria. Try adjusting the frequency thresholds.")
    else:
        st.error("No data available for the selected parameters. Please try a different date range or location.")

if __name__ == "__main__":
    app()