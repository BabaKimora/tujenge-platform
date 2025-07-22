# Tujenge Platform - Quick Setup Guide

## 🚀 Quick Start with Cursor AI

### 1. Copy Project Structure
```bash
# Run the complete setup script
bash setup_complete.sh
```

### 2. Environment Setup
```bash
# Navigate to project directory
cd tujenge-platform

# Run development setup
./scripts/setup_dev.sh

# Update .env file with your configuration
# Edit database credentials, API keys, etc.
```

### 3. Database Setup
```bash
# Start PostgreSQL and Redis (using Docker)
docker-compose up -d postgres redis

# Run database migrations
alembic upgrade head
```

### 4. Start Development Server
```bash
# Option 1: Direct Python
./scripts/start_dev.sh

# Option 2: Using Docker Compose
docker-compose up -d

# Option 3: Manual uvicorn
source venv/bin/activate
uvicorn backend.main:app --reload
```

### 5. Verify Installation
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- Admin Interface: http://localhost:8000/admin (coming soon)

## 🛠️ Development Workflow

### Using Cursor AI
1. Open the project in Cursor AI
2. Use Ctrl+K to ask questions about the codebase
3. Reference the schemas and models when building features
4. Use the existing API structure to add new endpoints

### Key Files to Understand
- `backend/main.py` - Main FastAPI application
- `backend/models/` - Database models
- `backend/api/` - API endpoints
- `backend/schemas/` - Pydantic validation models
- `backend/core/config.py` - Configuration management

### Next Development Steps
1. Complete the customer management module
2. Implement NIDA verification service
3. Add M-Pesa integration
4. Build loan management system
5. Add risk assessment algorithms

## 🧪 Testing

### Run Tests
```bash
# All tests
./scripts/test.sh

# Specific test types
./scripts/test.sh unit
./scripts/test.sh integration
./scripts/test.sh coverage
```

### Test Coverage
Tests are organized in:
- `tests/unit/` - Unit tests
- `tests/integration/` - Integration tests
- `tests/api/` - API endpoint tests

## 📊 Monitoring

### Development Monitoring
- Flower (Celery): http://localhost:5555
- API Health: http://localhost:8000/health
- Database: PostgreSQL on port 5432
- Cache: Redis on port 6379

## 🔧 Configuration

### Environment Variables
Key variables in `.env`:
- `DATABASE_URL` - PostgreSQL connection
- `REDIS_URL` - Redis connection
- `MPESA_*` - M-Pesa API credentials
- `NIDA_*` - NIDA API credentials
- `SECRET_KEY` - Application secret

### Tanzania-Specific Settings
- Currency: TZS (Tanzanian Shilling)
- Timezone: Africa/Dar_es_Salaam
- Default Language: Swahili (sw)
- Phone Format: +255XXXXXXXXX

## 🚨 Troubleshooting

### Common Issues
1. **Database Connection Error**
   ```bash
   # Check if PostgreSQL is running
   docker-compose ps postgres
   
   # Restart if needed
   docker-compose restart postgres
   ```

2. **Redis Connection Error**
   ```bash
   # Check Redis status
   docker-compose ps redis
   
   # Test Redis connection
   redis-cli ping
   ```

3. **Migration Errors**
   ```bash
   # Reset migrations (development only)
   alembic downgrade base
   alembic upgrade head
   ```

### Development Tips for Cursor AI
1. Use `Ctrl+K` to ask about specific functions
2. Reference the existing models when creating new ones
3. Follow the established patterns in API routers
4. Use the logging system: `logger.info("message", key=value)`
5. Always validate input using Pydantic schemas

## 📱 Tanzania Mobile Money Integration

### M-Pesa Setup
1. Register at https://developer.safaricom.co.ke/
2. Get Consumer Key and Secret
3. Configure shortcode and passkey
4. Update `.env` with credentials

### Airtel Money Setup
1. Contact Airtel Money business team
2. Get API credentials
3. Configure callback URLs
4. Update `.env` with credentials

## 🏛️ Government API Integration

### NIDA Integration
1. Apply for NIDA API access
2. Get API credentials from NIDA
3. Configure endpoints in `.env`
4. Implement verification logic

### TRA Integration
1. Register with TRA for API access
2. Get TIN verification credentials
3. Configure API endpoints
4. Implement TIN validation

## 📈 Performance Optimization

### Database Optimization
- Use async queries everywhere
- Implement proper indexing
- Use connection pooling
- Cache frequent queries with Redis

### API Optimization
- Enable gzip compression
- Implement rate limiting
- Use response caching
- Optimize serialization

## 🔒 Security Best Practices

### Authentication
- Use JWT tokens with expiration
- Implement refresh token rotation
- Add rate limiting to auth endpoints
- Log all authentication attempts

### Data Protection
- Encrypt sensitive data at rest
- Use HTTPS in production
- Implement proper CORS policies
- Sanitize all user inputs

### Compliance
- Follow Bank of Tanzania guidelines
- Implement audit logging
- Add data retention policies
- Regular security assessments

## 📋 API Documentation

### Auto-Generated Docs
- OpenAPI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Custom Documentation
- Business logic in `docs/`
- API examples and tutorials
- Integration guides for partners

## 🤝 Contributing Guidelines

### Code Standards
- Follow Python PEP 8
- Use type hints everywhere
- Write comprehensive docstrings
- Add unit tests for new features

### Git Workflow
```bash
# Create feature branch
git checkout -b feature/customer-management

# Make changes and commit
git add .
git commit -m "feat: implement customer NIDA verification"

# Push and create PR
git push origin feature/customer-management
```

### Review Process
1. All code must be reviewed
2. Tests must pass
3. Documentation must be updated
4. Security review for sensitive changes

## 🌍 Localization

### Swahili Language Support
- Error messages in Swahili
- SMS notifications in Swahili
- User interface translations
- Currency formatting (TZS)

### Cultural Considerations
- Tanzania business hours
- Local holidays and calendar
- Regional variations
- Mobile money preferences

## 📞 Support and Maintenance

### Logging and Monitoring
- Structured logging with timestamps
- Error tracking with Sentry
- Performance monitoring
- Business metrics tracking

### Backup and Recovery
- Automated daily backups
- Point-in-time recovery
- Disaster recovery procedures
- Data retention policies

## 🎯 Business Logic Implementation

### Customer Lifecycle
1. Registration → NIDA Verification → KYC → Activation
2. Loan Application → Risk Assessment → Approval → Disbursement
3. Repayment → Collection → Account Management

### Risk Management
- Credit scoring algorithms
- Default prediction models
- Portfolio risk analytics
- Regulatory compliance monitoring

---

**Happy Coding with Cursor AI! 🚀**

For questions or issues:
- Check the documentation in `docs/`
- Review existing code patterns
- Use Cursor AI's code completion
- Test your changes thoroughly
