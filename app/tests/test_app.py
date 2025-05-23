"""test_app.py - Tests for the V-Pipe Scout Streamlit application"""

from streamlit.testing.v1 import AppTest
from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

APP_PATH = os.getenv("APP_PATH", default="app.py")

def test_navigation_links():
    """Test that all navigation links are present in the sidebar."""
    at = AppTest.from_file(APP_PATH)
    at.run()
    
    # Get all page links from the sidebar
    page_links = at.sidebar.get("page_link")
    
    # Check that we have the expected number of navigation links (5 pages)
    assert len(page_links) == 5
    
    # Check that all expected page titles are present in the navigation
    expected_pages = ["Home", "Resistance Mutations", "Dynamic Mutation Heatmap", 
                     "Variant Signature Explorer", "Variant Abundances"]
    
    page_titles = [link.label for link in page_links] # type: ignore
    for expected_page in expected_pages:
        assert any(expected_page in title for title in page_titles)


    
