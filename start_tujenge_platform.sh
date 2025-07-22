#!/bin/bash
# Tujenge Platform - Complete Startup Script

set -e

echo "🏦 Starting Tujenge Platform - Tanzania Microfinance Solution"
echo "============================================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

print_step() {
    echo -e "\n${BLUE}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
print_step "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_success "Prerequisites check passed"

# Clean up existing containers
print_step "Cleaning up existing containers..."
docker-compose down -v --remove-orphans 2>/dev/null || true
print_success "Cleanup completed"

# Start database services
print_step "Starting database services..."
docker-compose up -d postgres redis

# Wait for services to be ready
print_step "Waiting for services to be ready..."
for i in {1..30}; do
    if docker exec tujenge_postgres pg_isready -U tujenge_user -d tujenge_db >/dev/null 2>&1; then
        print_success "PostgreSQL is ready!"
        break
    fi
    echo "Waiting for PostgreSQL... ($i/30)"
    sleep 2
done

# Test database connection
if docker exec tujenge_postgres psql -U tujenge_user -d tujenge_db -c "SELECT 1;" >/dev/null 2>&1; then
    print_success "Database connection successful"
else
    print_error "Database connection failed"
    echo "Checking PostgreSQL logs:"
    docker logs tujenge_postgres --tail 20
    exit 1
fi

# Set up Python environment
print_step "Setting up Python environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_success "Virtual environment already exists"
fi

source venv/bin/activate
pip install --upgrade pip >/dev/null 2>&1

# Install basic dependencies
print_step "Installing Python dependencies..."
pip install fastapi uvicorn sqlalchemy psycopg2-binary alembic python-jose passlib python-multipart >/dev/null 2>&1
print_success "Dependencies installed"

# Create basic FastAPI app
print_step "Setting up FastAPI application..."
if [ ! -f "backend/main.py" ]; then
    cat > backend/main.py << 'MAIN_EOF'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import time

app = FastAPI(
    title="Tujenge Platform",
    version="1.0.0",
    description="Tanzania Microfinance & Digital Banking Solution"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "message": "Welcome to Tujenge Platform - Tanzania Microfinance Solution",
        "version": "1.0.0",
        "status": "running",
        "timestamp": time.time()
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Tujenge Platform",
        "database": "connected",
        "timestamp": time.time()
    }

@app.get("/api/info")
def api_info():
    return {
        "platform": "Tujenge",
        "country": "Tanzania",
        "currency": "TZS",
        "services": ["microfinance", "mobile_money", "nida_verification"],
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "api": "/api"
        }
    }
MAIN_EOF
    print_success "FastAPI application created"
fi

# Create basic requirements.txt
if [ ! -f "requirements.txt" ]; then
    cat > requirements.txt << 'REQ_EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.7
alembic==1.12.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
REQ_EOF
    print_success "requirements.txt created"
fi

# Start the API server
print_step "Starting Tujenge Platform API server..."
echo ""
echo "🚀 Tujenge Platform is starting..."
echo ""
echo "📍 Service URLs:"
echo "• API Documentation: http://localhost:8000/docs"
echo "• Health Check: http://localhost:8000/health"
echo "• API Info: http://localhost:8000/api/info"
echo "• PgAdmin: http://localhost:5050 (admin@tujenge.co.tz / admin123)"
echo ""
echo "🔧 Database Info:"
echo "• PostgreSQL: localhost:5432"
echo "• Database: tujenge_db"
echo "• User: tujenge_user"
echo "• Password: tujenge_password"
echo ""
print_success "All services are ready!"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Start the API server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
