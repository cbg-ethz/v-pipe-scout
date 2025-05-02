"""This page allosw to compose the list of variants and their respectirve mutational signatures.
    Steps: 
    1. Select the variants of interest with their respective signature mutations / or load a pre-defined signature mutation set
        1.1 For a variant, search for the signature mutaitons
        1.2 Or load a pre-defined signature mutation set
    2. Build the mutation-variant matrix
    3. Visualize the mutation-variant matrix
    4. Export and download the mutation-variant matrix and var_dates.yaml
"""

import streamlit as st
import streamlit_pydantic as sp
from pydantic import BaseModel, Field
from typing import Literal, Set

# Define the Pydantic model for the variant 
class Variant(BaseModel):
    name: str
    signature_mutations: list[str]

# Define the Pydantic model for the variant list
class VariantList(BaseModel):
    variants: list[Variant]
    def add_variant(self, variant: Variant):
        self.variants.append(variant)
    def remove_variant(self, variant: Variant):
        self.variants.remove(variant)


class ShowVariantList(BaseModel):

    variant_list: Set[Literal["LP.8", "XEC"]] = Field(
        ["LP.8", "XEC"], description="Select Variants"
    )

def app():
    st.title("Multi Variant Signature Composer")

    st.write("This page will create the mutation-variant matrix.")
    st.write("This is one of the inputs to Lollipop")

    st.markdown("---")

    # let's add a mutli-select box with the variants - this should be a pydantic object of the variant-list

    data = sp.pydantic_input(
    key="Variant List Input", model=ShowVariantList, group_optional_fields="no"
)
    st.write("Selected variants:", data["variant_list"])

if __name__ == "__main__":
    app()