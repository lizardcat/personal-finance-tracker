"""
Rate limiter instance for the application.
This module creates a limiter that can be imported by blueprints.

NOTE: For Railway serverless (free tier), in-memory rate limiting will reset
when the app sleeps/wakes. This still provides protection during active sessions.
For production with persistent rate limiting, set RATELIMIT_STORAGE_URI env var
to a Redis URL (e.g., redis://host:port).
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

# Create limiter instance (will be initialized with app later)
# Uses memory storage by default (resets on sleep), or Redis if configured
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
    strategy="fixed-window"
)
