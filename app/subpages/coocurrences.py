import streamlit as st
import pandas as pd
import logging
from datetime import datetime

from interface import MutationType
from api.wiseloculus import WiseLoculusLapis
from utils.config import get_wiseloculus_url
from utils.url_state import create_url_state_manager
from process.mutations import validate_mutation
from visualize.mutations import proportions_lineplot


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pd.set_option('future.no_silent_downcasting', True)

MAX_MUTATIONS_LIMIT = 80  # keep URL state manageable


server_ip = get_wiseloculus_url()
wiseLoculus = WiseLoculusLapis(server_ip)


def app():
    url_state = create_url_state_manager("complex")

    st.title("Co-occurrence of Mutations Over Time (Prototype)")
    st.write("Track a **set of mutations** (AND filter) over time to see the proportion of reads matching ALL specified mutations.")
    st.info("💡 This differs from other pages: here mutations are combined as a filter (must have ALL), not tracked individually.")
    st.markdown("---")

    # Fixed to nucleotide only for now
    mutation_type_value = MutationType.NUCLEOTIDE

    # Mutation input
    st.write("### Input Mutations and Deletions")
    st.caption("Comma-separated nucleotide mutations, e.g., A22893G, T22896G (XFG variant currently circulating)")
    
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
    
    default_mut = "A22893G, T22896G"

    url_mut_input = url_state.load_from_url("mutation_input", default_mut, str)
    mutation_input = st.text_area("Mutations | Deletions (nucleotide only):", value=url_mut_input, height=100)
    url_state.save_to_url(mutation_input=mutation_input if mutation_input and len(mutation_input) < 1500 else None)

    raw_mutations = [m.strip() for m in (mutation_input or "").split(',') if m.strip()]
    valid_mutations, invalid_mutations = [], []
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

    # Location - multi-select with "All locations" option
    if "locations" not in st.session_state:
        st.session_state.locations = wiseLoculus.fetch_locations(["Zürich (ZH)"])
    locations = st.session_state.locations
    
    # Add "All locations" option
    location_options = ["All locations"] + locations
    default_selection = [locations[0]] if locations else []
    
    url_locs = url_state.load_from_url("locations", default_selection, list)
    # Ensure URL locations are valid
    valid_url_locs = [loc for loc in url_locs if loc in location_options]
    if not valid_url_locs:
        valid_url_locs = default_selection
    
    selected_locations = st.multiselect(
        "Select Location(s):", 
        options=location_options,
        default=valid_url_locs
    )
    
    if not selected_locations:
        st.warning("Please select at least one location.")
        return
    
    # Determine actual locations to query
    if "All locations" in selected_locations:
        query_locations = locations  # All available locations
    else:
        query_locations = selected_locations
    
    url_state.save_to_url(locations=selected_locations)

    st.markdown("---")

    # Interval selection (API-side aggregation)
    interval = st.selectbox("Interval:", ["daily", "weekly", "monthly"], index=0)

    # Rolling mean (client-side)
    col1, col2 = st.columns(2)
    with col1:
        enable_smooth = st.checkbox("Apply rolling mean (days)", value=False)
    with col2:
        window_days = st.number_input("Window size (days)", min_value=3, max_value=60, value=7, step=1, disabled=not enable_smooth)
    smoothing = int(window_days) if enable_smooth else 0

    st.markdown("---")
    st.write("### Mutation Set Proportion Over Time")
    st.caption(f"Showing proportion of reads that have ALL {len(valid_mutations)} mutations")

    # Fetch and display one location at a time for faster progressive rendering
    for loc in query_locations:
        st.write(f"#### {loc}")
        
        with st.spinner(f"Fetching data for {loc}..."):
            try:
                df = __import__('asyncio').run(
                    wiseLoculus.coocurrences_over_time(
                        mutations=valid_mutations,
                        date_range=(start_date_dt, end_date_dt),
                        locationName=loc,
                        interval=interval
                    )
                )

                if df.empty:
                    st.warning(f"No data available for {loc}.")
                    continue

                # Show dataframe for debugging
                with st.expander(f"📊 View Raw Data for {loc}", expanded=False):
                    st.dataframe(df)

                # Prepare data for lineplot
                mutation_label = f"Set of {len(valid_mutations)} mutations"
                
                dates = df['samplingDate'].tolist()
                frequencies = df['frequency'].tolist()
                counts = df['count'].tolist()
                coverages = df['coverage'].tolist()
                
                # Create single-row dataframes
                freq_df = pd.DataFrame([frequencies], columns=dates, index=[mutation_label])
                counts_df = pd.DataFrame([counts], columns=dates, index=[mutation_label])
                
                # Create coverage dataframe in MultiIndex format for hover info
                coverage_records = []
                for i, date in enumerate(dates):
                    coverage_records.append({
                        'mutation': mutation_label,
                        'samplingDate': date,
                        'coverage': coverages[i],
                        'count': counts[i],
                        'frequency': frequencies[i]
                    })
                coverage_df = pd.DataFrame(coverage_records)
                coverage_df = coverage_df.set_index(['mutation', 'samplingDate'])

                info_placeholder = st.empty()
                progress = st.progress(0)

                def cb(cur, tot, msg):
                    progress.progress(min(1.0, cur))
                    info_placeholder.info(msg)

                fig = proportions_lineplot(
                    freq_df=freq_df,
                    counts_df=counts_df,
                    coverage_freq_df=coverage_df,
                    title=f"Proportion of Reads with ALL Mutations — {loc} ({interval})",
                    smoothing_window_days=smoothing,
                    progress_callback=cb
                )
                st.plotly_chart(fig)
                
                # Clear progress indicators
                progress.empty()
                info_placeholder.empty()

            except Exception as e:
                st.error(f"Error fetching or plotting data for {loc}: {e}")
                import traceback
                with st.expander(f"🔍 Error Details for {loc}", expanded=False):
                    st.code(traceback.format_exc())


if __name__ == "__main__":
    app()
