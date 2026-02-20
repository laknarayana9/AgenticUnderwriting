"""
Security middleware and authentication for production deployment.
"""

try:
    import jwt
except ImportError:
    jwt = None
import bcrypt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import redis
import re


# Rate limiting
limiter = Limiter(key_func=get_remote_address)
security = HTTPBearer()

# Redis client for rate limiting and session storage
redis_client = None

def init_redis(redis_url: str):
    """Initialize Redis client."""
    global redis_client
    redis_client = redis.from_url(redis_url, decode_responses=True)


class SecurityManager:
    """Manages authentication, authorization, and security."""
    
    def __init__(self, secret_key: str, jwt_secret: str):
        self.secret_key = secret_key
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = "HS256"
        self.jwt_expire_minutes = 1440  # 24 hours
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.jwt_expire_minutes)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token."""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )


# Initialize security manager
security_manager = None

def init_security(secret_key: str, jwt_secret: str):
    """Initialize security manager."""
    global security_manager
    security_manager = SecurityManager(secret_key, jwt_secret)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get current authenticated user."""
    if not security_manager:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Security not initialized"
        )
    
    token = credentials.credentials
    payload = security_manager.verify_token(token)
    
    # Check if user is active (you might want to add user lookup here)
    if not payload.get("active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )
    
    return payload


class InputValidator:
    """Input validation and sanitization."""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number format."""
        pattern = r'^\+?1?-?\.?\s?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})$'
        return re.match(pattern, phone) is not None
    
    @staticmethod
    def sanitize_string(text: str, max_length: int = 1000) -> str:
        """Sanitize string input."""
        if not text:
            return ""
        
        # Remove potentially harmful characters
        text = re.sub(r'[<>"\']', '', text)
        
        # Limit length
        if len(text) > max_length:
            text = text[:max_length]
        
        return text.strip()
    
    @staticmethod
    def validate_address(address: str) -> bool:
        """Validate address format."""
        if not address or len(address) < 5:
            return False
        
        # Basic address validation
        words = address.split()
        if len(words) < 3:
            return False
        
        # Check for street number and name
        has_number = any(char.isdigit() for char in words[0])
        return has_number
    
    @staticmethod
    def validate_coverage_amount(amount: float) -> bool:
        """Validate coverage amount."""
        if not isinstance(amount, (int, float)):
            return False
        
        return 1000 <= amount <= 10000000  # $1K to $10M
    
    @staticmethod
    def validate_year(year: int) -> bool:
        """Validate construction year."""
        current_year = datetime.now().year
        return 1800 <= year <= current_year + 1  # Allow next year


class RateLimiter:
    """Advanced rate limiting with Redis."""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed based on rate limit.
        
        Args:
            key: Rate limit key (e.g., IP address or user ID)
            limit: Number of requests allowed
            window: Time window in seconds
        
        Returns:
            (allowed, info_dict)
        """
        if not self.redis:
            return True, {"remaining": limit}
        
        current_time = int(datetime.now().timestamp())
        window_start = current_time - window
        
        # Use Redis sorted set for sliding window
        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        pipe.zadd(key, {str(current_time): current_time})
        pipe.expire(key, window)
        
        results = pipe.execute()
        current_requests = results[1]
        
        remaining = max(0, limit - current_requests)
        allowed = current_requests < limit
        
        return allowed, {
            "remaining": remaining,
            "limit": limit,
            "reset": current_time + window
        }


def create_rate_limiter():
    """Create rate limiter instance."""
    if redis_client:
        return RateLimiter(redis_client)
    return None


# Security headers middleware
async def security_headers_middleware(request, call_next):
    """Add security headers to responses."""
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'"
    )
    
    return response


# Input validation decorators
def validate_submission(func):
    """Decorator to validate quote submission data."""
    async def wrapper(*args, **kwargs):
        # Add validation logic here
        return await func(*args, **kwargs)
    return wrapper


def require_permissions(permissions: list):
    """Decorator to require specific permissions."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            user_permissions = current_user.get('permissions', [])
            if not all(perm in user_permissions for perm in permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Session management
class SessionManager:
    """Manage user sessions with Redis."""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.session_ttl = 3600  # 1 hour
    
    def create_session(self, user_id: str, session_data: Dict[str, Any]) -> str:
        """Create new session."""
        session_id = secrets.token_urlsafe(32)
        session_key = f"session:{session_id}"
        
        session_data.update({
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat()
        })
        
        self.redis.setex(session_key, self.session_ttl, str(session_data))
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        session_key = f"session:{session_id}"
        session_data = self.redis.get(session_key)
        
        if session_data:
            # Update last accessed
            self.redis.expire(session_key, self.session_ttl)
            return eval(session_data)  # In production, use JSON serialization
        
        return None
    
    def delete_session(self, session_id: str):
        """Delete session."""
        session_key = f"session:{session_id}"
        self.redis.delete(session_key)
