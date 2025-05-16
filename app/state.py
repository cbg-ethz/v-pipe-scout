"""
Session state management for the Multi Variant Signature Composer page.
"""
import streamlit as st
from typing import List

class VariantSignatureComposerState:
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
        
        # Main variant list
        if 'combined_variants_object' not in st.session_state:
            from subpages.variant_signature_composer import VariantList
            st.session_state.combined_variants_object = VariantList()
            
        # Selected curated variants
        if 'ui_selected_curated_names' not in st.session_state:
            from subpages.variant_signature_composer import cached_get_variant_names
            available_curated_names_init = cached_get_variant_names()
            st.session_state.ui_selected_curated_names = ["LP.8"] if "LP.8" in available_curated_names_init else []
    
    @staticmethod
    def get_combined_variants():
        """Get the current combined variants object."""
        return st.session_state.combined_variants_object
    
    @staticmethod
    def get_selected_curated_names() -> List[str]:
        """Get the list of currently selected curated variant names."""
        return st.session_state.ui_selected_curated_names
    
    @staticmethod
    def set_selected_curated_names(names: List[str]):
        """Update the selected curated variant names."""
        st.session_state.ui_selected_curated_names = names
    
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
