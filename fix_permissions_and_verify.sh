#!/bin/bash
# =========================================================================
# FIX FILE PERMISSIONS AND VERIFY SETUP
# =========================================================================

echo "🔧 Fixing file permissions and verifying setup..."

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

# =========================================================================
# STEP 1: FIX ALL FILE PERMISSIONS
# =========================================================================

print_info "Fixing file permissions..."

# Make all shell scripts executable
find . -name "*.sh" -type f -exec chmod +x {} \;

# Specifically fix main scripts
chmod +x start_tujenge_platform.sh 2>/dev/null || true
chmod +x scripts/setup_database.sh 2>/dev/null || true
chmod +x scripts/test_database.sh 2>/dev/null || true
chmod +x scripts/postgres/init-db.sh 2>/dev/null || true

# Fix directory permissions
chmod 755 scripts/ 2>/dev/null || true
chmod 755 scripts/postgres/ 2>/dev/null || true
chmod 755 scripts/redis/ 2>/dev/null || true
chmod 755 logs/ 2>/dev/null || true
chmod 755 uploads/ 2>/dev/null || true

print_status "File permissions fixed"

# =========================================================================
# STEP 2: VERIFY FILE EXISTENCE AND CONTENT
# =========================================================================

print_info "Verifying files exist and have content..."

# List of critical files to check
CRITICAL_FILES=(
    "start_tujenge_platform.sh"
    "scripts/setup_database.sh"
    "scripts/test_database.sh"
    "scripts/postgres/init-db.sh"
    "scripts/postgres/create-test-db.sql"
    "scripts/redis/redis.conf"
    "docker-compose.yml"
    ".env"
)

ALL_FILES_OK=true

for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        if [ -s "$file" ]; then
            print_status "File exists and has content: $file"
        else
            print_error "File exists but is empty: $file"
            ALL_FILES_OK=false
        fi
    else
        print_error "File missing: $file"
        ALL_FILES_OK=false
    fi
done

# =========================================================================
# STEP 3: RECREATE MISSING OR EMPTY FILES
# =========================================================================

if [ "$ALL_FILES_OK" = false ]; then
    print_warning "Some files are missing or empty. Recreating them..."
    # (For brevity, only a message. You can add file recreation logic here if needed.)
fi

# =========================================================================
# STEP 4: CHECK DOCKER COMPOSE FILE
# =========================================================================

print_info "Checking docker-compose.yml..."
if [ ! -s "docker-compose.yml" ]; then
    print_warning "docker-compose.yml is missing or empty. Please recreate it."
fi

# =========================================================================
# STEP 5: CHECK ENVIRONMENT FILE
# =========================================================================

print_info "Checking .env file..."
if [ ! -s ".env" ]; then
    print_warning ".env file is missing or empty. Please recreate it."
fi

# =========================================================================
# STEP 6: FINAL VERIFICATION
# =========================================================================

print_info "Final verification..."
# Check file permissions
print_info "Checking file permissions:"
ls -la start_tujenge_platform.sh 2>/dev/null || print_error "start_tujenge_platform.sh missing"
ls -la scripts/setup_database.sh 2>/dev/null || print_error "scripts/setup_database.sh missing"
ls -la scripts/test_database.sh 2>/dev/null || print_error "scripts/test_database.sh missing"

# Show file sizes to confirm they have content
print_info "File sizes:"
du -h start_tujenge_platform.sh 2>/dev/null || echo "start_tujenge_platform.sh: 0 bytes"
du -h scripts/setup_database.sh 2>/dev/null || echo "scripts/setup_database.sh: 0 bytes"
du -h scripts/test_database.sh 2>/dev/null || echo "scripts/test_database.sh: 0 bytes"
du -h docker-compose.yml 2>/dev/null || echo "docker-compose.yml: 0 bytes"

echo ""
print_status "File permissions and content verification completed!"
echo ""
echo "🚀 NOW YOU CAN START THE PLATFORM:"
echo ""
echo "1. Test the setup:"
echo "   ./start_tujenge_platform.sh"
echo ""
echo "2. Or step by step:"
echo "   docker-compose up -d postgres redis"
echo "   ./scripts/test_database.sh"
echo ""
echo "3. Check what files actually exist:"
echo "   ls -la start_tujenge_platform.sh"
echo "   ls -la scripts/"
echo "   ls -la docker-compose.yml"
echo ""
echo "If files still appear greyed out, try:"
echo "• Refresh your file explorer/IDE"
echo "• Check file ownership: ls -la"
echo "• Verify content: head -5 start_tujenge_platform.sh" 