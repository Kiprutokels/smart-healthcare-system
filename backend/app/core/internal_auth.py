"""
Internal service-to-service authentication.
All AI endpoints are protected by this dependency.
"""
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import settings

# Reads the header value; auto_error=False so we control the error message
_api_key_header = APIKeyHeader(name="X-Internal-API-Key", auto_error=False)


def verify_internal_api_key(api_key: str = Security(_api_key_header)) -> str:
    """
    FastAPI dependency — raises 401 if the key is absent or wrong.

    Usage:
        @router.post("/some-endpoint")
        def my_view(_: str = Depends(verify_internal_api_key)):
            ...
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing internal API key. Include 'X-Internal-API-Key' header.",
        )

    if api_key != settings.INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal API key.",
        )

    return api_key
