"""
Mutation processing utilities.

This module contains functions for processing mutation strings,
extracting genomic positions, and validating mutation formats.
"""

import re
from typing import List
from interface import MutationType


def get_symbols_for_mutation_type(mutation_type: MutationType) -> List[str]:
    """Returns the list of symbols (amino acids or nucleotides) for the given mutation type.
    
    Args:
        mutation_type (MutationType): The type of mutation (AMINO_ACID or NUCLEOTIDE)
        
    Returns:
        List[str]: List of valid symbols for the mutation type
        
    Raises:
        ValueError: If the mutation type is unknown
    """
    if mutation_type == MutationType.AMINO_ACID:
        return ["A", "C", "D", "E", "F", "G", "H", "I", "K", 
                "L", "M", "N", "P", "Q", "R", "S", "T", 
                "V", "W", "Y"]
    elif mutation_type == MutationType.NUCLEOTIDE:
        return ["A", "T", "C", "G"]
    else:
        raise ValueError(f"Unknown mutation type: {mutation_type}")


def extract_position(mutation_str: str) -> int:
    """Extract the genomic position number from a mutation string.
    
    This function works for both nucleotide and amino acid mutations:
    - Nucleotide mutations: "C345T", "456-", "748G" -> returns position number
    - Amino acid mutations: "ORF1a:T103L", "S:N126K" -> returns position number
    
    Args:
        mutation_str (str): The mutation string to parse
        
    Returns:
        int: The genomic position number, or 0 if parsing fails
        
    Examples:
        >>> extract_position("C345T")
        345
        >>> extract_position("ORF1a:T103L")
        103
        >>> extract_position("456-")
        456
        >>> extract_position("S:N126K")
        126
    """
    mutation_str = mutation_str.strip()
    
    # Check if it's an amino acid mutation (contains ':')
    if ':' in mutation_str:
        # Amino acid mutation format: "ORF1a:T103L", "S:N126K"
        try:
            # Split by colon and get the mutation part
            gene_part, mutation_part = mutation_str.split(':', 1)
            
            # Extract position from the mutation part
            # Pattern: [REF][POSITION][ALT] where REF and ALT are amino acids
            amino_acids = get_symbols_for_mutation_type(MutationType.AMINO_ACID)
            amino_acid_pattern = '|'.join(amino_acids)
            
            # Match patterns like T103L, N126K, etc.
            match = re.match(rf"^({amino_acid_pattern})?(\d+)({amino_acid_pattern}|-)?$", mutation_part.upper())
            if match:
                return int(match.group(2))
                
        except (ValueError, IndexError):
            pass
    else:
        # Nucleotide mutation format: "C345T", "456-", "748G"
        try:
            nucleotides = get_symbols_for_mutation_type(MutationType.NUCLEOTIDE)
            nucleotide_pattern = '|'.join(nucleotides)
            
            # Match patterns like C345T, 456-, 748G
            match = re.match(rf"^({nucleotide_pattern})?(\d+)({nucleotide_pattern}|-)?$", mutation_str.upper())
            if match:
                return int(match.group(2))
                
        except ValueError:
            pass
    
    # Fallback: try to extract any number from the string
    try:
        numbers = re.findall(r'\d+', mutation_str)
        if numbers:
            return int(numbers[0])
    except (ValueError, IndexError):
        pass
    
    return 0  # Return 0 if position extraction fails


def sort_mutations_by_position(mutations: List[str]) -> List[str]:
    """Sort a list of mutations by their genomic position in ascending order.
    
    Args:
        mutations (List[str]): List of mutation strings to sort
        
    Returns:
        List[str]: Sorted list of mutations by genomic position
        
    Examples:
        >>> mutations = ["C500T", "A100G", "T300C"]
        >>> sort_mutations_by_position(mutations)
        ["A100G", "T300C", "C500T"]
    """
    return sorted(mutations, key=extract_position)
