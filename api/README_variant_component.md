# Variant Signature Component

This document explains how to use the Variant Signature Component in your pages.

## Overview

The Variant Signature Component is a reusable module that allows you to:

1. Query CovSpectrum for variant signature mutations
2. Select and filter mutations
3. Download the signature as a YAML file
4. Visualize the coverage and proportion distributions (optional)

The component is highly configurable and can be used in different contexts with varying layouts.

## Basic Usage

Here's how to use the component in its simplest form:

```python
import streamlit as st
from api.covspectrum import CovSpectrumLapis
from api.variant_signature_component import render_signature_composer

# Load configuration and initialize APIs
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

server_ip = config.get('server', {}).get('lapis_address', 'http://default_ip:8000')
cov_spectrum_api = config.get('server', {}).get('cov_spectrum_api', 'https://lapis.cov-spectrum.org')
    
cov_spectrum = CovSpectrumLapis(cov_spectrum_api)

# Render the component with default settings
selected_mutations = render_signature_composer(
    cov_spectrum,
    server_ip,
    cov_spectrum_api
)

# Use the selected mutations
if selected_mutations:
    st.write("Selected mutations:", selected_mutations)
```

## Configuration Options

The component accepts a configuration dictionary with the following options:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `show_nucleotides_only` | bool | False | If True, only show nucleotide option without amino acid selection |
| `slim_table` | bool | False | If True, show a simplified table without coverage/proportion columns |
| `show_distributions` | bool | True | Whether to show coverage/proportion distribution plots |
| `show_download` | bool | True | Whether to show the download button for YAML export |
| `show_title` | bool | True | Whether to show the component title |
| `title` | str | "Variant Signature Composer" | The title to display when `show_title` is True |
| `show_description` | bool | True | Whether to show the component description |
| `default_variant` | str | "LP.8" | Default variant to query |
| `default_min_abundance` | float | 0.8 | Default minimum abundance value |
| `default_min_coverage` | int | 15 | Default minimum coverage value |

## Advanced Usage

### Using with a Custom Container

You can pass a custom Streamlit container to render the component in:

```python
container = st.container()
selected_mutations = render_signature_composer(
    cov_spectrum,
    cov_spectrum_api,
    config={},
    container=container
)
```

### Using in a Multi-Column Layout

You can use the component in a multi-column layout:

```python
# Create a two-column layout
col1, col2 = st.columns([1, 2])

# Configure component for compact display
compact_config = {
    'show_nucleotides_only': True,
    'slim_table': True,
    'show_distributions': False,
    'show_title': False,
    'show_description': False
}

# Render in the first column with a session prefix
with col1:
    selected_mutations = render_signature_composer(
        cov_spectrum,
        cov_spectrum_api,
        compact_config,
        session_prefix="compact_"  # Use prefix to avoid session state conflicts
    )

# Use the mutations in the second column
with col2:
    # Your custom content using selected_mutations
    pass
```

### Using Multiple Instances on One Page

If you need multiple instances of the component on a single page, use different `session_prefix` values to avoid conflicts in the session state:

```python
# First instance
with st.expander("Variant 1"):
    mutations1 = render_signature_composer(
        cov_spectrum,
        cov_spectrum_api,
        config={},
        session_prefix="v1_"
    )

# Second instance
with st.expander("Variant 2"):
    mutations2 = render_signature_composer(
        cov_spectrum,
        cov_spectrum_api,
        config={},
        session_prefix="v2_"
    )
```

## Examples

See the following files for examples:

1. `subpages/variant_signature_compose.py` - Full-featured implementation
2. `subpages/compact_variant_explorer.py` - Compact implementation

## Tips

- Use `session_prefix` when using multiple instances of the component to avoid session state conflicts
- For compact layouts, set `show_distributions` to False and use `slim_table: True`
- If you only need nucleotide mutations, set `show_nucleotides_only` to True
