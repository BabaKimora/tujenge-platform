#!/bin/bash
# Quick test script to verify setup

echo "🧪 Testing Tujenge Platform setup..."

# Test file existence
echo "📁 Checking files..."
for file in "start_tujenge_platform.sh" "docker-compose.yml" ".env" "scripts/postgres/init-db.sh"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ $file missing"
    fi
done

# Test Docker
echo "🐳 Testing Docker..."
if command -v docker &> /dev/null; then
    echo "✅ Docker is installed"
else
    echo "❌ Docker not found"
fi

# Test permissions
echo "🔐 Testing permissions..."
if [ -x "start_tujenge_platform.sh" ]; then
    echo "✅ start_tujenge_platform.sh is executable"
else
    echo "❌ start_tujenge_platform.sh is not executable"
    chmod +x start_tujenge_platform.sh
fi

echo ""
echo "🚀 Setup test completed!"
echo "Run: ./start_tujenge_platform.sh to start the platform"
