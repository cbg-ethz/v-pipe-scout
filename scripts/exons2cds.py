"""This script implements conversion of Sars-Cov-2 mutations given in mature protein products,
to coding domain sequences (CDS) mutations. Here we do this for the resitance mutations provides by 
the Stanford e.g. https://covdb.stanford.edu/drms/spike/ for the spike / 3CLpro and RdRP proteins. 
In particular we map to the CDSs: S ORF1a and ORF1b – aligned with databases as CovSpectrum 
(https://cov-spectrum.org/)"""


# Defining Subregions from the GBFF File
# GENEBank File: 
# https://github.com/LaraFuhrmann/Scan-for-mutations-of-interest-NGS-samples/blob/main/resources/GCF_009858895.2_ASM985889v3_genomic.gbff
# To define subregions like RdRp or 3CLpro from a GenBank Feature Format (GBFF) file excerpt, 
# such as the one provided, follow this streamlined process:

# - Locate Coordinates: Find the subregion’s nucleotide coordinates in the GBFF file. For example, 
#   RdRp is defined as join(13442..13468,13468..16236) under a mat_peptide feature, 
#   indicating it spans two segments due to a frameshift.
# - Identify Parent ORFs: Map the coordinates to the parent ORFs. The CDS feature for ORF1ab 
#   (join(266..13468,13468..21555)) shows ORF1a (266..13468) and ORF1b (13468..21555).
#   RdRp’s first segment (13442..13468) is in ORF1a, and the second (13468..16236) is in ORF1b.
# - Split by Frameshift: For subregions with a join() (like RdRp), split them into segments 
#   at the frameshift point (e.g., 13468 for RdRp).
# - Assign Amino Acid Ranges: Calculate amino acid positions within the subregion. 
#   RdRp’s first segment (27 nucleotides) is 9 amino acids (1–9), and the second 
#   (2769 nucleotides) is 923 amino acids (10–932).

# This allows you to configure subregions in code (e.g., a SUBREGIONS dictionary) with each 
# segment’s ORF, nucleotide start/end, and amino acid range, ensuring accurate mutation mapping 
# across frameshifts. For a simpler subregion like 3CLpro (e.g., 10055..10972), 
# it’s a single segment within ORF1a.


##### Imports
import re
import pandas as pd
import requests


### Define Logic to Transform Coordinates


# Configuration for subregions
SUBREGIONS = {
    "RdRp": {
        "regions": [
            {"orf": "ORF1a", "start": 13442, "end": 13468, "parent_start": 266, "aa_range": (1, 9)},
            {"orf": "ORF1b", "start": 13468, "end": 16236, "parent_start": 13468, "aa_range": (10, 932)}
        ]
    },
    "3CLpro": {
        "regions": [
            {"orf": "ORF1a", "start": 10055, "end": 10972, "parent_start": 266, "aa_range": (1, 306)}
        ]
    }
}

def translate_mutation(mutation, orf, offset):
    """Translate a mutation by applying an offset and ORF prefix."""
    match = re.match(r'([A-Za-z])(\d+)([A-Za-z]|del)', mutation)
    if match:
        orig, pos, new = match.groups()
        new_pos = int(pos) + offset
        return f"{orf}:{orig}{new_pos}{new}"
    return None

def get_offset(subregion, position):
    """Determine the correct ORF and offset for a mutation position."""
    config = SUBREGIONS[subregion]
    for region in config["regions"]:
        start_aa, end_aa = region["aa_range"]
        if start_aa <= position <= end_aa:
            # Calculate offset: parent ORF amino acid start - subregion start
            parent_aa_start = ((region["start"] - region["parent_start"]) // 3) + 1
            offset = parent_aa_start - start_aa
            return region["orf"], offset
    raise ValueError(f"Position {position} out of range for {subregion}")

def translate_mutations(mutations, subregion):
    """Translate mutations to their parent ORFs."""
    if subregion not in SUBREGIONS:
        raise ValueError(f"Unknown subregion: {subregion}")
    
    translated = []
    for mutation in mutations:
        match = re.match(r'([A-Za-z])(\d+)([A-Za-z]|del)', mutation)
        if match:
            position = int(match.group(2))
            orf, offset = get_offset(subregion, position)
            trans_mut = translate_mutation(mutation, orf, offset)
            if trans_mut:
                translated.append(trans_mut)
        else:
            print(f"Invalid mutation format: {mutation}")
    return translated

def get_aa_at_position(gene, position):
    """Get the amino acid at a specific position in a gene."""
    if position < 1 or position > len(gene["sequence"]):
        raise ValueError("Position out of range")
    return gene["sequence"][position - 1]  # Convert to zero-based index

def check_mutation_consistency(mutations, gene):
    """Check if mutations are consistent with the reference gene."""
    for mutation in mutations:
        # split by :
        if ":" in mutation:
            mutation = mutation.split(":")[1]
        match = re.match(r'([A-Za-z])(\d+)([A-Za-z]|del)', mutation)
        if match:
            original = match.group(1)
            position = int(match.group(2))
            print(f"Checking mutation {mutation} at position {position} in gene {gene['name']}")
            new = match.group(3)
            try:
                aa_at_position = get_aa_at_position(gene, position)
                if aa_at_position != original:
                    print(f"Mutation {mutation} is inconsistent with reference at position {position}")
                    print(f"Expected {original}, found {aa_at_position}")
            except ValueError as e:
                print(e)
        else:
            print(f"Invalid mutation format: {mutation}")

def main():
    # Load Data – as downloaded from the Stanford database
    options = {
        "3C-like proteinase": '../data/3CLpro_inhibitors_datasheet.csv',
        "RNA-dependent RNA polymerase": '../data/RdRP_inhibitors_datasheet.csv',
        "spike glycoprotein": '../data/spike_mAbs_datasheet.csv'
    }
    dfs = {}
    for product, file in options.items():
        try:
            df = pd.read_csv(file)
            dfs[product] = df
            print(f"Loaded {len(df)} mutations for {product}")
        except FileNotFoundError:
            print(f"Warning: File {file} not found")
        except Exception as e:
            print(f"Error loading {file}: {e}")

    # Example usage
    rdrp_mutations = dfs["RNA-dependent RNA polymerase"]["Mutation"].tolist()
    clpro_mutations = dfs["3C-like proteinase"]["Mutation"].tolist()

    # Translate mutations
    translated_rdrp = translate_mutations(rdrp_mutations, "RdRp")
    translated_clpro = translate_mutations(clpro_mutations, "3CLpro")

    # Output results
    print("Translated RdRp mutations:")
    print("\n".join(translated_rdrp))
    print("\nTranslated 3CLpro mutations:")
    print("\n".join(translated_clpro))

    # Save to CSV
    translated_rdrp_df = pd.DataFrame(translated_rdrp, columns=["Mutation"])
    translated_clpro_df = pd.DataFrame(translated_clpro, columns=["Mutation"])
    translated_rdrp_df.to_csv("translated_RdRp_in_ORF1a_ORF1b_mutations.csv", index=False)
    translated_clpro_df.to_csv("translated_3CLpro_in_ORF1a_mutations.csv", index=False)
    print("\nResults saved to CSV files.")

    # Also output Spike mutations as S:<mutation> (no mapping needed)
    spike_mutations = dfs["spike glycoprotein"]["Mutation"].tolist()
    formatted_spike = [f"S:{mut}" for mut in spike_mutations]
    formatted_spike_df = pd.DataFrame(formatted_spike, columns=["Mutation"])
    formatted_spike_df.to_csv("translated_Spike_in_S_mutations.csv", index=False)
    print("\nSpike mutations formatted and saved to translated_Spike_in_S_mutations.csv.")

    # Fetch the reference genome from the API
    url = "https://lapis.cov-spectrum.org/open/v2/sample/referenceGenome?downloadAsFile=false"
    response = requests.get(url)
    response.raise_for_status()
    ref_json = response.json()
    print("Reference genome fetched successfully.")

    genes = {}
    for gene in ref_json["genes"]:
        genes[gene["name"]] = gene

    # Example usage for get_aa_at_position
    gene_name = "ORF1a"  # Replace with the desired gene name
    position = 1000
    if gene_name in genes:
        gene = genes[gene_name]
        try:
            aa = get_aa_at_position(gene, position)
            print(f"Amino acid at position {position} in {gene_name}: {aa}")
        except ValueError as e:
            print(e)

    # Check consistency for RdRp and 3CLpro
    print("\nChecking consistency for RdRp mutations:")
    check_mutation_consistency(translated_rdrp_df["Mutation"].to_list(), genes["ORF1b"])
    print("\nChecking consistency for 3CLpro mutations:")
    check_mutation_consistency(translated_clpro_df["Mutation"].to_list(), genes["ORF1a"])

if __name__ == "__main__":
    main()

