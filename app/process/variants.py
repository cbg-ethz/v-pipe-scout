"""
Variant processing utilities.

This module contains functions for processing variant data,
creating mutation-variant matrices, and related utilities.
"""

import pandas as pd
from typing import List, Any
from .mutations import extract_position


def create_mutation_variant_matrix(combined_variants: Any) -> pd.DataFrame:
    """Create a mutation-variant matrix DataFrame.

    This function builds a binary matrix where:
    - Rows represent unique mutations across all selected variants
    - Columns represent variant names (sorted alphabetically)
    - Values are 1 if the mutation is present in the variant's signature, 0 otherwise

    Args:
        combined_variants: Object containing a list of variant objects with 'name' and 'signature_mutations' attributes

    Returns:
        pd.DataFrame: Mutation-variant matrix with mutations as rows and variants as columns

    The matrix is sorted by:
    - Mutations: by genomic position in descending order
    - Variants: alphabetically by variant name
    """
    # Collect all unique mutations across selected variants
    all_mutations = set()
    for variant in combined_variants.variants:
        all_mutations.update(variant.signature_mutations)

    # Sort mutations for consistent display
    all_mutations = sorted(list(all_mutations))

    # Create a DataFrame with mutations as rows and variants as columns
    matrix_data = []
    for mutation in all_mutations:
        row = [mutation]
        for variant in combined_variants.variants:
            # 1 if mutation is in variant's signature mutations, 0 otherwise
            row.append(1 if mutation in variant.signature_mutations else 0)
        matrix_data.append(row)

    # Create column names (variant names)
    columns = ["Mutation"] + [variant.name for variant in combined_variants.variants]

    # Sort mutations by position number using the utility function
    matrix_data.sort(key=lambda x: extract_position(x[0]), reverse=True)  # Sort by position in descending order

    # Sort columns alphabetically by variant name, but keep "Mutation" as the first column
    variant_columns = columns[1:]  # Skip the "Mutation" column
    variant_columns.sort()  # Sort alphabetically
    columns = ["Mutation"] + variant_columns

    # Create a mapping from original variant order to sorted order
    original_variant_order = [variant.name for variant in combined_variants.variants]
    variant_index_map = {name: original_variant_order.index(name) for name in original_variant_order}

    # Reorder each row's data to match the sorted columns
    for row in matrix_data:
        original_data = row[1:]  # Data in original variant order
        sorted_data = [original_data[variant_index_map[name]] for name in variant_columns]
        row[1:] = sorted_data

    # Create DataFrame
    matrix_df = pd.DataFrame(matrix_data, columns=columns)

    return matrix_df