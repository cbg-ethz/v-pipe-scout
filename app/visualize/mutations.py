"""
Mutation visualization functions.

This module contains plotting functions specifically for visualizing
mutation data over time, including heatmaps and other mutation-specific charts.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from process.mutations import sort_mutations_by_position


def mutations_over_time(freq_df, counts_df=None, coverage_freq_df=None, title="Mutations Over Time", progress_callback=None):
    """Plot mutations over time as a heatmap using Plotly.
    
    This function creates an interactive heatmap showing mutation frequencies
    over time with enhanced hover information including counts and coverage data.
    Mutations are automatically sorted by genomic position in ascending order.
    
    Args:
        freq_df (pd.DataFrame): DataFrame with mutations as rows, dates as columns, 
                               and frequency values (0-1 range)
        counts_df (pd.DataFrame, optional): DataFrame with mutations as rows, dates as columns, 
                                          and count values (for hover info)
        coverage_freq_df (pd.DataFrame, optional): MultiIndex DataFrame with detailed 
                                                  coverage and frequency data
        title (str, optional): Title for the heatmap. Defaults to "Mutations Over Time"
        progress_callback (callable, optional): Function to call with progress updates.
                                              Should accept (current, total, message) parameters.
    
    Returns:
        plotly.graph_objects.Figure: Interactive heatmap figure
    """
    # Sort mutations by genomic position before processing
    if progress_callback:
        progress_callback(0.1, 1.0, "Sorting mutations by genomic position...")
    
    mutations_list = freq_df.index.tolist()
    sorted_mutations = sort_mutations_by_position(mutations_list)
    
    # Reorder all DataFrames by the sorted mutation order
    freq_df = freq_df.reindex(sorted_mutations)
    if counts_df is not None and not counts_df.empty:
        counts_df = counts_df.reindex(sorted_mutations)
    
    if progress_callback:
        progress_callback(0.3, 1.0, "Processing frequency data...")
    
    # Replace None with np.nan and remove commas from numbers
    df_processed = freq_df.replace({None: np.nan, ',': ''}, regex=True)
    df_processed = df_processed.apply(pd.to_numeric, errors='coerce')

    if progress_callback:
        progress_callback(0.5, 1.0, "Creating enhanced hover text...")
    
    # Create enhanced hover text
    hover_text = []
    total_mutations = len(df_processed.index)
    
    for idx, mutation in enumerate(df_processed.index):
        # Update progress during hover text creation (this is the slowest part)
        if progress_callback and total_mutations > 0:
            hover_progress = 0.5 + (idx / total_mutations) * 0.3  # Progress from 0.5 to 0.8
            progress_callback(hover_progress, 1.0, f"Creating hover text for mutation {idx + 1}/{total_mutations}...")
        
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

    if progress_callback:
        progress_callback(0.9, 1.0, "Finalizing plot layout...")
    
    # Determine dynamic height
    height = max(400, len(df_processed.index) * 20 + 100)  # Base height + per mutation + padding for title/axes

    # Determine dynamic left margin based on mutation label length
    max_len_mutation_label = 0
    if not df_processed.index.empty:  # Check if index is not empty
        max_len_mutation_label = max(len(str(m)) for m in df_processed.index)
    
    margin_l = max(80, max_len_mutation_label * 7 + 30)  # Min margin or calculated, adjust multiplier as needed

    fig = go.Figure(data=go.Heatmap(
        z=df_processed.values,  # Using frequency values
        x=df_processed.columns,
        y=df_processed.index,
        colorscale='Blues',
        showscale=False,  # Hide color bar as requested
        hoverongaps=True,  # Show hover for gaps (NaNs)
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
        if num_cols > 2 and num_cols // 2 != num_cols - 1:  # Avoid duplicate if middle is last
            tick_indices.append(df_processed.columns[-1])
        tick_labels = [str(label) for label in tick_indices]

    fig.update_layout(
        title=title,
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
            autorange='reversed'  # Show mutations from top to bottom as in original df
        ),
        height=height,
        plot_bgcolor='lightpink',  # NaN values will appear as this background color
        margin=dict(l=margin_l, r=20, t=80, b=100),  # Adjust margins
    )
    return fig





def proportions_heatmap(freq_df, counts_df=None, coverage_freq_df=None, title="Proportions Heatmap", progress_callback=None):
    """Plot proportions as a heatmap using Plotly.
    
    This function creates an interactive heatmap showing proportions (frequencies)
    over time with enhanced hover information including counts and coverage data.
    Designed for comparing multiple locations or categories over time.
    
    Args:
        freq_df (pd.DataFrame): DataFrame with locations/categories as rows, dates as columns, 
                               and frequency values (0-1 range)
        counts_df (pd.DataFrame, optional): DataFrame with same shape as freq_df, 
                                          containing count values (for hover info)
        coverage_freq_df (pd.DataFrame, optional): MultiIndex DataFrame with detailed 
                                                  coverage and frequency data. 
                                                  Index should be (location, samplingDate).
        title (str, optional): Title for the heatmap. Defaults to "Proportions Heatmap"
        progress_callback (callable, optional): Function to call with progress updates.
                                              Should accept (current, total, message) parameters.
    
    Returns:
        plotly.graph_objects.Figure: Interactive heatmap figure
    """
    if progress_callback:
        progress_callback(0.1, 1.0, "Preparing data for heatmap...")
    
    # Replace None with np.nan and remove commas from numbers
    df_processed = freq_df.replace({None: np.nan, ',': ''}, regex=True)
    df_processed = df_processed.apply(pd.to_numeric, errors='coerce')

    if progress_callback:
        progress_callback(0.3, 1.0, "Creating enhanced hover text...")
    
    # Create enhanced hover text
    hover_text = []
    total_rows = len(df_processed.index)
    
    for idx, row_label in enumerate(df_processed.index):
        # Update progress during hover text creation
        if progress_callback and total_rows > 0:
            hover_progress = 0.3 + (idx / total_rows) * 0.5  # Progress from 0.3 to 0.8
            progress_callback(hover_progress, 1.0, f"Creating hover text for {row_label}...")
        
        row_hover_text = []
        for date in df_processed.columns:
            frequency = df_processed.loc[row_label, date]
            
            # Try to get additional data from other sources
            count = None
            coverage = None
            
            # First try to get count from counts_df if provided
            if counts_df is not None and not counts_df.empty:
                try:
                    val = counts_df.loc[row_label, date]
                    count = val if not pd.isna(val) else None
                except KeyError:
                    pass
            
            # Then try to get additional data from coverage_freq_df
            if coverage_freq_df is not None and not coverage_freq_df.empty:
                try:
                    # Check if we can access by (row_label, date)
                    # Assuming coverage_freq_df has MultiIndex (location, samplingDate)
                    if (row_label, date) in coverage_freq_df.index:
                        mutation_data = coverage_freq_df.loc[(row_label, date)]
                        coverage_val = mutation_data.get('coverage')
                        
                        # If count is still None, try to get it from coverage_freq_df
                        if count is None:
                            count_val = mutation_data.get('count')
                            count = count_val if count_val != 'NA' else None
                        
                        # Handle 'NA' values for coverage
                        coverage = coverage_val if coverage_val != 'NA' else None
                except (KeyError, IndexError, TypeError):
                    pass  # Data not available for this combination
            
            # Build hover text
            if pd.isna(frequency):
                text = f"Location: {row_label}<br>Date: {date}<br>Status: No data"
            else:
                text = f"Location: {row_label}<br>Date: {date}<br>Proportion: {frequency * 100:.1f}%"
                if count is not None:
                    text += f"<br>Count: {float(count):.0f}"
                if coverage is not None:
                    text += f"<br>Coverage: {float(coverage):.0f}"
            
            row_hover_text.append(text)
        hover_text.append(row_hover_text)

    if progress_callback:
        progress_callback(0.9, 1.0, "Finalizing plot layout...")
    
    # Determine dynamic height
    height = max(400, len(df_processed.index) * 30 + 100)  # Base height + per row + padding

    # Determine dynamic left margin based on label length
    max_len_label = 0
    if not df_processed.index.empty:
        max_len_label = max(len(str(m)) for m in df_processed.index)
    
    margin_l = max(80, max_len_label * 7 + 30)

    # Apply power transformation to highlight low non-zero values
    # This acts similar to a log scale but preserves 0 -> 0 mapping
    # Using power of 0.25 makes small values (e.g. 0.01) much more visible (0.01^0.25 ~= 0.31)
    z_values = np.power(df_processed.values, 0.25)

    fig = go.Figure(data=go.Heatmap(
        z=z_values,
        x=df_processed.columns,
        y=df_processed.index,
        colorscale='Blues',
        showscale=False,
        hoverongaps=True,
        text=hover_text,
        hoverinfo='text',
        zmin=0,
        zmax=1
    ))

    # Customize layout
    num_cols = len(df_processed.columns)
    tick_indices = []
    tick_labels = []
    if num_cols > 0:
        # Show fewer ticks to avoid crowding
        step = max(1, num_cols // 10)
        tick_indices = df_processed.columns[::step]
        tick_labels = [str(label) for label in tick_indices]

    fig.update_layout(
        title=title,
        xaxis=dict(
            title='Date',
            side='bottom',
            tickmode='auto',
            tickangle=45,
        ),
        yaxis=dict(
            title='Location',
            autorange='reversed'  # Show locations from top to bottom
        ),
        height=height,
        plot_bgcolor='lightpink',  # NaN values will appear as this background color
        margin=dict(l=margin_l, r=20, t=80, b=100),
    )
    return fig
