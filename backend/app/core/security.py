import hmac
import hashlib
import time
from typing import Optional, Dict, Any
from pathlib import Path

try:
    import jwt
    _JWT_ERROR = jwt.PyJWTError
except ImportError:
    from jose import jwt, JWTError as _JWT_ERROR

from fastapi import Request, HTTPException, status
from app.core.config import settings


def verify_github_signature(payload: bytes, signature_header: Optional[str]) -> bool:
    """
    Verifies that the webhook payload was sent from GitHub using HMAC-SHA256.
    """
    if not signature_header:
        return False
    
    parts = signature_header.split("=")
    if len(parts) != 2 or parts[0] != "sha256":
        return False
    
    expected_signature = parts[1]
    mac = hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256
    )
    computed_signature = mac.hexdigest()
    return hmac.compare_digest(computed_signature, expected_signature)


def get_github_app_jwt() -> str:
    """
    Generate an RS256 JWT to authenticate as the GitHub App.
    JWT is valid for up to 10 minutes.
    """
    private_key_content: Optional[str] = settings.GITHUB_APP_PRIVATE_KEY
    if not private_key_content and settings.GITHUB_APP_PRIVATE_KEY_PATH:
        key_path = Path(settings.GITHUB_APP_PRIVATE_KEY_PATH)
        if key_path.exists():
            private_key_content = key_path.read_text()

    if not private_key_content:
        # Fallback dummy RS256 key for development/mocking if key not supplied
        raise ValueError("GitHub App private key is not configured.")

    now = int(time.time())
    payload = {
        # Issued at time (60 seconds in the past to allow for clock drift)
        "iat": now - 60,
        # JWT expiration time (10 minute maximum)
        "exp": now + (9 * 60),
        # GitHub App's identifier
        "iss": settings.GITHUB_APP_ID,
    }
    encoded_jwt = jwt.encode(payload, private_key_content, algorithm="RS256")
    return encoded_jwt


def create_access_token(data: Dict[str, Any], expires_delta: Optional[int] = 86400) -> str:
    """Create HS256 JWT for API access."""
    to_encode = data.copy()
    now = int(time.time())
    to_encode.update({"iat": now, "exp": now + expires_delta})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and verify HS256 JWT."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except _JWT_ERROR as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}"
        )
