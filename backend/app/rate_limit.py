from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

# Per-client-IP limiter. In-memory storage is fine for a single instance;
# point `storage_uri` at Redis if the backend ever scales horizontally.
limiter = Limiter(
    key_func=get_remote_address,
    enabled=settings.rate_limit_enabled,
    headers_enabled=True,
)
