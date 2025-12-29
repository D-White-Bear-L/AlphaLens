"""Google search tool using Serper API."""
import httpx
from loguru import logger
from mira import LLMTool
from pydantic import Field

from app.config import settings


class GoogleSearch(LLMTool):
    """Search Google for information using Serper API.
    
    This tool allows you to search Google and retrieve relevant search results
    including titles, snippets, and URLs.
    """
    
    query: str = Field(..., description="Search query string")
    num_results: int = Field(default=10, ge=1, le=50, description="Number of results to return")
    
    @classmethod
    def schema(cls):
        """Override schema to fix required fields."""
        schema = super().schema()
        # Remove num_results from required since it has a default value
        if 'function' in schema and 'parameters' in schema['function']:
            params = schema['function']['parameters']
            if 'required' in params and 'num_results' in params['required']:
                params['required'].remove('num_results')
        return schema
    
    def __call__(self):
        """Execute Google search."""
        try:
            url = "https://google.serper.dev/search"
            headers = {
                "X-API-KEY": settings.serper_api_key,
                "Content-Type": "application/json"
            }
            payload = {
                "q": self.query,
                "num": self.num_results
            }
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
            
            # Format results
            results = []
            if "organic" in data:
                for item in data["organic"][:self.num_results]:
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "position": item.get("position", 0)
                    })
            
            logger.info(f"Google search completed: {len(results)} results for query '{self.query}'")
            
            return {
                "success": True,
                "query": self.query,
                "results": results,
                "total_results": len(results)
            }
            
        except Exception as e:
            logger.error(f"Google search failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "query": self.query,
                "results": []
            }

