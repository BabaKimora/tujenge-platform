"""
Tujenge Platform - Database Management
Async database setup and connection management using SQLAlchemy
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from backend.core.config import settings

# Create declarative base for models
Base = declarative_base()

DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(DATABASE_URL, echo=settings.DEBUG)
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

class DBManager:
    def __init__(self):
        self.engine = engine
        self.session_factory = AsyncSessionLocal

    async def get_session(self):
        async with self.session_factory() as session:
            yield session

    async def close(self):
        await self.engine.dispose()

    async def health_check(self):
        try:
            async with self.engine.connect() as conn:
                await conn.execute("SELECT 1")
            return {"status": "healthy", "database": "postgresql"}
        except SQLAlchemyError as e:
            return {"status": "unhealthy", "database": "postgresql", "error": str(e)}

db_manager = DBManager()

# Dependency for getting database session
async def get_async_db() -> AsyncSession:
    """Dependency for getting async database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Alias for backwards compatibility
get_db = get_async_db

async def init_database():
    """Initialize database tables"""
    # Import all models to ensure they're registered with Base
    from backend.models.customer import Customer
    from backend.models.user import User
    from backend.models.tenant import Tenant
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ Database tables created successfully") 