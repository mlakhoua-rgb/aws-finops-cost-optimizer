"""
Shared pytest configuration: make scripts/ importable as top-level modules.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
