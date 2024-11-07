import matplotlib.pyplot as plt
import pandas as pd
import yaml
import boto3
import seaborn as sns
import matplotlib.pyplot as plt
import streamlit as st

def app():
    # Streamlit title and description
    st.title('Identifing Mutations Arising')
    st.write('Visualizing the frequency of mutations arising')
    

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
    kp3_mutations = 'mut_def/kp23.yaml'
    xec_mutations = "mut_def/xec.yaml"


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
            if file_name.endswith('.gz'):
                data = pd.read_csv(obj['Body'], sep='\t', compression='gzip')
            else:
                data = pd.read_csv(obj['Body'], sep='\t')
            return data
        except Exception as e:
            st.error(f"Error loading tsv from S3: {e}")
            return None


    # Load the YAML data from S3
    kp3_mutations_yaml = load_yaml_from_s3(bucket_name, kp3_mutations)
    xec_mutations_yaml = load_yaml_from_s3(bucket_name, xec_mutations)
    # discard all fileds but 'mut'
    kp3_mutations_yaml = kp3_mutations_yaml['mut']
    xec_mutations_yaml = xec_mutations_yaml['mut']
    # format the yamls with line breaks
    kp3_mutations_yaml = yaml.dump(kp3_mutations_yaml, default_flow_style=False)
    xec_mutations_yaml = yaml.dump(xec_mutations_yaml, default_flow_style=False)

    # Load the selected mutations tally
    tallymut = load_tsv_from_s3(bucket_name, 'subset_tallymut.tsv.gz')


    @st.cache_data  # Cache the data for better performance
    def filter_for_variant(tally, mutation_data):
            # Extract the positions and mutations from kp3_df
            variant_positions = list(mutation_data.keys())
            variant_basechange = [v.split('>')[1] for v in mutation_data.values()]

            # Filter the tally DataFrame based on the positions and mutations in the variant data
            filtered_df = tally[tally.apply(lambda row: row['pos'] in variant_positions and row['base'] == variant_basechange[variant_positions.index(row['pos'])], axis=1)]
   
            return filtered_df

    @st.cache_data  # Cache the data for better performance
    def plot_heatmap(data, title='Heatmap of Fractions by Date and Position', xlabel='Date', ylabel='Position', figsize=(20, 10), num_labels=20, location=''):
        
        # Pivot the dataframe to get the desired format for the heatmap 
        heatmap_data = data.pivot_table(index='pos', columns='date', values='frac')

        # Create the heatmap
        plt.figure(figsize=figsize)
        # Create a custom colormap to highlight NaN values with a different color
        cmap = sns.color_palette("Blues", as_cmap=True)
        cmap.set_bad(color='pink')

        # Create the heatmap with the custom colormap
        sns.heatmap(heatmap_data, cmap=cmap, cbar_kws={'label': 'Fraction'}, mask=heatmap_data.isna())

        plt.title(title)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)

        # Limit the date labels to fit nicely
        xticks = plt.xticks()
        plt.xticks(ticks=xticks[0][::len(xticks[0]) // num_labels], labels=[xticks[1][i] for i in range(0, len(xticks[1]), len(xticks[1]) // num_labels)], rotation=60)

        plt.yticks(rotation=0)
        plt.tight_layout()

        # Display the plot in Streamlit
        st.pyplot(plt)


    def filter_by_location(data, location):
        return data[data['location'] == location]

    # Dropdown to select a location
    locations = [
        'Aggregate (All Locations)',
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

    # Dropdown to select prebuilt YAML configurations
    yaml_options = {
        'KP3': kp3_mutations_yaml,
        'XEC': xec_mutations_yaml,
        'Custom': ''
    }

    selected_option = st.selectbox('Select Mutation Configuration', list(yaml_options.keys()))

    # Populate the text area based on the dropdown selection
    if selected_option == 'Custom':
        mutation_config = st.text_area("Edit Mutation Configuration", height=300)
    else:
        mutation_config = st.text_area("Edit Mutation Configuration", yaml_options[selected_option], height=300)

    if st.button("Plot Heatmap"):
        # Read the data from the text field
        try:
            mutation_data = yaml.safe_load(mutation_config)
            filtered_data = filter_for_variant(tallymut, mutation_data)
            if selected_location != 'Aggregate (All Locations)':
                filtered_data = filter_by_location(filtered_data, selected_location)
            plot_heatmap(filtered_data, location=selected_location)
        except yaml.YAMLError as e:
            st.error(f"Error parsing YAML: {e}")