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
