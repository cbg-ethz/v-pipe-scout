import streamlit as st
import pandas as pd
import logging

from datetime import datetime, date

from interface import MutationType
from api.wiseloculus import WiseLoculusLapis
from components.mutation_plot_component import render_mutation_plot_component
from utils.config import get_wiseloculus_url
from utils.url_state import create_url_state_manager
from process.mutations import possible_mutations_at_position, extract_position, validate_mutation

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


pd.set_option('future.no_silent_downcasting', True)

# Constants
MAX_MUTATIONS_LIMIT = 300
MAX_GENOMIC_POSITIONS_LIMIT = 100

# Get server configuration from centralized config
server_ip = get_wiseloculus_url()
wiseLoculus = WiseLoculusLapis(server_ip)


def app():
    # Initialize URL state manager for this page
    url_state = create_url_state_manager("region")
    
    st.title("Region Explorer")
    st.write("This page allows you to visualize a custom set or genomic range of mutations over time.")
    st.write("This feature may be useful for positions of interest or primer design and redesign.")
    st.markdown("---")
    
    # select mutation type - nucleotide or amino acid, mutli-selcted default to nucleotide
    url_mutation_type = url_state.load_from_url("mutation_type", "Nucleotide", str)
    mutation_type_options = ["Nucleotide", "Amino Acid"]
    mutation_type_index = mutation_type_options.index(url_mutation_type) if url_mutation_type in mutation_type_options else 0
    
    # Track previous mutation type to detect changes (use session state, not URL)
    previous_mutation_type = st.session_state.get("region_previous_mutation_type", None)
    
    logger.info(f"🔍 MUTATION TYPE - URL: {url_mutation_type}, Previous: {previous_mutation_type}")
    
    mutation_type = st.radio(
        "Select mutation type:",
        options=mutation_type_options,
        index=mutation_type_index
    )
    mutation_type_value = MutationType.NUCLEOTIDE if mutation_type == "Nucleotide" else MutationType.AMINO_ACID
    
    # Detect if user actively changed mutation type
    mutation_type_changed = previous_mutation_type is not None and mutation_type != previous_mutation_type
    st.session_state["region_previous_mutation_type"] = mutation_type
    
    logger.info(f"🔄 MUTATION TYPE CHANGE - Current: {mutation_type}, Changed: {mutation_type_changed}")
    
    # Save mutation type to URL
    url_state.save_to_url(mutation_type=mutation_type)

    # select mode - seleced mutations or genomic range
    url_mode = url_state.load_from_url("mode", "Custom Mutation Set", str)
    mode_options = ["Custom Mutation Set", "Genomic Ranges"]
    mode_index = mode_options.index(url_mode) if url_mode in mode_options else 0
    mode = st.radio(
        "Select mode:",
        options=mode_options,
        index=mode_index
    )
    
    logger.info(f"📋 MODE SELECTION - Selected: {mode}, URL: {url_mode}")
    
    # Save mode to URL
    url_state.save_to_url(mode=mode)

    # Initialize variables
    mutations = []

    # allow input by comma-separated list of mutations as free text that is then validated
    if mode == "Custom Mutation Set":
        logger.info(f"🧬 CUSTOM MUTATION SET - Starting logic for {mutation_type_value}")
        st.write("### Input Mutations")
        
        # Handle mutation input with smart defaults based on user interaction
        existing_mutation_input = url_state.load_from_url("mutation_input", None, str)
        
        if mutation_type_value == MutationType.NUCLEOTIDE:
            st.write("Enter a comma-separated list of nucleotide mutations (e.g., C43T, G96A, T456C).")
            st.write("Mutations should be in nucleotide format (e.g., A123T), you may also skip the reference base (e.g., 123T, 456-).")
            appropriate_default_mutations = "C43T, G96A, T456C"
        else:
            st.write("Enter a comma-separated list of amino acid mutations (e.g., ORF1a:T103L, S:N126K).")
            st.write("Mutations should include the gene name (e.g., ORF1a:T103L, S:N126K).")
            appropriate_default_mutations = "ORF1a:T103L, S:N126K"
        
        mutations_initialized = st.session_state.get("region_mutations_initialized", False)
        
        # Check if existing input is compatible with current mutation type
        existing_is_compatible = True
        if existing_mutation_input is not None:
            # Quick check: if we have amino acid mutations but are in nucleotide mode (or vice versa)
            sample_mutations = [mut.strip() for mut in existing_mutation_input.split(",") if mut.strip()][:2]  # Check first 2
            compatible_count = sum(1 for mut in sample_mutations if validate_mutation(mut, mutation_type_value))
            existing_is_compatible = len(sample_mutations) == 0 or compatible_count > 0
        
        # Logic for determining what to show in the text area:
        if mutation_type_changed and mutations_initialized:
            # User actively changed mutation type - always use new appropriate defaults
            url_mutation_input = appropriate_default_mutations
        elif existing_mutation_input is not None and not existing_is_compatible:
            # Existing input is incompatible with current mutation type - use appropriate defaults
            url_mutation_input = appropriate_default_mutations
        elif existing_mutation_input is not None and existing_is_compatible:
            # Loading from URL or preserving existing input - use what's there (if compatible)
            url_mutation_input = existing_mutation_input
        else:
            # No existing input or initialization - use appropriate defaults
            url_mutation_input = appropriate_default_mutations
        
        # Mark that mutations have been initialized (for detecting future changes)
        st.session_state["region_mutations_initialized"] = True
        
        mutation_input = st.text_area("Mutations:", value=url_mutation_input, height=100)
        
        # Save mutation input to URL
        url_state.save_to_url(mutation_input=mutation_input)
        
        # Split input into a list and strip whitespace
        input_mutations = [mut.strip() for mut in mutation_input.split(",") if mut.strip()]
        
        # Validate mutations
        valid_mutations = []
        invalid_mutations = []
        
        for i, mut in enumerate(input_mutations):
            is_valid = validate_mutation(mut, mutation_type_value)
            if is_valid:
                valid_mutations.append(mut)
            else:
                invalid_mutations.append(mut)
        
        mutations = valid_mutations
        
        # Show validation results
        if invalid_mutations:
            st.warning(f"Invalid mutations found and excluded: {', '.join(invalid_mutations)}")
        
        if mutations:
            st.info(f"Valid mutations: {len(mutations)} / {len(input_mutations)}")
        else:
            st.error("No valid mutations found. Please check your input format.")

    elif mode == "Genomic Ranges":
        logger.info(f"🧬 GENOMIC RANGES - Starting logic for {mutation_type_value}")
        st.write("### Input Genomic Ranges")
        st.write("Enter genomic ranges in the format 'start-end' (e.g., 100-200). You can enter multiple ranges separated by commas.")
        st.write("For amino acid mutations, please also specify the gene (e.g., ORF1a:100-200).")
        
        # Add guidance about mutation counts
        if mutation_type_value == MutationType.AMINO_ACID:
            st.info(f"💡 **Amino acid ranges**: Each position generates ~21 mutations (20 amino acids + deletion). You can use larger ranges (~14 positions max) to stay under the {MAX_MUTATIONS_LIMIT} mutation limit.")
        else:
            st.info("💡 **Nucleotide ranges**: Each position generates ~5 mutations (4 nucleotides + deletion). You can use larger ranges (~60 positions max).")
        
        # Handle genomic ranges with smart defaults based on user interaction
        existing_range_input = url_state.load_from_url("range_input", None, str)
        
        # Determine appropriate default ranges for current mutation type
        if mutation_type_value == MutationType.AMINO_ACID:
            appropriate_default = "ORF1a:20-25, S:34-40"
        elif mutation_type_value == MutationType.NUCLEOTIDE:
            appropriate_default = "100-120, 200-220"
        else:
            appropriate_default = ""
        
        
        ranges_initialized = st.session_state.get("region_ranges_initialized", False)
             
        # Check if existing input is compatible with current mutation type
        existing_is_compatible = True
        if existing_range_input is not None:
            # Quick check: amino acid ranges should have colons, nucleotide shouldn't need them
            if mutation_type_value == MutationType.AMINO_ACID:
                # For amino acid, we expect format like "ORF1a:20-25"
                ranges = [r.strip() for r in existing_range_input.split(",") if r.strip()]
                existing_is_compatible = all(':' in r for r in ranges)
            else:
                # For nucleotide, we expect format like "100-120" (no gene specification needed)
                ranges = [r.strip() for r in existing_range_input.split(",") if r.strip()]
                existing_is_compatible = True  # Nucleotide ranges are more flexible
               
        # Logic for determining what to show in the text area:
        if mutation_type_changed and ranges_initialized:
            # User actively changed mutation type - use new appropriate defaults
            url_range_input = appropriate_default
        elif existing_range_input is not None and existing_is_compatible:
            # Loading from URL or preserving existing input - use what's there (if compatible)
            url_range_input = existing_range_input
        else:
            # No existing input, incompatible input, or no mutation type change - use appropriate defaults
            url_range_input = appropriate_default
        
        # Mark that ranges have been initialized (for detecting future changes)
        st.session_state["region_ranges_initialized"] = True
        
        range_input = st.text_area("Genomic Ranges:", value=url_range_input, height=100)

        
        # Save range input to URL
        url_state.save_to_url(range_input=range_input)
        # Split input into a list and strip whitespace
        ranges = [r.strip() for r in range_input.split(",") if r.strip()]
        # Generate possible mutations for each range
        for r in ranges:
            try:
                gene = None
                # Check if it's amino acid with gene specification
                if mutation_type_value == MutationType.AMINO_ACID and ':' in r:
                    gene_part, range_part = r.split(':', 1)
                    gene = gene_part.strip()
                    r = range_part.strip()
                elif mutation_type_value == MutationType.AMINO_ACID:
                    st.warning(f"For amino acid mutations, please specify gene in format 'GENE:start-end'. Skipping range: {r}")
                    continue
                
                if '-' not in r:
                    st.warning(f"Invalid range format: {r}. Expected format is 'start-end'.")
                    continue
                start_str, end_str = r.split('-')
                start = int(start_str)
                end = int(end_str)
                if start >= end:
                    st.warning(f"Invalid range: {r}. Start should be less than end.")
                    continue
                
                for pos in range(start, end + 1):
                    possible_muts = possible_mutations_at_position(pos, mutation_type_value, gene, include_reference=False)
                    mutations.extend(possible_muts)
            except ValueError:
                st.warning(f"Invalid range format: {r}. Please ensure you enter valid integers for start and end.")
        # Remove duplicates and log statistics
        original_count = len(mutations)
        mutations = list(set(mutations))
        deduplicated_count = len(mutations)
        
        if original_count != deduplicated_count:
            st.info(f"Removed {original_count - deduplicated_count} duplicate mutations. Final count: {deduplicated_count}")
            
        if not mutations:
            st.warning("No valid mutations generated from the provided ranges.")


    st.markdown("---")
    # Allow the user to choose a date range
    st.write("Choose your data to inspect:")
    # Get dynamic date range from API with bounds to enforce limits
    default_start, default_end, min_date, max_date = wiseLoculus.get_cached_date_range_with_bounds("resistance_mutations")
    
    # Load date range from URL or use defaults
    url_start_date = url_state.load_from_url("start_date", default_start, date)
    url_end_date = url_state.load_from_url("end_date", default_end, date)
    
    date_range_input = st.date_input(
        "Select a date range:", 
        [url_start_date, url_end_date],
        min_value=min_date,
        max_value=max_date
    )

    # Ensure date_range is a tuple with two elements
    if len(date_range_input) != 2:
        st.error("Please select a valid date range with a start and end date.")
        return

    # Save date range to URL
    url_state.save_to_url(start_date=date_range_input[0], end_date=date_range_input[1])

    start_date = datetime.fromisoformat(date_range_input[0].strftime('%Y-%m-%d'))
    end_date = datetime.fromisoformat(date_range_input[1].strftime('%Y-%m-%d'))

    date_range = (start_date, end_date)

    ## Fetch locations from API
    default_locations = [
        "Zürich (ZH)",
    ]  # Define default locations
    
    # Fetch locations using cached session state
    if "locations" not in st.session_state:
        st.session_state.locations = wiseLoculus.fetch_locations(default_locations)
    locations = st.session_state.locations

    # Load location from URL or use default
    default_location = locations[0] if locations else ""
    url_location = url_state.load_from_url("location", default_location, str)
    
    # Make sure the URL location is still valid
    if url_location not in locations:
        url_location = default_location
    
    location_index = locations.index(url_location) if url_location in locations else 0
    location = st.selectbox("Select Location:", locations, index=location_index)
    
    # Save location to URL
    url_state.save_to_url(location=location)

    st.markdown("---")
    st.write(f"### Mutations in {mode} Over Time")
    st.write("Shows the mutations over time in wastewater for the selected date range.")

    # Add radio button for showing/hiding dates with no data
    url_show_empty = url_state.load_from_url("show_empty", "Show all dates", str)
    show_empty_dates = st.radio(
        "Date display options:",
        options=["Show all dates", "Skip dates with no coverage"],
        index=0 if url_show_empty == "Show all dates" else 1
    )
    
    # Save radio button selection to URL
    url_state.save_to_url(show_empty=show_empty_dates)
    if mutations not in (None, []):
        # Calculate unique genomic positions for display
        unique_positions = set()
        for mutation in mutations:
            pos = extract_position(mutation)
            if pos > 0:
                unique_positions.add(pos)
        
        total_genomic_sites = len(unique_positions)
        
        # Check if we need to limit the number of mutations/positions
        original_mutation_count = len(mutations)
        if original_mutation_count > MAX_MUTATIONS_LIMIT:
            st.warning(f"⚠️ You have requested {original_mutation_count} mutations. For performance reasons, we limit plots to {MAX_MUTATIONS_LIMIT} mutations maximum.")
            st.info("Suggestions:")
            st.info("• Reduce the size of your genomic ranges")
            st.info("• Use fewer ranges")
            st.info("• For nucleotide mutations: limit ranges to ~25 positions each")
            st.info("• For amino acid mutations: limit ranges to ~5 positions each")
            
            # Offer to show first {MAX_MUTATIONS_LIMIT} mutations
            if st.button("Show first {MAX_MUTATIONS_LIMIT} mutations anyway"):
                mutations = mutations[:MAX_MUTATIONS_LIMIT]
                st.info(f"Showing first {MAX_MUTATIONS_LIMIT} mutations out of {original_mutation_count} total.")
            else:
                return
        
        if total_genomic_sites > MAX_GENOMIC_POSITIONS_LIMIT:
            st.warning(f"⚠️ You have requested {total_genomic_sites} genomic positions. For performance reasons, we limit plots to {MAX_GENOMIC_POSITIONS_LIMIT} positions maximum.")
            st.info("Please reduce your genomic range to proceed with visualization.")
            return
        
        if mode == "Genomic Ranges":
            st.info(f"Processing {total_genomic_sites} genomic loci for visualization ({len(mutations)} total mutations). Note: Mutations are generated without reference bases (e.g., '100A' instead of 'C100A') since reference doesn't affect the analysis.")

        if mode == "Custom Mutation Set":
            st.info(f"Processing {len(mutations)} mutations for visualization ({total_genomic_sites} unique genomic positions).")

        with st.spinner("Fetching genomic regions data..."):

            # Configure the component for dynamic mutations
            plot_config = {
                'show_frequency_filtering': True,
                'show_date_options': True,
                'show_download': True,
                'show_summary_stats': True,
                'default_min_frequency': 0.0,
                'default_max_frequency': 1.0,
                'plot_title': "Mutations Over Time",
                'enable_empty_date_toggle': True,
                'show_mutation_count': True
            }
            
            # Use the mutation plot component
            result = render_mutation_plot_component(
                wiseLoculus=wiseLoculus,
                mutations=mutations,
                sequence_type=mutation_type_value,
                date_range=(start_date, end_date),
                location=location,
                config=plot_config,
                session_prefix="region_",
                url_state_manager=url_state
            )


    
    else:
        st.error("No valid mutations provided. Please input mutations or ranges to proceed.")
        return
    
if __name__ == "__main__":
    app()
