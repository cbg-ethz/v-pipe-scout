import streamlit as st

def app():
    st.title("Variant Deconvolution")

    st.image("images/lollipop.svg", width=140)
    st.write("Identify new variants emerging, by mutations")
    st.write("powered by Lollipop")


    import streamlit as st
    import requests
    import yaml

    st.title('Process YAML Data')

    yaml_data = st.text_area('Enter YAML data')

    if st.button('Process YAML'):
        response = requests.post('http://<your-container-ip>:8000/process_yaml', json=yaml.safe_load(yaml_data))
        if response.status_code == 200:
            st.success('YAML data processed successfully')
            st.json(response.json())
        else:
            st.error('Failed to process YAML data')