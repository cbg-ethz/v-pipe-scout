"""
Reusable component for variant signature composition.
This module provides functions to create a configurable variant signature composer
that can be embedded in different pages with custom configurations.
"""

import streamlit as st
import pandas as pd
import yaml
import io
import time
import matplotlib.pyplot as plt
from typing import List, Dict, Optional, Tuple, Any


def initialize_session_state(session_prefix: str = "") -> None:
    """Initialize the session state variables needed for the component."""
    if f'{session_prefix}last_change' not in st.session_state:
        st.session_state[f'{session_prefix}last_change'] = time.time()
    if f'{session_prefix}mutations' not in st.session_state:
        st.session_state[f'{session_prefix}mutations'] = []
    if f'{session_prefix}mutation_df' not in st.session_state:
        st.session_state[f'{session_prefix}mutation_df'] = pd.DataFrame()
    if f'{session_prefix}edit_mode' not in st.session_state:
        st.session_state[f'{session_prefix}edit_mode'] = False
    if f'{session_prefix}debounce_triggered' not in st.session_state:
        st.session_state[f'{session_prefix}debounce_triggered'] = False


def fetch_mutations(
    covSpectrum: Any,
    variant_query: str,
    sequence_type: str,
    min_abundance: float,
    min_coverage: int,
    session_prefix: str = ""
) -> None:
    """
    Fetch mutations from the API based on user input and update session state.
    
    Args:
        covSpectrum: CovSpectrumLapis instance
        variant_query: The variant to query (e.g., LP.8, B.1.617.2)
        sequence_type: Type of sequence to query (Nucleotides or Amino Acids)
        min_abundance: Minimal proportion for mutations
        min_coverage: Minimal coverage for mutations
        session_prefix: Optional prefix for session state keys to avoid conflicts
    """
    if not variant_query or not variant_query.strip():
        st.warning("Please enter a variant query before fetching mutations.")
        return
    try:
        mutation_data = covSpectrum.fetch_mutations(variant_query, sequence_type, min_abundance)
        df = pd.DataFrame(mutation_data)
        st.session_state[f'{session_prefix}last_fetched_df'] = df.copy()
        st.session_state[f'{session_prefix}has_fetched_mutations'] = True  # Set flag after first fetch
        
        if df.empty:
            st.session_state[f'{session_prefix}mutations'] = []
            st.session_state[f'{session_prefix}mutation_df'] = pd.DataFrame()
            st.error("No mutations found. This may be due to an invalid query or a server error. Please check your query and try again.\nIf you see errors in the console, please review the details or contact support.")
            return
        
        # Filter by min_coverage
        df = df[df['coverage'] >= min_coverage]
        muts = df['mutation'].tolist()
        st.session_state[f'{session_prefix}mutations'] = muts
        st.session_state[f'{session_prefix}mutation_df'] = pd.DataFrame({
            'Mutation': muts,
            'Selected': [True]*len(muts)
        })
    except Exception as e:
        st.session_state[f'{session_prefix}mutations'] = []
        st.session_state[f'{session_prefix}mutation_df'] = pd.DataFrame()
        st.session_state[f'{session_prefix}has_fetched_mutations'] = True  # Set flag even on error
        st.error(f"Failed to fetch mutations. Please check your query and try again.\nError details: {e}")


def render_signature_composer(
    covSpectrum: Any, 
    config: Optional[Dict],
    session_prefix: str = "",
    container = None
) -> Optional[Tuple[List[str], str]]:
    """
    Render a variant signature composer component in the provided container.
    
    Args:
        covSpectrum: CovSpectrumLapis instance
        config: Configuration dictionary with options:
            - show_nucleotides_only: Whether to only show nucleotide option
            - slim_table: Whether to show a slim version of the mutation table
            - show_distributions: Whether to show coverage/proportion distributions
            - show_download: Whether to show the download button 
            - default_variant: Default variant to query
            - default_min_abundance: Default minimal abundance
            - default_min_coverage: Default minimal coverage
        session_prefix: Optional prefix for session state keys to avoid conflicts
        container: Streamlit container to render in (optional)
    
    Returns:
        Tuple containing:
        - List of selected mutations if available, otherwise None
        - The sequence type value ("nucleotide" or "amino acid")
    """
    # Default configuration
    default_config = {
        'show_nucleotides_only': False,
        'slim_table': False,
        'show_distributions': True,
        'show_download': True,
        'show_plot': False, # Plot is removed, so default to False
        'default_variant': 'LP.8',
        'default_min_abundance': 0.8,
        'default_min_coverage': 15,
    }
    
    # Merge provided config with defaults
    if config is None:
        config = default_config
    else:
        for key, value in default_config.items():
            if key not in config:
                config[key] = value
    
    # Use provided container or main streamlit
    target = container if container is not None else st
    
    # Initialize session state with prefix
    initialize_session_state()

    # --- Fetch wrapper ---
    def fetch_mutations_wrapper():
        # Ensure variant_query is a string
        variant_query_str = str(variant_query) if variant_query is not None else ""
        fetch_mutations(
            covSpectrum, 
            variant_query_str, 
            sequence_type, 
            min_abundance, 
            min_coverage, 
            session_prefix
        )
    
    # --- UI controls ---
    variant_query = target.text_input(
        "Enter your CovSpectrum variant query (e.g., LP.8, B.1.617.2):", 
        config['default_variant'], 
        key=f'{session_prefix}variantQuery',
        help="Variant queries may use pango lineage queries (either called by pangolin or by Nextclade) "
             "and filter by Nextstrain clades e.g.: BA.5* | nextcladePangoLineage:BA.5* | nextstrainClade:22B, "
             "see https://lapis-docs.readthedocs.io/en/latest/concepts/variant_query.html#variantquery for details."
    )

    if config['show_nucleotides_only']:
        sequence_type = "Nucleotides"
        sequence_type_value = "nucleotide"
    else:
        sequence_type = target.selectbox(
            "Select Sequence Type:", 
            ["Nucleotides", "Amino Acids"],
            key=f'{session_prefix}sequence_type'
        )
        sequence_type_value = "amino acid" if sequence_type == "Amino Acids" else "nucleotide"

    min_abundance = target.slider(
        "Minimal Proportion (fraction of clinical sequences with this mutation in this variant):",
        0.0, 1.0, config['default_min_abundance'], 
        key=f'{session_prefix}min_abundance',
        help="This is the minimal fraction of clinical sequences assigned to this variant that must have the mutation for it to be included."
    )

    min_coverage = target.slider(
        "Minimal number of known clinical sequences with this mutation for this variant:", 
        0, 250, config['default_min_coverage'], 
        key=f'{session_prefix}min_coverage',
        help="This is the minimal number of clinical sequences for this variant that must have this mutation for it to be included. "
             "This is useful to filter out mutations that are not well supported by the data."
    )

    # --- Manual fetch button only ---
    if target.button("Fetch Mutations", key=f'{session_prefix}fetch_button'):
        fetch_mutations_wrapper()
    
    target.markdown(
        """
        Below are the mutations found for your selected variant and filters.\
        You can deselect mutations you don't want to include, or add extra ones by adding a new row in the table below.
        """
    )
    
    # --- Data editor for mutation selection ---
    selected_mutations = None
    mutation_df = st.session_state.get(f'{session_prefix}mutation_df', pd.DataFrame())
    expander_placeholder = target.empty()
    if not mutation_df.empty:
        # Add edit mode toggle only if table is shown
        if st.session_state.get(f'{session_prefix}edit_mode', False):
            if target.button('Done Editing', key=f'{session_prefix}done_edit'):
                st.session_state[f'{session_prefix}edit_mode'] = False
        else:
            if target.button('Edit Table', key=f'{session_prefix}edit_table'):
                st.session_state[f'{session_prefix}edit_mode'] = True

        # Try to get the last fetched DataFrame for extra columns
        df = st.session_state.get(f'{session_prefix}last_fetched_df', pd.DataFrame())

        # Merge coverage and proportion columns if available
        if not df.empty and 'mutation' in df.columns:
            cols = ['mutation']
            if 'coverage' in df.columns and not config['slim_table']:
                cols.append('coverage')
            if 'proportion' in df.columns and not config['slim_table']:
                cols.append('proportion')
            extra = df[cols].rename(columns={'mutation': 'Mutation'})
            merged = pd.merge(mutation_df, extra, on='Mutation', how='left')
            display_cols = ['Mutation', 'Selected']
            if 'coverage' in merged.columns and not config['slim_table']:
                display_cols.append('coverage')
            if 'proportion' in merged.columns and not config['slim_table']:
                display_cols.append('proportion')
            merged = merged[display_cols]
        else:
            merged = mutation_df

        target.info(f"{len(merged)} signature mutations found.")

        # Set disabled columns based on edit mode
        if st.session_state.get(f'{session_prefix}edit_mode', False):
            disabled_cols = []  # allow editing all
        else:
            disabled_cols = merged.columns.tolist()  # disable all columns

        # Use placeholder for expander to keep widget tree stable
        with expander_placeholder.expander("View and Edit Mutations", expanded=False):
            edited_df = target.data_editor(
                merged,
                num_rows="dynamic",
                use_container_width=True,
                key=f'{session_prefix}mutation_editor',
                disabled=disabled_cols,
            )

        st.session_state[f'{session_prefix}mutation_df'] = edited_df[[c for c in edited_df.columns if c in ['Mutation', 'Selected']]]

        # Fill NaN in 'Selected' with False to avoid ValueError when filtering
        edited_df['Selected'] = edited_df['Selected'].fillna(False)
        edited_df = edited_df.infer_objects(copy=False) # type: ignore
        selected_mutations = edited_df[edited_df['Selected']]['Mutation'].tolist()
    else:
        expander_placeholder.empty()
        if st.session_state.get(f'{session_prefix}has_fetched_mutations', False):
            # Only show info message, do not show expander
            target.info("No mutations found. Adjust your filters or add mutations manually.")
    
    # --- Only show coverage/proportion plots after first query ---
    if config['show_distributions'] and f'{session_prefix}last_fetched_df' in st.session_state:
        render_distribution_plots(target, session_prefix)
    
    # --- Option to download mutation signature as YAML ---
    if config['show_download'] and selected_mutations and not st.session_state[f'{session_prefix}mutation_df'].empty:
        # Prepare YAML content
        yaml_dict = {variant_query: selected_mutations}
        yaml_str = yaml.dump(yaml_dict, sort_keys=False, allow_unicode=True)
        yaml_bytes = io.BytesIO(yaml_str.encode('utf-8'))
        
        target.download_button(
            label="Download mutation signature as YAML",
            data=yaml_bytes,
            file_name=f"{variant_query}_signature.yaml",
            mime="application/x-yaml",
            key=f'{session_prefix}download_button'
        )
    
    return selected_mutations, sequence_type_value


def render_distribution_plots(target, session_prefix: str = ""):
    """Render coverage and proportion distribution plots."""
    target.markdown('---')
    target.markdown("### [CovSpectrum]: Clinical Sequences Available – Statistics")
    target.info(
        """
        These statistics are meant to help calibrate the above filters and are for all sequences found globally on CovSpectrum.\n\n
        **Coverage Distribution:** Mutation count to number of clinical sequences for that given variant that have it.\n
        **Proportion Distribution:** Mutation count to fraction of clinical sequences for that given variant that have it.
        """
    )

    # Try to use the last mutation DataFrame if available
    mutation_df = st.session_state.get(f'{session_prefix}mutation_df', pd.DataFrame())

    # Use the original DataFrame if available (for coverage/proportion columns)
    if f'{session_prefix}mutation_data_df' in st.session_state:
        df = st.session_state[f'{session_prefix}mutation_data_df']
    else:
        df = None

    # Try to get the DataFrame from the last fetch
    if df is None or df.empty:
        if f'{session_prefix}last_fetched_df' in st.session_state:
            df = st.session_state[f'{session_prefix}last_fetched_df']

    if df is None or df.empty:
        df = mutation_df

    # Prepare columns for separate plots
    col1, col2 = target.columns(2)
    # Remove plot_style and blue background for a cleaner look

    # Coverage Distribution Plot
    with col1:
        if not df.empty and 'coverage' in df.columns:
            fig1, ax1 = plt.subplots(figsize=(5, 3))
            ax1.hist(df['coverage'].dropna(), bins=20, color='#1E88E5', edgecolor='white', alpha=0.9)
            ax1.set_title('Coverage Distribution', fontsize=14, fontweight='light')
            ax1.set_xlabel('Number of Clinical Sequences', fontsize=12)
            ax1.set_ylabel('Mutation Count', fontsize=12)
            ax1.grid(axis='y', linestyle=':', alpha=0.5)
            # No custom facecolor for a cleaner look
            target.pyplot(fig1, use_container_width=True)
        else:
            target.info('No coverage data available.')

    # Proportion Distribution Plot
    with col2:
        if not df.empty and 'proportion' in df.columns:
            fig2, ax2 = plt.subplots(figsize=(5, 3))
            ax2.hist(df['proportion'].dropna(), bins=20, color='#FFA726', edgecolor='white', alpha=0.9)
            ax2.set_title('Proportion Distribution', fontsize=14, fontweight='light')
            ax2.set_xlabel('Fraction of Clinical Sequences', fontsize=12)
            ax2.set_ylabel('Mutation Count', fontsize=12)
            ax2.grid(axis='y', linestyle=':', alpha=0.5)
            # No custom facecolor for a cleaner look
            target.pyplot(fig2, use_container_width=True)
        else:
            target.info('No proportion data available.')

    target.markdown("---")
