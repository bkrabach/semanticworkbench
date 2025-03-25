#!/bin/bash
# Check for architectural violations in the codebase
# This script helps enforce the architectural boundaries defined in the project

echo "========== ARCHITECTURE VALIDATION =========="
echo "Running architecture tests..."

# Run the architecture tests
result=$(python -m pytest tests/architecture/test_layer_integrity.py -v)
exit_code=$?

if [ $exit_code -ne 0 ]; then
    echo "❌ ARCHITECTURE VIOLATIONS DETECTED!"
    echo "$result"
    echo ""
    echo "Fix these violations to maintain proper layer separation."
    echo "See docs/IMPLEMENTATION_PHILOSOPHY.md for guidance on proper architecture."
    exit 1
else
    echo "✅ Architecture is clean! All layers respect their boundaries."
fi

echo ""
echo "Checking for SQLAlchemy model imports in API layer..."
api_violations=$(grep -r "from app.database.models import" --include="*.py" app/api/)
if [ -n "$api_violations" ]; then
    echo "❌ CRITICAL ARCHITECTURE VIOLATION DETECTED IN API LAYER:"
    echo "$api_violations"
    echo ""
    echo "Fix by using domain models instead of SQLAlchemy models in API layer."
    violations=1
else
    echo "✅ API layer is clean (no SQLAlchemy model imports)"
fi

echo ""
echo "Checking for backend client direct imports in API layer..."
client_violations=$(grep -r "from app.backend.[a-z_]* import" --include="*.py" app/api/)
if [ -n "$client_violations" ]; then
    echo "❌ ARCHITECTURE VIOLATION DETECTED IN API LAYER:"
    echo "$client_violations"
    echo ""
    echo "Fix by accessing backend clients via app.state.client_name instead of direct imports."
    violations=1
else
    echo "✅ API layer is clean (no direct backend client imports)"
fi

echo ""
if [ -n "$violations" ]; then
    echo "⚠️ ARCHITECTURE VIOLATIONS DETECTED ⚠️"
    echo "Please fix violations to maintain clean architecture."
    exit 1
else
    echo "🎉 All layers are clean! Architecture integrity maintained."
fi