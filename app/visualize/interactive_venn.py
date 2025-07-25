"""
Interactive Plotly-based Venn diagrams using pyvenn backend.

This module provides functionality to create interactive Venn diagrams 
that support 2-6 sets using the pyvenn library and converting them to 
Plotly interactive plots.
"""

import plotly.graph_objects as go
import plotly.express as px
from typing import List, Dict, Any, Tuple, Set, Union
import matplotlib
matplotlib.use('Agg')  # Set non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import base64

from .pyvenn import get_labels, venn2, venn3, venn4, venn5, venn6


def create_interactive_venn(
    data: List[Set],
    names: List[str],
    title: str = "Venn Diagram",
    width: int = 600,
    height: int = 500,
    show_counts: bool = True,
    show_percentages: bool = True
) -> go.Figure:
    """
    Create an interactive Plotly Venn diagram supporting 2-6 sets.
    
    Args:
        data: List of sets to create Venn diagram for
        names: List of names for each set
        title: Title for the diagram
        width: Width of the plot
        height: Height of the plot  
        show_counts: Whether to show counts in labels
        show_percentages: Whether to show percentages in labels
        
    Returns:
        Plotly Figure object with interactive Venn diagram
    """
    num_sets = len(data)
    
    if num_sets < 2 or num_sets > 6:
        raise ValueError("Venn diagrams are supported for 2-6 sets only")
    
    # Prepare fill options for labels
    fill_options = []
    if show_counts:
        fill_options.append("number")
    if show_percentages:
        fill_options.append("percent")
    
    # Get labels from pyvenn
    labels = get_labels(data, fill=fill_options)
    
    # Calculate total size for percentage calculations
    total_size = len(set().union(*data))
    
    # Create matplotlib figure using pyvenn
    venn_functions = {
        2: venn2,
        3: venn3, 
        4: venn4,
        5: venn5,
        6: venn6
    }
    
    # Use smaller figure size for embedding
    figsize = _get_optimal_figsize(num_sets)
    
    fig_mpl, ax_mpl = venn_functions[num_sets](
        labels, 
        names=names, 
        figsize=figsize,
        fontsize=10
    )
    
    # Convert matplotlib figure to image
    buf = BytesIO()
    fig_mpl.savefig(buf, format='png', bbox_inches='tight', dpi=150, transparent=True)
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig_mpl)  # Clean up matplotlib figure
    
    # Create Plotly figure with the image as background
    fig = go.Figure()
    
    # Add the venn diagram as an image
    fig.add_layout_image(
        dict(
            source=f"data:image/png;base64,{img_b64}",
            xref="x",
            yref="y", 
            x=0,
            y=1,
            sizex=1,
            sizey=1,
            sizing="stretch",
            opacity=1,
            layer="below"
        )
    )
    
    # Add invisible scatter points for interactivity with hover info
    hover_points = _create_hover_points(labels, data, names, total_size)
    
    for region_key, hover_info in hover_points.items():
        fig.add_trace(go.Scatter(
            x=[hover_info['x']], 
            y=[hover_info['y']],
            mode='markers',
            marker=dict(size=10, opacity=0),  # Invisible markers
            hovertemplate=hover_info['hovertext'],
            showlegend=False,
            name=f"Region {region_key}"
        ))
    
    # Update layout
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center'
        },
        width=width,
        height=height,
        xaxis=dict(
            range=[0, 1],
            showgrid=False,
            showticklabels=False,
            zeroline=False
        ),
        yaxis=dict(
            range=[0, 1], 
            showgrid=False,
            showticklabels=False,
            zeroline=False,
            scaleanchor="x",
            scaleratio=1
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=50, b=20)
    )
    
    return fig


def _get_optimal_figsize(num_sets: int) -> Tuple[int, int]:
    """Get optimal figure size based on number of sets."""
    size_map = {
        2: (8, 6),
        3: (8, 8), 
        4: (10, 10),
        5: (12, 12),
        6: (16, 16)
    }
    return size_map.get(num_sets, (10, 10))


def _create_hover_points(
    labels: Dict[str, str], 
    data: List[Set], 
    names: List[str],
    total_size: int
) -> Dict[str, Dict[str, Any]]:
    """
    Create hover points with detailed information for each region.
    
    Returns dict mapping region keys to hover point information.
    """
    hover_points = {}
    num_sets = len(data)
    
    # Approximate center positions for different diagram types
    # These are rough estimates - in a full implementation you'd want to 
    # extract actual coordinates from the matplotlib figure
    positions = _get_region_positions(num_sets)
    
    for region_key, label_text in labels.items():
        if not label_text or label_text == '0':
            continue
            
        # Parse the count from the label
        count = _parse_count_from_label(label_text)
        percentage = (count / total_size * 100) if total_size > 0 else 0
        
        # Determine which sets this region belongs to
        region_sets = []
        for i, bit in enumerate(region_key):
            if bit == '1':
                region_sets.append(names[i])
        
        # Create hover text
        if len(region_sets) == 1:
            hover_text = f"<b>Only in {region_sets[0]}</b><br>"
        else:
            hover_text = f"<b>Intersection of:</b><br>• " + "<br>• ".join(region_sets) + "<br>"
        
        hover_text += f"<b>Count:</b> {count}<br>"
        hover_text += f"<b>Percentage:</b> {percentage:.1f}%"
        
        # Get position (approximate)
        pos = positions.get(region_key, {'x': 0.5, 'y': 0.5})
        
        hover_points[region_key] = {
            'x': pos['x'],
            'y': pos['y'], 
            'hovertext': hover_text
        }
    
    return hover_points


def _parse_count_from_label(label_text: str) -> int:
    """Parse the count from a pyvenn label string."""
    # Labels can be like "5", "01: 5", "5(10.0%)" etc.
    import re
    
    # Look for numbers in the label
    numbers = re.findall(r'\d+', label_text)
    if numbers:
        return int(numbers[0])  # Return first number found
    return 0


def _get_region_positions(num_sets: int) -> Dict[str, Dict[str, float]]:
    """
    Get approximate positions for different regions in the Venn diagram.
    These are rough estimates for hover point placement.
    """
    if num_sets == 2:
        return {
            '10': {'x': 0.25, 'y': 0.5},  # Only A
            '01': {'x': 0.75, 'y': 0.5},  # Only B  
            '11': {'x': 0.5, 'y': 0.5},   # A ∩ B
        }
    elif num_sets == 3:
        return {
            '100': {'x': 0.3, 'y': 0.3},   # Only A
            '010': {'x': 0.7, 'y': 0.3},   # Only B
            '001': {'x': 0.5, 'y': 0.7},   # Only C
            '110': {'x': 0.5, 'y': 0.2},   # A ∩ B
            '101': {'x': 0.35, 'y': 0.55}, # A ∩ C
            '011': {'x': 0.65, 'y': 0.55}, # B ∩ C
            '111': {'x': 0.5, 'y': 0.45},  # A ∩ B ∩ C
        }
    else:
        # For 4-6 sets, use center positions as approximation
        # In a full implementation, these would be calculated based on 
        # the actual pyvenn coordinates
        positions = {}
        for i in range(1, 2**num_sets):
            key = bin(i)[2:].zfill(num_sets)
            positions[key] = {'x': 0.5, 'y': 0.5}
        return positions


def create_venn_from_mutations(
    variant_data: List[Tuple[str, List[str]]],
    title: str = "Variant Mutation Overlap",
    width: int = 700,
    height: int = 600
) -> go.Figure:
    """
    Create a Venn diagram from variant mutation data.
    
    Args:
        variant_data: List of tuples (variant_name, mutations_list)
        title: Title for the diagram
        width: Width of the plot
        height: Height of the plot
        
    Returns:
        Plotly Figure object with interactive Venn diagram
    """
    # Convert to sets
    names = [item[0] for item in variant_data]
    data = [set(item[1]) for item in variant_data]
    
    return create_interactive_venn(
        data=data,
        names=names, 
        title=title,
        width=width,
        height=height,
        show_counts=True,
        show_percentages=True
    )