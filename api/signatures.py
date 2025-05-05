"""Implements functions to load pre-defined variant signature mutations from GitHub."""

import requests
import yaml
import os
from typing import Dict, List, Optional, Any
from pathlib import Path
from pydantic import BaseModel, Field, validator
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
GITHUB_API_URL = "https://api.github.com/repos/cbg-ethz/cowwid/contents/voc"
RAW_CONTENT_URL = "https://raw.githubusercontent.com/cbg-ethz/cowwid/master/voc"
LOCAL_CACHE_DIR = Path("data/known_variants")

# Pydantic models that match the YAML structure
class VariantInfo(BaseModel):
    short: str
    pangolin: str
    nextstrain: str = ""

class VariantDefinition(BaseModel):
    variant: VariantInfo
    mut: Dict[int, str]
    
    @validator('mut', pre=True)
    def convert_string_keys_to_int(cls, v: Dict) -> Dict[int, str]:
        """Convert dictionary string keys to integers for mutation positions."""
        return {int(k): v for k, v in v.items()}

# Enhanced models for the multi_variant_signatures.py
class Variant(BaseModel):
    name: str
    short_name: str
    nextstrain_name: str = ""
    signature_mutations: List[str]
    
    @classmethod
    def from_variant_definition(cls, variant_def: VariantDefinition) -> "Variant":
        """Create a Variant from a VariantDefinition."""
        # Convert mutations from {position: change} format to list of strings
        mutations = [f"{pos}{change}" for pos, change in variant_def.mut.items()]
        return cls(
            name=variant_def.variant.pangolin,
            short_name=variant_def.variant.short,
            nextstrain_name=variant_def.variant.nextstrain,
            signature_mutations=mutations
        )

class VariantList(BaseModel):
    variants: List[Variant] = []
    
    def add_variant(self, variant: Variant) -> None:
        """Add a variant to the list."""
        self.variants.append(variant)
    
    def remove_variant(self, variant: Variant) -> None:
        """Remove a variant from the list."""
        self.variants.remove(variant)
    
    def get_variant_by_name(self, name: str) -> Optional[Variant]:
        """Get a variant by its name."""
        for variant in self.variants:
            if variant.name == name:
                return variant
        return None

def ensure_cache_dir() -> None:
    """Ensure that the local cache directory exists."""
    os.makedirs(LOCAL_CACHE_DIR, exist_ok=True)

def list_github_files() -> List[Dict[str, Any]]:
    """List all YAML files in the GitHub repository's VOC folder."""
    try:
        response = requests.get(GITHUB_API_URL)
        response.raise_for_status()
        
        # Filter for YAML files only
        files = [file for file in response.json() if file['name'].endswith('.yaml')]
        logger.info(f"Found {len(files)} YAML files in GitHub repository")
        return files
    except requests.RequestException as e:
        logger.error(f"Error fetching files from GitHub: {e}")
        return []

def download_yaml_file(file_name: str) -> Optional[Dict[str, Any]]:
    """Download and parse a YAML file from GitHub."""
    # Check if file exists in local cache
    cache_path = LOCAL_CACHE_DIR / file_name
    
    if cache_path.exists():
        logger.info(f"Loading {file_name} from local cache")
        try:
            with open(cache_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading cached file {file_name}: {e}")
    
    # If not in cache or error occurred, download from GitHub
    try:
        url = f"{RAW_CONTENT_URL}/{file_name}"
        logger.info(f"Downloading {file_name} from {url}")
        response = requests.get(url)
        response.raise_for_status()
        
        # Parse the YAML content
        content = yaml.safe_load(response.text)
        
        # Save to cache
        ensure_cache_dir()
        with open(cache_path, 'w') as f:
            yaml.dump(content, f)
        
        return content
    except (requests.RequestException, yaml.YAMLError) as e:
        logger.error(f"Error downloading or parsing {file_name}: {e}")
        return None

def load_variant_definition(yaml_data: Dict[str, Any]) -> Optional[VariantDefinition]:
    """Convert YAML data to VariantDefinition."""
    try:
        return VariantDefinition.model_validate(yaml_data)
    except Exception as e:
        logger.error(f"Error parsing variant definition: {e}")
        return None

def get_all_variant_definitions() -> List[VariantDefinition]:
    """Get all variant definitions from GitHub."""
    files = list_github_files()
    variant_defs = []
    
    for file in files:
        yaml_data = download_yaml_file(file['name'])
        if yaml_data:
            variant_def = load_variant_definition(yaml_data)
            if variant_def:
                variant_defs.append(variant_def)
    
    logger.info(f"Successfully loaded {len(variant_defs)} variant definitions")
    return variant_defs

def get_variant_list() -> VariantList:
    """Get a VariantList containing all variants from GitHub."""
    variant_defs = get_all_variant_definitions()
    variant_list = VariantList()
    
    for variant_def in variant_defs:
        variant = Variant.from_variant_definition(variant_def)
        variant_list.add_variant(variant)
    
    return variant_list

def get_variant_by_name(name: str) -> Optional[Variant]:
    """Get a variant by its name (pangolin designation)."""
    variant_list = get_variant_list()
    return variant_list.get_variant_by_name(name)

def get_variant_names() -> List[str]:
    """Get a list of all available variant names."""
    variant_list = get_variant_list()
    return [variant.name for variant in variant_list.variants]


if __name__ == "__main__":

    # Test the functions
    logger.info("Testing variant signature loading...")
    variant_list = get_variant_list()
    logger.info(f"Loaded {len(variant_list.variants)} variants")
    
    for variant in variant_list.variants:
        logger.info(f"Variant: {variant.name}, Signature mutations: {variant.signature_mutations}")
    
    # Example of getting a specific variant by name
    test_variant = get_variant_by_name("JN.1")
    if test_variant:
        logger.info(f"Found variant: {test_variant.name}, Signature mutations: {test_variant.signature_mutations}")
    else:
        logger.info("Variant not found")