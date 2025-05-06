"""This page allows to compose the list of variants and their respective mutational signatures.
    Steps: 
    1. Select the variants of interest with their respective signature mutations / or load a pre-defined signature mutation set
        1.1 For a variant, search for the signature mutaitons
        1.2 Or load a pre-defined signature mutation set
    2. Build the mutation-variant matrix
    3. Visualize the mutation-variant matrix
    4. Export and download the mutation-variant matrix and var_dates.yaml
"""

import streamlit as st
import yaml
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from pydantic import BaseModel, Field
from typing import List
from api.signatures import get_variant_list, get_variant_names
from api.covspectrum import CovSpectrumLapis
from components.variant_signature_component import render_signature_composer

# Import the Variant class from signatures but adapt it to our needs
from api.signatures import Variant as SignatureVariant
from api.signatures import VariantList as SignatureVariantList

# Define a simplified Variant class for this page
class Variant(BaseModel):
    """Model for a variant with its signature mutations.
    This is a simplified version of the Variant class from signatures.py.
    """
    name: str  # pangolin name
    signature_mutations: List[str]
    
    @classmethod
    def from_signature_variant(cls, signature_variant: SignatureVariant) -> "Variant":
        """Convert a signature Variant to our simplified Variant."""
        return cls(
            name=signature_variant.name,  # This is already the pangolin name
            signature_mutations=signature_variant.signature_mutations
        )


class VariantList(BaseModel):
    """Model for a list of variants."""
    variants: List[Variant] = []
    
    @classmethod
    def from_signature_variant_list(cls, signature_variant_list: SignatureVariantList) -> "VariantList":
        """Convert a signature VariantList to our simplified VariantList."""
        variant_list = cls()
        for signature_variant in signature_variant_list.variants:
            variant_list.add_variant(Variant.from_signature_variant(signature_variant))
        return variant_list
        
    def add_variant(self, variant: Variant):
        self.variants.append(variant)
        
    def remove_variant(self, variant: Variant):
        self.variants.remove(variant)


class ShowVariantList(BaseModel):
    """Model for showing and selecting variants from the available list."""
    variant_list: List[str] = Field(
        default=["LP.8", "XEC"], 
        description="Select Variants"
    )

# Cache the API calls to avoid unnecessary requests
@st.cache_data(ttl=3600)  # Cache for 1 hour
def cached_get_variant_list():
    """Cached version of get_variant_list to avoid repeated API calls."""
    return get_variant_list()

@st.cache_data(ttl=3600)  # Cache for 1 hour
def cached_get_variant_names():
    """Cached version of get_variant_names to avoid repeated API calls."""
    return get_variant_names()

def app():
    st.title("Multi Variant Signature Composer")

    st.write("This page will create the mutation-variant matrix.")
    st.write("This is one of the inputs to Lollipop")

    st.markdown("---")

    # Load configuration from config.yaml
    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)
    
    # Setup APIs
    cov_spectrum_api = config.get('server', {}).get('cov_spectrum_api', 'https://lapis.cov-spectrum.org')
    covSpectrum = CovSpectrumLapis(cov_spectrum_api)

    st.subheader("Variant Selection")
    st.write("Select the variants of interest from either the curated list or compose new signature on the fly from CovSpectrum.")
    
    # Initialize list to store all selected variants and their mutations
    combined_variants = VariantList()
    

    st.markdown("#### Curated Variant List")
    # Get the available variant names from the signatures API (cached)
    available_variants = cached_get_variant_names()
    
    # Create a multi-select box for variants
    selected_curated_variants = st.multiselect(
        "Select known variants of interest – curated by the V-Pipe team",
        options=available_variants,
        default=["LP.8"] if "LP.8" in available_variants else None,
        help="Select from the list of known variants. The signature mutations of these variants have been curated by the V-Pipe team"
    )
    
    # Add selected curated variants to the combined list
    if selected_curated_variants:
        # Load the full variant list (cached)
        signature_variant_list = cached_get_variant_list()
        
        # Filter to only include selected variants
        for variant in signature_variant_list.variants:
            if variant.name in selected_curated_variants:
                combined_variants.add_variant(Variant.from_signature_variant(variant))
    
    st.markdown("#### Compose Custom Variant")
    
    # Configure the component with compact functionality
    component_config = {
        'show_nucleotides_only': True,
        'slim_table': True,
        'show_distributions': False,
        'show_download': True,
        'show_plot': False,
        'title': "Custom Variant Composer",
        'show_title': False,
        'show_description': False,
        'default_variant': None,
        'default_min_abundance': 0.8,
        'default_min_coverage': 15
    }
    
    # Create a container for the component
    custom_container = st.container()
    
    # Render the variant signature component
    selected_mutations, _ = render_signature_composer(
        covSpectrum,
        cov_spectrum_api,
        component_config,
        session_prefix="custom_variant_",  # Use a prefix to avoid session state conflicts
        container=custom_container
    )
    
    # Add custom variant to the combined list if mutations were selected
    if selected_mutations:
        # Get the variant name from the input field
        variant_query = st.session_state.get("custom_variant_variantQuery", "Custom Variant")
        
        # Create and add the custom variant
        custom_variant = Variant(
            name=variant_query,
            signature_mutations=selected_mutations
        )
        combined_variants.add_variant(custom_variant)
        
        # Show confirmation
        st.success(f"Added custom variant '{variant_query}' with {len(selected_mutations)} mutations")

    # Combine all selected variants for processing
    selected_variants = [variant.name for variant in combined_variants.variants]

    if not selected_variants:
        st.warning("Please select at least one variant from either the curated list or create a custom variant")
        return

    # Build the mutation-variant matrix
    if combined_variants.variants:
        
        # Collect all unique mutations across selected variants
        all_mutations = set()
        for variant in combined_variants.variants:
            all_mutations.update(variant.signature_mutations)
        
        # Sort mutations for consistent display
        all_mutations = sorted(list(all_mutations))
        
        # Build the matrix
        # Create a DataFrame with mutations as rows and variants as columns
        matrix_data = []
        for mutation in all_mutations:
            row = [mutation]
            for variant in combined_variants.variants:
                # 1 if mutation is in variant's signature mutations, 0 otherwise
                row.append(1 if mutation in variant.signature_mutations else 0)
            matrix_data.append(row)
        
        # Create column names (variant names)
        columns = ["Mutation"] + [variant.name for variant in combined_variants.variants]
        
        # Create DataFrame
        matrix_df = pd.DataFrame(matrix_data, columns=columns)
        
        # Visualize the data in different ways
        if len(combined_variants.variants) > 1:
            import altair as alt
            
            # Create a matrix to show shared mutations between variants
            variant_names = [variant.name for variant in combined_variants.variants]
            variant_comparison = pd.DataFrame(index=variant_names, columns=variant_names)
            
            # For each pair of variants, count the number of shared mutations
            for i, variant1 in enumerate(combined_variants.variants):
                for j, variant2 in enumerate(combined_variants.variants):
                    # Get the sets of mutations for each variant
                    mutations1 = set(variant1.signature_mutations)
                    mutations2 = set(variant2.signature_mutations)
                    
                    # Count number of shared mutations
                    shared_count = len(mutations1.intersection(mutations2))
                    
                    # Store in the dataframe
                    variant_comparison.iloc[i, j] = shared_count
        
            # Make sure to convert numeric data to avoid potential rendering issues
            variant_comparison = variant_comparison.astype(int)
            variant_comparison_melted = variant_comparison.reset_index().melt(
                id_vars="index", 
                var_name="variant2", 
                value_name="shared_mutations"
            )
            variant_comparison_melted.columns = ["variant1", "variant2", "shared_mutations"]
            
            # Create a section with two visualizations side by side
            st.subheader("Variant Signature Comparison")
            
            # Create two columns for the visualizations
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Shared Mutations Heatmap")
                # Calculate the shared mutations for hover text
                shared_mutations_hover = {}
                for i, variant1 in enumerate(combined_variants.variants):
                    for j, variant2 in enumerate(combined_variants.variants):
                        mutations1 = set(variant1.signature_mutations)
                        mutations2 = set(variant2.signature_mutations)
                        shared = mutations1.intersection(mutations2)
                        shared_mutations_hover[(variant1.name, variant2.name)] = shared

                # Create hover text with shared mutations
                hover_text = []
                for i, variant1 in enumerate([v.name for v in combined_variants.variants]):
                    hover_row = []
                    for j, variant2 in enumerate([v.name for v in combined_variants.variants]):
                        count = variant_comparison.iloc[i, j]
                        shared = shared_mutations_hover.get((variant1, variant2), set())
                        
                        if variant1 == variant2:
                            text = f"<b>{variant1}</b><br>{count} signature mutations"
                        else:
                            text = f"<b>{variant1} ∩ {variant2}</b><br>{count} shared mutations"
                            if shared:
                                mutations_list = list(shared)
                                if len(mutations_list) > 10:
                                    text += f"<br>First 10 shared mutations:<br>• " + "<br>• ".join(mutations_list[:10]) + f"<br>...and {len(mutations_list)-10} more"
                                else:
                                    text += "<br>Shared mutations:<br>• " + "<br>• ".join(mutations_list)
                        
                        hover_row.append(text)
                    hover_text.append(hover_row)

                # Get min and max values for better color mapping
                min_val = variant_comparison.values.min()
                max_val = variant_comparison.values.max()
                
                # Create annotation text with adaptive text color
                annotations = []
                for i in range(len(variant_comparison.index)):
                    for j in range(len(variant_comparison.columns)):
                        value = variant_comparison.iloc[i, j]
                        # Normalize value between 0 and 1
                        normalized_val = (value - min_val) / (max_val - min_val) if max_val > min_val else 0
                        # Adjust threshold based on the Blues colorscale - text is white above this normalized value
                        text_color = "white" if normalized_val > 0.5 else "black"
                        
                        annotations.append(
                            dict(
                                x=j,
                                y=i,
                                text=str(value),
                                showarrow=False,
                                font=dict(color=text_color, size=14)
                            )
                        )

                # Determine size based on number of variants (square plot)
                size = max(350, min(500, 100 * len(combined_variants.variants)))

                # Create Plotly heatmap
                fig = go.Figure(data=go.Heatmap(
                    z=variant_comparison.values,
                    x=variant_comparison.columns,
                    y=variant_comparison.index,
                    colorscale='Blues',
                    text=hover_text,
                    hoverinfo='text',
                    showscale=False  # Remove colorbar/legend
                ))

                # Update layout
                fig.update_layout(
                    xaxis=dict(title='Variant', showgrid=False),
                    yaxis=dict(title='Variant', showgrid=False),
                    height=size,
                    width=size,
                    margin=dict(l=50, r=20, t=50, b=20),
                    annotations=annotations
                )

                # Display the interactive Plotly chart in Streamlit
                st.plotly_chart(fig)
            
            # Venn Diagram in the second column (only for 2-3 variants)
            with col2:
                if 2 <= len(combined_variants.variants) <= 3:
                    st.markdown("#### Mutation Overlap")
                    
                    # Matplotlib is already imported at the top
                    matplotlib.use('agg')  # Set non-interactive backend
                    
                    # Set a professional style for the plots
                    plt.style.use('seaborn-v0_8-whitegrid')  # Modern, clean style
                    
                    if len(combined_variants.variants) == 2:
                        from matplotlib_venn import venn2
                        
                        # Create sets of mutations for each variant
                        sets = [set(variant.signature_mutations) for variant in combined_variants.variants]
                        
                        # Create a more compact figure with better proportions
                        fig_venn, ax_venn = plt.subplots(figsize=(5, 4))
                        venn = venn2(sets, [variant.name for variant in combined_variants.variants], ax=ax_venn)
                        
                        # Adjust layout to be more compact
                        plt.tight_layout(pad=1.0)
                        
                        # Add a light gray border
                        for spine in ax_venn.spines.values():
                            spine.set_visible(True)
                            spine.set_color('#f0f0f0')
                        
                        # Display the venn diagram
                        st.pyplot(fig_venn)
                        
                    elif len(combined_variants.variants) == 3:
                        from matplotlib_venn import venn3
                        
                        # Create sets of mutations for each variant
                        sets = [set(variant.signature_mutations) for variant in combined_variants.variants]
                        
                        # Create a more compact figure with better proportions
                        fig_venn, ax_venn = plt.subplots(figsize=(5, 4))
                        venn = venn3(sets, [variant.name for variant in combined_variants.variants], ax=ax_venn)
                        
                        # Adjust layout to be more compact
                        plt.tight_layout(pad=1.0)
                        
                        # Add a light gray border
                        for spine in ax_venn.spines.values():
                            spine.set_visible(True)
                            spine.set_color('#f0f0f0')
                        
                        # Display the venn diagram
                        st.pyplot(fig_venn)
                else:
                    st.markdown("#### Mutation Overlap")
                    st.info("Venn diagram is only available for 2-3 variants")
            

            # 3. Mutation-Variant Matrix Visualization (heatmap) - Collapsible
            with st.expander("Variant-Signatures Bitmap Visualization", expanded=False):
                # Add debug information at the top of the expander
                if not variant_comparison_melted.empty:
                    st.write(f"Comparing {len(combined_variants.variants)} variants with {variant_comparison_melted['shared_mutations'].sum()} total shared mutations")
                
                st.write("This heatmap shows which mutations (rows) are present in each variant (columns). Blue cells indicate the mutation is present.")
                
                # First prepare the data in a suitable format
                binary_matrix = matrix_df.set_index("Mutation")
                
        
                # Use Plotly for a more interactive visualization
                fig = go.Figure(data=go.Heatmap(
                    z=binary_matrix.values,
                    x=binary_matrix.columns,
                    y=binary_matrix.index,
                    colorscale=[[0, 'white'], [1, '#1E88E5']],  # Match the color scheme
                    showscale=False,  # Hide color scale bar
                    hoverongaps=False
                ))
                
                # Customize layout
                fig.update_layout(
                    title='Mutation-Variant Matrix',
                    xaxis=dict(
                        title='Variant',
                        side='top',  # Show x-axis on top
                    ),
                    yaxis=dict(
                        title='Mutation',
                    ),
                    height=max(500, min(1200, 20 * len(all_mutations))),  # Dynamic height based on mutations
                    width=max(600, 100 * len(combined_variants.variants)),  # Dynamic width based on variants
                    margin=dict(l=100, r=20, t=60, b=20),  # Adjust margins for labels
                )
                
                # Add custom hover text
                hover_text = []
                for i, mutation in enumerate(binary_matrix.index):
                    row_hover = []
                    for j, variant in enumerate(binary_matrix.columns):
                        if binary_matrix.iloc[i, j] == 1:
                            text = f"Mutation: {mutation}<br>Variant: {variant}<br>Status: Present"
                        else:
                            text = f"Mutation: {mutation}<br>Variant: {variant}<br>Status: Absent"
                        row_hover.append(text)
                    hover_text.append(row_hover)
                
                fig.update_traces(hoverinfo='text', text=hover_text)
                
                # Display the interactive Plotly chart in Streamlit
                st.plotly_chart(fig, use_container_width=True)

    
        # Export functionality
        st.subheader("Export Data")
        
        # Convert to CSV for download
        csv = matrix_df.to_csv(index=False)
        st.download_button(
            label="Download Mutation-Variant Matrix (CSV)",
            data=csv,
            file_name="mutation_variant_matrix.csv",
            mime="text/csv",
        )
        
        # Also prepare a YAML for var_dates
        var_dates = {variant.name: "" for variant in combined_variants.variants}
        yaml_str = yaml.dump(var_dates, default_flow_style=False)
        
        st.download_button(
            label="Download var_dates.yaml Template",
            data=yaml_str,
            file_name="var_dates.yaml",
            mime="text/yaml",
        )

if __name__ == "__main__":
    app()