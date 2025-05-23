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
import plotly.graph_objects as go
import plotly.express as px 
from pydantic import BaseModel, Field
from typing import List
import re
import logging
import os
import json
import pickle  
import base64 
from celery import Celery
import redis


from api.signatures import get_variant_list, get_variant_names
from api.signatures import Mutation
from api.covspectrum import CovSpectrumLapis
from api.wiseloculus import WiseLoculusLapis
from components.variant_signature_component import render_signature_composer
from state import VariantSignatureComposerState
from api.signatures import Variant as SignatureVariant
from api.signatures import VariantList as SignatureVariantList


# Initialize Celery
celery_app = Celery(
    'tasks',
    broker=os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
)

# Initialize Redis client for checking task status
redis_client = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'redis'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    db=0
)


class Variant(BaseModel):
    """
    Model for a variant with its signature mutations.
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
    """Model for a simplified list of variants."""
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


@st.cache_data(ttl=3600)  # Cache for 1 hour
def cached_get_variant_list():
    """Cached version of get_variant_list to avoid repeated API calls."""
    return get_variant_list()

@st.cache_data(ttl=3600)  # Cache for 1 hour
def cached_get_variant_names():
    """Cached version of get_variant_names to avoid repeated API calls."""
    return get_variant_names()

def app():
    # ============== INITIALIZATION ==============
    # Initialize all session state variables
    VariantSignatureComposerState.initialize()
    
    # Apply clearing flag for manual inputs if needed
    VariantSignatureComposerState.apply_clear_flag()
    
    # Create a reference to the persistent variant list
    combined_variants = VariantSignatureComposerState.get_combined_variants()
    
    # Check if we need to handle first-time loading of variants
    # If the combined list is empty and we have selected curated names, register them
    if not combined_variants.variants and VariantSignatureComposerState.get_selected_curated_names():
        selected_names = VariantSignatureComposerState.get_selected_curated_names()
        all_curated_variants = cached_get_variant_list().variants
        curated_variant_map = {v.name: v for v in all_curated_variants}
        
        for name in selected_names:
            if name in curated_variant_map and not VariantSignatureComposerState.is_variant_registered(name):
                variant_to_add = curated_variant_map[name]
                from state import VariantSource
                VariantSignatureComposerState.register_variant(
                    name=variant_to_add.name,
                    signature_mutations=variant_to_add.signature_mutations,
                    source=VariantSource.CURATED
                )
        
        # Refresh the combined variants after registering
        combined_variants = VariantSignatureComposerState.get_combined_variants()
    
    # ============== UI HEADER ==============
    # Now start the UI
    st.title("Rapid Variant Abundance Estimation")
    st.subheader("Compose the list of variants and their respective mutational signatures, then estimate their abundance in recent wastewater.")
    st.write("This page allows you to select variants of interest and their respective signature mutations.")
    st.write("You can either select from a curated list, compose a custom variant signature with live queries to CovSpectrum or manually input the mutations.")
    st.write("The selected variants will be used to build a mutation-variant matrix.")
    st.write("Fetch counts and coverage for these mutaitons.")
    st.write("And finally, estimate the abundance of the variants in the wastewater data.")

    st.markdown("---")

    # ============== CONFIGURATION ==============
    # Load configuration from config.yaml
    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)
    
    # Setup APIs
    cov_spectrum_api = config.get('server', {}).get('cov_spectrum_api', 'https://lapis.cov-spectrum.org')
    covSpectrum = CovSpectrumLapis(cov_spectrum_api)

    # ============== VARIANT SELECTION ==============
    st.subheader("Variant Selection")
    st.write("Select the variants of interest from either the curated list or compose new signature on the fly from CovSpectrum.")
    
    # combined_variants is already initialized from session state

    # --- Curated Variants Section ---
    st.markdown("#### Curated Variant List")
    # Get the available variant names from the signatures API (cached)
    available_variants = cached_get_variant_names()
    
    # Create a multi-select box for variants
    selected_curated_variants = st.multiselect(
        "Select known variants of interest – curated by the V-Pipe team",
        options=available_variants,
        default=VariantSignatureComposerState.get_selected_curated_names(),
        help="Select from the list of known variants. The signature mutations of these variants have been curated by the V-Pipe team (see https://github.com/cbg-ethz/cowwid/tree/master/voc)"
    )
    
    # Update the session state if the selection has changed
    if selected_curated_variants != VariantSignatureComposerState.get_selected_curated_names():
        VariantSignatureComposerState.set_selected_curated_names(selected_curated_variants)
        
        # Force immediate registration of selected variants
        all_curated_variants = cached_get_variant_list().variants
        curated_variant_map = {v.name: v for v in all_curated_variants}
        
        # First, unregister any curated variants that are no longer selected
        from state import VariantSource
        registered_variants = VariantSignatureComposerState.get_registered_variants()
        for variant_name, variant_data in list(registered_variants.items()):
            if variant_data['source'] == VariantSource.CURATED and variant_name not in selected_curated_variants:
                VariantSignatureComposerState.unregister_variant(variant_name)
        
        # Then register all newly selected variants
        for name in selected_curated_variants:
            if name in curated_variant_map and not VariantSignatureComposerState.is_variant_registered(name):
                variant_to_add = curated_variant_map[name]
                signature_variant = Variant.from_signature_variant(variant_to_add)
                VariantSignatureComposerState.register_variant(
                    name=signature_variant.name,
                    signature_mutations=signature_variant.signature_mutations,
                    source=VariantSource.CURATED
                )
        
        st.rerun()
    
    # Sync the combined_variants with selected curated variants
    # First, remove any curated variants that are no longer selected
    all_curated_variants = cached_get_variant_list().variants
    curated_names = {v.name for v in all_curated_variants}
    
    # Get custom variant names to avoid removing them
    from state import VariantSource
    custom_variant_names = {
        variant_data['name'] 
        for variant_data in VariantSignatureComposerState.get_registered_variants().values()
        if variant_data['source'] in [VariantSource.CUSTOM_COVSPECTRUM, VariantSource.CUSTOM_MANUAL]
    }
    
    # Create a copy of the list to safely iterate and remove
    variants_to_remove = []
    for v in combined_variants.variants:
        # Only remove curated variants that are no longer selected
        # Make sure NOT to remove custom variants here
        if v.name in curated_names and v.name not in selected_curated_variants and v.name not in custom_variant_names:
            variants_to_remove.append(v)
    
    # Now perform the removal
    for v in variants_to_remove:
        # Remove from the registry first - this is the single source of truth
        VariantSignatureComposerState.unregister_variant(v.name)
        
    # Then add newly selected curated variants if they're not already in the combined list
    if selected_curated_variants:
        # Build a map of name to variant object for quick lookup
        existing_variant_names = {v.name for v in combined_variants.variants}
        curated_variant_map = {v.name: v for v in all_curated_variants}
        
        for name in selected_curated_variants:
            if name not in existing_variant_names and name in curated_variant_map:
                variant_to_add = curated_variant_map[name]
                signature_variant = Variant.from_signature_variant(variant_to_add)
                
                # Register in the unified registry first
                from state import VariantSource
                VariantSignatureComposerState.register_variant(
                    name=signature_variant.name,
                    signature_mutations=signature_variant.signature_mutations,
                    source=VariantSource.CURATED
                )
    
    # ============== CUSTOM VARIANT CREATION ==============
    st.markdown("#### Compose Custom Variant")
    st.markdown("##### by selecting Signature Mutations from CovSpectrum")
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
    result = render_signature_composer(
        covSpectrum,
        component_config,
        session_prefix="custom_variant_",  
        container=custom_container
    )
    if result is not None:
        selected_mutations, _ = result
    else:
        selected_mutations = []


    # make button to add custom variant
    st.button("Add Custom Variant", key="add_custom_variant_button")
    # Check if the button was clicked
    if st.session_state.get("add_custom_variant_button", False):
        # Check if any mutations were selected
        if not selected_mutations:
            st.warning("Please select at least one mutation to create a custom variant.")
        else:
            # Show the selected mutations
            st.write("Selected Signature Mutations:")
            variant_query = st.session_state.get("custom_variant_variantQuery", "Custom Variant")
            
            # Check if the variant is already registered
            if VariantSignatureComposerState.is_variant_registered(variant_query):
                st.warning(f"Variant '{variant_query}' already exists in the list. Please choose a different name.")
            else:
                
                # Register directly in the variant registry
                from state import VariantSource
                VariantSignatureComposerState.register_variant(
                    name=variant_query,
                    signature_mutations=selected_mutations,
                    source=VariantSource.CUSTOM_COVSPECTRUM
                )
                
                # Add to the UI tracking for custom variants
                custom_selected = VariantSignatureComposerState.get_selected_custom_names()
                if variant_query not in custom_selected:
                    custom_selected.append(variant_query)
                    VariantSignatureComposerState.set_selected_custom_names(custom_selected)
                
                logging.info(f"Added custom variant '{variant_query}' with {len(selected_mutations)} mutations.")
                
                # Show confirmation
                st.success(f"Added custom variant '{variant_query}' with {len(selected_mutations)} mutations")
                
                # Trigger a rerun to immediately update the UI with the new variant
                st.rerun()
    
    # --- Manual Input Section ---
    with st.expander("##### Or Manual Input", expanded=False):
        manual_variant_name = st.text_input(
            "Variant Name", 
            value="", 
            max_chars=20,  # Increased max_chars slightly
            placeholder="Enter unique variant name", 
            key="manual_variant_name_input"
        )
        manual_mutations_input_str = st.text_area(
            "Signature Mutations", 
            value="", 
            placeholder="e.g., C345T, 456-, 748G", 
            help="Enter mutations separated by commas. Format: [REF]Position[ALT]. REF is optional (e.g., for insertions like 748G or deletions like 456-).",
            key="manual_mutations_input"
        )

        if st.button("Add Manual Variant", key="add_manual_variant_button"):
            # Validate variant name
            if not manual_variant_name.strip():
                st.error("Manual Variant Name cannot be empty.")
            else:
                # Process mutations
                mutations_str_list = [m.strip() for m in manual_mutations_input_str.split(',') if m.strip()]
                
                validated_signature_mutations = []
                all_mutations_valid = True

                if not mutations_str_list:
                    st.warning(f"No mutations entered for '{manual_variant_name}'. It will be added with an empty signature if the name is unique.")
                
                for mut_str in mutations_str_list:
                    # Use the improved validation method from the Mutation class
                    is_valid, error_message, mutation_data = Mutation.validate_mutation_string(mut_str)
                    
                    if is_valid:
                        validated_signature_mutations.append(mut_str) # Store original valid string
                    else:
                        st.error(f"Invalid mutation: {error_message}")
                        all_mutations_valid = False

                if all_mutations_valid:
                    # Check if the variant is already registered
                    if VariantSignatureComposerState.is_variant_registered(manual_variant_name):
                        st.warning(f"Variant '{manual_variant_name}' already exists in the list. Please choose a different name.")
                    else:
                        
                        # Register directly in the variant registry
                        from state import VariantSource
                        VariantSignatureComposerState.register_variant(
                            name=manual_variant_name,
                            signature_mutations=validated_signature_mutations,
                            source=VariantSource.CUSTOM_MANUAL
                        )
                        
                        # Add to the UI tracking for custom variants
                        custom_selected = VariantSignatureComposerState.get_selected_custom_names()
                        if manual_variant_name not in custom_selected:
                            custom_selected.append(manual_variant_name)
                            VariantSignatureComposerState.set_selected_custom_names(custom_selected)
                        
                        st.success(f"Added manual variant '{manual_variant_name}' with {len(validated_signature_mutations)} mutations.")
                        # Set flag to clear inputs on next rerun
                        VariantSignatureComposerState.clear_manual_inputs()
                        st.rerun() # Trigger rerun
    
    # ============== VARIANT VALIDATION AND PROCESSING ==============
    
    # Only show warning if combined_variants.variants is empty AND we've already loaded data
    if not combined_variants.variants and VariantSignatureComposerState.get_registered_variants():
        st.warning("Please select at least one variant from either the curated list or create a custom variant")
    
    st.markdown("---")
    
    # ============== SELECTED VARIANTS MANAGEMENT ==============
    st.subheader("Selected Variants")
    
    # Get the current variants for display
    current_variant_names = [variant.name for variant in combined_variants.variants]
    
    if current_variant_names:
        # Create a multiselect showing current variants (user can deselect to remove)
        displayed_variant_names = st.multiselect(
            "Currently Selected Variants (Deselect to remove)",
            options=current_variant_names,
            default=current_variant_names,  # Always default to show all current variants
            help="Deselect variants to remove them from the list."
        )
        
        # Check if any variants were deselected
        variants_removed = False
        all_removed = False
        
        # Get reference to state for tracking
        curated_selected = VariantSignatureComposerState.get_selected_curated_names()
        custom_selected = VariantSignatureComposerState.get_selected_custom_names()
        
        for variant in combined_variants.variants:
            if variant.name not in displayed_variant_names:
                # Remove from unified variant registry
                VariantSignatureComposerState.unregister_variant(variant.name)
                
                # Also remove from UI tracking lists
                if variant.name in curated_selected:
                    curated_selected.remove(variant.name)
                    VariantSignatureComposerState.set_selected_curated_names(curated_selected)
                
                if variant.name in custom_selected:
                    custom_selected.remove(variant.name)
                    VariantSignatureComposerState.set_selected_custom_names(custom_selected)
                
                st.success(f"Removed variant '{variant.name}' from the list.")
                variants_removed = True
        
        # If all variants were deselected, handle this special case
        if not displayed_variant_names and current_variant_names:
            all_removed = True
            # Clear all registries
            for name in current_variant_names:
                VariantSignatureComposerState.unregister_variant(name)
            
            # Clear UI tracking lists
            VariantSignatureComposerState.set_selected_curated_names([])
            VariantSignatureComposerState.set_selected_custom_names([])
            st.warning("All variants were removed. Please select new variants from the curated list or create custom variants.")
        
        # If variants were removed, rerun to update the UI
        if variants_removed or all_removed:
            st.rerun()
    else:
        st.info("No variants are currently selected. Select variants from the Curated Variant List or create Custom Variants above.")
    
    # ============== VARIANT DEBUG INFO (EXPANDABLE) ==============
    with st.expander("🔍 Variant Selection Information", expanded=False):
        st.write("**Currently Selected Variants:**")
        
        registered_variants = VariantSignatureComposerState.get_registered_variants()
        if registered_variants:
            for variant_name, variant_data in registered_variants.items():
                col1, col2, col3 = st.columns([2, 1, 3])
                with col1:
                    st.write(f"**{variant_name}**")
                with col2:
                    # Display the source as a nicely formatted string
                    source_display = variant_data['source'].value.replace('_', ' ').title()
                    st.write(f"*{source_display}*")
                with col3:
                    st.write(f"{len(variant_data['signature_mutations'])} mutations")
        else:
            st.write("No custom variants registered")
        
    # ============== MUTATION-VARIANT MATRIX ==============
    st.markdown("---")
    
    if not combined_variants.variants:
        st.info("Select at least one variant to see the mutation-variant matrix and visualizations.")
        
    # Build the mutation-variant matrix
    elif combined_variants.variants:
        
        # Collect all unique mutations across selected variants
        all_mutations = set()
        for variant in combined_variants.variants:
            all_mutations.update(variant.signature_mutations)
        
        # Sort mutations for consistent display
        all_mutations = sorted(list(all_mutations))
        
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

        # Extract the position number from mutation strings for sorting
        def extract_position(mutation_str):
            # Use the same regex pattern from Mutation.validate_mutation_string
            match = re.match(r"^([ACGTN]?)(\d+)([ACGTN-])$", mutation_str.upper())
            if match:
                return int(match.group(2))  # Return the position as integer
            return 0  # Fallback if regex fails
        
        # Sort mutations by position number
        matrix_data.sort(key=lambda x: extract_position(x[0]), reverse=True)  # Sort by position in descending order
        
        # Sort columns alphabetically by variant name, but keep "Mutation" as the first column
        variant_columns = columns[1:]  # Skip the "Mutation" column
        variant_columns.sort()  # Sort alphabetically
        columns = ["Mutation"] + variant_columns
        
        # Create DataFrame
        matrix_df = pd.DataFrame(matrix_data, columns=columns)
        
        # Create a section with two visualizations side by side
        
        # ============== VARIANT SIGNATURE COMPARISON ==============
        st.subheader("Variant Signature Comparison")

        # Visualize the data in different ways
        if len(combined_variants.variants) > 1:
            
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
                        set1 = set(combined_variants.variants[0].signature_mutations)
                        set2 = set(combined_variants.variants[1].signature_mutations)
            
                        # Create a more compact figure with better proportions
                        fig_venn, ax_venn = plt.subplots(figsize=(5, 4))
                        
                        # Fix the typing issue by explicitly creating a tuple of exactly 2 elements
                        variant_name1 = combined_variants.variants[0].name
                        variant_name2 = combined_variants.variants[1].name
                        variant_labels = (variant_name1, variant_name2)
                        
                        venn2((set1, set2), variant_labels, ax=ax_venn)
                        
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
                        
                        # Create sets of mutations for each variant - extract exactly 3 sets as required by venn3
                        set1 = set(combined_variants.variants[0].signature_mutations)
                        set2 = set(combined_variants.variants[1].signature_mutations)
                        set3 = set(combined_variants.variants[2].signature_mutations)
                        
                        # Create a more compact figure with better proportions
                        fig_venn, ax_venn = plt.subplots(figsize=(5, 4))
                        
                        # Fix the typing issue by explicitly creating a tuple of exactly 3 elements
                        variant_name1 = combined_variants.variants[0].name
                        variant_name2 = combined_variants.variants[1].name
                        variant_name3 = combined_variants.variants[2].name
                        variant_labels = (variant_name1, variant_name2, variant_name3)
                        
                        venn3((set1, set2, set3), variant_labels, ax=ax_venn)
                        
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

                # Calculate dimensions based on data size
                num_mutations = len(binary_matrix.index)
                num_variants = len(binary_matrix.columns)

                # Customize layout with settings to ensure all labels are visible
                fig.update_layout(
                    title='Mutation-Variant Matrix',
                    xaxis=dict(
                        title='Variant',
                        side='top',  # Show x-axis on top
                    ),
                    yaxis=dict(
                        title='Mutation',
                        automargin=True,  # Automatically adjust margins for labels
                        tickmode='array',  # Force all ticks
                        tickvals=list(range(len(binary_matrix.index))),  # Positions for each mutation
                        ticktext=binary_matrix.index,  # Actual mutation labels
                    ),
                    height=max(500, min(2000, 25 * num_mutations)),  # Dynamic height based on mutations
                    width=max(600, 120 * num_variants),  # Dynamic width based on variants
                    margin=dict(l=150, r=20, t=50, b=20),  # Increase left margin for y labels
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
        else:
            st.warning("At least two variants are required to visualize the mutation-variant matrix.")
    
        # ============== EXPORT FUNCTIONALITY ==============
        # Export functionality
        st.subheader("Export Variant Signatures")
        
        if combined_variants.variants:
            # Convert to CSV for download
            csv = matrix_df.to_csv(index=False)
            st.download_button(
                label="Download Mutation-Variant Matrix (CSV)",
                data=csv,
                file_name="mutation_variant_matrix.csv",
                mime="text/csv",
            )
        else:
            st.info("Select at least one variant to enable export functionality.")
        
        st.markdown("---")

        # ============== DATA FETCHING ==============
        st.subheader("Download Mutation Counts and Coverage")

        with st.expander("Fetch and download mutation counts and coverage data", expanded=False):
            st.write("You can download the mutation counts and coverage data for the selected mutations over a specified date range and location.")
            st.write("This data is fetched from the the Loculus Wastewater Instance and can be used for further analysis, such as tracking variant prevalence over time.")
            st.write("Please specify the date range for the data.")
            # Date range input
            date_range = st.date_input(
            "Select Date Range",
            value=[pd.to_datetime("2025-02-10"), pd.to_datetime("2025-03-8")],
            min_value=pd.to_datetime("2025-01-01"),
            max_value=pd.to_datetime("2025-05-31"),
            help="Select the date range for which you want to fetch mutation counts and coverage data."
            )
            
            server_ip = config.get('server', {}).get('lapis_address', 'http://default_ip:8000')
            wiseLoculus = WiseLoculusLapis(server_ip)

            # Fetch locations using the new function
            if "locations" not in st.session_state:
                st.session_state.locations = wiseLoculus.fetch_locations()
            locations = st.session_state.locations
            location = st.selectbox("Select Location:", locations)

            # Add a button to trigger fetching
            if st.button("Fetch Data"):
                # Get the latest mutation list
                mutations = matrix_df["Mutation"].tolist()
                
                with st.spinner('Fetching mutation counts and coverage data...'):
                    # Store the result in session state
                    st.session_state.counts_df3d = wiseLoculus.fetch_counts_and_coverage_3D_df_nuc(
                    mutations,
                    date_range,
                    location
                    )
                st.success("Data fetched successfully!")
                
            # Only show download buttons if data exists
            if 'counts_df3d' in st.session_state and st.session_state.counts_df3d is not None:
                # Create columns for download buttons
                col1, col2 = st.columns(2)
                
                # 1. CSV Download
                with col1:
                    # Make sure to preserve index for dates and mutations
                    csv = st.session_state.counts_df3d.to_csv(index=True)
                    st.download_button(
                    label="Download as CSV",
                    data=csv,
                    file_name='mutation_counts_coverage.csv',
                    mime='text/csv',
                    help="Download all data as a single CSV file with preserved indices."
                    )
                
                # 2. JSON Download
                with col2:
                    # Convert to JSON structure - using 'split' format to preserve indices
                    json_data = st.session_state.counts_df3d.to_json(orient='split', date_format='iso', index=True)
                    
                    st.download_button(
                    label="Download as JSON",
                    data=json_data,
                    file_name='mutation_counts_coverage.json',
                    mime='application/json',
                    help="Download data as a JSON file that preserves dates and mutation indices."
                    )

        # Create a separate section for Variant Abundance Estimation
        st.markdown("---")

        # ============== VARIANT ABUNDANCE ESTIMATION ==============
        st.subheader("Estimate Variant Abundances")
        
        # Add information about LolliPop
        st.markdown("Processing is done with **LolliPop - a tool for Deconvolution for Wastewater Genomics**", 
            help="LolliPop has been developed to improve wastewater-based genomic surveillance as the number of variants of concern increased and to account for shared mutations among variants. It relies on a kernel-based deconvolution, and leverages the time series nature of the samples. This approach enables to generate higher confidence relative abundance curves despite the very high noise and overdispersion present in wastewater samples.")
        
        # Check if data has been fetched
        if 'counts_df3d' not in st.session_state or st.session_state.counts_df3d is None:
            st.warning("Please fetch mutation counts and coverage data first in the section above before estimating variant abundances.")
        else:
            bootstraps = st.slider("Number of Bootstrap Iterations", 
                                min_value=0, max_value=300, value=10, step=10)
            
            mutation_counts_df = st.session_state.counts_df3d
            mutation_variant_matrix_df = matrix_df

            # Initialize task ID in session state if not present
            if 'deconv_task_id' not in st.session_state:
                st.session_state.deconv_task_id = None
            
            if 'deconv_result' not in st.session_state:
                st.session_state.deconv_result = None

            # Button logic depends on whether we already have results
            if st.session_state.deconv_result is not None:
                # If we have results, show a "Start New Deconvolution" button instead
                if st.button("Start New Deconvolution", help="Clear current results and start a new deconvolution"):
                    # Clear both the task ID and result to reset the workflow
                    st.session_state.deconv_task_id = None
                    st.session_state.deconv_result = None
                    # Also clear any data hash to force recomputation
                    if 'last_data_hash' in st.session_state:
                        del st.session_state.last_data_hash
                    st.rerun()  # Rerun to show the parameters and Run Deconvolution button
            else:
                # Only show Run Deconvolution button if we don't have results yet
                if st.button("Run Deconvolution"):
                    with st.spinner('Starting deconvolution task...'):
                        # Convert DataFrames to base64-encoded pickle strings for serialization
                        counts_pickle = base64.b64encode(pickle.dumps(mutation_counts_df)).decode('utf-8')
                        matrix_pickle = base64.b64encode(pickle.dumps(mutation_variant_matrix_df)).decode('utf-8')
                        
                        # Submit the task to Celery worker
                        task = celery_app.send_task(
                            'tasks.run_deconvolve',
                            kwargs={
                                'mutation_counts_df': counts_pickle,
                                'mutation_variant_matrix_df': matrix_pickle,
                                'bootstraps': bootstraps
                            }
                        )
                        # Store task ID in session state
                    st.session_state.deconv_task_id = task.id
                    st.success(f"Deconvolution started! Task ID: {task.id}")

            # Display task status and results
            if st.session_state.deconv_task_id:
    
                    task_id = st.session_state.deconv_task_id
                    
                    # Check if we already have results
                    if st.session_state.deconv_result is not None:
                        st.success("Deconvolution completed!")
                        
                        # Parse and visualize the deconvolution results
                        result_data = st.session_state.deconv_result
                        
                        # Get the location (for now, we just use the first location key)
                        if result_data and len(result_data) > 0:
                            location = list(result_data.keys())[0]
                            variants_data = result_data[location]
                            
                            # Create a figure for visualization
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
                            
                            # Plot each variant
                            for i, (variant_name, variant_data) in enumerate(variants_data.items()):
                                timeseries = variant_data.get('timeseriesSummary', [])
                                if not timeseries:
                                    continue
                                
                                # Extract dates and proportions
                                dates = [pd.to_datetime(point['date']) for point in timeseries]
                                all_dates.extend(dates)
                                proportions = [point['proportion'] for point in timeseries]
                                lower_bounds = [point.get('proportionLower', point['proportion']) for point in timeseries]
                                upper_bounds = [point.get('proportionUpper', point['proportion']) for point in timeseries]
                                
                                color_idx = i % len(colors)
                                
                                # Add line plot for this variant
                                fig.add_trace(go.Scatter(
                                    x=dates,
                                    y=proportions,
                                    mode='lines+markers',
                                    line=dict(color=colors[color_idx], width=2),
                                    name=variant_name
                                ))
                                
                                # Add shaded confidence interval using the exact same color as the line
                                color = colors[color_idx]
                                # Convert to rgba with 0.2 opacity - keeping the exact same color
                                if color.startswith('#'):
                                    # Convert hex to rgb
                                    r = int(color[1:3], 16) / 255
                                    g = int(color[3:5], 16) / 255
                                    b = int(color[5:7], 16) / 255
                                    rgba_color = f'rgba({r:.3f}, {g:.3f}, {b:.3f}, 0.2)'
                                else:
                                    # Handle other color formats (rgb, rgba, etc.)
                                    # Strip any existing rgba/rgb format and extract the color values
                                    if color.startswith('rgb'):
                                        # Extract the RGB values from the string
                                        rgb_values = color.replace('rgb(', '').replace('rgba(', '').replace(')', '').split(',')
                                        if len(rgb_values) >= 3:
                                            r = float(rgb_values[0].strip()) / 255 if float(rgb_values[0].strip()) > 1 else float(rgb_values[0].strip())
                                            g = float(rgb_values[1].strip()) / 255 if float(rgb_values[1].strip()) > 1 else float(rgb_values[1].strip())
                                            b = float(rgb_values[2].strip()) / 255 if float(rgb_values[2].strip()) > 1 else float(rgb_values[2].strip())
                                            rgba_color = f'rgba({r:.3f}, {g:.3f}, {b:.3f}, 0.2)'
                                        else:
                                            rgba_color = f'rgba(0, 0, 0, 0.2)'  # Default as fallback
                                    else:
                                        # For any other format, use a default transparency
                                        rgba_color = f'{color.split(")")[0]}, 0.2)' if ')' in color else f'rgba(0, 0, 0, 0.2)'
                                
                                fig.add_trace(go.Scatter(
                                    x=dates + dates[::-1],  # Forward then backwards
                                    y=upper_bounds + lower_bounds[::-1],  # Upper then lower bounds
                                    fill='toself',
                                    fillcolor=rgba_color,
                                    line=dict(color='rgba(0,0,0,0)'),
                                    hoverinfo="skip",
                                    showlegend=False
                                ))
                            
                            # Update layout
                            fig.update_layout(
                                title=f"Variant Proportion Estimates",
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
                            
                            # Display the plot
                            st.plotly_chart(fig, use_container_width=True)
                            
                            
                            # Optionally add CSV download for the timeseries data
                            st.write("Download variant timeseries data:")
                            
                            # Prepare data for CSV export
                            all_variant_data = []
                            for variant_name, variant_data in variants_data.items():
                                for point in variant_data.get('timeseriesSummary', []):
                                    all_variant_data.append({
                                        'variant': variant_name,
                                        'date': point['date'],
                                        'proportion': point['proportion'],
                                        'proportionLower': point.get('proportionLower', ''),
                                        'proportionUpper': point.get('proportionUpper', '')
                                    })
                            
                            if all_variant_data:
                                col1, col2 = st.columns(2)
                                with col1:
                                        csv_data = pd.DataFrame(all_variant_data).to_csv(index=False)
                                        st.download_button(
                                            label="Download Results as CSV",
                                            data=csv_data,
                                            file_name='deconvolution_results.csv',
                                            mime='text/csv',
                                        )
                                with col2:
                                    # Add download button for the JSON data
                                    json_data = json.dumps(result_data, indent=2)
                                    st.download_button(
                                        label="Download Results as JSON",
                                        data=json_data,
                                        file_name='deconvolution_results.json',
                                        mime='application/json',
                                    )
                        else:
                            st.warning("No results data available to visualize.")
                    else:
                        # Check task status with spinner
                        with st.spinner("Checking deconvolution task status..."):
                            # First check if the task is completed
                            task = celery_app.AsyncResult(task_id)
                            if task.ready():
                                try:
                                    # Task is complete - get the result and store it
                                    result = task.get()
                                    st.session_state.deconv_result = result
                                    st.success("Deconvolution completed!")
                                    # Rerun to show the visualization immediately
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error retrieving result: {str(e)}")
                            
                            # If task is not ready yet, show progress
                            progress_key = f"task_progress:{task_id}"
                            progress_data = redis_client.get(progress_key)
                            
                            if progress_data:
                                # Parse progress data from Redis
                                progress_info = json.loads(progress_data) # type: ignore
                                # ignore as redis 5.0.1 typing sucks, see https://github.com/redis/redis-py/issues/2933
                                current = progress_info.get('current', 0)
                                total = progress_info.get('total', 1) 
                                status = progress_info.get('status', 'Processing...')
                                
                                # Display progress bar
                                st.progress(current / total)
                                st.write(f"Status: {status}")
                        
                        st.write("You can check if the deconvolution task has completed.")
                        
                        # Add information about auto-refresh
                        st.write("""
                        The page will automatically check for results every 5 seconds.
                        You can also manually check if the results are ready using the button below.
                        """)
                        
                        # Import the streamlit-autorefresh component
                        from streamlit_autorefresh import st_autorefresh
                        
                        # Set up auto-refresh every 5 seconds (5000 ms)
                        # This will automatically rerun the app without showing a countdown
                        st_autorefresh(interval=5000, key="autorefresh")
                        
                        # Check result button
                        check_col1, check_col2 = st.columns([1, 3])
                        with check_col1:
                            if st.button("Check Result"):
                                with st.spinner('Checking if results are ready...'):
                                    task = celery_app.AsyncResult(task_id)
                                    if task.ready():
                                        try:
                                            result = task.get()
                                            st.session_state.deconv_result = result
                                            st.success("Deconvolution completed!")
                                            # The visualization will be shown on the next rerun
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error retrieving result: {str(e)}")
                                    else:
                                        st.info("Task is still running. Please check again later.")
            
if __name__ == "__main__":
    app()