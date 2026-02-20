"""
Configuration settings for the Agentic Quote-to-Underwrite API.
"""
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # API Configuration
    title: str = Field(
        default="Agentic Quote-to-Underwrite API",
        description="API title"
    )
    description: str = Field(
        default="An agentic workflow for insurance quote processing and underwriting",
        description="API description"
    )
    version: str = Field(
        default="1.0.0",
        description="API version"
    )
    
    # CORS Configuration
    cors_origins: List[str] = Field(
        default=["*"],
        description="Allowed origins for CORS. Use ['*'] for development, specific domains for production"
    )
    cors_allow_credentials: bool = Field(
        default=True,
        description="Allow credentials in CORS requests"
    )
    cors_allow_methods: List[str] = Field(
        default=["*"],
        description="Allowed HTTP methods for CORS"
    )
    cors_allow_headers: List[str] = Field(
        default=["*"],
        description="Allowed headers for CORS"
    )
    
    # Database Configuration
    database_path: str = Field(
        default="storage/underwriting.db",
        description="Path to SQLite database"
    )
    
    # RAG Configuration
    chroma_path: str = Field(
        default="./storage/chroma_db",
        description="Path to ChromaDB storage"
    )
    data_directory: str = Field(
        default="data/guidelines",
        description="Directory containing guideline documents"
    )
    
    # API Server Configuration
    host: str = Field(
        default="0.0.0.0",
        description="Host to bind the server to"
    )
    port: int = Field(
        default=8000,
        description="Port to run the server on"
    )
    
    model_config = {
        "env_file": ".env", 
        "env_file_encoding": "utf-8",
        "extra": "allow"  # Allow extra fields from environment
    }


# Development vs Production configurations
class DevelopmentSettings(Settings):
    """Development-specific settings."""
    
    cors_origins: List[str] = ["*"]
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]
    debug: bool = True
    log_level: str = "debug"


class ProductionSettings(Settings):
    """Production-specific settings."""
    
    # Restrict CORS to specific domains in production
    cors_origins: List[str] = [
        "https://your-frontend.com",
        "https://admin.your-frontend.com",
        "https://api.your-frontend.com"
    ]
    cors_allow_methods: List[str] = ["GET", "POST", "PUT", "DELETE"]
    cors_allow_headers: List[str] = ["Content-Type", "Authorization", "X-API-Key"]
    debug: bool = False
    log_level: str = "info"


def get_settings() -> Settings:
    """Get appropriate settings based on environment."""
    import os
    from pathlib import Path
    
    # Try to get environment from ENVIRONMENT variable or default to development
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    # Load environment-specific file if it exists
    env_file = f".env.{env}"
    if Path(env_file).exists():
        print(f"Loading {env_file} configuration...")
        os.environ.setdefault("ENV_FILE", env_file)
    
    if env == "production":
        return ProductionSettings()
    else:
        return DevelopmentSettings()


# Global settings instance
settings = get_settings()
