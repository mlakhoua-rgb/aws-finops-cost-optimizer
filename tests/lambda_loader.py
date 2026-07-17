"""
Helper to load the Lambda handlers for testing.

The three Lambda functions all live in files named main.py, so they are loaded
under distinct module names via importlib instead of a plain import.
"""
import importlib.util
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_lambda_module(function_dir: str, module_name: str):
    """Load lambda/<function_dir>/main.py under a unique module name."""
    if module_name in sys.modules:
        return sys.modules[module_name]
    path = os.path.join(REPO_ROOT, "lambda", function_dir, "main.py")
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
