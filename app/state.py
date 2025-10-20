"""
Session state management for the Multi Variant Signature Composer page.
"""
import streamlit as st
from typing import List, Dict, Any
from enum import Enum

class VariantSource(Enum):
    """Enum to identify the source of a variant."""
    CURATED = "curated"
    CUSTOM_COVSPECTRUM = "custom_covspectrum"
    CUSTOM_MANUAL = "custom_manual"

class AbundanceEstimatorState:
    """
    Manages the session state for the Multi Variant Signature Composer page.
    Centralizes access to all session variables related to variant selection,
    manual inputs, and composition state.
    """
    
    @staticmethod
    def initialize():
        """Initialize all session state variables if they don't exist."""
        # Manual input fields
        if "manual_variant_name_input" not in st.session_state:
            st.session_state.manual_variant_name_input = ""
        
        if "manual_mutations_input" not in st.session_state:
            st.session_state.manual_mutations_input = ""
        
        if "clear_manual_inputs_flag" not in st.session_state:
            st.session_state.clear_manual_inputs_flag = False
            
        # Unified variant tracking with source information
        is_new_registry = 'variant_registry' not in st.session_state
        if is_new_registry:
            st.session_state.variant_registry = {}
            
        # Selected curated variants (for backward compatibility and UI state)
        if 'ui_selected_curated_names' not in st.session_state:
            default_variants = []
            st.session_state.ui_selected_curated_names = default_variants
        
        # Selected custom variants (for UI state)
        if 'ui_selected_custom_names' not in st.session_state:
            st.session_state.ui_selected_custom_names = []
            
        # If this is a first-time initialization AND we have selected variants,
        # make sure they're registered in the registry
        if is_new_registry:
            selected_curated = st.session_state.ui_selected_curated_names
            if selected_curated:
                try:
                    from subpages.abundance import cached_get_variant_list
                    curated_variants = cached_get_variant_list().variants
                    curated_variant_map = {v.name: v for v in curated_variants}
                    
                    for name in selected_curated:
                        if name in curated_variant_map:
                            variant = curated_variant_map[name]
                            AbundanceEstimatorState.register_variant(
                                name=variant.name,
                                signature_mutations=variant.signature_mutations,
                                source=VariantSource.CURATED
                            )
                except Exception as e:
                    # Don't fail initialization if data loading fails
                    # This can happen during imports or startup before API is ready
                    st.radio(
                        f"Error loading curated variants. Please try again later: {e}",
                        options=["OK"],
                        index=0,
                        key="error_loading_curated_variants"
                    )
                    pass
    
    # ============== UNIFIED VARIANT MANAGEMENT ==============
    
    @staticmethod
    def register_variant(name: str, signature_mutations: List[str], source: VariantSource):
        """Register a variant in the unified registry with source tracking."""
        st.session_state.variant_registry[name] = {
            'name': name,
            'signature_mutations': signature_mutations,
            'source': source
        }
    
    @staticmethod
    def unregister_variant(name: str):
        """Remove a variant from the unified registry."""
        if name in st.session_state.variant_registry:
            del st.session_state.variant_registry[name]
    
    @staticmethod
    def get_registered_variants() -> Dict[str, Dict[str, Any]]:
        """Get all registered variants with their source and mutation information."""
        return st.session_state.variant_registry
    
    @staticmethod
    def get_variants_by_source(source: VariantSource) -> List[Dict[str, Any]]:
        """Get variants filtered by source."""
        return [variant for variant in st.session_state.variant_registry.values() 
                if variant['source'] == source]
    
    @staticmethod
    def is_variant_registered(name: str) -> bool:
        """Check if a variant is already registered."""
        return name in st.session_state.variant_registry
    

    @staticmethod
    def get_combined_variants():
        """
        Get the current combined variants object.
        
        This method dynamically constructs a VariantList from the variant registry,
        eliminating the need for redundant storage.
        """
        from subpages.abundance import Variant, VariantList
        
        # Create a new VariantList instance
        combined_variants = VariantList()
        
        # Add all variants from the registry to the combined variants list
        for variant_name, variant_data in st.session_state.variant_registry.items():
            variant = Variant(
                name=variant_data['name'],
                signature_mutations=variant_data['signature_mutations']
            )
            combined_variants.add_variant(variant)
            
        return combined_variants
    
    @staticmethod
    def get_selected_curated_names() -> List[str]:
        """Get the list of currently selected curated variant names."""
        return st.session_state.ui_selected_curated_names
    
    @staticmethod
    def set_selected_curated_names(names: List[str]):
        """Update the selected curated variant names."""
        st.session_state.ui_selected_curated_names = names
    
    # ============== CUSTOM VARIANT MANAGEMENT ==============
    
    @staticmethod
    def get_selected_custom_names() -> List[str]:
        """Get the list of currently selected custom variant names."""
        if 'ui_selected_custom_names' not in st.session_state:
            st.session_state.ui_selected_custom_names = []
        return st.session_state.ui_selected_custom_names
    
    @staticmethod
    def set_selected_custom_names(names: List[str]):
        """Update the selected custom variant names."""
        st.session_state.ui_selected_custom_names = names
    
    # ============== MANUAL INPUT MANAGEMENT ==============
    
    @staticmethod
    def clear_manual_inputs():
        """Set flag to clear manual input fields on next rerun."""
        st.session_state.clear_manual_inputs_flag = True
    
    @staticmethod
    def apply_clear_flag():
        """Apply the clearing flag for manual inputs if set."""
        if st.session_state.clear_manual_inputs_flag:
            st.session_state.manual_variant_name_input = ""
            st.session_state.manual_mutations_input = ""
            st.session_state.clear_manual_inputs_flag = False  # Reset the flag
            
    @staticmethod
    def get_manual_variant_name() -> str:
        """Get the current manual variant name input."""
        return st.session_state.manual_variant_name_input
    
    @staticmethod
    def get_manual_mutations() -> str:
        """Get the current manual mutations input."""
        return st.session_state.manual_mutations_input
