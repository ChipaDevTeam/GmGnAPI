"""
GmGnAPI - Professional Python client for GMGN.ai WebSocket API

A robust, type-safe, and easy-to-use client for connecting to GMGN's 
real-time Solana blockchain data streams with advanced features including:
- Real-time data filtering and processing
- Data export capabilities (JSON, CSV, Database)
- Monitoring and statistics
- Alert and notification system
- Automatic reconnection and error handling
"""

__version__ = "0.2.0"
__author__ = "GmGnAPI Team"
__email__ = "contact@gmgnapi.dev"
__license__ = "MIT"

from .client import GmGnClient
from .client_enhanced import GmGnEnhancedClient
from .exceptions import (
    GmGnAPIError,
    ConnectionError,
    AuthenticationError,
    SubscriptionError,
    MessageParsingError,
)
from .models import (
    # Core message types
    Message,
    SubscriptionRequest,
    
    # Data structures
    NewPoolInfo,
    TokenInfo,
    PoolData,
    PairUpdateData,
    TokenLaunchData,
    ChainStatistics,
    TokenSocialInfo,
    TradeData,
    WalletTradeData,
    LimitOrderInfo,
    
    # Configuration models
    TokenFilter,
    DataExportConfig,
    AlertConfig,
    MonitoringStats,
)

__all__ = [
    # Clients
    "GmGnClient",
    "GmGnEnhancedClient",
    
    # Exceptions
    "GmGnAPIError",
    "ConnectionError",
    "AuthenticationError", 
    "SubscriptionError",
    "MessageParsingError",
    
    # Core models
    "Message",
    "SubscriptionRequest",
    "NewPoolInfo",
    "TokenInfo",
    "PoolData",
    "PairUpdateData",
    "TokenLaunchData",
    "ChainStatistics",
    "TokenSocialInfo",
    "TradeData",
    "WalletTradeData",
    "LimitOrderInfo",
    
    # Configuration models
    "TokenFilter",
    "DataExportConfig",
    "AlertConfig",
    "MonitoringStats",
]
