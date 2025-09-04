
"""
Tests for the process.variants module.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from typing import List
from process.variants import create_mutation_variant_matrix




class MockVariant:
    """Mock variant class for testing."""
    def __init__(self, name: str, signature_mutations: List[str]):
        self.name = name
        self.signature_mutations = signature_mutations


class MockVariantList:
    """Mock variant list class for testing."""
    def __init__(self, variants: List[MockVariant]):
        self.variants = variants


class TestCreateMutationVariantMatrix:
    """Test the create_mutation_variant_matrix function."""

    def test_basic_functionality(self):
        """Test basic matrix creation with simple data."""
        # Create mock data
        combined_variants = MockVariantList([
            MockVariant("Delta", ["C123T", "A456G"]),
            MockVariant("Omicron", ["C123T", "G234A"])
        ])

        result = create_mutation_variant_matrix(combined_variants)

        # Check basic structure
        assert isinstance(result, pd.DataFrame)
        assert "Mutation" in result.columns
        assert "Delta" in result.columns
        assert "Omicron" in result.columns

        # Check data correctness
        assert len(result) == 3  # 3 unique mutations
        assert set(result["Mutation"].tolist()) == {"A456G", "C123T", "G234A"}

    def test_matrix_values_correctness(self):
        """Test that matrix values are correct (1=present, 0=absent)."""
        combined_variants = MockVariantList([
            MockVariant("VariantA", ["C100T", "A200G"]),
            MockVariant("VariantB", ["C100T", "T300C"])
        ])

        result = create_mutation_variant_matrix(combined_variants)

        # Check specific values
        c100t_row = result[result["Mutation"] == "C100T"]
        assert c100t_row["VariantA"].iloc[0] == 1  # Present in VariantA
        assert c100t_row["VariantB"].iloc[0] == 1  # Present in VariantB

        a200g_row = result[result["Mutation"] == "A200G"]
        assert a200g_row["VariantA"].iloc[0] == 1  # Present in VariantA
        assert a200g_row["VariantB"].iloc[0] == 0  # Absent in VariantB

        t300c_row = result[result["Mutation"] == "T300C"]
        assert t300c_row["VariantA"].iloc[0] == 0  # Absent in VariantA
        assert t300c_row["VariantB"].iloc[0] == 1  # Present in VariantB

    def test_data_alignment_bug_fix(self):
        """Test that data is correctly aligned after column sorting."""
        # This test specifically checks the bug we fixed
        combined_variants = MockVariantList([
            MockVariant("Zeta", ["C123T", "A456G"]),  # Zeta has both mutations
            MockVariant("Alpha", ["C123T"]),          # Alpha has only C123T
            MockVariant("Beta", ["A456G"])            # Beta has only A456G
        ])

        result = create_mutation_variant_matrix(combined_variants)

        # After sorting, columns should be: Mutation, Alpha, Beta, Zeta
        # Check that data is correctly aligned
        c123t_row = result[result["Mutation"] == "C123T"]
        assert c123t_row["Alpha"].iloc[0] == 1  # Alpha has C123T
        assert c123t_row["Beta"].iloc[0] == 0   # Beta doesn't have C123T
        assert c123t_row["Zeta"].iloc[0] == 1   # Zeta has C123T

        a456g_row = result[result["Mutation"] == "A456G"]
        assert a456g_row["Alpha"].iloc[0] == 0  # Alpha doesn't have A456G
        assert a456g_row["Beta"].iloc[0] == 1   # Beta has A456G
        assert a456g_row["Zeta"].iloc[0] == 1   # Zeta has A456G
