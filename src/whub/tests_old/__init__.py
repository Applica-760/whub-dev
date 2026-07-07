"""Test package init — resolve whub_root() to a throwaway dir for the suite."""
import os
import tempfile

os.environ.setdefault("WHUB_ROOT", tempfile.mkdtemp(prefix="whub-test-"))
os.environ.setdefault("WHUB_DATA_DIR", tempfile.mkdtemp(prefix="whub-data-test-"))
