import streamlit as st
import time
import requests
from PIL import Image
from io import BytesIO
import base64

def app():
    st.title("Variant Deconvolution")

    import requests
    from PIL import Image
    from io import BytesIO
    import base64
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
        with st.spinner('Processing...'):
            start_time = time.time()
            try:
                response = requests.post('http://68.221.168.92:8000/run_lollipop', json={'yaml': yaml_data, 'location': selected_location})
                elapsed_time = time.time() - start_time
                st.success(f'Request completed in {elapsed_time:.2f} seconds')
                
                if response.status_code == 200:
                    plot_url = response.json()['plot_url']
                    image_data = base64.b64decode(plot_url.split(',')[1])
                    image = Image.open(BytesIO(image_data))
                    st.image(image)
            except requests.exceptions.RequestException as e:
                # This exception is raised for network-related errors, such as connection issues, timeouts, or invalid responses.
                # It handles any request-related errors and displays an appropriate error message to the user.
                st.error(f'An error occurred: {e}')
