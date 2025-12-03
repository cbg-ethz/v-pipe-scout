import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from visualize.mutations import proportions_heatmap

def test_proportions_heatmap_basic():
    # Create sample data
    dates = ['2024-01-01', '2024-01-02']
    locations = ['LocA', 'LocB']
    
    freq_data = {
        '2024-01-01': [0.1, 0.2],
        '2024-01-02': [0.3, 0.4]
    }
    freq_df = pd.DataFrame(freq_data, index=locations)
    
    fig = proportions_heatmap(freq_df, title="Test Heatmap")
    
    assert isinstance(fig, go.Figure)
    assert fig.layout.title.text == "Test Heatmap"
    assert len(fig.data) == 1
    assert fig.data[0].type == 'heatmap'
    
    # Check data
    # Plotly heatmap z is list of lists (rows)
    # Values are power-transformed (x^0.25)
    # Row 0 (LocA): [0.1, 0.3] -> [0.1^0.25, 0.3^0.25]
    # Row 1 (LocB): [0.2, 0.4] -> [0.2^0.25, 0.4^0.25]
    
    expected_0_0 = 0.1 ** 0.25
    expected_1_1 = 0.4 ** 0.25
    
    assert np.isclose(fig.data[0].z[0][0], expected_0_0)
    assert np.isclose(fig.data[0].z[1][1], expected_1_1)
    
    # Check hover text has original values
    assert "Proportion: 10.0%" in fig.data[0].text[0][0]
    assert "Proportion: 40.0%" in fig.data[0].text[1][1]

def test_proportions_heatmap_with_counts_coverage():
    dates = ['2024-01-01']
    locations = ['LocA']
    
    freq_df = pd.DataFrame({'2024-01-01': [0.5]}, index=locations)
    counts_df = pd.DataFrame({'2024-01-01': [100]}, index=locations)
    
    coverage_records = [{
        'location': 'LocA',
        'samplingDate': '2024-01-01',
        'coverage': 200,
        'count': 100,
        'frequency': 0.5
    }]
    coverage_df = pd.DataFrame(coverage_records).set_index(['location', 'samplingDate'])
    
    fig = proportions_heatmap(freq_df, counts_df=counts_df, coverage_freq_df=coverage_df)
    
    # Check hover text contains coverage info
    hover_text = fig.data[0].text[0][0]
    assert "Coverage: 200" in hover_text
    assert "Count: 100" in hover_text
    assert "Proportion: 50.0%" in hover_text
