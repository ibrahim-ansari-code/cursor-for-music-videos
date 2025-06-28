"""
Root conftest.py for all tests.

This file configures the Python path so that tests can import modules from the Backend directory.
"""

import os
import sys

# Standard Project Root Setup
_THIS_SCRIPT_ABSPATH = os.path.abspath(__file__)
_TESTS_DIR = os.path.dirname(_THIS_SCRIPT_ABSPATH)
_BACKEND_DIR = os.path.dirname(_TESTS_DIR)
PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)

# Add project root to Python path
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Add Backend directory to Python path
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR) 