#!/bin/bash
# Check for SQLAlchemy model imports in API and service layers
# This script helps enforce the clean architecture by preventing database models
# from leaking into API or service layers.

echo "========== ARCHITECTURE VALIDATION =========="
echo "Checking for SQLAlchemy model imports in API layer..."
API_VIOLATIONS=$(grep -r "from app.database.models import" --include="*.py" app/api/)
if [ -n "$API_VIOLATIONS" ]; then
    echo "❌ CRITICAL ARCHITECTURE VIOLATION DETECTED IN API LAYER:"
    echo "$API_VIOLATIONS"
    echo ""
    echo "Fix by replacing with domain models: from app.models.domain.* import *"
    VIOLATIONS=1
else
    echo "✅ API layer is clean"
fi

echo ""
echo "Checking for SQLAlchemy model imports in service layer..."
SERVICE_VIOLATIONS=$(grep -r "from app.database.models import" --include="*.py" app/services/)
if [ -n "$SERVICE_VIOLATIONS" ]; then
    echo "❌ CRITICAL ARCHITECTURE VIOLATION DETECTED IN SERVICE LAYER:"
    echo "$SERVICE_VIOLATIONS"
    echo ""
    echo "Fix by replacing with domain models: from app.models.domain.* import *"
    VIOLATIONS=1
else
    echo "✅ Service layer is clean"
fi

echo ""
echo "Checking for SQLAlchemy model imports in components..."
COMPONENT_VIOLATIONS=$(grep -r "from app.database.models import" --include="*.py" app/components/)
if [ -n "$COMPONENT_VIOLATIONS" ]; then
    echo "❌ CRITICAL ARCHITECTURE VIOLATION DETECTED IN COMPONENTS:"
    echo "$COMPONENT_VIOLATIONS"
    echo ""
    echo "Fix by replacing with domain models: from app.models.domain.* import *"
    VIOLATIONS=1
else
    echo "✅ Components are clean"
fi

echo ""
if [ -n "$VIOLATIONS" ]; then
    echo "⚠️ ARCHITECTURE VIOLATIONS DETECTED ⚠️"
    echo "Please fix violations to maintain clean architecture."
    echo "See docs/DEVELOPMENT.md for guidance on proper layer separation."
    exit 1
else
    echo "🎉 All layers are clean! Architecture integrity maintained."
fi