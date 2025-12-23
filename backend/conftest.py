"""
Pytest configuration for backend tests.
Sets up Python path to allow importing from backend root.
"""

import sys
from pathlib import Path

# Add backend root to Python path
backend_root = Path(__file__).parent
sys.path.insert(0, str(backend_root))
