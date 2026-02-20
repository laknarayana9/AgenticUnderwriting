#!/bin/bash

# Environment Switcher Script
# Usage: ./switch_env.sh [development|production]

ENVIRONMENT=${1:-development}

echo "Switching to $ENVIRONMENT environment..."

# Copy the appropriate environment file
if [ -f ".env.$ENVIRONMENT" ]; then
    cp ".env.$ENVIRONMENT" .env
    echo "✅ Loaded .env.$ENVIRONMENT"
    echo "🔧 Environment: $ENVIRONMENT"
    echo "📋 Current settings:"
    echo "   - CORS Origins: $(grep CORS_ORIGINS .env | cut -d'=' -f2)"
    echo "   - Debug Mode: $(grep DEBUG .env | cut -d'=' -f2)"
    echo "   - Log Level: $(grep LOG_LEVEL .env | cut -d'=' -f2)"
else
    echo "❌ Error: .env.$ENVIRONMENT not found"
    exit 1
fi

echo "✨ Environment switched successfully!"
echo "💡 Restart your application to apply changes."
