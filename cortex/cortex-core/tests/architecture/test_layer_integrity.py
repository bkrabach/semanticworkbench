import ast
import os
from pathlib import Path
import pytest

# Define the architectural boundaries
LAYER_RULES = {
    "api": {
        "can_import": ["api", "models", "core", "utils", "backend"],
        "cannot_import": ["database.models"],
        "description": "API layer cannot import database models directly"
    },
    "core": {
        "can_import": ["core", "models", "utils", "backend"],
        "cannot_import": ["api", "database.models"],
        "description": "Core logic cannot import API components or database models"
    },
    "utils": {
        "can_import": ["utils", "core.config"],
        "cannot_import": ["api", "database.models", "backend"],
        "description": "Utilities should be self-contained with minimal dependencies"
    },
    "models": {
        "can_import": ["models", "utils"],
        "cannot_import": ["api", "core", "database.models", "backend"],
        "description": "Domain models should be plain data structures without dependencies"
    },
    "backend": {
        "can_import": ["backend", "models", "utils", "core.config", "core.storage_service"],
        "cannot_import": ["api", "database.models"],
        "description": "Backend clients should not import API components"
    }
}


class ImportVisitor(ast.NodeVisitor):
    """AST visitor to find import statements."""
    def __init__(self):
        self.imports = []

    def visit_Import(self, node):
        for name in node.names:
            self.imports.append(name.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module is not None:
            if node.level > 0:  # Relative import
                # We don't have enough context to resolve relative imports
                self.imports.append(f"relative.{node.module}")
            else:
                self.imports.append(node.module)
        self.generic_visit(node)


def get_imports_from_file(file_path):
    """Extract imports from a Python file."""
    with open(file_path, 'r', encoding='utf-8') as file:
        try:
            tree = ast.parse(file.read(), filename=file_path)
            visitor = ImportVisitor()
            visitor.visit(tree)
            return visitor.imports
        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
            return []


def is_violation(layer, import_path):
    """Check if an import violates the layer's rules."""
    if layer not in LAYER_RULES:
        return False
    
    # Check for explicit disallowed imports
    for banned in LAYER_RULES[layer]["cannot_import"]:
        if import_path == banned or import_path.startswith(f"{banned}."):
            return True
    
    # Check if it's not in the allowed list
    for allowed in LAYER_RULES[layer]["can_import"]:
        if import_path == allowed or import_path.startswith(f"{allowed}."):
            return False
    
    # If the import doesn't match any allowed pattern, it's a violation
    if import_path.startswith("app."):
        return True
    
    # External imports are allowed
    return False


def get_module_layer(file_path):
    """Determine which layer a file belongs to."""
    parts = file_path.parts
    for i, part in enumerate(parts):
        if part == "app" and i + 1 < len(parts):
            next_part = parts[i + 1]
            if next_part in LAYER_RULES:
                return next_part
    return None


def collect_python_files(base_dir="app"):
    """Collect all Python files in the project."""
    base_path = Path(base_dir)
    if not base_path.exists():
        return []
    
    py_files = []
    for path in base_path.rglob("*.py"):
        if "__pycache__" not in str(path):
            py_files.append(path)
    return py_files


def test_layer_integrity():
    """Test that layers respect their boundaries."""
    violations = []
    py_files = collect_python_files()
    
    for file_path in py_files:
        layer = get_module_layer(file_path)
        if not layer or layer not in LAYER_RULES:
            continue
        
        imports = get_imports_from_file(file_path)
        for import_path in imports:
            if import_path.startswith("app."):
                # Remove 'app.' prefix for checking
                clean_import = import_path[4:]
                if is_violation(layer, clean_import):
                    violations.append((str(file_path), import_path, LAYER_RULES[layer]["description"]))
    
    # Generate report of violations
    if violations:
        report = ["Layer integrity violations found:"]
        for file_path, import_path, reason in violations:
            report.append(f"- {file_path} imports {import_path} -> {reason}")
        pytest.fail("\n".join(report))


def test_no_sqlalchemy_in_api():
    """Test that SQLAlchemy models are not imported in the API layer."""
    violations = []
    py_files = collect_python_files("app/api")
    
    for file_path in py_files:
        imports = get_imports_from_file(file_path)
        for import_path in imports:
            if "database.models" in import_path or "sqlalchemy" in import_path.lower():
                violations.append((str(file_path), import_path))
    
    if violations:
        report = ["SQLAlchemy models in API layer:"]
        for file_path, import_path in violations:
            report.append(f"- {file_path} imports {import_path}")
        pytest.fail("\n".join(report))


def test_no_circular_imports():
    """Test that there are no circular imports in the project."""
    # This is a simple check for obvious circular imports
    # For a more comprehensive check, we would need a dependency graph
    
    # Example of circular import pattern that we're checking for:
    # a.py: from app.b import B
    # b.py: from app.a import A
    
    imports_map = {}
    py_files = collect_python_files()
    
    for file_path in py_files:
        # Convert the file path to a module path
        # Use string manipulation to avoid relative_to path issues
        abs_path = str(file_path.absolute())
        project_root = str(Path.cwd())
        if abs_path.startswith(project_root):
            rel_part = abs_path[len(project_root)+1:]  # +1 to remove leading slash
            module_path = rel_part.replace(os.sep, '.').replace('.py', '')
        else:
            # For files outside project root, use the full path
            module_path = str(file_path).replace(os.sep, '.').replace('.py', '')
        
        # Get the imports from the file
        imports = get_imports_from_file(file_path)
        imports_map[module_path] = imports
    
    # Check for circular imports
    circular_imports = []
    for module, imports in imports_map.items():
        for imported in imports:
            if imported in imports_map and module in imports_map.get(imported, []):
                # Allow specific exemptions for known circular dependencies
                allowed_circular_dependencies = [
                    ('app.backend.cognition_client', 'app.core.storage_service'),
                    ('app.backend.memory_client', 'app.core.config'),
                    ('app.utils.auth', 'app.core.config')
                ]
                
                if (module, imported) not in allowed_circular_dependencies and \
                   (imported, module) not in allowed_circular_dependencies:
                    circular_imports.append((module, imported))
    
    if circular_imports:
        report = ["Circular imports detected:"]
        for module1, module2 in circular_imports:
            report.append(f"- {module1} imports {module2} and {module2} imports {module1}")
        pytest.fail("\n".join(report))
