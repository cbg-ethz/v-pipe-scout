"""
Reusable component for mutation plotting with frequency filtering.
This module provides functions to create configurable mutation plots
that can be embedded in different pages with custom configurations.
"""

import streamlit as st
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any

from interface import MutationType
from visualize.mutations import mutations_over_time
from api.exceptions import APIError

# Sequencing error rate threshold (0.32%)
SEQUENCING_ERROR_RATE = 0.0032


def render_mutation_plot_component(
    wiseLoculus: Any,
    mutations: List[str],
    sequence_type: MutationType,
    date_range: Tuple[datetime, datetime],
    location: str,
    config: Optional[Dict] = None,
    session_prefix: str = "",
    container = None,
    url_state_manager = None
) -> Optional[Dict]:
    """
    Render a configurable mutation plot with frequency filtering.
    
    Args:
        wiseLoculus: WiseLoculusLapis instance for API calls
        mutations: List of mutations to plot 
        sequence_type: MutationType.AMINO_ACID or MutationType.NUCLEOTIDE"
        date_range: Tuple of (start_date, end_date)
        location: Location name for filtering
        config: Configuration dictionary with plotting options
        session_prefix: Optional prefix for session state keys to avoid conflicts
        container: Streamlit container to render in (optional)
        url_state_manager: Optional URLStateManager instance for URL state persistence
    
    Returns:
        Dict containing:
        - filtered_mutations: List of mutations after frequency filtering
        - plot_data: Dictionary with counts_df, freq_df, coverage_freq_df
        - download_data: DataFrame ready for download
        - summary_stats: Dictionary with summary statistics
    """
    # Default configuration
    default_config = {
        'show_frequency_filtering': True,
        'show_date_options': True,
        'show_download': True,
        'show_summary_stats': True,
        'default_min_frequency': 0.01,
        'default_max_frequency': 1.0,
        'plot_title': "Mutations Over Time",
        'enable_empty_date_toggle': True,
        'show_mutation_count': True
    }
    
    # Merge provided config with defaults
    if config is None:
        config = default_config
    else:
        for key, value in default_config.items():
            if key not in config:
                config[key] = value
    
    # Use provided container or main streamlit
    target = container if container is not None else st
    
    start_date, end_date = date_range
    
    # Show mutation count if enabled
    if config['show_mutation_count']:
        target.write(f"**Total mutations to analyze: {len(mutations)}**")
    
    # Handle case where no mutations are provided
    if not mutations:
        target.warning("⚠️ No mutations available for analysis. Please ensure mutations are selected or available.")
        return None
    
    # Fetch mutation data
    with target.spinner("Fetching mutation data..."):
        try:
            # Convert sequence_type string to MutationType enum
            mutation_type = sequence_type

            if mutation_type not in [MutationType.NUCLEOTIDE, MutationType.AMINO_ACID]:
                target.error("⚠️ Invalid sequence type. Must be 'nucleotide' or 'amino acid'.")
                return None
            
            # Get data using the mutations_over_time function
            mutations_over_time_df = asyncio.run(wiseLoculus.mutations_over_time(
                mutations=mutations,
                mutation_type=mutation_type,
                date_range=(start_date, end_date),
                locationName=location
            ))

            # Check if fallback was used and notify user
            if hasattr(mutations_over_time_df, 'attrs') and mutations_over_time_df.attrs.get('fallback_used', False):
                if mutations_over_time_df.attrs.get('fallback_failed', False):
                    target.error("🚨 **Both primary and fallback methods failed**")
                    target.error("Unable to retrieve mutation data at this time.")
                    if mutations_over_time_df.attrs.get('fallback_reason'):
                        with target.expander("🔍 Error Details", expanded=False):
                            target.code(mutations_over_time_df.attrs['fallback_reason'])
                    return None
                else:
                    target.warning("⚠️ **Primary API endpoint failed - switched to slower fallback method**")
                    target.info("✅ Data retrieved successfully using legacy endpoint. This may be slower but should provide complete results.")
                    if mutations_over_time_df.attrs.get('fallback_reason'):
                        with target.expander("🔍 Fallback Reason", expanded=False):
                            target.text(mutations_over_time_df.attrs['fallback_reason'])

            # Transform the data to match mutations_over_time_dfs signature:
            # 1. counts_df and freq_df: mutations as rows, dates as columns
            # 2. coverage_freq_df: keep the MultiIndex structure for compatibility
            
            # Reset index to access mutation and samplingDate as columns
            df_reset = mutations_over_time_df.reset_index()
            
            # Check for duplicate entries and throw error if found
            duplicates = df_reset.duplicated(subset=['mutation', 'samplingDate'], keep=False)
            if duplicates.any():
                duplicate_rows = df_reset[duplicates]
                error_msg = f"Duplicate mutation-date combinations detected: {len(duplicate_rows)} entries"
                target.error(f"🚨 **Data Integrity Error**: {error_msg}")
                
                with target.expander("🔍 Duplicate entries details", expanded=True):
                    target.write("**Duplicate entries found:**")
                    target.dataframe(duplicate_rows[['mutation', 'samplingDate', 'count', 'frequency']])
                    target.write("**This indicates a problem with data processing that needs to be fixed.**")
                
                # Throw a detailed error for debugging
                duplicate_details = duplicate_rows[['mutation', 'samplingDate', 'count', 'frequency']].to_string()
                raise ValueError(f"Index contains duplicate entries, cannot reshape. "
                               f"Found {len(duplicate_rows)} duplicate mutation-date combinations:\n{duplicate_details}")
            
            # No duplicates, use regular pivot
            counts_df = df_reset.pivot(index='mutation', columns='samplingDate', values='count')
            freq_df = df_reset.pivot(index='mutation', columns='samplingDate', values='frequency')
            
            # Keep the original MultiIndex structure for coverage_freq_df for compatibility with visualization
            coverage_freq_df = mutations_over_time_df

        except APIError as api_err:
            # Handle API-specific errors with clear messaging
            if api_err.status_code == 500:
                target.error("🚨 **Internal Server Error (500)**")
                target.error("The backend API server is experiencing technical difficulties. This is **not** an issue with this web application.")
                
                with target.expander("🔍 Debug Information", expanded=False):
                    target.write("**Error Details:**")
                    target.code(str(api_err.details) if api_err.details else "No additional details available")
                    if api_err.payload:
                        target.write("**Request Payload:**")
                        target.json(api_err.payload)
                
                target.info("💡 **What you can try:**")
                target.write("• Try again – we are aware that the backend may have transient failures.")
                target.write("• Reduce the number of mutations or date range")
            else:
                target.error(f"🚨 **API Error ({api_err.status_code})**")
                target.error("The API request failed. This may be a temporary issue.")
                target.write(f"**Error:** {str(api_err)}")
                if api_err.details:
                    with target.expander("🔍 Debug Information", expanded=False):
                        target.code(str(api_err.details))
            return None
        except Exception as e:
            target.error(f"⚠️ Error fetching mutation analysis data: {str(e)}")
            target.info("This could be due to API connectivity issues. Please try again later.")
            return None
    
    # Handle empty data
    if freq_df.empty:
        target.warning("⚠️ No mutation data found for the selected parameters.")
        target.info("This could be due to:")
        target.write("• No mutations present in the specified time period")
        target.write("• The selected location having no data for this date range")
        target.write("• API connectivity issues")
        return None
    
    # Frequency filtering controls
    filter_error_rate = False  # Default value
    if config['show_frequency_filtering']:
        target.markdown("---")
        target.write("### Frequency Filtering")
        target.write("Filter mutations to plot based on their frequency ranges to focus on mutations of interest.")
        
        # Load frequency thresholds from URL if URL state manager is provided
        if url_state_manager:
            url_min_freq = url_state_manager.load_from_url("min_frequency", config['default_min_frequency'], float)
            url_max_freq = url_state_manager.load_from_url("max_frequency", config['default_max_frequency'], float)
        else:
            url_min_freq = config['default_min_frequency']
            url_max_freq = config['default_max_frequency']
        
        col1, col2 = target.columns(2)
        
        with col1:
            min_frequency = target.slider(
                "Minimum frequency threshold",
                min_value=0.0,
                max_value=1.0,
                value=url_min_freq,
                step=0.001,
                format="%.3f",
                help="Only show mutations that reach at least this frequency at some point in the timeframe.",
                key=f"{session_prefix}min_frequency"
            )
        
        with col2:
            max_frequency = target.slider(
                "Maximum frequency threshold", 
                min_value=0.0,
                max_value=1.0,
                value=url_max_freq,
                step=0.001,
                format="%.3f",
                help="Only show mutations that stay below this frequency throughout the timeframe.",
                key=f"{session_prefix}max_frequency"
            )
        
        # Save frequency thresholds to URL if URL state manager is provided
        if url_state_manager:
            url_state_manager.save_to_url(min_frequency=min_frequency, max_frequency=max_frequency)
        
        # Validate that min <= max
        if min_frequency > max_frequency:
            target.error("Minimum frequency cannot be greater than maximum frequency.")
            return None
        
        # Error rate filtering checkbox
        target.markdown("")
        error_rate_percent = SEQUENCING_ERROR_RATE * 100
        filter_error_rate = target.checkbox(
            f"Filter out individual frequencies below sequencing error rate ({error_rate_percent:.2f}%)",
            value=False,
            help=f"When enabled, individual data points with frequency < {SEQUENCING_ERROR_RATE} will be shown as 'No data'. Mutations are still included if their maximum frequency meets the threshold above.",
            key=f"{session_prefix}filter_error_rate"
        )
    else:
        min_frequency = config['default_min_frequency']
        max_frequency = config['default_max_frequency']
    
    # Filter mutations based on frequency criteria
    freq_df_numeric = freq_df.replace({None: np.nan, ',': ''}, regex=True)
    freq_df_numeric = freq_df_numeric.apply(pd.to_numeric, errors='coerce')
    
    # Find mutations that meet the frequency criteria
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
            
        if config['show_summary_stats']:
            target.write(f"**Mutations after frequency filtering: {len(filtered_mutations)}** (was {len(mutations)})")
            target.write(f"Frequency range: {min_frequency:.3f} - {max_frequency:.3f}")
        
    else:
        target.warning(f"No mutations found within the frequency range {min_frequency:.3f} - {max_frequency:.3f}. Please adjust the frequency thresholds.")
        return None
    
    # Apply error rate filtering to individual data points if enabled
    if config['show_frequency_filtering'] and filter_error_rate:
        # Convert to numeric for comparison (optimize by only converting non-numeric columns)
        freq_df_for_filtering = freq_df_filtered.replace({None: np.nan, ',': ''}, regex=True)
        
        # Only convert object (string) columns to numeric for efficiency
        obj_cols = freq_df_for_filtering.select_dtypes(include='object').columns
        if len(obj_cols) > 0:
            freq_df_for_filtering[obj_cols] = freq_df_for_filtering[obj_cols].apply(pd.to_numeric, errors='coerce')
        
        # Create masks for values below error rate
        below_error_rate = freq_df_for_filtering < SEQUENCING_ERROR_RATE
        
        # Apply filtering by setting values below threshold to NaN
        freq_df_filtered = freq_df_filtered.copy()
        freq_df_filtered[below_error_rate] = np.nan
        
        # Also filter counts_df to match
        counts_df_filtered = counts_df_filtered.copy()
        counts_df_filtered[below_error_rate] = np.nan
    
    # Date display options
    if config['show_date_options'] and config['enable_empty_date_toggle']:
        target.markdown("---")
        show_empty_dates = target.radio(
            "Date display options:",
            options=["Show all dates", "Skip dates with no coverage"],
            index=0,  # Default to showing all dates
            key=f"{session_prefix}show_empty_dates"
        )
        
        # Use the filtered DataFrames for plotting
        if show_empty_dates == "Skip dates with no coverage":
            plot_counts_df = counts_df_filtered.dropna(axis=1, how='all')
            plot_freq_df = freq_df_filtered.dropna(axis=1, how='all')
        else:
            plot_counts_df = counts_df_filtered
            plot_freq_df = freq_df_filtered
    else:
        plot_counts_df = counts_df_filtered
        plot_freq_df = freq_df_filtered
    
    # Display the visualization
    target.markdown("---")
    
    if not freq_df_filtered.empty and len(filtered_mutations) > 0:
        if freq_df_filtered.isnull().all().all():
            target.error("The fetched data contains only NaN values. Please try a different date range or adjust frequency filters.")
            return None
        else:
            # Show data size information
            num_mutations = len(plot_freq_df.index)
            num_dates = len(plot_freq_df.columns)
            data_points = num_mutations * num_dates
            
            # Create placeholders for info message and progress indicators
            info_placeholder = target.empty()
            info_placeholder.info(f"📊 Generating heatmap for {num_mutations:,} mutations × {num_dates:,} dates ({data_points:,} data points)")
            
            progress_bar = target.progress(0)
            status_text = target.empty()
            
            try:
                status_text.text("🔄 Sorting mutations by genomic position...")
                progress_bar.progress(0.2)
                
                # Define progress callback to update UI
                def update_progress(current, total, message):
                    progress = 0.2 + (current * 0.6)  # Map 0-1 progress to 0.2-0.8 range
                    progress_bar.progress(progress)
                    status_text.text(f"🔄 {message}")
                
                fig = mutations_over_time(
                    plot_freq_df, 
                    plot_counts_df, 
                    coverage_freq_df_filtered,
                    title=config['plot_title'],
                    progress_callback=update_progress
                )
                
                status_text.text("🔄 Rendering plot...")
                progress_bar.progress(0.8)
                
                target.plotly_chart(fig, width="container")
                
                progress_bar.progress(1.0)
                status_text.text("✅ Plot ready!")
                
                # Clean up progress indicators and info message after a brief delay
                import time
                time.sleep(0.5)
                progress_bar.empty()
                status_text.empty()
                info_placeholder.empty()  # Clear the info message
                
            except Exception as e:
                # Clean up progress indicators and info message on error
                progress_bar.empty()
                status_text.empty()
                info_placeholder.empty()  # Clear the info message on error too
                target.error(f"Error creating plot: {str(e)}")
                return None
    else:
        target.error("No data available for plotting.")
        return None
    
    # Prepare return data
    plot_data = {
        'counts_df': counts_df_filtered,
        'freq_df': freq_df_filtered,
        'coverage_freq_df': coverage_freq_df_filtered
    }
    
    summary_stats = {
        'total_mutations': len(mutations),
        'filtered_mutations_count': len(filtered_mutations),
        'date_range_days': len(freq_df_filtered.columns),
        'min_frequency': min_frequency,
        'max_frequency': max_frequency
    }
    
    # Download functionality
    download_data = None
    if config['show_download']:
        download_data = _create_download_section(
            target, 
            filtered_mutations, 
            freq_df_filtered, 
            counts_df_filtered, 
            coverage_freq_df_filtered,
            location,
            start_date,
            end_date,
            min_frequency,
            max_frequency,
            session_prefix
        )
    
    return {
        'filtered_mutations': filtered_mutations,
        'plot_data': plot_data,
        'download_data': download_data,
        'summary_stats': summary_stats
    }


def _create_download_section(
    target,
    filtered_mutations: List[str],
    freq_df_filtered: pd.DataFrame,
    counts_df_filtered: pd.DataFrame,
    coverage_freq_df_filtered: pd.DataFrame,
    location: str,
    start_date: datetime,
    end_date: datetime,
    min_frequency: float,
    max_frequency: float,
    session_prefix: str
) -> pd.DataFrame:
    """Create download section and return download data."""
    target.markdown("---")
    target.write("### 📥 Download Filtered Data")
    target.write("Download the filtered mutation data for further analysis.")
    
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
    col1, col2 = target.columns(2)
    
    with col1:
        # CSV Download
        csv_data = download_df.to_csv(index=False)
        target.download_button(
            label="📊 Download as CSV",
            data=csv_data,
            file_name=f'mutation_data_{location.replace(" ", "_")}_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.csv',
            mime='text/csv',
            help="Download the filtered mutation data as a CSV file",
            key=f"{session_prefix}download_csv"
        )
    
    with col2:
        # JSON Download
        json_data = download_df.to_json(orient='records', date_format='iso', indent=2)
        target.download_button(
            label="📋 Download as JSON",
            data=json_data,
            file_name=f'mutation_data_{location.replace(" ", "_")}_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.json',
            mime='application/json',
            help="Download the filtered mutation data as a JSON file",
            key=f"{session_prefix}download_json"
        )
    
    # Show preview of the data
    with target.expander("📖 Preview download data", expanded=False):
        target.write(f"**Data Preview** ({len(download_df)} rows)")
        target.dataframe(download_df.head(10), width="container")
        
        # Show summary statistics
        target.write("**Summary Statistics:**")
        summary_col1, summary_col2, summary_col3 = target.columns(3)
        
        with summary_col1:
            target.metric("Total Records", len(download_df))
        
        with summary_col2:
            target.metric("Unique Mutations", download_df['mutation'].nunique())
        
        with summary_col3:
            target.metric("Date Range", f"{len(download_df['date'].unique())} days")
    
    return download_df
