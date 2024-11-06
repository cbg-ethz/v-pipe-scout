
def app():
    import streamlit as st
    # Streamlit title and description
    st.title('Identifing New Variants')
    st.write('Visualizing new variants emerging, by mutations')
    st.write('powered by V-pipe')
    
    import matplotlib.pyplot as plt
    import pandas as pd
    import yaml
    import boto3
    import seaborn as sns
    import matplotlib.pyplot as plt

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
    kp3_mutations_data = load_yaml_from_s3(bucket_name, kp3_mutations)
    xec_mutations_data = load_yaml_from_s3(bucket_name, xec_mutations)
    # Load the selected mutations tally
    tallymut = load_tsv_from_s3(bucket_name, 'subset_tallymut.tsv.gz')

    # only keep columns we need

    # lets convert these dictionaries to dataframes
    kp3_df = pd.DataFrame(kp3_mutations_data)
    xec_df = pd.DataFrame(xec_mutations_data)

    # subset the dataframes for the positions that only exist in one of the dataframes
    #kp3_pos = set(kp3_mutations_data['mut'].keys())
    #xec_pos =set(xec_mutations_data['mut'].keys())
    #kp3_only = kp3_pos - xec_pos
    #xec_only = xec_pos - kp3_pos

    # subset the dataframes for the positions that only exist in one of the dataframes
    #kp3_df = kp3_df[kp3_df['mut'].isin(kp3_only)]
    #xec_df = xec_df[xec_df['mut'].isin(xec_only)]

    @st.cache_data  # Cache the data for better performance
    def filter_for_variant(tally, variant):
            # Extract the positions and mutations from kp3_df
            kp3_positions = variant.index
            kp3_mutations = variant['mut'].str[-1]

            # Filter new_df based on the positions and mutations in kp3_df
            filtered_df = tally[tally.apply(lambda row: row['pos'] in kp3_positions and row['base'] == kp3_mutations.get(row['pos']), axis=1)]

            return filtered_df

    # Filter tallymut for the KP3 variant
    kp3_filtered_df = filter_for_variant(tallymut, kp3_df)

    # Filter tallymut for the XEC variant
    xec_filtered_df = filter_for_variant(tallymut, xec_df)


    # Dataset selection
    selected_dataset = st.selectbox('Select Dataset', ['kp3/kp2', 'xec'])  # Replace with your dataset names

    @st.cache_data  # Cache the data for better performance
    def plot_heatmap(data, title='Heatmap of Fractions by Date and Position', xlabel='Date', ylabel='Position', figsize=(20, 10), num_labels=20):
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

    # Plot button
    if st.button('Plot Heatmap'):
        if selected_dataset == 'kp3/kp2':
            plot_heatmap(kp3_filtered_df, title='kp3/kp2 Heatmap')  
        elif selected_dataset == 'xec':
            plot_heatmap(xec_filtered_df, title='xec Heatmap') 