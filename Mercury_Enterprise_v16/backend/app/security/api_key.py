from fastapi import Header, HTTPException, status

from ..core.config import settings


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Optional API-key guard.

    Development remains frictionless when MERCURY_API_KEY is empty. Production
    deployments should always set a strong secret and place TLS in front of API.
    """
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
