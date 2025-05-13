import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import yaml
import logging 
import io

from api.wiseloculus import WiseLoculusLapis

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Load configuration from config.yaml
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

server_ip = config.get('server', {}).get('lapis_address', 'http://default_ip:8000')

wiseLoculus = WiseLoculusLapis(server_ip)

def app():

    ## Add a title
    st.title("Download mutation counts and coverage")
    st.markdown("for a list of nucleotide mutations over a date range.")    

    # load data/mutation_variant_matrix.csv
    mutations_df = pd.read_csv('data/mutation_variant_matrix.csv')
    mutations = mutations_df['Mutation'].tolist()

    date_range = [pd.to_datetime("2025-02-10"), pd.to_datetime("2025-03-8")]

    st.write(date_range)

    # Fetch locations from API
    default_location = ["Zürich (ZH)"]
    with st.spinner('Fetching mutation counts and coverage data...'):
        counts_df3d = wiseLoculus.fetch_counts_and_coverage_3D_df_nuc(
            mutations,
            date_range,
            default_location
        )

    # Display the DataFrame
    st.write("Counts and coverage for nucleotide mutations:")
    st.dataframe(counts_df3d)
    
    # Debug - show column names
    st.write("DataFrame columns:", counts_df3d.columns.tolist())

# Create a download section
    st.subheader("Download Data")
    
    # Create columns for download buttons
    col1, col2, col3 = st.columns(3)
    
    # 1. CSV Download (original)
    with col1:
        # Make sure to preserve index for dates and mutations
        csv = counts_df3d.to_csv(index=True)
        st.download_button(
            label="Download as CSV",
            data=csv,
            file_name='mutation_counts_coverage.csv',
            mime='text/csv',
            help="Download all data as a single CSV file with preserved indices."
        )
    
    # 2. JSON Download
    with col2:
        # Convert to JSON structure - using 'split' or 'index' to preserve indices
        # 'split' format includes separate index, columns and data arrays
        json_data = counts_df3d.to_json(orient='split', date_format='iso', index=True)
        
        st.download_button(
            label="Download as JSON",
            data=json_data,
            file_name='mutation_counts_coverage.json',
            mime='application/json',
            help="Download data as a JSON file that preserves dates and mutation indices."
        )
    

if __name__ == "__main__":
    app()