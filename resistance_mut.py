import streamlit as st
import time
import requests
from PIL import Image
from io import BytesIO
import base64
import yaml
import pandas as pd

# Load configuration from config.yaml
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

server_ip = config.get('server', {}).get('ip_address', 'http://default_ip:8000')

def app():
    st.title("Resistance Mutations")

    st.write("This page allows you to run the Lollipop variant deconvolution tool with a custom variant definitions.")

    # have three buttons for the three sets of mutaitons 
    # data/3CLpro_inhibitors_datasheet.csv
    # data/RdRP_inhibitors_datasheet.csv
    # data/spike_mAbs_datasheet.csv
    st.write("Select from the following resistance mutation sets:")

    options = ["3CLpro Inhibitors", "RdRP Inhibitors", "Spike mAbs"]
    selected_option = st.selectbox("Select a resistance mutation set:", options)


    if selected_option == "3CLpro Inhibitors":
        df = pd.read_csv('data/3CLpro_inhibitors_datasheet.csv')
    elif selected_option == "RdRP Inhibitors":
        df = pd.read_csv('data/RdRP_inhibitors_datasheet.csv')
    elif selected_option == "Spike mAbs":
        df = pd.read_csv('data/spike_mAbs_datasheet.csv')

    st.write(df)
