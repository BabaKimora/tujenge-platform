-- Create test database for running tests
-- This ensures tests don't interfere with development data

-- Connect as the main user to create test database
\c tujenge_db postgres;

-- Create test database
SELECT 'CREATE DATABASE tujenge_test_db OWNER postgres'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'tujenge_test_db')\gexec

-- Connect to test database and set it up
\c tujenge_test_db postgres;

-- Create same extensions in test database
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create the same custom types
CREATE TYPE customer_status AS ENUM ('pending', 'verified', 'active', 'suspended', 'blocked', 'inactive');
CREATE TYPE transaction_type AS ENUM ('deposit', 'withdrawal', 'transfer', 'payment', 'fee', 'interest');
CREATE TYPE loan_status AS ENUM ('pending', 'approved', 'disbursed', 'active', 'completed', 'defaulted', 'written_off'); 