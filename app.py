import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import yaml
import boto3

# Access AWS credentials from secrets management
AWS_ACCESS_KEY_ID = st.secrets["aws"]["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = st.secrets["aws"]["AWS_SECRET_ACCESS_KEY"]
AWS_DEFAULT_REGION = st.secrets["aws"]["AWS_DEFAULT_REGION"]


# Create an S3 client
s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_DEFAULT_REGION, 

)

bucket_name = 'vpipe-output'
kp3_mutations = 'mut_def/kp.3_mutations_full.yaml'
xec_mutations = "mut_def/xec_mutations_full.yaml"


@st.cache_data  # Cache the data for better performance
def load_yaml_from_s3(bucket_name, file_name):
    """Loads YAML data from an S3 bucket.
    
    Args:
        bucket_name (str): The name of the S3 bucket.
        file_name (str): The name of the file to load, including the path.
                         also called object key.
    """
    try:
        obj = s3.get_object(Bucket=bucket_name, Key=file_name)
        data = yaml.safe_load(obj["Body"])
        return data
    except Exception as e:
        st.error(f"Error loading YAML from S3: {e}")
        return None
    

@st.cache_data  # Cache the data for better performance
def load_tsv_from_s3(bucket_name, file_name):
    """Loads tsv data from an S3 bucket.
    
    Args:
        bucket_name (str): The name of the S3 bucket.
        file_name (str): The name of the file to load, including the path.
                         also called object key.
    """
    try:
        obj = s3.get_object(Bucket=bucket_name, Key=file_name)
        data = pd.read_csv(obj['Body'], sep='\t')
        return data
    except Exception as e:
        st.error(f"Error loading tsv from S3: {e}")
        return None



# Load the YAML data from S3
kp3_mutations_data = load_yaml_from_s3(bucket_name, kp3_mutations)
xec_mutations_data = load_yaml_from_s3(bucket_name, xec_mutations)
# Load the selected mutations tally
tallymut = load_tsv_from_s3(bucket_name, 'selected_columns_tallymut.tsv')


# Display the data
st.write("KP3 Mutations:")
st.write(kp3_mutations_data)

st.write("XEC Mutations:")
st.write(xec_mutations_data)

st.write("Selected Mutations Tally:")
st.write(tallymut)


# Streamlit title and description
st.title('Mutation Frequency Over Time')
st.write('This application displays a heatmap of mutation frequencies over time.')


# 1. Data Generation
mutations = [
    "V166A",
    "V166L",
    "N198S",
    "R285C",
    "A376V",
    "A449V",
    "F480L",
    "D484Y",
    "A526V",
    "V557L",
    "G671S",
    "S759A",
    "V792I",
    "E796G",
    "C799F",
    "C799R",
    "E802A",
    "E802D",
    "M924R"
]
start_date = datetime(2024, 4, 23)
end_date = datetime(2024, 10, 7)

# Generate dates three times per week
current_date = start_date
dates = [current_date]
while current_date < end_date:
    current_date += timedelta(days=2)
    dates.append(current_date)
dates.sort()

# Generate random data (skewed towards 0)
data = {}
for mutation in mutations:
    data[mutation] = np.random.choice(np.arange(7), size=len(dates), p=[0.99, 0.01, 0.0, 0.0, 0.0, 0.0, 0.0])

df = pd.DataFrame(data, index=dates)

# 2. Heatmap Construction
fig, ax = plt.subplots(figsize=(12, 8))
im = ax.imshow(df.values.T, cmap='Blues')  # Use a blue colormap

# Set axis labels
ax.set_xticks([0, len(dates) // 2, len(dates) - 1])
ax.set_xticklabels([dates[0].strftime('%Y-%m-%d'), dates[len(dates) // 2].strftime('%Y-%m-%d'), dates[-1].strftime('%Y-%m-%d')], rotation=45)
ax.set_yticks(np.arange(len(mutations)))
ax.set_yticklabels(mutations, fontsize=8)

# Add colorbar
cbar = ax.figure.colorbar(im, ax=ax)
cbar.ax.set_ylabel("Occurrence Frequency", rotation=-90, va="bottom")

plt.tight_layout()

# Display the plot in Streamlit
st.pyplot(fig)