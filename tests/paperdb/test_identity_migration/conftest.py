"""Conftest for Task 2 tests — adds repo root to sys.path for imports."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
