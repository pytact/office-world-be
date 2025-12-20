"""Domain-specific utilities for authentication."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4, UUID
from passlib.context import CryptContext
from jose import jwt, JWTError
from src.config import settings


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(seconds=settings.jwt_access_token_expire_seconds)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError:
        raise


def generate_token() -> UUID:
    """Generate a UUID v4 token for invitations and password resets."""
    return uuid4()


def is_token_expired(expiry: datetime | None) -> bool:
    """Check if a token is expired."""
    if expiry is None:
        return True
    return datetime.now(timezone.utc) > expiry.replace(tzinfo=timezone.utc) if expiry.tzinfo is None else datetime.now(timezone.utc) > expiry


async def is_token_blacklisted(token: str) -> bool:
    """Check if a JWT token is in the blacklist."""
    try:
        from src.infra.cache_redis import get_redis_client
        
        # Create a hash of the token for storage (for security)
        import hashlib
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        blacklist_key = f"blacklist:token:{token_hash}"
        
        redis_client = await get_redis_client()
        exists = await redis_client.exists(blacklist_key)
        return bool(exists)
    except Exception:
        # If Redis is unavailable, allow the request (fail open)
        # In production, you might want to fail closed instead
        return False


async def blacklist_token(token: str) -> None:
    """Add a JWT token to the blacklist until it expires."""
    try:
        from src.infra.cache_redis import get_redis_client
        
        # Decode token to get expiration time
        payload = decode_token(token)
        exp = payload.get("exp")
        
        if exp:
            # Calculate remaining TTL (time until token expires)
            exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
            now = datetime.now(timezone.utc)
            ttl_seconds = int((exp_datetime - now).total_seconds())
            
            # Only blacklist if token hasn't expired yet
            if ttl_seconds > 0:
                # Create a hash of the token for storage (for security)
                import hashlib
                token_hash = hashlib.sha256(token.encode()).hexdigest()
                blacklist_key = f"blacklist:token:{token_hash}"
                
                redis_client = await get_redis_client()
                # Store with TTL equal to remaining token lifetime
                await redis_client.setex(blacklist_key, ttl_seconds, "1")
    except Exception:
        # If Redis is unavailable or token decode fails, log but don't fail
        # In production, you might want to log this error
        pass
