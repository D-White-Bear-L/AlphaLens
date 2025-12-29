"""Database search tool."""
from typing import List, Optional

from loguru import logger
from mira import LLMTool
from pydantic import Field

# Try to import sqlalchemy, but make it optional
try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    logger.warning("sqlalchemy not installed, DatabaseSearch will return empty results")

from app.config import settings


class DatabaseSearch(LLMTool):
    """Search the database for stored news articles and sources.
    
    This tool allows you to query the database using natural language or SQL-like queries
    to find relevant news articles and sources that have been previously stored.
    """
    
    query: str = Field(..., description="Search query (natural language or SQL-like)")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    
    def __call__(self):
        """Execute database search."""
        # If sqlalchemy is not available, return empty results
        if not SQLALCHEMY_AVAILABLE:
            logger.info(f"Database search skipped (sqlalchemy not installed) for query '{self.query}'")
            return {
                "success": True,
                "query": self.query,
                "results": [],
                "total_results": 0,
                "note": "Database search is disabled (sqlalchemy not installed)"
            }
        
        try:
            engine = create_engine(settings.database_url, echo=False)
            Session = sessionmaker(bind=engine)
            session = Session()
            
            # For now, we'll use a simple text search approach
            # In production, you'd want to use full-text search or vector search
            sql_query = text("""
                SELECT url, title, snippet, published_date, author, created_at
                FROM news_articles
                WHERE title LIKE :pattern OR snippet LIKE :pattern
                ORDER BY created_at DESC
                LIMIT :limit
            """)
            
            pattern = f"%{self.query}%"
            results = session.execute(
                sql_query,
                {"pattern": pattern, "limit": self.limit}
            ).fetchall()
            
            session.close()
            
            # Format results
            formatted_results = []
            for row in results:
                formatted_results.append({
                    "url": row[0],
                    "title": row[1],
                    "snippet": row[2],
                    "published_date": str(row[3]) if row[3] else None,
                    "author": row[4],
                    "stored_at": str(row[5]) if row[5] else None
                })
            
            logger.info(f"Database search completed: {len(formatted_results)} results for query '{self.query}'")
            
            return {
                "success": True,
                "query": self.query,
                "results": formatted_results,
                "total_results": len(formatted_results)
            }
            
        except Exception as e:
            # If table doesn't exist, return empty results
            if "no such table" in str(e).lower():
                logger.warning(f"Database table not found, returning empty results: {str(e)}")
                return {
                    "success": True,
                    "query": self.query,
                    "results": [],
                    "total_results": 0,
                    "note": "Database table not initialized yet"
                }
            
            logger.error(f"Database search failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "query": self.query,
                "results": []
            }

