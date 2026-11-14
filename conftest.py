"""Keep pytest temporary files in a newly owned project-local directory."""
from pathlib import Path
import tempfile


def pytest_configure(config):
    if config.option.basetemp is None:
        parent=Path(__file__).resolve().parent/'work'/'pytest'
        parent.mkdir(parents=True,exist_ok=True)
        # New, empty, uniquely named directory; never reuse user data as basetemp.
        config.option.basetemp=tempfile.mkdtemp(prefix='session-',dir=parent)
