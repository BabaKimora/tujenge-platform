#!/bin/bash

# ==========
# bootstrap.sh
# Cross-platform bootstrap for Cursor AI, Docker, and Python venv
# ==========

echo "🚀 Starting Bootstrap..."

# Detect OS
OS_TYPE="$(uname -s)"
case "$OS_TYPE" in
    Linux*)     OS=Linux;;
    Darwin*)    OS=Mac;;
    CYGWIN*|MINGW*|MSYS*) OS=Windows;;
    *)          OS="UNKNOWN"
esac
echo "🖥️ Detected OS: $OS"

# Set project root
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "📂 Project Root: $PROJECT_ROOT"

# --- STEP 1: Fix permissions ---
fix_permissions() {
    echo "🔧 Fixing permissions for $OS..."
    if [ "$OS" = "Mac" ] || [ "$OS" = "Linux" ]; then
        USER_ID=$(id -u)
        GROUP_ID=$(id -g)
        echo "👤 User: $(whoami) (UID: $USER_ID, GID: $GROUP_ID)"
        sudo chown -R $USER_ID:$GROUP_ID "$PROJECT_ROOT"
        chmod -R u+rwX "$PROJECT_ROOT"
        chmod -R go-rwx "$PROJECT_ROOT"
    elif [ "$OS" = "Windows" ]; then
        echo "⚡ Skipping chmod/chown on Windows (handled by NTFS ACLs)"
    else
        echo "❌ Unsupported OS for permission fixing"
    fi
}

# --- STEP 2: Set up Python virtual environment ---
setup_venv() {
    echo "🐍 Setting up Python virtual environment..."
    if command -v python3 >/dev/null 2>&1; then
        PYTHON=python3
    elif command -v python >/dev/null 2>&1; then
        PYTHON=python
    else
        echo "❌ Python not found. Install Python 3.x first."
        return
    fi

    if [ ! -d "$PROJECT_ROOT/venv" ]; then
        $PYTHON -m venv venv
        echo "✅ Virtual environment created"
    else
        echo "ℹ️ Virtual environment already exists"
    fi

    # Activate venv
    if [ "$OS" = "Windows" ]; then
        source venv/Scripts/activate
    else
        source venv/bin/activate
    fi

    # Install dependencies
    if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
        echo "📦 Installing Python dependencies..."
        pip install --upgrade pip
        pip install -r requirements.txt
    else
        echo "⚠️ No requirements.txt found, skipping pip install"
    fi
}

# --- STEP 3: Disable Git global hooks ---
disable_git_hooks() {
    echo "⛔ Disabling Git global hooks..."
    git config --global core.hooksPath /dev/null
}

# --- STEP 4: Docker build & up ---
docker_up() {
    echo "🐳 Checking Docker..."
    if ! command -v docker >/dev/null 2>&1; then
        echo "❌ Docker not installed. Install Docker Desktop first."
        return
    fi

    # Inject UID/GID into .env for Docker
    if [ "$OS" = "Mac" ] || [ "$OS" = "Linux" ]; then
        echo "UID=$(id -u)" > "$PROJECT_ROOT/.env"
        echo "GID=$(id -g)" >> "$PROJECT_ROOT/.env"
        echo "✅ Added UID/GID to .env for Docker"
    fi

    if [ -f "$PROJECT_ROOT/docker-compose.yml" ]; then
        echo "📦 Building and starting Docker containers..."
        docker compose up --build -d
        echo "✅ Docker containers are up"
    else
        echo "⚠️ No docker-compose.yml found, skipping Docker setup"
    fi
}

# --- STEP 5: Verify everything ---
verify() {
    echo "🔍 Verifying permissions..."
    ls -l "$PROJECT_ROOT" | head -n 10

    echo "🔍 Verifying Docker containers..."
    docker ps --format "table {{.Names}}\t{{.Status}}" || echo "⚠️ Docker not running"

    echo "🔍 Verifying Python venv..."
    if [ -n "$VIRTUAL_ENV" ]; then
        echo "✅ Virtual environment active: $VIRTUAL_ENV"
    else
        echo "⚠️ Virtual environment not active"
    fi
}

# --- RUN ALL STEPS ---
fix_permissions
setup_venv
disable_git_hooks
docker_up
verify

echo "🎉 Bootstrap complete. You’re ready to code in Cursor AI!"