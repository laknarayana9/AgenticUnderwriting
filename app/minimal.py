"""
Minimal application for testing without complex middleware.
"""

from fastapi import FastAPI
from config import settings


def create_minimal_app() -> FastAPI:
    """
    Create minimal FastAPI application for testing.
    """
    app = FastAPI(
        title=settings.title,
        description=settings.description,
        version=settings.version
    )
    
    @app.get("/health")
    async def health():
        return {"status": "healthy", "message": "Minimal app working"}
    
    @app.get("/")
    async def root():
        return {"message": "Agentic Quote-to-Underwrite API", "version": "1.0.0"}
    
    return app
