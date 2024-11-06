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

    x_values = st.text_input('Enter X values (comma-separated)', '1,2,3,4,5')
    y_values = st.text_input('Enter Y values (comma-separated)', '1,4,9,16,25')

    if st.button('Generate Plot'):
        x = list(map(int, x_values.split(',')))
        y = list(map(int, y_values.split(',')))

        response = requests.post('http://68.221.168.92:8000/plot', json={'x': x, 'y': y})
        if response.status_code == 200:
            plot_url = response.json()['plot_url']
            image = Image.open(BytesIO(base64.b64decode(plot_url.split(',')[1])))
            st.image(image)
        else:
            st.error('Failed to generate plot')