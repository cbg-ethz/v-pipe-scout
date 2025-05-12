import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import yaml
import logging 

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
    st.title("Downlaod mutaiton counts and coverage")
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




if __name__ == "__main__":
    app()