"""Rate-limiter singleton shared across all routers.

Uses the client IP as the bucket key.  In-memory storage is sufficient
for a single-process deployment (Railway); swap to a Redis backend if
horizontal scaling is needed.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
