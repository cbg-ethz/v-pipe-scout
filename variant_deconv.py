import streamlit as st
import time
import requests
from PIL import Image
from io import BytesIO
import base64
import yaml

# Load configuration from config.yaml
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

server_ip = config['server']['ip_address']


@st.cache_data
def fetch_plot(yaml_data, location):
    try:
        response = requests.post(f'{server_ip}/run_lollipop', json={'yaml': yaml_data, 'location': location})
        if response.status_code == 200:
            plot_url = response.json()['plot_url']
            image_data = base64.b64decode(plot_url.split(',')[1])
            image = Image.open(BytesIO(image_data))
            return image, None
        else:
            return None, f"Error: {response.status_code}"
    except requests.exceptions.RequestException as e:
        return None, f"An error occurred: {e}"

def app():
    st.title("Variant Deconvolution")
    # make a subtitel powered by lollipop
    st.markdown("## Powered by **Lollipop**")

    st.write("This page allows you to run the Lollipop variant deconvolution tool with a custom variant definitions.")

    # Prebuilt YAML configurations
    yaml_option_1 = """
    var_dates:
        '2024-01-01':
        - BA.4
        - BA.5
        - BA.2.75
        - BA.2.86
        - BQ.1.1
        - XBB.1.5
        - XBB.1.9
        - XBB.1.16
        - XBB.2.3
        - EG.5
        - JN.1
        - BA.2.87.1
        - BA.1
        - BA.2
        - KP.2
        - KP.3
    """

    yaml_option_2 = """
    var_dates:
        '2024-01-01':
        - BA.4
        - BA.5
        - BA.2.75
        - BA.2.86
        - BQ.1.1
        - XBB.1.5
        - XBB.1.9
        - XBB.1.16
        - XBB.2.3
        - EG.5
        - JN.1
        - BA.2.87.1
        - BA.1
        - BA.2
        - KP.2
        - KP.3
        - XEC
    """

    # Dropdown to select prebuilt YAML configurations
    yaml_options = {
        'No XEC': yaml_option_1,
        'With XEC': yaml_option_2,
        'Custom': ''
    }

    # Dropdown to select a location
    locations = [
        'Lugano (TI)',
        'Zürich (ZH)',
        'Chur (GR)',
        'Altenrhein (SG)',
        'Laupen (BE)',
        'Genève (GE)',
        'Basel (BS)',
        'Luzern (LU)'
    ]

    selected_location = st.selectbox('Select a location', locations)

    selected_option = st.selectbox('Variant YAML configuration', list(yaml_options.keys()))

    if selected_option == 'Custom':
        yaml_data = st.text_area('Edit YAML configuration', height=300)
    else:
        yaml_data = st.text_area('YAML configuration', yaml_options[selected_option], height=300)

    if st.button('Run Lollipop'):
            start_time = time.time()
            st.write("For demonstration purposes, we run the tool at 1/10 of the confidence used in production. (bootstraps=10)")
            st.write("Calculation takes up to 90 seconds.")
            with st.spinner('Processing...'):
                image, error = fetch_plot(yaml_data, selected_location)
            elapsed_time = time.time() - start_time
            st.success(f'Request completed in {elapsed_time:.2f} seconds')
            
            if error:
                st.error(error)
            else:
                st.image(image)