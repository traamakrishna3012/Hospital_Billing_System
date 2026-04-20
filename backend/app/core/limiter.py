"""
Rate Limiting setup using slowapi.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize standard simple rate limiter using in-memory storage. 
# (In production with multiple workers, Redis storage should be used, but this suffices for the scope)
limiter = Limiter(key_func=get_remote_address)
