"""Centralized configuration loading utilities."""

import yaml
import pathlib
import logging
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)


def load_config() -> Dict[str, Any]:
    """
    Load configuration from config.yaml.
    
    Returns:
        Dictionary containing the configuration
    """
    config_path = pathlib.Path(__file__).parent.parent / "config.yaml"
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
            logger.info(f"Loaded configuration from {config_path}")
            return config
    except FileNotFoundError:
        logger.error(f"Configuration file not found at {config_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML configuration: {e}")
        raise


def get_api_urls() -> Tuple[str, str]:
    """
    Get API URLs from configuration.
    
    Returns:
        Tuple of (wiseloculus_url, covspectrum_url)
    """
    config = load_config()
    
    wise_url = config.get('server', {}).get('lapis_address', 'http://default_ip:8000')
    covspectrum_url = config.get('server', {}).get('cov_spectrum_api', 'https://lapis.cov-spectrum.org')
    
    logger.info(f"API URLs - WiseLoculus: {wise_url}, CovSpectrum: {covspectrum_url}")
    
    return wise_url, covspectrum_url


def get_wiseloculus_url() -> str:
    """
    Get WiseLoculus API URL from configuration.
    
    Returns:
        WiseLoculus API URL
    """
    wise_url, _ = get_api_urls()
    return wise_url


def get_covspectrum_url() -> str:
    """
    Get CovSpectrum API URL from configuration.
    
    Returns:
        CovSpectrum API URL
    """
    _, covspectrum_url = get_api_urls()
    return covspectrum_url
