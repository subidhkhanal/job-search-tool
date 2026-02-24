import os
import sys

# Add backend directories to Python path so imports resolve correctly
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_root, "backend", "app"))
sys.path.insert(0, os.path.join(_root, "backend", "modules"))

from backend.app.main import app  # noqa: E402
