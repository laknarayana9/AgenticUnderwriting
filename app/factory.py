"""
Application factory to avoid circular imports.
"""

from fastapi import FastAPI
from config import settings
from metrics_dashboard import create_dashboard_routes


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    """
    # Initialize FastAPI app
    app = FastAPI(
        title=settings.title,
        description=settings.description,
        version=settings.version
    )
    
    # Add middleware with error handling
    try:
        # Security headers
        from security import security_headers_middleware
        app.middleware("http")(security_headers_middleware)
        
        # Monitoring
        from monitoring import monitoring_middleware
        app.middleware("http")(monitoring_middleware)
        
        # CORS
        from fastapi.middleware.cors import CORSMiddleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=settings.cors_allow_credentials,
            allow_methods=settings.cors_allow_methods,
            allow_headers=settings.cors_allow_headers,
        )
        
    except Exception as e:
        print(f"Warning: Middleware setup failed: {e}")
        # Continue without problematic middleware
    
    # Mount static files
    try:
        from fastapi.staticfiles import StaticFiles
        import os
        if os.path.exists("static"):
            app.mount("/static", StaticFiles(directory="static"), name="static")
    except Exception as e:
        print(f"Warning: Static files mount failed: {e}")
    
    # Add dashboard routes
    try:
        create_dashboard_routes(app)
    except Exception as e:
        print(f"Warning: Dashboard routes setup failed: {e}")
    
    # Add monitoring endpoints
    try:
        from monitoring import health_endpoint, metrics_endpoint
        app.add_route("/metrics", metrics_endpoint, methods=["GET"])
        app.add_route("/health", health_endpoint, methods=["GET"])
    except Exception as e:
        print(f"Warning: Monitoring endpoints setup failed: {e}")
    
    # Lazy load API routes to avoid circular imports
    @app.on_event("startup")
    def load_routes():
        try:
            from .api import router as quote_router
            from .runs import router as runs_router
            app.include_router(quote_router, prefix="/quote")
            app.include_router(runs_router, prefix="/runs")
        except Exception as e:
            print(f"Warning: API routes loading failed: {e}")
    
    # Initialize production components
    @app.on_event("startup")
    def startup_event():
        try:
            from .startup import initialize_production
            initialize_production()
        except Exception as e:
            print(f"Warning: Production initialization failed: {e}")
    
    @app.on_event("shutdown")
    def shutdown_event():
        try:
            from .startup import cleanup_production
            cleanup_production()
        except Exception as e:
            print(f"Warning: Production cleanup failed: {e}")
    
    return app
