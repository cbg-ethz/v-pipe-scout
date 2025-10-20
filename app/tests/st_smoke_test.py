import sys
from pathlib import Path

# Add parent directory (app/) to sys.path for Streamlit AppTest imports
# This is needed because AppTest.from_file() uses Streamlit's module loader
# which reads sys.path at import time, not at pytest discovery time
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import pytest

from streamlit.testing.v1 import AppTest

APP_PATH = Path(os.getenv("APP_PATH", default="app.py"))
SKIP_SMOKE = os.getenv("SKIP_SMOKE", "False").lower() in ("true", "1", "t")

pytestmark = pytest.mark.skipif(SKIP_SMOKE, reason="smoke test is disabled by config")


def get_file_paths() -> list[str]:
    """Get a list of file paths for the main page + each page in the pages folder."""
    app_path = APP_PATH.resolve()
    page_folder = app_path.parent / "subpages"
    if not page_folder.exists():
        return [str(app_path)]
    page_files = page_folder.glob("*.py")
    file_paths = [str(file.absolute().resolve()) for file in page_files]
    return [str(app_path)] + file_paths


def pytest_generate_tests(metafunc):
    """
    This is a special function that is called automatically by pytest to generate tests.
    https://docs.pytest.org/en/7.1.x/how-to/parametrize.html#pytest-generate-tests

    This generates list of file paths for each page in the pages folder, which will
    automatically be used if a test function has an argument called "file_path".

    Each file path will be the absolute path to each file, but the test ids will be
    just the file name. This is so that the test output is easier to read.

    st_smoke_test.py::test_smoke_page[streamlit_app.py] PASSED                  [ 33%]
    st_smoke_test.py::test_smoke_page[p1.py] PASSED                             [ 66%]
    st_smoke_test.py::test_smoke_page[p2.py] PASSED                             [100%]
    """
    if "file_path" in metafunc.fixturenames:
        metafunc.parametrize(
            "file_path", get_file_paths(), ids=lambda x: x.split("/")[-1]
        )

@pytest.mark.skipif(SKIP_SMOKE, reason="smoke test is disabled by config")
def test_smoke_page(file_path):
    """
    This will run a basic test on each page in the pages folder, checking to see that
    there are no exceptions raised while the app runs.
    """
    # Ensure app directory is in PYTHONPATH for AppTest subprocess
    # AppTest.from_file() spawns a new interpreter that needs to find components
    app_dir = str(APP_PATH.resolve().parent)
    current_pythonpath = os.environ.get('PYTHONPATH', '')
    
    # Prepend app directory to PYTHONPATH
    if current_pythonpath:
        os.environ['PYTHONPATH'] = f"{app_dir}{os.pathsep}{current_pythonpath}"
    else:
        os.environ['PYTHONPATH'] = app_dir
    
    try:
        at = AppTest.from_file(file_path, default_timeout=20).run()
        assert not at.exception
    finally:
        # Restore original PYTHONPATH
        if current_pythonpath:
            os.environ['PYTHONPATH'] = current_pythonpath
        else:
            os.environ.pop('PYTHONPATH', None)