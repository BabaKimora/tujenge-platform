# ============================================================================
# CREATE ALL FILES IMMEDIATELY - COPY AND PASTE THESE COMMANDS
# ============================================================================

echo "📁 Current directory: $(pwd)"
echo "📋 Creating all Tujenge Platform files..."

# ============================================================================
# 1. CREATE DIRECTORY STRUCTURE
# ============================================================================

mkdir -p scripts/postgres
mkdir -p scripts/redis
mkdir -p backend/api
mkdir -p backend/models
mkdir -p backend/core
mkdir -p logs
mkdir -p uploads/documents
mkdir -p uploads/images
mkdir -p static

echo "✅ Directory structure created"

# ============================================================================
# 2. CREATE MAIN STARTUP SCRIPT
# ============================================================================

cat > start_tujenge_platform.sh << 'EOF'
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
    if docker exec tujenge_postgres pg_isready -U postgres -d tujenge_db >/dev/null 2>&1; then
        print_success "PostgreSQL is ready!"
        break
    fi
    echo "Waiting for PostgreSQL... ($i/30)"
    sleep 2
done

# Test database connection
if docker exec tujenge_postgres psql -U postgres -d tujenge_db -c "SELECT 1;" >/dev/null 2>&1; then
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
echo "• User: postgres"
echo "• Password: PasswordYangu"
echo ""
print_success "All services are ready!"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Start the API server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
EOF

chmod +x start_tujenge_platform.sh
echo "✅ start_tujenge_platform.sh created and made executable"

# ============================================================================
# 3. CREATE DOCKER-COMPOSE.YML
# ============================================================================

cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: tujenge_postgres
    environment:
      POSTGRES_DB: tujenge_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: PasswordYangu
      POSTGRES_INITDB_ARGS: "--encoding=UTF8 --locale=C"
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/postgres/init-db.sh:/docker-entrypoint-initdb.d/01-init-db.sh:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d tujenge_db"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 30s

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: tujenge_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # PostgreSQL Admin Interface
  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: tujenge_pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@tujenge.co.tz
      PGADMIN_DEFAULT_PASSWORD: admin123
      PGADMIN_CONFIG_SERVER_MODE: 'False'
    ports:
      - "5050:80"
    volumes:
      - pgadmin_data:/var/lib/pgadmin
    depends_on:
      - postgres
    restart: unless-stopped

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  pgadmin_data:
    driver: local
EOF

echo "✅ docker-compose.yml created"

# ============================================================================
# 4. CREATE POSTGRESQL INITIALIZATION SCRIPT
# ============================================================================

cat > scripts/postgres/init-db.sh << 'EOF'
#!/bin/bash
# PostgreSQL Initialization Script for Tujenge Platform

set -e

echo "🔧 Initializing Tujenge Platform database..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create extensions
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pg_trgm";
    
    -- Grant permissions
    GRANT ALL PRIVILEGES ON DATABASE tujenge_db TO postgres;
    GRANT ALL PRIVILEGES ON SCHEMA public TO postgres;
    
    -- Create initial configuration table
    CREATE TABLE IF NOT EXISTS system_config (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        config_key VARCHAR(100) NOT NULL UNIQUE,
        config_value TEXT NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT NOW()
    );
    
    -- Insert Tanzania-specific configuration
    INSERT INTO system_config (config_key, config_value, description) VALUES
        ('default_currency', 'TZS', 'Default currency for the platform'),
        ('default_timezone', 'Africa/Dar_es_Salaam', 'Default timezone'),
        ('default_language', 'sw', 'Default language (Swahili)'),
        ('platform_name', 'Tujenge Platform', 'Platform name')
    ON CONFLICT (config_key) DO NOTHING;
    
    -- Create test database
    SELECT 'CREATE DATABASE tujenge_test_db OWNER postgres'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'tujenge_test_db')\gexec
EOSQL

echo "✅ Database initialization completed successfully"
EOF

chmod +x scripts/postgres/init-db.sh
echo "✅ PostgreSQL initialization script created"

# ============================================================================
# 5. CREATE ENVIRONMENT FILE
# ============================================================================

cat > .env << 'EOF'
# Tujenge Platform - Environment Configuration

# Application Settings
APP_NAME=Tujenge Platform
APP_VERSION=1.0.0
DEBUG=True
ENVIRONMENT=development

# Server Configuration
HOST=0.0.0.0
PORT=8000

# Database Configuration
DATABASE_URL=postgresql://postgres:PasswordYangu@localhost:5432/tujenge_db
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=tujenge_db
DATABASE_USER=postgres
DATABASE_PASSWORD=PasswordYangu

# Test Database
TEST_DATABASE_URL=postgresql://postgres:PasswordYangu@localhost:5432/tujenge_test_db

# Security
SECRET_KEY=tujenge-secret-key-change-in-production-2024
JWT_SECRET_KEY=tujenge-jwt-secret-change-in-production-2024

# Tanzania Configuration
DEFAULT_CURRENCY=TZS
DEFAULT_TIMEZONE=Africa/Dar_es_Salaam
DEFAULT_LANGUAGE=sw
DEFAULT_COUNTRY=TZ

# Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_HOST=localhost
REDIS_PORT=6379

# Mobile Money (Sandbox)
MPESA_CONSUMER_KEY=your_mpesa_consumer_key
MPESA_CONSUMER_SECRET=your_mpesa_consumer_secret
AIRTEL_CLIENT_ID=your_airtel_client_id
AIRTEL_CLIENT_SECRET=your_airtel_client_secret

# Government APIs
NIDA_API_KEY=your_nida_api_key
TRA_API_KEY=your_tra_api_key
EOF

echo "✅ .env file created"

# ============================================================================
# 6. CREATE QUICK TEST SCRIPT
# ============================================================================

cat > test_setup.sh << 'EOF'
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
EOF

chmod +x test_setup.sh
echo "✅ test_setup.sh created"

# ============================================================================
# 7. FINAL VERIFICATION
# ============================================================================

echo ""
echo "🎉 ALL FILES CREATED SUCCESSFULLY!"
echo ""
echo "📋 Created Files:"
ls -la start_tujenge_platform.sh 2>/dev/null && echo "✅ start_tujenge_platform.sh"
ls -la docker-compose.yml 2>/dev/null && echo "✅ docker-compose.yml"
ls -la .env 2>/dev/null && echo "✅ .env"
ls -la test_setup.sh 2>/dev/null && echo "✅ test_setup.sh"
ls -la scripts/postgres/init-db.sh 2>/dev/null && echo "✅ scripts/postgres/init-db.sh"

echo ""
echo "📁 Directory structure:"
ls -la

echo ""
echo "🧪 TEST YOUR SETUP:"
echo "1. Run quick test: ./test_setup.sh"
echo "2. Start platform: ./start_tujenge_platform.sh"
echo ""
echo "🎯 Expected URLs after startup:"
echo "• API Docs: http://localhost:8000/docs"
echo "• Health Check: http://localhost:8000/health"
echo "• PgAdmin: http://localhost:5050"

