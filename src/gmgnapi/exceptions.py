"""
Custom exceptions for GmGnAPI client.
"""

from typing import Optional, Any


class GmGnAPIError(Exception):
    """Base exception for all GmGnAPI errors."""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.details = details


class ConnectionError(GmGnAPIError):
    """Raised when there are WebSocket connection issues."""
    pass


class AuthenticationError(GmGnAPIError):
    """Raised when authentication fails."""
    pass


class SubscriptionError(GmGnAPIError):
    """Raised when subscription to a channel fails."""
    pass


class MessageParsingError(GmGnAPIError):
    """Raised when a received message cannot be parsed."""
    pass


class RateLimitError(GmGnAPIError):
    """Raised when rate limits are exceeded."""
    pass


class InvalidChannelError(GmGnAPIError):
    """Raised when an invalid channel is specified."""
    pass
