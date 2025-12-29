"""Configuration management for the application."""
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables from .env file
# Try to find .env file in multiple locations
env_paths = [
    Path(__file__).parent.parent / ".env",  # backend/.env
    Path(__file__).parent.parent.parent / ".env",  # finhub/new_trace/.env
    Path(__file__).parent.parent.parent.parent / ".env",  # finhub/.env
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break
else:
    # If no .env found, try loading from current directory
    load_dotenv()


class Settings(BaseModel):
    """Application settings loaded from .env file.
    
    Supports multiple API providers:
    - ONEAPI (ONEAPI_API_KEY, ONEAPI_BASE_URL)
    - OPENROUTER (OPENROUTER_API_KEY, OPENROUTER_BASE_URL)
    - OPENAI (OPENAI_API_KEY, OPENAI_BASE_URL)
    - ARK/DOUBAO (ARK_API_KEY, ARK_BASE_URL)
    """
    
    # API Provider Selection
    api_provider: str = Field(
        default_factory=lambda: os.getenv("API_PROVIDER", "ONEAPI"),
        description="API provider to use: ONEAPI, OPENROUTER, OPENAI, ARK"
    )
    
    # ONEAPI Configuration
    oneapi_api_key: str = Field(
        default_factory=lambda: os.getenv("ONEAPI_API_KEY", ""),
        description="One-API key from .env file"
    )
    oneapi_base_url: str = Field(
        default_factory=lambda: os.getenv("ONEAPI_BASE_URL", "https://unifyapi.zeabur.app/v1"),
        description="One-API base URL from .env file"
    )
    
    # OpenRouter Configuration
    openrouter_api_key: str = Field(
        default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""),
        description="OpenRouter API key from .env file"
    )
    openrouter_base_url: str = Field(
        default_factory=lambda: os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        description="OpenRouter base URL from .env file"
    )
    
    # OpenAI Configuration
    openai_api_key: str = Field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", ""),
        description="OpenAI API key from .env file"
    )
    openai_base_url: str = Field(
        default_factory=lambda: os.getenv("OPENAI_BASE_URL", "https://api.openai-proxy.com/v1"),
        description="OpenAI base URL from .env file"
    )
    
    # ARK/Doubao Configuration
    ark_api_key: str = Field(
        default_factory=lambda: os.getenv("ARK_API_KEY", ""),
        description="ARK/Doubao API key from .env file"
    )
    ark_base_url: str = Field(
        default_factory=lambda: os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
        description="ARK/Doubao base URL from .env file"
    )
    
    # Model Configuration
    model: str = Field(
        default_factory=lambda: os.getenv("MODEL", "qwen*/qwen3-8b"),
        description="Model name to use"
    )
    
    # Serper API Configuration
    serper_api_key: str = Field(
        default_factory=lambda: os.getenv("SERPER_API_KEY", ""),
        description="Serper API key from .env file"
    )
    
    # Database Configuration
    database_url: str = Field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./news_trace.db"),
        description="Database URL from .env file"
    )
    
    # Server Configuration
    host: str = Field(
        default_factory=lambda: os.getenv("HOST", "0.0.0.0"),
        description="Server host from .env file"
    )
    port: int = Field(
        default_factory=lambda: int(os.getenv("PORT", "8000")),
        description="Server port from .env file"
    )
    
    def get_api_key(self) -> str:
        """Get API key based on selected provider."""
        provider = self.api_provider.upper()
        if provider == "ONEAPI":
            return self.oneapi_api_key
        elif provider == "OPENROUTER":
            return self.openrouter_api_key
        elif provider == "OPENAI":
            return self.openai_api_key
        elif provider == "ARK":
            return self.ark_api_key
        else:
            return self.oneapi_api_key  # Default to ONEAPI
    
    def get_base_url(self) -> str:
        """Get base URL based on selected provider."""
        provider = self.api_provider.upper()
        if provider == "ONEAPI":
            return self.oneapi_base_url
        elif provider == "OPENROUTER":
            return self.openrouter_base_url
        elif provider == "OPENAI":
            return self.openai_base_url
        elif provider == "ARK":
            return self.ark_base_url
        else:
            return self.oneapi_base_url  # Default to ONEAPI
    
    class Config:
        """Pydantic config."""
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"


# Create settings instance - will automatically load from .env file
settings = Settings()

