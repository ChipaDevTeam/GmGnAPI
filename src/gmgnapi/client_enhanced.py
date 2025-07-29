"""
Enhanced GMGN API WebSocket client with comprehensive features.
"""

import asyncio
import csv
import json
import logging
import sqlite3
import ssl
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Union
from urllib.parse import urlencode
import uuid

import websockets
from websockets.exceptions import ConnectionClosed, InvalidStatusCode

from .exceptions import (
    AuthenticationError,
    ConnectionError as GmGnConnectionError,
    GmGnAPIError,
    SubscriptionError,
)
from .models import (
    AlertConfig,
    ChainStatistics,
    DataExportConfig,
    LimitOrderInfo,
    Message,
    MonitoringStats,
    NewPoolInfo,
    PairUpdateData,
    SubscriptionRequest,
    TokenFilter,
    TokenLaunchData,
    TokenSocialInfo,
    TradeData,
    WalletTradeData,
)


logger = logging.getLogger(__name__)


class GmGnEnhancedClient:
    """
    Advanced WebSocket client for GMGN.ai API with comprehensive features.
    
    This client provides real-time access to Solana blockchain data with:
    - Multiple data channels (pools, trades, launches, social, etc.)
    - Advanced filtering and alerting
    - Data export capabilities (JSON, CSV, database)
    - Real-time monitoring and statistics
    - Auto-reconnection and error handling
    
    Example:
        ```python
        import asyncio
        from gmgnapi import GmGnEnhancedClient, TokenFilter, DataExportConfig
        
        async def on_new_pool(pool_info):
            print(f"New pool: {pool_info.pools[0].bti.s if pool_info.pools else 'Unknown'}")
        
        async def main():
            # Configure advanced features
            token_filter = TokenFilter(
                min_market_cap=Decimal("10000"),
                min_liquidity=Decimal("5000"),
                exchanges=["raydium", "orca"]
            )
            
            export_config = DataExportConfig(
                enabled=True,
                format="json",
                file_path="./gmgn_data"
            )
            
            client = GmGnEnhancedClient(
                token_filter=token_filter,
                export_config=export_config
            )
            
            client.on_new_pool(on_new_pool)
            
            await client.connect()
            await client.subscribe_all_channels()
            
            # Monitor for 1 hour
            await asyncio.sleep(3600)
            
            # Get statistics
            stats = client.get_monitoring_stats()
            print(f"Processed {stats.total_messages} messages")
        
        asyncio.run(main())
        ```
    """
    
    WEBSOCKET_URL = "wss://gmgn.ai/query"
    SUPPORTED_CHANNELS = {
        "new_pools",
        "pair_update", 
        "token_launch",
        "chain_stats",
        "token_social",
        "wallet_trades",
        "limit_orders"
    }
    
    def __init__(
        self,
        access_token: Optional[str] = None,
        chain: str = "sol",
        auto_reconnect: bool = True,
        reconnect_interval: float = 5.0,
        token_filter: Optional[TokenFilter] = None,
        export_config: Optional[DataExportConfig] = None,
        alert_config: Optional[AlertConfig] = None,
        rate_limit: Optional[int] = None,
        max_queue_size: int = 10000,
    ):
        """
        Initialize the advanced GMGN client.
        
        Args:
            access_token: Optional access token for authenticated channels
            chain: Blockchain to monitor (default: "sol" for Solana)
            auto_reconnect: Whether to automatically reconnect on connection loss
            reconnect_interval: Seconds to wait between reconnection attempts
            token_filter: Filter configuration for tokens
            export_config: Data export configuration
            alert_config: Alert and notification configuration
            rate_limit: Maximum messages per second to process
            max_queue_size: Maximum message queue size
        """
        self.access_token = access_token
        self.chain = chain
        self.auto_reconnect = auto_reconnect
        self.reconnect_interval = reconnect_interval
        self.token_filter = token_filter or TokenFilter()
        self.export_config = export_config or DataExportConfig()
        self.alert_config = alert_config or AlertConfig()
        self.rate_limit = rate_limit
        self.max_queue_size = max_queue_size
        
        self._websocket: Optional[websockets.WebSocketServerProtocol] = None
        self._handlers: Dict[str, List[Callable]] = {}
        self._subscriptions: Set[str] = set()
        self._running = False
        self._reconnect_task: Optional[asyncio.Task] = None
        self._message_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._stats = MonitoringStats()
        self._connection_start_time: Optional[datetime] = None
        
        # Data storage
        self._db_connection: Optional[sqlite3.Connection] = None
        self._export_file_handle = None
        self._csv_writer = None
        
        # Rate limiting
        self._last_message_times: List[datetime] = []
        
        # Tracking sets for statistics
        self._seen_tokens: Set[str] = set()
        self._seen_pools: Set[str] = set()
        
    async def connect(self) -> None:
        """
        Establish WebSocket connection to GMGN API.
        
        Raises:
            ConnectionError: If connection cannot be established
            AuthenticationError: If authentication fails
        """
        try:
            # Initialize data export if enabled
            if self.export_config.enabled:
                await self._setup_data_export()
            
            # Create SSL context for secure connection
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Build connection URL with parameters
            params = {
                "vsn": "2.0.0",
                "timeout": "60000"
            }
            url = f"{self.WEBSOCKET_URL}?{urlencode(params)}"
            
            logger.info(f"Connecting to {url}")
            
            self._websocket = await websockets.connect(
                url,
                ssl=ssl_context,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10,
                max_size=10**7,  # 10MB max message size
            )
            
            self._running = True
            self._connection_start_time = datetime.now()
            
            # Start message handlers
            asyncio.create_task(self._handle_messages())
            asyncio.create_task(self._process_message_queue())
            
            logger.info("Connected to GMGN WebSocket API")
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise GmGnConnectionError(f"Failed to connect to GMGN API: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from the WebSocket and cleanup resources."""
        self._running = False
        
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
        
        if self._websocket and not self._websocket.closed:
            await self._websocket.close()
        
        # Cleanup data export resources
        if self._export_file_handle:
            self._export_file_handle.close()
        
        if self._db_connection:
            self._db_connection.close()
            
        logger.info("Disconnected from GMGN WebSocket API")
    
    # Subscription methods for all channels
    async def subscribe_new_pools(self, chain: Optional[str] = None) -> None:
        """Subscribe to new liquidity pool creation events."""
        await self._subscribe("new_pools", chain or self.chain)
    
    async def subscribe_pair_updates(self, chain: Optional[str] = None) -> None:
        """Subscribe to trading pair price and volume updates."""
        await self._subscribe("pair_update", chain or self.chain)
    
    async def subscribe_token_launches(self, chain: Optional[str] = None) -> None:
        """Subscribe to new token launch events."""
        await self._subscribe("token_launch", chain or self.chain)
    
    async def subscribe_chain_stats(self, chain: Optional[str] = None) -> None:
        """Subscribe to blockchain statistics updates."""
        await self._subscribe("chain_stats", chain or self.chain)
    
    async def subscribe_token_social(self, chain: Optional[str] = None) -> None:
        """Subscribe to token social media and community information."""
        await self._subscribe("token_social", chain or self.chain, requires_auth=True)
    
    async def subscribe_wallet_trades(self, chain: Optional[str] = None) -> None:
        """Subscribe to wallet trading activity."""
        await self._subscribe("wallet_trades", chain or self.chain, requires_auth=True)
    
    async def subscribe_limit_orders(self, chain: Optional[str] = None) -> None:
        """Subscribe to limit order updates."""
        await self._subscribe("limit_orders", chain or self.chain, requires_auth=True)
    
    async def subscribe_all_channels(self, chain: Optional[str] = None) -> None:
        """Subscribe to all available channels."""
        chain = chain or self.chain
        
        # Public channels
        await self.subscribe_new_pools(chain)
        await self.subscribe_pair_updates(chain)
        await self.subscribe_token_launches(chain)
        await self.subscribe_chain_stats(chain)
        
        # Authenticated channels (if token available)
        if self.access_token:
            try:
                await self.subscribe_token_social(chain)
                await self.subscribe_wallet_trades(chain)
                await self.subscribe_limit_orders(chain)
            except AuthenticationError:
                logger.warning("Authentication failed for some channels")
    
    # Event handler registration methods
    def on_new_pool(self, handler: Callable[[NewPoolInfo], None]) -> None:
        """Register handler for new pool events."""
        self._add_handler("new_pools", handler)
    
    def on_pair_update(self, handler: Callable[[PairUpdateData], None]) -> None:
        """Register handler for pair update events."""
        self._add_handler("pair_update", handler)
    
    def on_token_launch(self, handler: Callable[[TokenLaunchData], None]) -> None:
        """Register handler for token launch events."""
        self._add_handler("token_launch", handler)
    
    def on_chain_stats(self, handler: Callable[[ChainStatistics], None]) -> None:
        """Register handler for chain statistics events."""
        self._add_handler("chain_stats", handler)
    
    def on_token_social(self, handler: Callable[[TokenSocialInfo], None]) -> None:
        """Register handler for token social info events."""
        self._add_handler("token_social", handler)
    
    def on_wallet_trades(self, handler: Callable[[WalletTradeData], None]) -> None:
        """Register handler for wallet trade events."""
        self._add_handler("wallet_trades", handler)
    
    def on_limit_orders(self, handler: Callable[[LimitOrderInfo], None]) -> None:
        """Register handler for limit order events."""
        self._add_handler("limit_orders", handler)
    
    def on_message(self, handler: Callable[[Message], None]) -> None:
        """Register handler for all messages."""
        self._add_handler("message", handler)
    
    # Monitoring and statistics
    def get_monitoring_stats(self) -> MonitoringStats:
        """Get current monitoring statistics."""
        if self._connection_start_time:
            self._stats.connection_uptime = (
                datetime.now() - self._connection_start_time
            ).total_seconds()
        
        self._stats.unique_tokens_seen = len(self._seen_tokens)
        self._stats.unique_pools_seen = len(self._seen_pools)
        
        return self._stats
    
    def reset_stats(self) -> None:
        """Reset monitoring statistics."""
        self._stats = MonitoringStats()
        self._seen_tokens.clear()
        self._seen_pools.clear()
        self._connection_start_time = datetime.now()
    
    # Filtering and data processing
    def update_token_filter(self, token_filter: TokenFilter) -> None:
        """Update token filtering configuration."""
        self.token_filter = token_filter
        logger.info("Token filter updated")
    
    def _passes_filter(self, data: Dict[str, Any], channel: str) -> bool:
        """Check if data passes current filters."""
        if not self.token_filter:
            return True
        
        try:
            # Extract relevant fields based on channel
            if channel == "new_pools" and isinstance(data, NewPoolInfo):
                # Filter new pools based on token info
                if data.pools and len(data.pools) > 0:
                    pool = data.pools[0]
                    if pool.bti:  # base token info
                        return self._check_token_criteria(pool.bti.model_dump())
            
            elif channel == "pair_update":
                # Filter pair updates based on market data
                market_cap = data.get("market_cap_usd")
                liquidity = data.get("liquidity_usd")
                volume = data.get("volume_24h_usd")
                
                if self.token_filter.min_market_cap and market_cap:
                    if Decimal(str(market_cap)) < self.token_filter.min_market_cap:
                        return False
                
                if self.token_filter.min_liquidity and liquidity:
                    if Decimal(str(liquidity)) < self.token_filter.min_liquidity:
                        return False
                
                if self.token_filter.min_volume_24h and volume:
                    if Decimal(str(volume)) < self.token_filter.min_volume_24h:
                        return False
            
            return True
            
        except Exception as e:
            logger.debug(f"Filter check error: {e}")
            return True  # Default to passing if filter check fails
    
    def _check_token_criteria(self, token_data: Dict[str, Any]) -> bool:
        """Check if token data meets filter criteria."""
        try:
            # Check symbol filters
            symbol = token_data.get("s")  # symbol field
            if symbol:
                if self.token_filter.symbols and symbol not in self.token_filter.symbols:
                    return False
                if self.token_filter.exclude_symbols and symbol in self.token_filter.exclude_symbols:
                    return False
            
            # Check market cap
            market_cap = token_data.get("mc")  # market cap field
            if market_cap and self.token_filter.min_market_cap:
                if Decimal(str(market_cap)) < self.token_filter.min_market_cap:
                    return False
            
            # Check holder count
            holder_count = token_data.get("hc")  # holder count field
            if holder_count and self.token_filter.min_holder_count:
                if holder_count < self.token_filter.min_holder_count:
                    return False
            
            return True
            
        except Exception as e:
            logger.debug(f"Token criteria check error: {e}")
            return True
    
    # Data export functionality
    async def _setup_data_export(self) -> None:
        """Setup data export based on configuration."""
        if not self.export_config.file_path:
            return
        
        export_path = Path(self.export_config.file_path)
        export_path.mkdir(parents=True, exist_ok=True)
        
        if self.export_config.format == "json":
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = export_path / f"gmgn_data_{timestamp}.json"
            self._export_file_handle = open(file_path, "w")
            
        elif self.export_config.format == "csv":
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = export_path / f"gmgn_data_{timestamp}.csv"
            self._export_file_handle = open(file_path, "w", newline="")
            self._csv_writer = csv.writer(self._export_file_handle)
            
            # Write CSV header
            header = ["timestamp", "channel", "data"]
            self._csv_writer.writerow(header)
            
        elif self.export_config.format == "database":
            db_path = export_path / "gmgn_data.db"
            self._db_connection = sqlite3.connect(str(db_path))
            await self._setup_database()
    
    async def _setup_database(self) -> None:
        """Setup SQLite database schema."""
        if not self._db_connection:
            return
        
        cursor = self._db_connection.cursor()
        
        # Create tables for different data types
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                channel TEXT NOT NULL,
                data TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS new_pools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                chain TEXT,
                pool_address TEXT,
                token_address TEXT,
                data TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                wallet_address TEXT,
                token_address TEXT,
                trade_type TEXT,
                amount_usd REAL,
                data TEXT
            )
        """)
        
        self._db_connection.commit()
    
    async def _export_data(self, channel: str, data: Any) -> None:
        """Export data based on configuration."""
        if not self.export_config.enabled:
            return
        
        try:
            timestamp = datetime.now().isoformat()
            
            if self.export_config.format == "json" and self._export_file_handle:
                export_record = {
                    "timestamp": timestamp,
                    "channel": channel,
                    "data": data
                }
                json.dump(export_record, self._export_file_handle)
                self._export_file_handle.write("\n")
                self._export_file_handle.flush()
                
            elif self.export_config.format == "csv" and self._csv_writer:
                self._csv_writer.writerow([timestamp, channel, json.dumps(data)])
                self._export_file_handle.flush()
                
            elif self.export_config.format == "database" and self._db_connection:
                cursor = self._db_connection.cursor()
                cursor.execute(
                    "INSERT INTO messages (channel, data) VALUES (?, ?)",
                    (channel, json.dumps(data))
                )
                self._db_connection.commit()
                
        except Exception as e:
            logger.error(f"Export error: {e}")
    
    # Rate limiting
    def _check_rate_limit(self) -> bool:
        """Check if message processing should be rate limited."""
        if not self.rate_limit:
            return True
        
        now = datetime.now()
        cutoff = now - timedelta(seconds=1)
        
        # Remove old timestamps
        self._last_message_times = [
            t for t in self._last_message_times if t > cutoff
        ]
        
        # Check if under rate limit
        if len(self._last_message_times) < self.rate_limit:
            self._last_message_times.append(now)
            return True
        
        return False
    
    # Internal methods
    async def _subscribe(self, channel: str, chain: str, requires_auth: bool = False) -> None:
        """Internal method to handle subscriptions."""
        if channel not in self.SUPPORTED_CHANNELS:
            raise SubscriptionError(f"Unsupported channel: {channel}")
        
        if requires_auth and not self.access_token:
            raise AuthenticationError(f"Channel {channel} requires authentication")
        
        if not self._websocket or self._websocket.closed:
            raise GmGnConnectionError("Not connected to WebSocket")
        
        subscription = SubscriptionRequest(
            channel=channel,
            data=[{"c": chain}],
            access_token=self.access_token if requires_auth else None
        )
        
        try:
            await self._websocket.send(subscription.model_dump_json())
            self._subscriptions.add(channel)
            logger.info(f"Subscribed to {channel} for chain {chain}")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to {channel}: {e}")
            raise SubscriptionError(f"Failed to subscribe to {channel}: {e}")
    
    def _add_handler(self, event_type: str, handler: Callable) -> None:
        """Add event handler."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    async def _handle_messages(self) -> None:
        """Handle incoming WebSocket messages."""
        try:
            async for raw_message in self._websocket:
                if not self._check_rate_limit():
                    continue
                
                try:
                    # Add to processing queue
                    await self._message_queue.put(raw_message)
                    
                except asyncio.QueueFull:
                    logger.warning("Message queue full, dropping message")
                    self._stats.error_count += 1
                    
        except ConnectionClosed:
            logger.warning("WebSocket connection closed")
            if self.auto_reconnect and self._running:
                await self._reconnect()
        except Exception as e:
            logger.error(f"Error in message handler: {e}")
            self._stats.error_count += 1
            if self.auto_reconnect and self._running:
                await self._reconnect()
    
    async def _process_message_queue(self) -> None:
        """Process messages from the queue."""
        while self._running:
            try:
                raw_message = await asyncio.wait_for(
                    self._message_queue.get(), timeout=1.0
                )
                
                await self._process_single_message(raw_message)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                self._stats.error_count += 1
    
    async def _process_single_message(self, raw_message: str) -> None:
        """Process a single message."""
        try:
            data = json.loads(raw_message)
            message = Message(**data)
            
            # Update statistics
            self._stats.total_messages += 1
            self._stats.last_message_time = datetime.now()
            
            # Calculate messages per minute
            if self._stats.total_messages > 1:
                time_diff = (datetime.now() - self._connection_start_time).total_seconds() / 60
                self._stats.messages_per_minute = self._stats.total_messages / max(time_diff, 1)
            
            # Check filters
            if not self._passes_filter(message.data, message.channel):
                return
            
            # Export data if enabled
            await self._export_data(message.channel, message.data)
            
            # Call general message handlers
            await self._call_handlers("message", message)
            
            # Call specific channel handlers with parsed data
            if message.channel == "new_pools":
                try:
                    pool_info = NewPoolInfo(**message.data)
                    # Track unique pools
                    for pool in pool_info.pools:
                        self._seen_pools.add(pool.a)
                        if pool.bti and hasattr(pool.bti, 's'):
                            self._seen_tokens.add(pool.ba)
                    
                    await self._call_handlers(message.channel, pool_info)
                except Exception as e:
                    logger.debug(f"Failed to parse pool info: {e}")
                    await self._call_handlers(message.channel, message.data)
            
            elif message.channel == "pair_update":
                try:
                    pair_data = PairUpdateData(**message.data)
                    await self._call_handlers(message.channel, pair_data)
                except Exception:
                    await self._call_handlers(message.channel, message.data)
            
            elif message.channel == "token_launch":
                try:
                    launch_data = TokenLaunchData(**message.data)
                    self._seen_tokens.add(launch_data.token_address)
                    await self._call_handlers(message.channel, launch_data)
                except Exception:
                    await self._call_handlers(message.channel, message.data)
            
            else:
                # Handle other channels with raw data
                await self._call_handlers(message.channel, message.data)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON message: {e}")
            self._stats.error_count += 1
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            self._stats.error_count += 1
    
    async def _call_handlers(self, event_type: str, data: Any) -> None:
        """Call all registered handlers for an event type."""
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    logger.error(f"Error in {event_type} handler: {e}")
                    self._stats.error_count += 1
    
    async def _reconnect(self) -> None:
        """Attempt to reconnect to the WebSocket."""
        if self._reconnect_task and not self._reconnect_task.done():
            return
        
        self._reconnect_task = asyncio.create_task(self._do_reconnect())
    
    async def _do_reconnect(self) -> None:
        """Perform the actual reconnection."""
        logger.info("Attempting to reconnect...")
        
        while self._running:
            try:
                await self.connect()
                
                # Re-subscribe to all previous subscriptions
                subscriptions = self._subscriptions.copy()
                self._subscriptions.clear()
                
                for channel in subscriptions:
                    try:
                        await self._subscribe(channel, self.chain)
                    except Exception as e:
                        logger.error(f"Failed to re-subscribe to {channel}: {e}")
                
                logger.info("Reconnected successfully")
                break
                
            except Exception as e:
                logger.error(f"Reconnection failed: {e}")
                await asyncio.sleep(self.reconnect_interval)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
