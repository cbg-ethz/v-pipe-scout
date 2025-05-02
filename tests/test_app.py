"""test_app.py"""
from streamlit.testing.v1 import AppTest

def test_app():
    at = AppTest.from_file("app.py")
    at.run()
    # Check that the sidebar is rendered
    assert at.sidebar is not None
    # Check that the navigation radio exists and has the correct options
    nav_radio = at.sidebar.radio[0] # Access the first radio button
    assert nav_radio.label == "Explore the data using" # Verify it's the correct one by label
    
