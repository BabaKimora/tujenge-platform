# 🏦 Tujenge Platform

**Tanzania Enterprise Fintech Solution** 🇹🇿

A comprehensive fintech platform specifically designed for Tanzania's financial services market, providing enterprise-grade customer management, government API integration, and regulatory compliance.

## 🌟 Features

### 🏦 Core Banking Services
- **Customer Management**: Complete lifecycle management with Tanzania KYC compliance
- **Loan Management**: Risk-based lending with BOT regulatory compliance
- **Transaction Processing**: Real-time transaction handling and monitoring
- **Account Management**: Multi-currency support (TZS primary)

### 🇹🇿 Tanzania-Specific Features
- **NIDA Integration**: Real-time National ID verification with government database
- **TIN Validation**: Tax ID verification with Tanzania Revenue Authority (TRA)
- **Mobile Money**: M-Pesa and Airtel Money integration ready
- **Regional Support**: All Tanzania regions, districts, and wards
- **Multi-language**: Swahili and English support

### 🛡️ Compliance & Security
- **BOT Compliance**: Bank of Tanzania regulatory requirements
- **AML/CFT**: Anti-Money Laundering and Counter-Financing Terrorism
- **KYC**: Enhanced Know Your Customer with risk scoring
- **Data Protection**: Tanzania Data Protection Act compliance
- **Audit Logging**: Banking-grade audit trails

### 🔧 Technical Features
- **Redis Caching**: High-performance caching with intelligent fallback
- **Enterprise Security**: JWT authentication and authorization
- **API Rate Limiting**: Protection against abuse
- **Monitoring**: Prometheus metrics and health checks
- **Documentation**: Comprehensive API documentation

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 13+
- Redis 6+ (optional, has memory fallback)
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/tujenge-platform.git
   cd tujenge-platform
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the application**
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```

6. **Access the platform**
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

## 📊 API Endpoints

### Core Platform
- `GET /` - Platform information
- `GET /health` - Health monitoring
- `GET /docs` - Interactive API documentation

### Customer Management
- `POST /api/v1/customers/` - Create customer
- `GET /api/v1/customers/` - List customers
- `GET /api/v1/customers/{id}` - Get customer details
- `POST /api/v1/customers/{id}/verify-nida` - NIDA verification
- `GET /api/v1/customers/{id}/loan-eligibility` - Loan assessment
- `GET /api/v1/customers/analytics/summary` - Analytics dashboard

### Government Integration
- NIDA validation with caching
- TIN verification with TRA integration
- Compliance scoring and monitoring

## 🏗️ Architecture

```
Tujenge Platform/
├── 🏗️ FastAPI Backend
├── 🛡️ Security Layer (JWT + validation)
├── 📊 Customer Management (Tanzania-specific)
├── 🏛️ Government API Integration (NIDA/TIN)
├── 📝 Audit Logging (Banking compliance)
├── 🗄️ Redis Caching (with fallback)
└── ✅ Tanzania Regulatory Compliance
```

### Key Components

- **Backend API**: FastAPI with async/await support
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Caching**: Redis with intelligent memory fallback
- **Authentication**: JWT-based secure authentication
- **Validation**: Pydantic models with Tanzania-specific validation
- **Monitoring**: Prometheus metrics and structured logging

## 🇹🇿 Tanzania Compliance

### Regulatory Frameworks
- **Bank of Tanzania (BOT)**: Microfinance and digital lending compliance
- **Tanzania Revenue Authority (TRA)**: TIN validation and tax compliance
- **National Identification Authority (NIDA)**: National ID verification
- **Data Protection**: Tanzania Data Protection Act compliance

### Features
- Real-time compliance scoring
- Automated risk assessment
- Regulatory reporting
- Customer protection measures

## 🔧 Configuration

### Environment Variables

```env
# Application
APP_NAME=Tujenge Platform
APP_VERSION=1.0.0
DEBUG=True
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://user:password@localhost/tujenge
POSTGRES_USER=tujenge
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=tujenge

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=jwt-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# Tanzania Government APIs
NIDA_API_URL=https://nida.go.tz/api
NIDA_API_KEY=your-nida-api-key
TIN_API_URL=https://tra.go.tz/api
TIN_API_KEY=your-tin-api-key

# Mobile Money
MPESA_API_KEY=your-mpesa-api-key
AIRTEL_API_KEY=your-airtel-api-key
```

## 🧪 Testing

### Run Tests
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=backend

# Run specific test file
pytest tests/test_customer_management.py
```

### Test Coverage
- Unit tests for all core components
- Integration tests for API endpoints
- Government API mocking for development

## 📈 Monitoring

### Health Checks
- Application health: `/health`
- Database connectivity
- Redis connectivity
- External API status

### Metrics
- Customer registration rates
- Transaction volumes
- API response times
- Compliance scores
- Error rates

## 🚀 Deployment

### Docker Deployment
```bash
# Build image
docker build -t tujenge-platform .

# Run container
docker-compose up -d
```

### Production Checklist
- [ ] Set up PostgreSQL database
- [ ] Configure Redis server
- [ ] Obtain NIDA API credentials
- [ ] Obtain TIN API credentials
- [ ] Set up SSL/TLS certificates
- [ ] Configure environment variables
- [ ] Set up monitoring and logging
- [ ] Implement backup strategy

## 📝 Development

### Code Style
```bash
# Format code
black .

# Sort imports
isort .

# Lint code
flake8 .

# Type checking
mypy .
```

### Pre-commit Hooks
```bash
# Install pre-commit hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

## 📚 Documentation

- **API Documentation**: Available at `/docs` when running
- **Architecture**: See `docs/architecture.md`
- **Deployment Guide**: See `docs/deployment.md`
- **Tanzania Compliance**: See `docs/compliance.md`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup
```bash
# Clone your fork
git clone https://github.com/yourusername/tujenge-platform.git
cd tujenge-platform

# Install development dependencies
pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install

# Run tests
pytest
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/yourusername/tujenge-platform/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/tujenge-platform/discussions)

## 🙏 Acknowledgments

- Tanzania Government for API specifications
- Bank of Tanzania for regulatory guidance
- FastAPI community for the excellent framework
- Open source contributors

---

**Built with ❤️ for Tanzania's financial inclusion** 🇹🇿

*Tujenge - Let's Build Together* 