# URL State Management and Sharing

V-Pipe Scout now supports URL-based session state management, allowing users to share their current page configuration via URL links.

## Overview

The URL state management system enables users to:
- **Share configurations**: Send URLs that preserve current settings
- **Bookmark states**: Save specific analysis configurations
- **Resume sessions**: Return to previous analysis setups
- **Collaborate**: Share analysis setups with colleagues

## Supported Pages and Parameters

### Resistance Mutations Page (`/resistance`)
- **resistance_set**: Selected resistance mutation set (3CLpro Inhibitors, RdRP Inhibitors, Spike mAbs)
- **start_date**: Analysis start date
- **end_date**: Analysis end date  
- **location**: Selected location/region
- **show_empty**: Display option for dates with no data

Example URL: `http://localhost:8888/resistance?resistance_start_date=2024-02-01&resistance_end_date=2024-03-01&resistance_location=Zürich (ZH)&resistance_resistance_set=3CLpro Inhibitors`

### Untracked Mutations Page (`/untracked`)
- **start_date**: Analysis start date
- **end_date**: Analysis end date
- **location**: Selected location/region
- **variants**: List of variants to exclude from analysis

Example URL: `http://localhost:8888/untracked?untracked_start_date=2024-02-01&untracked_end_date=2024-03-01&untracked_location=Zürich (ZH)&untracked_variants=LP.8,JN.1`

### Variant Signature Explorer Page (`/signature-explorer`)
- **start_date**: Analysis start date
- **end_date**: Analysis end date
- **location**: Selected location/region

Example URL: `http://localhost:8888/signature-explorer?signature_start_date=2024-02-01&signature_end_date=2024-03-01&signature_location=Zürich (ZH)`

## Technical Implementation

### URL State Manager (`utils/url_state.py`)

The URL state management is implemented through the `URLStateManager` class, which provides:

- **Data Type Support**: Handles strings, lists, dates, booleans, and numbers
- **URL-Safe Encoding**: Converts complex data types to URL-safe strings
- **Page Prefixes**: Prevents parameter conflicts between different pages
- **Backward Compatibility**: URLs without parameters still work normally

### Usage in Pages

```python
from utils.url_state import create_url_state_manager

def app():
    # Initialize URL state manager for this page
    url_state = create_url_state_manager("page_name")
    
    # Load parameter from URL with default fallback
    selected_option = url_state.load_from_url("option", "default_value", str)
    
    # Create UI component with loaded value
    selected_option = st.selectbox("Select option:", options, 
                                   index=options.index(selected_option))
    
    # Save current selection to URL
    url_state.save_to_url(option=selected_option)
```

## Data Type Encoding

- **Strings**: Direct URL encoding
- **Lists**: Comma-separated for simple string lists, base64 JSON for complex lists
- **Dates**: ISO format (YYYY-MM-DD)
- **Booleans**: "true"/"false" strings
- **Numbers**: String representation

## Best Practices

1. **Selective Parameters**: Only include parameters that are meaningful to share
2. **Default Fallbacks**: Always provide sensible defaults for missing parameters
3. **Validation**: Validate URL parameters against current valid options
4. **URL Length**: Be mindful of URL length limitations (keep under 2000 characters)

## Limitations

- **Complex State**: Very complex UI state may not be fully captured
- **URL Length**: Browser URL length limits may truncate very long parameter lists
- **API Dependencies**: Some parameters depend on current API data availability
- **Session-Specific Data**: User-generated content (custom variants) may not persist

## Future Enhancements

- Support for additional pages (abundance estimator, proportion search)
- Compressed parameter encoding for complex configurations
- URL shortening service integration
- Export/import of analysis configurations