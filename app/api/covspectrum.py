"""Implements Queries to CovSpectrum API using CovSpectrumLapis class."""

import requests
from .lapis import Lapis

class CovSpectrumLapis(Lapis):
    """Implements CovSpectrum API."""

    def fetch_mutations(self, variantQuery, sequence_type, min_abundance):
        """Fetches mutations from CovSpectrum API for a given variant query, sequence type, and minimal abundance."""
        base_url = f"{self.server_ip}/open/v2/sample/"
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
