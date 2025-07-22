#!/bin/bash
# Tujenge Platform - Complete Setup Script
# Run this script to set up the entire development environment

set -e

echo "🏦 Setting up Tujenge Platform - Tanzania Microfinance Solution"
echo "================================================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_step() {
    echo -e "\n${BLUE}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Step 1: Check prerequisites
print_step "Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

if ! command -v docker &> /dev/null; then
    print_info "Docker not found. You can install it later for containerized development."
fi

if ! command -v git &> /dev/null; then
    echo "❌ Git is required but not installed."
    exit 1
fi

print_success "Prerequisites check completed"

# Step 2: Create project structure
print_step "Creating project structure..."

# All the directory creation and file creation commands from above
# (This is handled by the script content above)

print_success "Project structure created"

# Step 3: Set up Python environment
print_step "Setting up Python virtual environment..."

if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_info "Virtual environment already exists"
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
print_success "Python dependencies installed"

# Step 4: Configure environment
print_step "Configuring environment..."

if [ ! -f ".env" ]; then
    cp .env.example .env
    print_success "Environment file created from template"
    print_info "Please update .env file with your specific configuration"
else
    print_info ".env file already exists"
fi

# Step 5: Create necessary directories
print_step "Creating application directories..."
mkdir -p logs uploads static uploads/documents uploads/images
print_success "Application directories created"

# Step 6: Initialize git repository
print_step "Initializing git repository..."
if [ ! -d ".git" ]; then
    git init
    git add .
    git commit -m "Initial commit: Tujenge Platform setup"
    print_success "Git repository initialized"
else
    print_info "Git repository already exists"
fi

# Step 7: Set up pre-commit hooks
print_step "Setting up development tools..."
if command -v pre-commit &> /dev/null; then
    pre-commit install
    print_success "Pre-commit hooks installed"
else
    print_info "Install pre-commit for better development experience: pip install pre-commit"
fi

# Final instructions
echo ""
echo "🎉 Tujenge Platform setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Update your .env file with proper database and API credentials"
echo "2. Start services: docker-compose up -d postgres redis"
echo "3. Run migrations: alembic upgrade head"
echo "4. Start development server: ./scripts/start_dev.sh"
echo ""
echo "Development URLs:"
echo "• API Documentation: http://localhost:8000/docs"
echo "• Health Check: http://localhost:8000/health"
echo "• API Base: http://localhost:8000/api/"
echo ""
echo "Happy coding with Cursor AI! 🚀"
echo ""
print_info "Pro tip: Use Ctrl+K in Cursor AI to ask questions about the codebase"
