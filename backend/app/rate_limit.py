from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

# Per-client-IP limiter. In-memory storage only holds within one instance, so on
# serverless / horizontally-scaled deploys the limits are effectively bypassed.
# Set RATE_LIMIT_STORAGE_URI to a shared Redis endpoint (e.g. Upstash) so counters
# are shared across every instance; empty falls back to in-memory for local/dev.
limiter = Limiter(
    key_func=get_remote_address,
    enabled=settings.rate_limit_enabled,
    headers_enabled=True,
    storage_uri=settings.rate_limit_storage_uri or "memory://",
)
