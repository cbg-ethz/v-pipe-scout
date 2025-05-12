import pandas as pd

from typing import Dict

# Load the mutations file and create a dictionary of mutations
mutations_df = pd.read_csv('data/mutation_variant_matrix.csv')


# define a function wiht the lapis request for fetching the mutations over a data range for a specific mutation
from api.wiseloculus import WiseLoculusLapis


lapis_api = WiseLoculusLapis(server_ip="http://88.198.54.174")
from datetime import datetime, timedelta
start_date = datetime.fromisoformat("2025-03-02")
one_month_ago = start_date - timedelta(days=30)
date_range_example = (one_month_ago, start_date)

# Create an async function to fetch the data
import asyncio

async def fetch_data():
	# Fetch nucleotide mutation data
	nuc_data = await lapis_api.fetch_mutation_counts_and_coverage(["A2455G", "A234G"], "nucleotide", date_range_example) # No location
	print("Nucleotide Data:", nuc_data)
	return nuc_data

# Run the async function
nuc_data = asyncio.run(fetch_data())




def fetch_counts_and_coverage_nuc(formatted_mutations, date_range) -> Dict[str, pd.DataFrame]:
    """Fetches mutation counts, coverage and frequnecy for a list of nucleotide mutaitons over a date range.
    
    Args:
        formatted_mutations (list): List of nucleotide mutations to fetch data for.
        date_range (tuple): Tuple containing start and end dates for the data range.
    Returns:
        dict: Dictionary containing DataFrames for counts, coverage, and frequency.
    """
    mutation_type = "nucleotide"
    all_data = asyncio.run(lapis_api.fetch_mutation_counts_and_coverage(formatted_mutations, mutation_type, date_range))

    # Initialize dictionaries for each metric
    counts = {}
    coverage = {}
    frequency = {}

    # Populate the dictionaries
    for mutation_data in all_data:
        mutation = mutation_data["mutation"]
        for stratified in mutation_data["stratified"]:
            date = stratified["sampling_date"]
            if mutation not in counts:
                counts[mutation] = {}
                coverage[mutation] = {}
                frequency[mutation] = {}
            counts[mutation][date] = stratified["count"]
            coverage[mutation][date] = stratified["coverage"]
            frequency[mutation][date] = stratified["frequency"]

    # Convert dictionaries to DataFrames
    counts_df = pd.DataFrame.from_dict(counts, orient="index").sort_index(axis=1)
    coverage_df = pd.DataFrame.from_dict(coverage, orient="index").sort_index(axis=1)
    frequency_df = pd.DataFrame.from_dict(frequency, orient="index").sort_index(axis=1)

    # Return a dictionary of DataFrames
    return {"counts": counts_df, "coverage": coverage_df, "frequency": frequency_df}

# Example usage
mutation_type = "nucleotide"
data_frames = fetch_counts_and_coverage_nuc(["A2455G", "A234G"], date_range_example)
print("Counts DataFrame:")
print(data_frames["counts"])
print("Coverage DataFrame:")
print(data_frames["coverage"])
print("Frequency DataFrame:")
print(data_frames["frequency"])