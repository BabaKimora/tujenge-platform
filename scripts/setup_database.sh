#!/bin/bash
# Tujenge Platform - Database Setup and Verification Script

set -e

echo "🔧 Setting up Tujenge Platform database..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Function to wait for PostgreSQL to be ready
wait_for_postgres() {
    print_info "Waiting for PostgreSQL to be ready..."
    
    for i in {1..30}; do
        if docker exec tujenge_postgres pg_isready -U postgres -d tujenge_db >/dev/null 2>&1; then
            print_status "PostgreSQL is ready!"
            return 0
        fi
        echo "Waiting... ($i/30)"
        sleep 2
    done
    
    print_error "PostgreSQL failed to start after 60 seconds"
    return 1
}

# Function to verify database setup
verify_database() {
    print_info "Verifying database setup..."
    
    # Test database connection
    if docker exec tujenge_postgres psql -U postgres -d tujenge_db -c "SELECT 1;" >/dev/null 2>&1; then
        print_status "Database connection successful"
    else
        print_error "Database connection failed"
        return 1
    fi
    
    # Check if extensions are installed
    EXTENSIONS=$(docker exec tujenge_postgres psql -U postgres -d tujenge_db -t -c "SELECT COUNT(*) FROM pg_extension WHERE extname IN ('uuid-ossp', 'pg_trgm');")
    if [ "$EXTENSIONS" -ge 2 ]; then
        print_status "Required extensions are installed"
    else
        print_warning "Some extensions may be missing"
    fi
    
    # Check if test database exists
    if docker exec tujenge_postgres psql -U postgres -d tujenge_test_db -c "SELECT 1;" >/dev/null 2>&1; then
        print_status "Test database is available"
    else
        print_warning "Test database may not be available"
    fi
}

# Main execution
echo "Starting database setup process..."

# Step 1: Start PostgreSQL and Redis
print_info "Starting PostgreSQL and Redis services..."
docker-compose up -d postgres redis

# Step 2: Wait for PostgreSQL to be ready
if ! wait_for_postgres; then
    print_error "Database setup failed"
    exit 1
fi

# Step 3: Verify database setup
if ! verify_database; then
    print_warning "Database verification had issues, but continuing..."
fi

# Step 4: Display connection information
print_status "Database setup completed successfully!"
echo ""
echo "📊 Database Information:"
echo "• Host: localhost"
echo "• Port: 5432"
echo "• Database: tujenge_db"
echo "• User: postgres"
echo "• Password: PasswordYangu"
echo "• Test Database: tujenge_test_db"
echo ""
echo "🔗 Admin Interfaces:"
echo "• PgAdmin: http://localhost:5050 (admin@tujenge.co.tz / admin123)"
echo "• Redis Commander: http://localhost:8081"
echo ""
echo "🚀 Next Steps:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Run migrations: alembic upgrade head"
echo "3. Start API server: uvicorn backend.main:app --reload" 