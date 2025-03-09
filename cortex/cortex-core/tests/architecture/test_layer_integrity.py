"""
Tests for architectural integrity of the codebase.

These tests verify that the architecture layers maintain proper separation
and that database models are properly confined to repositories.
"""

import os
import re
import pytest
from pathlib import Path

# Modules that should never import database models
PROTECTED_MODULES = [
    "app/api",
    "app/services", 
    "app/components"
]

# Pattern to match SQLAlchemy model imports
DB_MODEL_IMPORT_PATTERN = r"from\s+app\.database\.models\s+import"

# Root directory of the project (relative to this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent


def get_python_files(directory):
    """Get all Python files in a directory recursively."""
    python_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files


def check_file_for_db_model_imports(file_path):
    """Check if a file imports SQLAlchemy models directly."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        matches = re.findall(DB_MODEL_IMPORT_PATTERN, content)
        return matches


@pytest.mark.parametrize("module_path", PROTECTED_MODULES)
def test_no_db_model_imports_in_protected_modules(module_path):
    """
    Test that protected modules don't import database models directly.
    
    This enforces the architectural boundary that database models should
    only be used within repositories, never in API or service layers.
    """
    full_path = os.path.join(PROJECT_ROOT, module_path)
    violations = []
    
    # Get all Python files in the directory
    for file_path in get_python_files(full_path):
        matches = check_file_for_db_model_imports(file_path)
        if matches:
            # Compute relative path for cleaner error messages
            rel_path = os.path.relpath(file_path, PROJECT_ROOT)
            violations.append(f"{rel_path}: {len(matches)} database model imports")
    
    # Assert no violations were found
    assert not violations, f"Database model imports found in {module_path}:\n" + "\n".join(violations)