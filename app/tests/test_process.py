"""
Tests for the process.mutations module.
"""

import pytest
from interface import MutationType
from process.mutations import (
    get_symbols_for_mutation_type,
    extract_position,
    sort_mutations_by_position
)


class TestGetSymbolsForMutationType:
    """Test the get_symbols_for_mutation_type function."""
    
    def test_nucleotide_symbols(self):
        """Test that nucleotide symbols are returned correctly."""
        result = get_symbols_for_mutation_type(MutationType.NUCLEOTIDE)
        expected = ["A", "T", "C", "G"]
        assert result == expected
    
    def test_amino_acid_symbols(self):
        """Test that amino acid symbols are returned correctly."""
        result = get_symbols_for_mutation_type(MutationType.AMINO_ACID)
        expected = ["A", "C", "D", "E", "F", "G", "H", "I", "K", 
                   "L", "M", "N", "P", "Q", "R", "S", "T", 
                   "V", "W", "Y"]
        assert result == expected
    
    def test_invalid_mutation_type(self):
        """Test that invalid mutation type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown mutation type"):
            get_symbols_for_mutation_type("invalid")  # type: ignore


class TestExtractPosition:
    """Test the extract_position function."""
    
    def test_nucleotide_mutations(self):
        """Test position extraction from nucleotide mutations."""
        assert extract_position("C345T") == 345
        assert extract_position("A100G") == 100
        assert extract_position("T1234C") == 1234
    
    def test_deletion_mutations(self):
        """Test position extraction from deletion mutations."""
        assert extract_position("456-") == 456
        assert extract_position("123-") == 123
    
    def test_insertion_mutations(self):
        """Test position extraction from simple mutations without reference."""
        assert extract_position("748G") == 748
        assert extract_position("999A") == 999
    
    def test_amino_acid_mutations(self):
        """Test position extraction from amino acid mutations."""
        assert extract_position("ORF1a:T103L") == 103
        assert extract_position("S:N126K") == 126
        assert extract_position("ORF1b:P314L") == 314
    
    def test_case_insensitive(self):
        """Test that position extraction is case insensitive."""
        assert extract_position("c345t") == 345
        assert extract_position("orf1a:t103l") == 103
        assert extract_position("s:n126k") == 126
    
    def test_whitespace_handling(self):
        """Test that whitespace is handled correctly."""
        assert extract_position(" C345T ") == 345
        assert extract_position(" ORF1a:T103L ") == 103
    
    def test_invalid_mutations(self):
        """Test that invalid mutations return 0."""
        assert extract_position("") == 0
        assert extract_position("invalid") == 0
        assert extract_position("ABC") == 0
    
    def test_fallback_number_extraction(self):
        """Test fallback number extraction from complex strings."""
        assert extract_position("mutation_123_something") == 123
        assert extract_position("complex456string") == 456


class TestSortMutationsByPosition:
    """Test the sort_mutations_by_position function."""
    
    def test_nucleotide_mutations_sorting(self):
        """Test sorting of nucleotide mutations."""
        mutations = ["C500T", "A100G", "T300C"]
        result = sort_mutations_by_position(mutations)
        expected = ["A100G", "T300C", "C500T"]
        assert result == expected
    
    def test_amino_acid_mutations_sorting(self):
        """Test sorting of amino acid mutations."""
        mutations = ["ORF1a:T500L", "S:N126K", "ORF1b:P314L"]
        result = sort_mutations_by_position(mutations)
        expected = ["S:N126K", "ORF1b:P314L", "ORF1a:T500L"]
        assert result == expected
    
    def test_mixed_mutations_sorting(self):
        """Test sorting of mixed mutation types."""
        mutations = ["C500T", "S:N126K", "A100G", "ORF1a:T200L"]
        result = sort_mutations_by_position(mutations)
        expected = ["A100G", "S:N126K", "ORF1a:T200L", "C500T"]
        assert result == expected
    
    def test_empty_list(self):
        """Test sorting of empty list."""
        result = sort_mutations_by_position([])
        assert result == []
    
    def test_single_mutation(self):
        """Test sorting of single mutation."""
        mutations = ["C345T"]
        result = sort_mutations_by_position(mutations)
        assert result == ["C345T"]
    
    def test_already_sorted(self):
        """Test sorting of already sorted mutations."""
        mutations = ["A100G", "T300C", "C500T"]
        result = sort_mutations_by_position(mutations)
        assert result == mutations
    
    def test_reverse_sorted(self):
        """Test sorting of reverse sorted mutations."""
        mutations = ["C500T", "T300C", "A100G"]
        result = sort_mutations_by_position(mutations)
        expected = ["A100G", "T300C", "C500T"]
        assert result == expected
    
    def test_duplicate_positions(self):
        """Test sorting with duplicate positions."""
        mutations = ["C345T", "A345G", "T100C"]
        result = sort_mutations_by_position(mutations)
        # Should maintain original order for same positions
        assert result[0] == "T100C"
        assert len(result) == 3
        assert set(result) == set(mutations)
    
    def test_invalid_mutations_sorting(self):
        """Test sorting with invalid mutations (position 0)."""
        mutations = ["C345T", "invalid", "A100G"]
        result = sort_mutations_by_position(mutations)
        # Invalid mutations (position 0) should come first
        assert result[0] == "invalid"
        assert "A100G" in result
        assert "C345T" in result
