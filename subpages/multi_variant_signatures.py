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
from pydantic import BaseModel, Field
from typing import List
from api.signatures import get_variant_list, get_variant_names

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

    # Get the available variant names from the signatures API (cached)
    available_variants = cached_get_variant_names()
    
    # Create a multi-select box for variants
    selected_variants = st.multiselect(
        "Select known variants of interest – curated by the V-Pipe team",
        options=available_variants,
        default=["LP.8"] if "LP.8" in available_variants else None,
        help="Select one or more variants to include in the mutation matrix"
    )
    
    if not selected_variants:
        st.warning("Please select at least one variant")
        return

    # Load the full variant list (cached)
    signature_variant_list = cached_get_variant_list()
    
    # Filter to only include selected variants
    filtered_variants = VariantList()
    for variant in signature_variant_list.variants:
        if variant.name in selected_variants:
            filtered_variants.add_variant(Variant.from_signature_variant(variant))


    # Build the mutation-variant matrix
    if filtered_variants.variants:
        
        # Collect all unique mutations across selected variants
        all_mutations = set()
        for variant in filtered_variants.variants:
            all_mutations.update(variant.signature_mutations)
        
        # Sort mutations for consistent display
        all_mutations = sorted(list(all_mutations))
        
        # Build the matrix
        import pandas as pd
        
        # Create a DataFrame with mutations as rows and variants as columns
        matrix_data = []
        for mutation in all_mutations:
            row = [mutation]
            for variant in filtered_variants.variants:
                # 1 if mutation is in variant's signature mutations, 0 otherwise
                row.append(1 if mutation in variant.signature_mutations else 0)
            matrix_data.append(row)
        
        # Create column names (variant names)
        columns = ["Mutation"] + [variant.name for variant in filtered_variants.variants]
        
        # Create DataFrame
        matrix_df = pd.DataFrame(matrix_data, columns=columns)
        
        # Display the matrix
        # st.dataframe(matrix_df)
        
        # Visualize the data in different ways
        if len(filtered_variants.variants) > 1:
            import altair as alt
            
            # 1. Variant-to-Variant Comparison Heatmap (for 2+ variants)
            st.subheader("Variant-to-Variant Shared Mutations")
            
            # Create a matrix to show shared mutations between variants
            variant_names = [variant.name for variant in filtered_variants.variants]
            variant_comparison = pd.DataFrame(index=variant_names, columns=variant_names)
            
            # For each pair of variants, count the number of shared mutations
            for i, variant1 in enumerate(filtered_variants.variants):
                for j, variant2 in enumerate(filtered_variants.variants):
                    # Get the sets of mutations for each variant
                    mutations1 = set(variant1.signature_mutations)
                    mutations2 = set(variant2.signature_mutations)
                    
                    # Count number of shared mutations
                    shared_count = len(mutations1.intersection(mutations2))
                    
                    # Store in the dataframe
                    variant_comparison.iloc[i, j] = shared_count
            
            # Convert to long format for Altair
            variant_comparison_melted = variant_comparison.reset_index().melt(
                id_vars="index", 
                var_name="variant2", 
                value_name="shared_mutations"
            )
            variant_comparison_melted.columns = ["variant1", "variant2", "shared_mutations"]
            
            # Create a heatmap with text values
            base = alt.Chart(variant_comparison_melted).encode(
                x=alt.X('variant1:N', title='Variant'),
                y=alt.Y('variant2:N', title='Variant'),
            )
            
            # Heatmap
            heatmap = base.mark_rect().encode(
                color=alt.Color('shared_mutations:Q', 
                                title='Shared Mutations',
                                scale=alt.Scale(scheme='blues'))
            )
            
            # Text overlay
            text = base.mark_text(baseline='middle').encode(
                text='shared_mutations:Q',
                color=alt.condition(
                    alt.datum.shared_mutations > variant_comparison.mean().mean() * 1.5,
                    alt.value('white'),
                    alt.value('black')
                )
            )
            
            # Combine heatmap and text
            st.altair_chart(heatmap + text, use_container_width=True)
            
            # 2. Venn Diagram (only for 2-3 variants)
            if 2 <= len(filtered_variants.variants) <= 3:
                st.subheader("Mutation Overlap - Venn Diagram")
                
                import matplotlib.pyplot as plt
                import matplotlib
                matplotlib.use('agg')  # Use non-interactive backend
                
                # Set a professional style for the plots
                plt.style.use('seaborn-v0_8-whitegrid')  # Modern, clean style
                
                if len(filtered_variants.variants) == 2:
                    from matplotlib_venn import venn2
                    
                    # Create sets of mutations for each variant
                    sets = [set(variant.signature_mutations) for variant in filtered_variants.variants]
                    
                    # Create a more compact figure with better proportions
                    fig, ax = plt.subplots(figsize=(5, 3.5))
                    venn = venn2(sets, [variant.name for variant in filtered_variants.variants], ax=ax)
                    
                    # Adjust layout to be more compact
                    plt.tight_layout(pad=1.5)
                    
                    # Add a light gray border
                    for spine in ax.spines.values():
                        spine.set_visible(True)
                        spine.set_color('#f0f0f0')
                    
                    # Display the venn diagram in a container with a fixed width
                    col1, col2, col3 = st.columns([1, 3, 1])
                    with col2:
                        st.pyplot(fig)
                    
                elif len(filtered_variants.variants) == 3:
                    from matplotlib_venn import venn3
                    
                    # Create sets of mutations for each variant
                    sets = [set(variant.signature_mutations) for variant in filtered_variants.variants]
                    
                    # Create a more compact figure with better proportions
                    fig, ax = plt.subplots(figsize=(5, 3.5))
                    venn = venn3(sets, [variant.name for variant in filtered_variants.variants], ax=ax)
                    
                    # Adjust layout to be more compact
                    plt.tight_layout(pad=1.5)
                    
                    # Add a light gray border
                    for spine in ax.spines.values():
                        spine.set_visible(True)
                        spine.set_color('#f0f0f0')
                    
                    # Display the venn diagram in a container with a fixed width
                    col1, col2, col3 = st.columns([1, 3, 1])
                    with col2:
                        st.pyplot(fig)
            

            # 3. Mutation-Variant Matrix Visualization (heatmap)
            st.subheader("Variant-Signatures Bitmap Visualization")
            
            # Prepare data for heatmap - binary values (0 = Not Present, 1 = Present)
            heatmap_data = pd.melt(
                matrix_df, 
                id_vars=["Mutation"], 
                value_vars=[variant.name for variant in filtered_variants.variants],
                var_name="Variant", 
                value_name="Present"
            )
            
            # Create heatmap
            heatmap = alt.Chart(heatmap_data).mark_rect().encode(
                x=alt.X('Variant:N', title='Variant'),
                y=alt.Y('Mutation:N', title='Mutation'),
                color=alt.Color('Present:Q', scale=alt.Scale(domain=[0, 1], range=['#FFFFFF', '#1E88E5']))
            ).properties(
                width=500,
                height=min(1000, 20 * len(all_mutations))  # Dynamic height based on number of mutations
            )
            
            st.altair_chart(heatmap, use_container_width=True)
        
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
        import yaml
        var_dates = {variant.name: "" for variant in filtered_variants.variants}
        yaml_str = yaml.dump(var_dates, default_flow_style=False)
        
        st.download_button(
            label="Download var_dates.yaml Template",
            data=yaml_str,
            file_name="var_dates.yaml",
            mime="text/yaml",
        )

if __name__ == "__main__":
    app()