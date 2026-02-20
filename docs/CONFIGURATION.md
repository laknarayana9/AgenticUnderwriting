# Configuration Management

This application uses a professional configuration management system with environment-specific settings.

## Configuration Files

### `config.py`
- Contains all application settings using Pydantic Settings
- Supports environment variable overrides
- Provides separate classes for Development and Production environments

### `.env.example`
- Template for environment variables
- Copy to `.env` and update for your environment

## Environment-Specific Settings

### Development (Default)
```python
# Permissive CORS for development
cors_origins: ["*"]
cors_allow_methods: ["*"] 
cors_allow_headers: ["*"]
```

### Production
```python
# Restricted CORS for security
cors_origins: [
    "https://your-frontend.com",
    "https://admin.your-frontend.com"
]
cors_allow_methods: ["GET", "POST", "PUT", "DELETE"]
cors_allow_headers: ["Content-Type", "Authorization", "X-API-Key"]
```

## Usage

### Setting Environment
```bash
# Development (default)
export ENVIRONMENT=development

# Production
export ENVIRONMENT=production
```

### Environment Variables
Create `.env` file:
```bash
cp .env.example .env
# Edit .env with your values
```

### In Code
```python
from config import settings

# Access configuration
app = FastAPI(title=settings.title)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    # ... other settings
)
```

## Available Settings

- **API Configuration**: title, description, version
- **CORS Configuration**: origins, methods, headers, credentials
- **Database Configuration**: path, URL
- **RAG Configuration**: ChromaDB path, data directory
- **Server Configuration**: host, port

## Benefits

1. **Environment Separation**: Different settings for dev/prod
2. **Security**: Restricted CORS in production
3. **Flexibility**: Easy to override with environment variables
4. **Type Safety**: Pydantic validation of all settings
5. **Documentation**: Field descriptions for clarity
