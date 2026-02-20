"""
Startup initialization to avoid circular imports.
"""

import asyncio
from monitoring import setup_monitoring, logger, monitoring_loop
from security import init_security
from performance import init_performance, init_cache
from config import settings


def initialize_production():
    """Initialize production components."""
    logger.info("Starting Agentic Quote-to-Underwrite application")
    
    # Initialize security
    init_security(settings.secret_key, settings.jwt_secret_key)
    
    # Initialize Redis for caching and rate limiting
    if hasattr(settings, 'redis_url'):
        init_redis(settings.redis_url)
        init_cache(settings.redis_url)
    
    # Initialize performance optimization
    init_performance("storage/underwriting.db", getattr(settings, 'redis_url', None))
    
    # Setup monitoring and alerting
    setup_monitoring()
    
    # Start background monitoring
    asyncio.create_task(monitoring_loop())
    
    logger.info("Application startup completed")


def cleanup_production():
    """Cleanup on shutdown."""
    logger.info("Shutting down application")
    # Add cleanup logic here
    logger.info("Application shutdown completed")


def init_redis(redis_url: str):
    """Initialize Redis client."""
    try:
        import redis
        global redis_client
        redis_client = redis.from_url(redis_url, decode_responses=False)
        logger.info("Redis client initialized")
    except Exception as e:
        logger.error("Redis initialization failed", error=str(e))


# Global redis client for rate limiting
redis_client = None
