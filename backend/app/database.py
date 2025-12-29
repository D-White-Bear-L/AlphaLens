"""Database initialization and models."""
from datetime import datetime
from loguru import logger

# Try to import sqlalchemy, but make it optional
try:
    from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    SQLALCHEMY_AVAILABLE = True
    Base = declarative_base()
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    Base = None
    logger.warning("sqlalchemy not installed, database features will be disabled")

from app.config import settings


class NewsArticle(Base):
    """News article model for database storage."""
    __tablename__ = "news_articles"
    
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    snippet = Column(Text)
    content = Column(Text)
    published_date = Column(DateTime)
    author = Column(String)
    source_domain = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_database():
    """Initialize the database and create tables."""
    if not SQLALCHEMY_AVAILABLE:
        logger.warning("Cannot initialize database: sqlalchemy not installed")
        return None
    
    engine = create_engine(settings.database_url, echo=False)
    Base.metadata.create_all(bind=engine)
    return engine


def get_session():
    """Get a database session."""
    if not SQLALCHEMY_AVAILABLE:
        logger.warning("Cannot get database session: sqlalchemy not installed")
        return None
    
    engine = create_engine(settings.database_url, echo=False)
    Session = sessionmaker(bind=engine)
    return Session()

