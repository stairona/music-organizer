"""
Pytest configuration: add src/ to sys.path for package imports.
"""

import sys
import os

# Insert the project's src/ directory at the front of sys.path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Insert project root so app/ package imports are stable across test runners.
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_path not in sys.path:
    sys.path.insert(0, root_path)
