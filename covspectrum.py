"""Implements Queryies to CovSpectrum API"""

import requests

def fetch_mutations_api(variantQuery, sequence_type, min_abundance, cov_sprectrum_api):
    """Fetches mutations from CovSpectrum API for a given variant query, sequence type, and minimal abundance."""
    base_url = f"{cov_sprectrum_api}/open/v2/sample/"
    params = (
        f"variantQuery={variantQuery}"
        f"&minProportion={min_abundance}"
        f"&limit=1000"
        f"&downloadAsFile=false"
    )
    if sequence_type == "Nucleotides":
        url = f"{base_url}nucleotideMutations?{params}"
    else:
        url = f"{base_url}aminoAcidMutations?{params}"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", [])
