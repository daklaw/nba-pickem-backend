from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.models import Base
from app.core.config import settings

# PostgreSQL database URL from settings
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Create engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using them
    echo=settings.DEBUG  # Log SQL queries in debug mode
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency function to get database session.
    Use this in FastAPI route dependencies.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database - create all tables.
    Call this on application startup.
    """
    Base.metadata.create_all(bind=engine)