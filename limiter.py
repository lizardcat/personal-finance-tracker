"""
Rate limiter instance for the application.
This module creates a limiter that can be imported by blueprints.
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Create limiter instance (will be initialized with app later)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
    strategy="fixed-window"
)
