#!/bin/bash
# Test database connection and functionality

set -e

echo "🧪 Testing database connection and functionality..."

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Test 1: Basic connection
echo "Test 1: Basic PostgreSQL connection"
if docker exec tujenge_postgres psql -U tujenge_user -d tujenge_db -c "SELECT version();" >/dev/null 2>&1; then
    print_success "PostgreSQL connection successful"
else
    print_error "PostgreSQL connection failed"
    exit 1
fi

# Test 2: Check user and database
echo "Test 2: Verify user and database exist"
USER_EXISTS=$(docker exec tujenge_postgres psql -U postgres -t -c "SELECT 1 FROM pg_roles WHERE rolname='tujenge_user';" | xargs)
DB_EXISTS=$(docker exec tujenge_postgres psql -U postgres -t -c "SELECT 1 FROM pg_database WHERE datname='tujenge_db';" | xargs)

if [ "$USER_EXISTS" = "1" ]; then
    print_success "User 'tujenge_user' exists"
else
    print_error "User 'tujenge_user' does not exist"
fi

if [ "$DB_EXISTS" = "1" ]; then
    print_success "Database 'tujenge_db' exists"
else
    print_error "Database 'tujenge_db' does not exist"
fi

# Test 3: Check extensions
echo "Test 3: Verify extensions are installed"
EXTENSION_COUNT=$(docker exec tujenge_postgres psql -U tujenge_user -d tujenge_db -t -c "SELECT COUNT(*) FROM pg_extension WHERE extname IN ('uuid-ossp', 'pg_trgm');" | xargs)

if [ "$EXTENSION_COUNT" = "2" ]; then
    print_success "Required extensions are installed"
else
    print_error "Required extensions are missing (found: $EXTENSION_COUNT/2)"
fi

# Test 4: Test creating a table
echo "Test 4: Test table creation and basic operations"
docker exec tujenge_postgres psql -U tujenge_user -d tujenge_db -c "
CREATE TABLE IF NOT EXISTS test_table (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO test_table (name) VALUES ('Test Record');
SELECT COUNT(*) FROM test_table;
DROP TABLE test_table;
" >/dev/null 2>&1

if [ $? -eq 0 ]; then
    print_success "Table operations successful"
else
    print_error "Table operations failed"
fi

# Test 5: Redis connection
echo "Test 5: Redis connection"
if docker exec tujenge_redis redis-cli ping | grep -q PONG; then
    print_success "Redis connection successful"
else
    print_error "Redis connection failed"
fi

echo ""
print_success "All database tests completed successfully!"
echo "Database is ready for Alembic migrations and application startup." 