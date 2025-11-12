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


def proportions_lineplot(freq_df: pd.DataFrame,
                         counts_df: pd.DataFrame | None = None,
                         coverage_freq_df: pd.DataFrame | None = None,
                         title: str = "Mutation Proportions Over Time",
                         smoothing_window_days: int = 0,
                         progress_callback=None) -> go.Figure:
    """Plot mutation proportions over time as line plots (one line per mutation).

    - Always plots proportion (frequency) on the y-axis (0-1).
    - Optionally applies a time-based rolling mean (in days) to smooth daily data.
    - Hover shows proportion plus count and coverage (if provided).

    Args:
        freq_df: Mutations as rows, dates as columns (values 0-1). Column labels should be dates or parsable to datetime.
        counts_df: Optional counts with same shape (for hover info).
        coverage_freq_df: Optional MultiIndex by (mutation, samplingDate) with 'count' and 'coverage' (for hover info).
        title: Figure title.
        progress_callback: Optional callable(progress, total, message).

    Returns:
        Plotly Figure with one trace per mutation.
    """
    if progress_callback:
        progress_callback(0.05, 1.0, "Preparing data for line plot...")

    # Ensure columns are datetimes and sorted
    df_freq = freq_df.copy()
    df_freq.columns = pd.to_datetime(df_freq.columns)
    df_freq = df_freq.sort_index(axis=1)

    # Sort mutations by genomic position
    mutations_list = df_freq.index.tolist()
    sorted_mutations = sort_mutations_by_position(mutations_list)
    df_freq = df_freq.reindex(sorted_mutations)

    # Align counts to freq if provided
    df_counts = None
    if counts_df is not None and not counts_df.empty:
        df_counts = counts_df.copy()
        df_counts.columns = pd.to_datetime(df_counts.columns)
        df_counts = df_counts.sort_index(axis=1)
        df_counts = df_counts.reindex(sorted_mutations)

    if progress_callback:
        progress_callback(0.35, 1.0, "Building traces...")

    # Build hover customdata: counts and coverage if available
    fig = go.Figure()
    all_dates = list(df_freq.columns)

    for mutation in df_freq.index:
        # Convert y values safely handling pandas NA
        y_series = df_freq.loc[mutation]
        y_vals = np.array([float(v) if not pd.isna(v) else np.nan for v in y_series], dtype=float)

        # counts per date (for hover)
        counts_vals = None
        if df_counts is not None:
            # align to same dates
            aligned_counts = df_counts.reindex(columns=all_dates)
            counts_series = aligned_counts.loc[mutation]
            if counts_series is not None:
                # Convert to numeric, replacing NA/NaN with None, handle pandas NA
                numeric_series = pd.to_numeric(counts_series, errors='coerce')
                # Convert to list to handle pandas NA types
                counts_vals = np.array([None if pd.isna(v) else float(v) for v in numeric_series], dtype=object)

        # coverage per date (for hover) via coverage_freq_df
        coverage_vals = None
        if coverage_freq_df is not None and not coverage_freq_df.empty:
            cov_tmp = []
            for dt in all_dates:
                try:
                    if mutation in coverage_freq_df.index.get_level_values('mutation'):
                        md = coverage_freq_df.loc[mutation]
                        if dt in md.index:
                            cov = md.loc[dt, 'coverage']
                            # Handle various NA types
                            if pd.isna(cov) or cov == 'NA':
                                cov_tmp.append(None)
                            else:
                                cov_tmp.append(float(cov))
                        else:
                            cov_tmp.append(None)
                    else:
                        cov_tmp.append(None)
                except Exception:
                    cov_tmp.append(None)
            coverage_vals = np.array(cov_tmp, dtype=object)

        # Assemble customdata columns for hover
        # customdata shape: (N, 2) -> [count, coverage]
        if counts_vals is not None or coverage_vals is not None:
            # Normalize shapes
            if counts_vals is None:
                counts_vals = np.array([None] * len(all_dates), dtype=object)
            if coverage_vals is None:
                coverage_vals = np.array([None] * len(all_dates), dtype=object)
            customdata = np.vstack([counts_vals, coverage_vals]).T
            hovertemplate = (
                "Date: %{x|%Y-%m-%d}<br>"
                "Proportion: %{y:.3f}<br>"
                "Count: %{customdata[0]:.0f}<br>"
                "Coverage: %{customdata[1]:.0f}<extra>%{fullData.name}</extra>"
            )
        else:
            customdata = None
            hovertemplate = (
                "Date: %{x|%Y-%m-%d}<br>"
                "Proportion: %{y:.3f}<extra>%{fullData.name}</extra>"
            )

        fig.add_trace(go.Scatter(
            x=all_dates,
            y=y_vals,
            mode="lines+markers",
            name=mutation,
            customdata=customdata,
            hovertemplate=hovertemplate,
            marker=dict(size=6, line=dict(width=0.5, color="white"))
        ))

    # Layout
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Proportion",
        template="plotly_white",
        height=max(400, 300 + int(len(df_freq.index) / 10) * 40),
        legend_title_text="Mutation",
        margin=dict(l=60, r=20, t=60, b=60)
    )
    # Auto-scale y-axis to data range instead of forcing 0-1
    fig.update_yaxes(autorange=True)

    if progress_callback:
        progress_callback(0.95, 1.0, "Rendering plot...")

    return fig
