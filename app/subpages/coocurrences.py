import streamlit as st
import pandas as pd
import logging
from datetime import datetime

from interface import MutationType
from api.wiseloculus import WiseLoculusLapis
from utils.config import get_wiseloculus_url
from utils.url_state import create_url_state_manager
from process.mutations import validate_mutation
from visualize.mutations import proportions_heatmap


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pd.set_option('future.no_silent_downcasting', True)

MAX_MUTATIONS_LIMIT = 80  # keep URL state manageable


server_ip = get_wiseloculus_url()
wiseLoculus = WiseLoculusLapis(server_ip)


def app():
    url_state = create_url_state_manager("complex")

    st.title("Co-occurrence of Mutations Over Time")
    st.write("Track a **set of mutations** (AND filter) or an **advanced query** over time to see the proportion of reads matching the criteria.")
    st.info("💡 This differs from other pages: here mutations are combined as a filter, not tracked individually.")
    st.info("""⚠️ **Coverage Definition:**
    Number of reads with valid calls (non-N) at all specified positions (Simple Mode) or satisfying the query logic (Advanced Mode).
    """)
    st.markdown("---")

    # Fixed to nucleotide only for now
    mutation_type_value = MutationType.NUCLEOTIDE

    # Query Mode Selection
    st.write("### Query Input")
    
    # Load mode from URL or default to Simple
    default_mode = "Simple"
    url_mode = url_state.load_from_url("query_mode", default_mode, str)
    
    # Ensure valid mode
    if url_mode not in ["Simple", "Advanced"]:
        url_mode = "Simple"
        
    query_mode = st.radio("Query Mode:", ["Simple", "Advanced"], index=0 if url_mode == "Simple" else 1, horizontal=True)
    url_state.save_to_url(query_mode=query_mode)

    valid_mutations = []
    advanced_query = None
    
    if query_mode == "Simple":
        st.caption("Comma-separated nucleotide mutations (AND logic). Example: `23149T, 23224T`")
        
        with st.expander("ℹ️ Mutation Format Examples", expanded=False):
            st.markdown("""
            **Examples:**
            - `A23403G`: the reference genome has an A at the 23403th position, and this query is looking for sequences which has instead a G at that position
            - `23403G`: this is equivalent to the previous one
            - `23403`: the 23403th position is mutated; in other words, it does not have the same base as the reference genome and it is not unknown
            - `23403.`: the 23403th position is not mutated, i.e., it has the same base as the reference genome
            - `23403-`: the 23403th position is deleted
            - `23403N`: the 23403th position is unknown
            
            For more details, see [CoV-Spectrum documentation](https://cov-spectrum.org/about#faq-search-variants).
            """)
        
        default_mut = "23149T, 23224T, 23311T, 23403G, 23436G"
        url_mut_input = url_state.load_from_url("mutation_input", default_mut, str)
        mutation_input = st.text_area("Mutations | Deletions (nucleotide only):", value=url_mut_input, height=100)
        url_state.save_to_url(mutation_input=mutation_input if mutation_input and len(mutation_input) < 1500 else None)

        raw_mutations = [m.strip() for m in (mutation_input or "").split(',') if m.strip()]
        invalid_mutations = []
        for m in raw_mutations:
            if validate_mutation(m, mutation_type_value):
                valid_mutations.append(m)
            else:
                invalid_mutations.append(m)

        if invalid_mutations:
            st.warning(f"Invalid mutations excluded: {', '.join(invalid_mutations)}")

        if len(valid_mutations) > MAX_MUTATIONS_LIMIT:
            st.warning(f"Limit to {MAX_MUTATIONS_LIMIT} mutations for performance and URL size. Showing first {MAX_MUTATIONS_LIMIT}.")
            valid_mutations = valid_mutations[:MAX_MUTATIONS_LIMIT]

        if not valid_mutations:
            st.error("No valid mutations provided.")
            return

        st.info(f"Using {len(valid_mutations)} mutations.")
        
    else: # Advanced Mode
        st.caption("Free-text advanced query with Boolean logic and N-of filtering.")
        
        # Documentation expanders
        with st.expander("[▼] Query Syntax Guide", expanded=False):
            st.markdown("""
            **Boolean Operators:**
            - `&` or `AND`: Both conditions must be true
            - `|` or `OR`: At least one condition must be true
            - `!` or `NOT`: Condition must be false
            
            **N-of Filtering:**
            - `[3-of: mut1, mut2, mut3, ...]` : At least N mutations must match
            
            **Exact-N-of Filtering:**
            - `[exactly-2-of: mut1, mut2, ...]` : Exactly N mutations must match
            
            **Grouping:**
            - Use parentheses `(...)` to group operations
            
            [Official Documentation](https://lapis.cov-spectrum.org/advanced-queries/)
            """)
            
        with st.expander("[▼] Example Queries", expanded=False):
            st.code("[3-of: 23149T, 23224T, 23311T, 23403G, 23436G]", language="text")
            st.caption("XBB signature (at least 3 of these mutations)")
            
            st.code("S:614G | S:614D", language="text")
            st.caption("OR logic")
            
            st.code("23149T & !23224-", language="text")
            st.caption("NOT logic")
            
            st.code("(S:484K | S:501Y) & ORF1a:3675-", language="text")
            st.caption("Complex nested logic")

        default_adv = "[3-of: 23149T, 23224T, 23311T, 23403G, 23436G]"
        url_adv_input = url_state.load_from_url("advanced_query", default_adv, str)
        advanced_query_input = st.text_area("Advanced Query:", value=url_adv_input, height=150)
        url_state.save_to_url(advanced_query=advanced_query_input if advanced_query_input and len(advanced_query_input) < 1500 else None)
        
        if advanced_query_input:
            advanced_query = advanced_query_input.strip()
            
        if not advanced_query:
            st.error("Please enter an advanced query.")
            return

    # Date range
    default_start, default_end, min_date, max_date = wiseLoculus.get_cached_date_range_with_bounds("coocurrences")
    url_start = url_state.load_from_url("start_date", default_start, type(default_start))
    url_end = url_state.load_from_url("end_date", default_end, type(default_end))
    date_range_input = st.date_input("Select a date range:", [url_start, url_end], min_value=min_date, max_value=max_date)
    if len(date_range_input) != 2:
        st.error("Please select a valid date range.")
        return
    url_state.save_to_url(start_date=date_range_input[0], end_date=date_range_input[1])
    start_date_dt = datetime.fromisoformat(date_range_input[0].strftime('%Y-%m-%d'))
    end_date_dt = datetime.fromisoformat(date_range_input[1].strftime('%Y-%m-%d'))

    # Fetch locations
    if "locations" not in st.session_state:
        st.session_state.locations = wiseLoculus.fetch_locations(["Zürich (ZH)"])
    locations = st.session_state.locations
    query_locations = locations  # Always use all available locations

    st.markdown("---")

    # Interval fixed to daily
    interval = "daily"

    # Clean up obsolete URL parameters from previous versions
    url_state.save_to_url(locations=None, interval=None)

    # Fetch data for all locations concurrently
    async def fetch_all_locations(locations):
        """Fetch data for all locations in parallel."""
        tasks = [
            wiseLoculus.coocurrences_over_time(
                mutations=valid_mutations if query_mode == "Simple" else None,
                advanced_query=advanced_query if query_mode == "Advanced" else None,
                date_range=(start_date_dt, end_date_dt),
                locationName=loc,
                interval=interval
            )
            for loc in locations
        ]
        return await __import__('asyncio').gather(*tasks, return_exceptions=True)

    # Execute all fetches in parallel
    with st.spinner(f"Fetching data for {len(query_locations)} location(s)..."):
        all_results = __import__('asyncio').run(fetch_all_locations(query_locations))

    # Consolidate results
    freq_data = {}
    counts_data = {}
    coverage_records = []
    
    has_data = False
    
    for loc, result in zip(query_locations, all_results):
        # Handle exceptions from fetch
        if isinstance(result, Exception):
            st.error(f"Error fetching data for {loc}: {result}")
            continue
        
        df = result
        if df.empty:
            continue
            
        has_data = True
        
        # Extract data for this location
        dates = df['samplingDate'].tolist()
        frequencies = df['frequency'].tolist()
        counts = df['count'].tolist()
        
        # Handle both old and new column names for backward compatibility
        if 'coverage' in df.columns:
            coverages = df['coverage'].tolist()
        else:
            coverages = [None] * len(dates)
            
        # Store frequency and counts mapped by date
        # We need to ensure dates are strings or consistent objects for DataFrame construction
        loc_freqs = {d: f for d, f in zip(dates, frequencies)}
        loc_counts = {d: c for d, c in zip(dates, counts)}
        
        freq_data[loc] = loc_freqs
        counts_data[loc] = loc_counts
        
        # Store coverage records for MultiIndex DataFrame
        for i, date in enumerate(dates):
            coverage_records.append({
                'location': loc,
                'samplingDate': date,
                'coverage': coverages[i],
                'count': counts[i],
                'frequency': frequencies[i]
            })

    if not has_data:
        st.warning("No data available for the selected locations and date range.")
        return

    try:
        # Create DataFrames for heatmap
        # freq_df: index=locations, columns=dates
        freq_df = pd.DataFrame.from_dict(freq_data, orient='index')
        # Sort columns (dates)
        freq_df = freq_df.sort_index(axis=1)
        
        # counts_df: index=locations, columns=dates
        counts_df = pd.DataFrame.from_dict(counts_data, orient='index')
        if not counts_df.empty:
            counts_df = counts_df.sort_index(axis=1)
            # Align columns with freq_df
            counts_df = counts_df.reindex(columns=freq_df.columns)
        
        # coverage_df: MultiIndex (location, samplingDate)
        if coverage_records:
            coverage_df = pd.DataFrame(coverage_records)
            coverage_df = coverage_df.set_index(['location', 'samplingDate'])
        else:
            coverage_df = None

        # Show raw data
        with st.expander("📊 View Consolidated Raw Data", expanded=False):
            if coverage_records:
                st.dataframe(pd.DataFrame(coverage_records))
                st.caption("**Coverage:** Reads with valid calls (non-N) satisfying the query logic.")
            else:
                st.write("No data to display.")

        # Render Heatmap
        info_placeholder = st.empty()
        progress = st.progress(0)

        def cb(cur, tot, msg):
            progress.progress(min(1.0, cur))
            info_placeholder.info(msg)

        # Format title
        if query_mode == "Simple":
            mut_title_str = ", ".join(valid_mutations)
            if len(mut_title_str) > 100:
                mut_title_str = mut_title_str[:97] + "..."
            title = f"Co-Occurring Mutations over Time: {mut_title_str}"
        else:
            title_query = advanced_query or ""
            if len(title_query) > 100:
                title_query = title_query[:97] + "..."
            title = f"Advanced Query: {title_query}"

        fig = proportions_heatmap(
            freq_df=freq_df,
            counts_df=counts_df,
            coverage_freq_df=coverage_df,
            title=title,
            progress_callback=cb
        )
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("ℹ️ About the Color Scale", expanded=False):
            st.markdown("""
            The heatmap uses a **power-transformed color scale** ($x^{0.25}$) to highlight low but non-zero frequencies.
            
            - **0% (No detection)** appears white.
            - **Low values (e.g., 1%)** appear significantly colored (~30% intensity) to be visible.
            - **High values** appear dark blue.
            
            Hover over any cell to see the exact percentage, count, and coverage.
            """)
        
        # Clear progress indicators
        progress.empty()
        info_placeholder.empty()

    except Exception as e:
        st.error(f"Error plotting heatmap: {e}")
        import traceback
        with st.expander("🔍 Error Details", expanded=False):
            st.code(traceback.format_exc())


if __name__ == "__main__":
    app()
