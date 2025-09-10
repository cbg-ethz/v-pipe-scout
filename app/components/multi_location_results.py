"""
Multi-location results component for V-Pipe Scout.

This module provides a tabbed interface for displaying results from multiple locations,
with progress tracking and per-location visualizations.
"""

import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, Any, Optional, Optional
import logging

logger = logging.getLogger(__name__)


def render_location_results_tabs(
    location_tasks: Dict[str, str],
    location_results: Dict[str, Any],
    celery_app,
    redis_client
) -> None:
    """
    Render tabbed interface for multi-location results.
    
    Args:
        location_tasks: Dictionary mapping location names to task IDs
        location_results: Dictionary mapping location names to result data
        celery_app: Celery application instance
        redis_client: Redis client for progress tracking
    """
    
    if not location_tasks:
        st.info("No analysis tasks have been started yet.")
        return
    
    # Add combined download section if multiple locations and results are available
    if len(location_tasks) > 1 and location_results:
        render_combined_download_options(location_results)
        st.divider()
    
    # Create tabs for each location
    location_names = list(location_tasks.keys())
    tabs = st.tabs([f"📍 {loc}" for loc in location_names])
    
    for i, (location, tab) in enumerate(zip(location_names, tabs)):
        with tab:
            task_id = location_tasks[location]
            
            # Check if we already have results for this location
            if location in location_results:
                render_single_location_result(location, location_results[location])
            else:
                # Check task status
                render_location_progress(location, task_id, celery_app, redis_client)


def render_single_location_result(location: str, result_data: Any) -> None:
    """
    Render results for a single location.
    
    Args:
        location: Location name
        result_data: Analysis results for the location
    """
    st.success(f"Analysis completed for {location}!")
    
    if not result_data or len(result_data) == 0:
        st.warning("No results data available to visualize.")
        return
    
   

    # Extract variants data based on the actual structure we see
    variants_data = None
    
    if isinstance(result_data, dict):
        # The result_data appears to be directly the variants data
        # where keys are variant names like "KP.2", "KP.3", etc.
        
        # Check if this looks like variants data by examining the structure
        sample_key = list(result_data.keys())[0] if result_data else None
        if sample_key and isinstance(result_data[sample_key], dict):
            sample_variant_data = result_data[sample_key]
            
            # Look for typical deconvolution result fields
            has_timeseries = any(key in sample_variant_data for key in [
                'timeseriesSummary', 'timeseries', 'time_series', 'summary'
            ])
            
            # Check if the keys look like variant names (not nested structure keys)
            variant_name_pattern = any(
                key for key in result_data.keys() 
                if isinstance(key, str) and (
                    '.' in key or  # KP.2, NB.1.8.1
                    key.startswith(('XEC', 'XFG', 'BA.', 'BQ.', 'XBB.', 'KP.', 'LP.', 'NB.')) or
                    key in ['undetermined']
                )
            )
            
            if has_timeseries or variant_name_pattern:
                variants_data = result_data
                st.info(f"✅ Using direct variants data structure with {len(variants_data)} variants")
            else:
                # Try looking for nested location data (prefer actual location name)
                if location in result_data:
                    variants_data = result_data[location]
                    st.info(f"✅ Found location-nested data for {location}")
                elif "location" in result_data:
                    # Handle generic "location" key structure (legacy)
                    variants_data = result_data["location"]
                    st.warning(f"⚠️ Using generic 'location' key for {location} (legacy structure)")
                else:
                    # Fall back to treating as variants data anyway
                    variants_data = result_data
                    st.warning(f"⚠️ Using result_data as variants data (fallback)")
    
    if not variants_data:
        st.error(f"❌ Could not extract variants data from result for {location}")
        st.write("**Available keys in result_data:**", list(result_data.keys()) if isinstance(result_data, dict) else "Not a dictionary")
        return
    
    # Create visualization
    try:
        fig = create_variant_plot(variants_data, location)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ Could not create plot - no valid time series data found")
            
            # Additional debugging for plot creation failure
            st.write("**Debugging plot creation:**")
            for variant_name, variant_data in list(variants_data.items())[:3]:  # Show first 3
                if isinstance(variant_data, dict):
                    st.write(f"- **{variant_name}**: {list(variant_data.keys())}")
                else:
                    st.write(f"- **{variant_name}**: {type(variant_data)}")
                    
    except Exception as e:
        st.error(f"❌ Error creating plot: {str(e)}")
        return
    
    # Add download options
    try:
        render_download_options(location, variants_data)
    except Exception as e:
        st.error(f"❌ Error creating download options: {str(e)}")


def render_location_progress(location: str, task_id: str, celery_app, redis_client) -> None:
    """
    Render progress for a location that's still processing.
    
    Args:
        location: Location name
        task_id: Celery task ID
        celery_app: Celery application instance
        redis_client: Redis client
    """
    
    # Check if task is completed
    try:
        task = celery_app.AsyncResult(task_id)
        if task.ready():
            try:
                result = task.get()
                
                # DEBUG: Log the raw result structure for understanding
                logger.info(f"Raw deconvolution result for {location}: type={type(result)}")
                if isinstance(result, dict):
                    logger.info(f"Result keys: {list(result.keys())}")
                    # Log first few characters of each key's value
                    for key, value in list(result.items())[:3]:
                        logger.info(f"  {key}: {type(value)} - {str(value)[:100]}...")
                
                # Store result in session state
                st.session_state.location_results[location] = result
                st.success(f"Analysis completed for {location}!")
                st.rerun()
            except Exception as e:
                st.error(f"Error retrieving result for {location}: {str(e)}")
                return
    except Exception as e:
        st.error(f"Error checking task status for {location}: {str(e)}")
        return
    
    # Show progress
    progress_key = f"task_progress:{task_id}"
    try:
        progress_data = redis_client.get(progress_key)
        
        if progress_data:
            progress_info = json.loads(progress_data)
            current = progress_info.get('current', 0)
            total = progress_info.get('total', 1)
            status = progress_info.get('status', 'Processing...')
            
            # Display progress bar
            progress_value = current / total if total > 0 else 0
            st.progress(progress_value)
            st.write(f"Status: {status}")
            
            if current > 0 and total > 0:
                st.caption(f"Progress: {current}/{total} ({progress_value:.1%})")
        else:
            st.info("Task is running... Progress information will appear shortly.")
    except Exception as e:
        logger.warning(f"Error retrieving progress for {location}: {e}")
        st.info("Task is running... Progress information unavailable.")
    
    # Add manual check button
    if st.button(f"🔄 Check Status for {location}", key=f"check_{location}"):
        st.rerun()


def create_variant_plot(variants_data: Dict[str, Any], location: str) -> Optional[go.Figure]:
    """
    Create plotly figure for variant abundance over time.
    
    Args:
        variants_data: Dictionary containing variant time series data
        location: Location name for the title
        
    Returns:
        Plotly figure object or None if no valid data
    """
    if not variants_data:
        logger.warning(f"No variants data provided for {location}")
        return None
    
    fig = go.Figure()
    
    # Color palette for variants
    colors = px.colors.qualitative.Bold if hasattr(px.colors.qualitative, 'Bold') else [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", 
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
    ]
    
    # Ensure we have enough colors
    if len(variants_data) > len(colors):
        # Extend by cycling through the list
        colors = colors * (len(variants_data) // len(colors) + 1)
    
    # Track the max time range for x-axis limits
    all_dates = []
    traces_added = 0
    
    # Plot each variant
    for i, (variant_name, variant_data) in enumerate(variants_data.items()):
        logger.info(f"Processing variant: {variant_name}, data type: {type(variant_data)}")
        
        if not isinstance(variant_data, dict):
            logger.warning(f"Variant {variant_name} data is not a dict: {type(variant_data)}")
            continue
        
        # Look for time series data with different possible key names
        timeseries = None
        timeseries_key_found = None
        for key in ['timeseriesSummary', 'timeseries', 'time_series', 'summary', 'data', 'points']:
            if key in variant_data:
                timeseries = variant_data[key]
                timeseries_key_found = key
                break
        
        if not timeseries:
            logger.warning(f"No timeseries data found for variant {variant_name}. Available keys: {list(variant_data.keys())}")
            # Try to see if the variant_data itself might be the timeseries
            if isinstance(variant_data, list):
                timeseries = variant_data
                timeseries_key_found = "direct_list"
            else:
                continue
        
        if not isinstance(timeseries, list):
            logger.warning(f"Timeseries for {variant_name} is not a list (found under '{timeseries_key_found}'): {type(timeseries)}")
            continue
            
        if len(timeseries) == 0:
            logger.warning(f"Empty timeseries for {variant_name}")
            continue
        
        logger.info(f"Found timeseries for {variant_name} under key '{timeseries_key_found}' with {len(timeseries)} points")
        
        try:
            # Extract dates and proportions
            dates = []
            proportions = []
            lower_bounds = []
            upper_bounds = []
            
            for j, point in enumerate(timeseries):
                if not isinstance(point, dict):
                    logger.warning(f"Point {j} for {variant_name} is not a dict: {type(point)}")
                    continue
                
                # Look for date field
                date_val = None
                date_key_found = None
                for date_key in ['date', 'time', 'timestamp', 'Date', 'Time']:
                    if date_key in point:
                        date_val = point[date_key]
                        date_key_found = date_key
                        break
                
                if date_val is None:
                    logger.warning(f"No date field found in point {j} for {variant_name}. Available keys: {list(point.keys())}")
                    continue
                
                # Look for proportion/value field
                prop_val = None
                prop_key_found = None
                for prop_key in ['proportion', 'value', 'abundance', 'frequency', 'Proportion', 'Value']:
                    if prop_key in point:
                        prop_val = point[prop_key]
                        prop_key_found = prop_key
                        break
                
                if prop_val is None:
                    logger.warning(f"No proportion field found in point {j} for {variant_name}. Available keys: {list(point.keys())}")
                    continue
                
                try:
                    parsed_date = pd.to_datetime(date_val)
                    dates.append(parsed_date)
                    proportions.append(float(prop_val))
                    
                    # Look for confidence intervals
                    lower_val = point.get('proportionLower', point.get('lower', point.get('Lower', prop_val)))
                    upper_val = point.get('proportionUpper', point.get('upper', point.get('Upper', prop_val)))
                    lower_bounds.append(float(lower_val))
                    upper_bounds.append(float(upper_val))
                    
                    if j == 0:  # Log the first successful point for debugging
                        logger.info(f"Successfully parsed first point for {variant_name}: date='{date_val}' ({date_key_found}), proportion={prop_val} ({prop_key_found})")
                    
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing data point {j} for {variant_name}: {e} (date='{date_val}', prop='{prop_val}')")
                    continue
            
            if not dates:
                logger.warning(f"No valid data points found for variant {variant_name}")
                continue
            
            all_dates.extend(dates)
            color_idx = i % len(colors)
            color = colors[color_idx]
            
            # Add line plot for this variant
            fig.add_trace(go.Scatter(
                x=dates,
                y=proportions,
                mode='lines+markers',
                line=dict(color=color, width=2),
                name=variant_name,
                hovertemplate=f'<b>{variant_name}</b><br>' +
                             'Date: %{x}<br>' +
                             'Proportion: %{y:.1%}<extra></extra>'
            ))
            
            # Add shaded confidence interval if we have different upper/lower bounds
            if any(l != u for l, u in zip(lower_bounds, upper_bounds)):
                rgba_color = get_rgba_color(color, 0.2)
                
                fig.add_trace(go.Scatter(
                    x=dates + dates[::-1],  # Forward then backwards
                    y=upper_bounds + lower_bounds[::-1],  # Upper then lower bounds
                    fill='toself',
                    fillcolor=rgba_color,
                    line=dict(color='rgba(0,0,0,0)'),
                    hoverinfo="skip",
                    showlegend=False
                ))
            
            traces_added += 1
            logger.info(f"Successfully added trace for {variant_name} with {len(dates)} data points")
            
        except Exception as e:
            logger.error(f"Error processing variant {variant_name}: {e}")
            continue
    
    if traces_added == 0:
        logger.warning(f"No valid traces added for location {location}")
        return None
    
    # Update layout
    fig.update_layout(
        title=f"Variant Proportion Estimates - {location}",
        xaxis_title="Date",
        yaxis_title="Estimated Proportion",
        yaxis=dict(
            tickformat='.0%',  # Format as percentage
            range=[0, 1]
        ),
        legend_title="Variants",
        height=500,
        template="plotly_white",
        hovermode="x unified"
    )
    
    logger.info(f"Successfully created plot for {location} with {traces_added} variants")
    return fig


def get_rgba_color(color: str, alpha: float) -> str:
    """
    Convert a color to RGBA format with specified alpha.
    
    Args:
        color: Color string (hex, rgb, or named color)
        alpha: Alpha value (0-1)
        
    Returns:
        RGBA color string
    """
    try:
        if color.startswith('#'):
            # Convert hex to rgb
            r = int(color[1:3], 16) / 255
            g = int(color[3:5], 16) / 255
            b = int(color[5:7], 16) / 255
            return f'rgba({r:.3f}, {g:.3f}, {b:.3f}, {alpha})'
        elif color.startswith('rgb'):
            # Extract RGB values from the string
            rgb_values = color.replace('rgb(', '').replace('rgba(', '').replace(')', '').split(',')
            if len(rgb_values) >= 3:
                r = float(rgb_values[0].strip()) / 255 if float(rgb_values[0].strip()) > 1 else float(rgb_values[0].strip())
                g = float(rgb_values[1].strip()) / 255 if float(rgb_values[1].strip()) > 1 else float(rgb_values[1].strip())
                b = float(rgb_values[2].strip()) / 255 if float(rgb_values[2].strip()) > 1 else float(rgb_values[2].strip())
                return f'rgba({r:.3f}, {g:.3f}, {b:.3f}, {alpha})'
        
        # Fallback for unknown color formats
        return f'rgba(0.5, 0.5, 0.5, {alpha})'
    except Exception:
        # Safe fallback
        return f'rgba(0.5, 0.5, 0.5, {alpha})'


def render_download_options(location: str, variants_data: Dict[str, Any]) -> None:
    """
    Render download buttons for location-specific results.
    
    Args:
        location: Location name
        variants_data: Variant analysis results
    """
    
    # Prepare CSV data
    all_variant_data = []
    
    for variant_name, variant_data in variants_data.items():
        if not isinstance(variant_data, dict):
            continue
        
        # Look for time series data with different possible key names
        timeseries = None
        for key in ['timeseriesSummary', 'timeseries', 'time_series', 'summary', 'data', 'points']:
            if key in variant_data:
                timeseries = variant_data[key]
                break
        
        # Fallback: check if variant_data itself is a list
        if not timeseries and isinstance(variant_data, list):
            timeseries = variant_data
        
        if not timeseries or not isinstance(timeseries, list):
            continue
        
        for point in timeseries:
            if not isinstance(point, dict):
                continue
            
            # Extract data with flexible field names
            date_val = None
            for date_key in ['date', 'time', 'timestamp', 'Date', 'Time']:
                if date_key in point:
                    date_val = point[date_key]
                    break
            
            prop_val = None
            for prop_key in ['proportion', 'value', 'abundance', 'frequency', 'Proportion', 'Value']:
                if prop_key in point:
                    prop_val = point[prop_key]
                    break
            
            if date_val is None or prop_val is None:
                continue
            
            all_variant_data.append({
                'location': location,
                'variant': variant_name,
                'date': str(date_val),
                'proportion': prop_val,
                'proportionLower': point.get('proportionLower', point.get('lower', '')),
                'proportionUpper': point.get('proportionUpper', point.get('upper', ''))
            })
    
    if all_variant_data:
        st.subheader(f"📥 Download {location} Results")
        st.caption(f"Download results for {location} only")
        
        col1, col2 = st.columns(2)
        
        with col1:
            csv_data = pd.DataFrame(all_variant_data).to_csv(index=False)
            st.download_button(
                label=f"📄 Download {location} (CSV)",
                data=csv_data,
                file_name=f'deconvolution_results_{location.replace(" ", "_")}.csv',
                mime='text/csv',
                key=f"csv_download_{location}",
                help=f"CSV format results for {location} only"
            )
        
        with col2:
            json_data = json.dumps({location: variants_data}, indent=2)
            st.download_button(
                label=f"📋 Download {location} (JSON)",
                data=json_data,
                file_name=f'deconvolution_results_{location.replace(" ", "_")}.json',
                mime='application/json',
                key=f"json_download_{location}",
                help=f"JSON format results for {location} only"
            )
    else:
        st.warning(f"No data available for download from {location}")


def render_combined_download_options(location_results: Dict[str, Any]) -> None:
    """
    Render download options for combined multi-location results.
    
    Args:
        location_results: Dictionary of location -> result data
    """
    if not location_results:
        return
    
    st.subheader("📥 Download Combined Results")
    st.caption("Download all location results in a single long-format table with location column")
    
    # Prepare combined data for download
    combined_data = []
    
    for location, result_data in location_results.items():
        # Handle different result data structures
        if isinstance(result_data, dict):
            # Check if result_data has location as a key (prefer actual location name)
            if location in result_data:
                variants_data = result_data[location]
            elif "location" in result_data:
                # Handle generic "location" key structure (legacy)
                variants_data = result_data["location"]
            else:
                # Result data directly contains variants
                variants_data = result_data
        else:
            logger.warning(f"Unexpected result data type for {location}: {type(result_data)}")
            continue
        
        if not isinstance(variants_data, dict):
            logger.warning(f"Variants data for {location} is not a dict: {type(variants_data)}")
            continue
        
        # Extract timeseries data for each variant
        for variant_name, variant_data in variants_data.items():
            if not isinstance(variant_data, dict):
                continue
            
            # Look for time series data with different possible key names
            timeseries = None
            timeseries_key_found = None
            for key in ['timeseriesSummary', 'timeseries', 'time_series', 'summary', 'data', 'points']:
                if key in variant_data:
                    timeseries = variant_data[key]
                    timeseries_key_found = key
                    break
            
            if not timeseries:
                # Try to see if the variant_data itself might be the timeseries
                if isinstance(variant_data, list):
                    timeseries = variant_data
                    timeseries_key_found = "direct_list"
                else:
                    continue
            
            if not isinstance(timeseries, list):
                continue
            
            # Process each time point
            for point in timeseries:
                if not isinstance(point, dict):
                    continue
                
                # Extract data with flexible field names
                date_val = None
                for date_key in ['date', 'time', 'timestamp', 'Date', 'Time']:
                    if date_key in point:
                        date_val = point[date_key]
                        break
                
                prop_val = None
                for prop_key in ['proportion', 'value', 'abundance', 'frequency', 'Proportion', 'Value']:
                    if prop_key in point:
                        prop_val = point[prop_key]
                        break
                
                if date_val is None or prop_val is None:
                    continue
                
                # Add to combined data with location information
                combined_data.append({
                    'location': location,
                    'variant': variant_name,
                    'date': str(date_val),
                    'proportion': prop_val,
                    'proportionLower': point.get('proportionLower', point.get('lower', '')),
                    'proportionUpper': point.get('proportionUpper', point.get('upper', ''))
                })
    
    # Show download options
    if combined_data:
        # Create summary info
        df_summary = pd.DataFrame(combined_data)
        total_rows = len(df_summary)
        total_locations = df_summary['location'].nunique()
        total_variants = df_summary['variant'].nunique()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📍 Locations", total_locations)
        with col2:
            st.metric("🦠 Variants", total_variants)
        with col3:
            st.metric("📊 Data Points", total_rows)
        
        # Download buttons
        col1, col2 = st.columns(2)
        
        with col1:
            csv_data = pd.DataFrame(combined_data).to_csv(index=False)
            st.download_button(
                label="📄 Download Combined Results (CSV)",
                data=csv_data,
                file_name='deconvolution_results_all_locations.csv',
                mime='text/csv',
                key="combined_csv_download",
                help="Long-format table with location column for all results"
            )
        
        with col2:
            json_data = json.dumps(location_results, indent=2)
            st.download_button(
                label="📋 Download Combined Results (JSON)",
                data=json_data,
                file_name='deconvolution_results_all_locations.json',
                mime='application/json',
                key="combined_json_download",
                help="Complete nested JSON structure with all results"
            )
        
        # Show data preview
        with st.expander("📋 Preview Combined Data Structure"):
            st.caption(f"First 10 rows of {total_rows} total data points")
            st.dataframe(df_summary.head(10), use_container_width=True)
    else:
        st.warning("No data available for combined download")


def render_combined_results_summary(location_results: Dict[str, Any]) -> None:
    """
    Render a summary view of all completed location results.
    
    Args:
        location_results: Dictionary of location -> result data
    """
    if not location_results:
        return
    
    st.subheader("Combined Results Summary")
    
    # Create summary metrics
    total_locations = len(location_results)
    total_variants = set()
    
    for location, result_data in location_results.items():
        if isinstance(result_data, dict):
            if location in result_data:
                variants_data = result_data[location]
            elif "location" in result_data:
                variants_data = result_data["location"]
            else:
                variants_data = result_data
        else:
            variants_data = result_data
        
        if isinstance(variants_data, dict):
            total_variants.update(variants_data.keys())
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Locations Analyzed", total_locations)
    with col2:
        st.metric("Unique Variants", len(total_variants))
    with col3:
        st.metric("Total Results", sum(
            len(variants_data) if isinstance(variants_data, dict) else 0 
            for result_data in location_results.values()
            for variants_data in [result_data.get(list(result_data.keys())[0], result_data) if isinstance(result_data, dict) and len(result_data) == 1 else result_data]
        ))