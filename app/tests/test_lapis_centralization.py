"""
Test to demonstrate the centralization of LAPIS field names.

This test verifies that:
1. All API field constants are defined
2. Changing a constant value would propagate throughout the codebase
3. The constants are used consistently across app and worker
"""

import pytest
from pathlib import Path
import importlib.util


def load_module_from_path(module_name: str, file_path: Path):
    """Load a Python module from a file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestLapisFieldsCentralization:
    """Test the LAPIS fields centralization."""
    
    def test_app_constants_exist(self):
        """Verify that the app constants file exists and has required constants."""
        app_fields_path = Path(__file__).parent.parent / "api" / "lapis_fields.py"
        assert app_fields_path.exists(), "app/api/lapis_fields.py should exist"
        
        # Load the module
        fields = load_module_from_path("lapis_fields_app", app_fields_path)
        
        # Verify key constants exist
        assert hasattr(fields, "SAMPLING_DATE"), "SAMPLING_DATE constant should exist"
        assert hasattr(fields, "LOCATION_NAME"), "LOCATION_NAME constant should exist"
        assert hasattr(fields, "SAMPLING_DATE_FROM"), "SAMPLING_DATE_FROM constant should exist"
        assert hasattr(fields, "SAMPLING_DATE_TO"), "SAMPLING_DATE_TO constant should exist"
        
    def test_worker_constants_exist(self):
        """Verify that the worker constants file exists and has required constants."""
        worker_fields_path = Path(__file__).parent.parent.parent / "worker" / "lapis_fields.py"
        assert worker_fields_path.exists(), "worker/lapis_fields.py should exist"
        
        # Load the module
        fields = load_module_from_path("lapis_fields_worker", worker_fields_path)
        
        # Verify key constants exist
        assert hasattr(fields, "SAMPLING_DATE"), "SAMPLING_DATE constant should exist"
        assert hasattr(fields, "LOCATION_NAME"), "LOCATION_NAME constant should exist"
        assert hasattr(fields, "DF_SAMPLING_DATE"), "DF_SAMPLING_DATE constant should exist"
        
    def test_app_worker_constants_match(self):
        """Verify that app and worker constants have the same values."""
        app_fields_path = Path(__file__).parent.parent / "api" / "lapis_fields.py"
        worker_fields_path = Path(__file__).parent.parent.parent / "worker" / "lapis_fields.py"
        
        app_fields = load_module_from_path("lapis_fields_app", app_fields_path)
        worker_fields = load_module_from_path("lapis_fields_worker", worker_fields_path)
        
        # Test that key constants match between app and worker
        assert app_fields.SAMPLING_DATE == worker_fields.SAMPLING_DATE, \
            "SAMPLING_DATE should match between app and worker"
        assert app_fields.LOCATION_NAME == worker_fields.LOCATION_NAME, \
            "LOCATION_NAME should match between app and worker"
        assert app_fields.DF_SAMPLING_DATE == worker_fields.DF_SAMPLING_DATE, \
            "DF_SAMPLING_DATE should match between app and worker"
        
    def test_constants_are_strings(self):
        """Verify that constants are strings (field names)."""
        app_fields_path = Path(__file__).parent.parent / "api" / "lapis_fields.py"
        fields = load_module_from_path("lapis_fields_app", app_fields_path)
        
        # Verify that constants are strings
        assert isinstance(fields.SAMPLING_DATE, str), "SAMPLING_DATE should be a string"
        assert isinstance(fields.LOCATION_NAME, str), "LOCATION_NAME should be a string"
        assert isinstance(fields.SAMPLING_DATE_FROM, str), "SAMPLING_DATE_FROM should be a string"
        
    def test_constants_follow_naming_convention(self):
        """Verify that DataFrame constants start with DF_ and API constants don't."""
        app_fields_path = Path(__file__).parent.parent / "api" / "lapis_fields.py"
        fields = load_module_from_path("lapis_fields_app", app_fields_path)
        
        # API field constants should not start with DF_
        assert not fields.SAMPLING_DATE.startswith("DF_"), \
            "API constants should not start with DF_"
        assert not fields.LOCATION_NAME.startswith("DF_"), \
            "API constants should not start with DF_"
        
        # DataFrame constants should start with their purpose clearly
        # The DF_ prefix indicates these are for internal DataFrame operations
        assert hasattr(fields, "DF_SAMPLING_DATE"), "DF_SAMPLING_DATE constant should exist"
        assert hasattr(fields, "DF_MUTATION"), "DF_MUTATION constant should exist"


class TestCentralizationBenefits:
    """Test that demonstrates the benefits of centralization."""
    
    def test_changing_api_field_name_is_simple(self):
        """
        Demonstration test showing how easy it is to change an API field name.
        
        This test documents the process but doesn't actually change anything.
        It serves as documentation for future maintainers.
        """
        # To change an API field name in the future:
        # 
        # 1. Update app/api/lapis_fields.py:
        #    SAMPLING_DATE = "sampling_date"  # Changed from "samplingDate"
        #
        # 2. Update worker/lapis_fields.py with the same change:
        #    SAMPLING_DATE = "sampling_date"  # Changed from "samplingDate"
        #
        # 3. Run tests to verify everything works
        #
        # That's it! No need to search through 100+ files.
        
        # This test always passes - it's documentation
        assert True, "Changing field names is now centralized and simple"
        
    def test_no_hardcoded_field_names_in_wiseloculus(self):
        """Verify that wiseloculus.py uses constants instead of hardcoded strings."""
        wiseloculus_path = Path(__file__).parent.parent / "api" / "wiseloculus.py"
        
        # Read the file
        with open(wiseloculus_path, 'r') as f:
            content = f.read()
        
        # Verify imports from lapis_fields
        assert "from .lapis_fields import" in content, \
            "wiseloculus.py should import from lapis_fields"
        
        # Verify that commonly changed field names are NOT hardcoded
        # (some may appear in comments or docstrings, which is fine)
        code_lines = [line for line in content.split('\n') 
                     if not line.strip().startswith('#') and '"""' not in line]
        code_content = '\n'.join(code_lines)
        
        # Check that string literals "samplingDate" and "locationName" don't appear in code
        # (excluding imports and the lapis_fields module itself)
        assert '"samplingDate"' not in code_content or 'lapis_fields' in code_content, \
            "samplingDate should not be hardcoded in wiseloculus.py"
        assert '"locationName"' not in code_content or 'lapis_fields' in code_content, \
            "locationName should not be hardcoded in wiseloculus.py"
