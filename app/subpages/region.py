import streamlit as st
import pandas as pd

from datetime import datetime

from interface import MutationType
from api.wiseloculus import WiseLoculusLapis
from components.mutation_plot_component import render_mutation_plot_component
from utils.config import get_wiseloculus_url
from process.mutations import get_symbols_for_mutation_type, possible_mutations_at_position, extract_position, validate_mutation


pd.set_option('future.no_silent_downcasting', True)


# Get server configuration from centralized config
server_ip = get_wiseloculus_url()
wiseLoculus = WiseLoculusLapis(server_ip)


def app():
    mutations = []
    st.title("Region Explorer")
    st.write("This page allows you to visualize a custom set or genomic range of mutations over time.")
    st.write("This feature may be useful for positions of interest or primer design and redesign.")
    st.markdown("---")
    
    # select mutation type - nucleotide or amino acid, mutli-selcted default to nucleotide
    mutation_type = st.radio(
        "Select mutation type:",
        options=["Nucleotide", "Amino Acid"],
        index=0  # Default to Nucleotide
    )
    mutation_type_value = MutationType.NUCLEOTIDE if mutation_type == "Nucleotide" else MutationType.AMINO_ACID

    # select mode - seleced mutations or genomic range
    mode = st.radio(
        "Select mode:",
        options=["Custom Mutation Set", "Genomic Ranges"],
        index=0  # Default to "Custom Mutation Set"
    )

    # Initialize variables
    mutations = []

    # allow input by comma-separated list of mutations as free text that is then validated
    if mode == "Custom Mutation Set":
        st.write("### Input Mutations")
        if mutation_type_value == MutationType.NUCLEOTIDE:
            st.write("Enter a comma-separated list of nucleotide mutations (e.g., C43T, G96A, T456C).")
            st.write("Mutations should be in nucleotide format (e.g., A123T), you may also skip the reference base (e.g., 123T, 456-).")
            mutation_input = st.text_area("Mutations:", value="C43T, G96A, T456C", height=100)
        else:
            st.write("Enter a comma-separated list of amino acid mutations (e.g., ORF1a:T103L, S:N126K).")
            st.write("Mutations should include the gene name (e.g., ORF1a:T103L, S:N126K).")
            mutation_input = st.text_area("Mutations:", value="ORF1a:T103L, S:N126K", height=100)
        
        # Split input into a list and strip whitespace
        input_mutations = [mut.strip() for mut in mutation_input.split(",") if mut.strip()]
        
        # Validate mutations
        valid_mutations = []
        invalid_mutations = []
        
        for mut in input_mutations:
            if validate_mutation(mut, mutation_type_value):
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
        st.write("### Input Genomic Ranges")
        st.write("Enter genomic ranges in the format 'start-end' (e.g., 100-200). You can enter multiple ranges separated by commas.")
        st.write("For amino acid mutations, please also specify the gene (e.g., ORF1a:100-200).")
        range_input = st.text_area("Genomic Ranges:", value="100-105, 200-204", height=100)
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
                    possible_muts = possible_mutations_at_position(pos, mutation_type_value, gene)
                    mutations.extend(possible_muts)
            except ValueError:
                st.warning(f"Invalid range format: {r}. Please ensure you enter valid integers for start and end.")
        # Remove duplicates
        mutations = list(set(mutations))
        if not mutations:
            st.warning("No valid mutations generated from the provided ranges.")


    st.markdown("---")
    # Allow the user to choose a date range
    st.write("Choose your data to inspect:")
    # Get dynamic date range from API with bounds to enforce limits
    default_start, default_end, min_date, max_date = wiseLoculus.get_cached_date_range_with_bounds("resistance_mutations")
    date_range_input = st.date_input(
        "Select a date range:", 
        [default_start, default_end],
        min_value=min_date,
        max_value=max_date
    )

    # Ensure date_range is a tuple with two elements
    if len(date_range_input) != 2:
        st.error("Please select a valid date range with a start and end date.")
        return

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

    location = st.selectbox("Select Location:", locations)

    st.markdown("---")
    st.write("### Resistance Mutations Over Time")
    st.write("Shows the mutations over time in wastewater for the selected date range.")

    # Add radio button for showing/hiding dates with no data
    show_empty_dates = st.radio(
        "Date display options:",
        options=["Show all dates", "Skip dates with no coverage"],
        index=0  # Default to showing all dates (off)
    )
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
        if original_mutation_count > 300:
            st.warning(f"⚠️ You have requested {original_mutation_count} mutations. For performance reasons, we limit plots to 300 mutations maximum.")
            st.info("Suggestions:")
            st.info("• Reduce the size of your genomic ranges")
            st.info("• Use fewer ranges")
            st.info("• For nucleotide mutations: limit ranges to ~25 positions each")
            st.info("• For amino acid mutations: limit ranges to ~5 positions each")
            
            # Offer to show first 100 mutations
            if st.button("Show first 100 mutations anyway"):
                mutations = mutations[:300]
                st.info(f"Showing first 300 mutations out of {original_mutation_count} total.")
            else:
                return
        
        if total_genomic_sites > 100:
            st.warning(f"⚠️ You have requested {total_genomic_sites} genomic positions. For performance reasons, we limit plots to 100 positions maximum.")
            st.info("Please reduce your genomic range to proceed with visualization.")
            return
        
        if mode == "Genomic Ranges":
            st.success(f"Processing {total_genomic_sites} genomic loci for visualization ({len(mutations)} total mutations). Note the number of mutations we query is times 4 by nucleotides and times 20 by amino acids.")

        if mode == "Custom Mutation Set":
            st.success(f"Processing {len(mutations)} mutations for visualization ({total_genomic_sites} unique genomic positions).")

        with st.spinner("Fetching genomic regions data..."):

            # Configure the component for dynamic mutations
            plot_config = {
                'show_frequency_filtering': True,
                'show_date_options': True,
                'show_download': True,
                'show_summary_stats': True,
                'default_min_frequency': 0.0,
                'default_max_frequency': 1.0,
                'plot_title': f"Mutations by Proportion Over Time",
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
                session_prefix="dynamic_"
            )


    
    else:
        st.error("No valid mutations provided. Please input mutations or ranges to proceed.")
        return
    
if __name__ == "__main__":
    app()
