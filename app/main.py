"""
Main application entry point using factory pattern.
"""

from .factory import create_app

# Create application using factory
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
