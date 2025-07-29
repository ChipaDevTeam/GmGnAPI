"""
GmGnAPI - Professional Python client for GMGN.ai WebSocket API

A robust, type-safe, and easy-to-use client for connecting to GMGN's 
real-time Solana blockchain data streams.
"""

__version__ = "0.1.0"
__author__ = "GmGnAPI Team"
__email__ = "contact@gmgnapi.dev"
__license__ = "MIT"

from .client import GmGnClient
from .exceptions import (
    GmGnAPIError,
    ConnectionError,
    AuthenticationError,
    SubscriptionError,
    MessageParsingError,
)
from .models import (
    Message,
    SubscriptionRequest,
    NewPoolInfo,
    PairUpdate,
    TokenLaunchInfo,
    ChainStatistics,
    TokenSocialInfo,
    WalletTradeData,
    LimitOrderInfo,
)

__all__ = [
    # Client
    "GmGnClient",
    # Exceptions
    "GmGnAPIError",
    "ConnectionError",
    "AuthenticationError", 
    "SubscriptionError",
    "MessageParsingError",
    # Models
    "Message",
    "SubscriptionRequest",
    "NewPoolInfo",
    "PairUpdate", 
    "TokenLaunchInfo",
    "ChainStatistics",
    "TokenSocialInfo",
    "WalletTradeData",
    "LimitOrderInfo",
]
