import streamlit as st

def app():
    st.title("Variant Deconvolution")

    st.image("images/lollipop.svg", width=140)
    st.write("Identify new variants emerging, by mutations")
    st.write("powered by Lollipop")

    import requests
    from PIL import Image
    from io import BytesIO
    import base64

    st.title('Generate Plot')

    import requests
    from PIL import Image
    from io import BytesIO
    import base64

    # Prebuilt YAML configurations
    yaml_option_1 = """
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

    st.title('Generate Plot from YAML')

    # Dropdown to select prebuilt YAML configurations
    yaml_options = {
        'No XEC': yaml_option_1,
        'With XEC 2': yaml_option_2,
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


    if st.button('Run Lollipop'):
        start_time = time.time()
        try:
            response = requests.post('http://<your-container-ip>:8000/run_lollipop', json={'yaml': yaml_data, 'location': selected_location}, timeout=10)
            elapsed_time = time.time() - start_time
            st.success(f'Request completed in {elapsed_time:.2f} seconds')
            
            if response.status_code == 200:
                plot_url = response.json()['plot_url']
                image = Image.open(BytesIO(base64.b64decode(plot_url.split(',')[1])))
                st.image(image)
            else:
                st.error('Failed to execute Lollipop command')
        except requests.exceptions.Timeout:
            st.error('The request timed out. Please try again later.')
        except requests.exceptions.RequestException as e:
            st.error(f'An error occurred: {e}')