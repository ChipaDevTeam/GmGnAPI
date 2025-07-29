"""
Main GmGnAPI WebSocket client implementation.
"""

import asyncio
import json
import logging
import os
import uuid
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Union
from urllib.parse import urlencode

import websockets
from websockets.exceptions import (
    ConnectionClosedError,
    ConnectionClosedOK,
    InvalidURI,
    WebSocketException,
)

from .exceptions import (
    AuthenticationError,
    ConnectionError,
    GmGnAPIError,
    MessageParsingError,
    SubscriptionError,
)
from .models import Message, SubscriptionRequest

logger = logging.getLogger(__name__)


class GmGnClient:
    """
    Professional WebSocket client for GMGN.ai API.
    
    Provides real-time access to Solana blockchain data including:
    - New pool creations
    - Token launches  
    - Trading pair updates
    - Wallet trading activity
    - Limit order updates
    - Blockchain statistics
    """

    DEFAULT_WS_URL = "wss://ws.gmgn.ai/quotation"
    DEFAULT_USER_AGENT = "GmGnAPI/0.1.0 Python Client"
    
    SUPPORTED_CHANNELS = {
        "new_pool_info",
        "new_pair_update", 
        "new_launched_info",
        "chain_stat",
        "token_social_info",
        "wallet_trade_data",
        "limit_order_info",
    }

    def __init__(
        self,
        ws_url: Optional[str] = None,
        device_id: Optional[str] = None,
        client_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        access_token: Optional[str] = None,
        auto_reconnect: bool = True,
        max_reconnect_attempts: int = 5,
        reconnect_delay: float = 5.0,
        ping_interval: float = 30.0,
        ping_timeout: float = 10.0,
    ):
        """
        Initialize the GmGnClient.
        
        Args:
            ws_url: WebSocket URL (defaults to GMGN's official endpoint)
            device_id: Unique device identifier
            client_id: Client identifier
            user_agent: User agent string
            access_token: JWT access token for authenticated endpoints
            auto_reconnect: Whether to automatically reconnect on disconnect
            max_reconnect_attempts: Maximum number of reconnection attempts
            reconnect_delay: Delay between reconnection attempts (seconds)
            ping_interval: WebSocket ping interval (seconds)
            ping_timeout: WebSocket ping timeout (seconds)
        """
        self.ws_url = ws_url or os.getenv("GMGN_WS_URL", self.DEFAULT_WS_URL)
        self.device_id = device_id or str(uuid.uuid4())
        self.client_id = client_id or f"gmgn_python_{uuid.uuid4().hex[:8]}"
        self.user_agent = user_agent or os.getenv("GMGN_USER_AGENT", self.DEFAULT_USER_AGENT)
        self.access_token = access_token or os.getenv("GMGN_ACCESS_TOKEN")
        
        # Connection settings
        self.auto_reconnect = auto_reconnect
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        
        # Internal state
        self._websocket: Optional[websockets.WebSocketServerProtocol] = None
        self._connected = False
        self._reconnect_count = 0
        self._subscriptions: Dict[str, SubscriptionRequest] = {}
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._connection_lock = asyncio.Lock()
        
        # Message queue for buffering
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._listener_task: Optional[asyncio.Task] = None

    @property
    def is_connected(self) -> bool:
        """Check if the WebSocket connection is active."""
        return self._connected and self._websocket is not None

    def _build_connection_url(self) -> str:
        """Build the WebSocket connection URL with query parameters."""
        params = {
            "device_id": self.device_id,
            "client_id": self.client_id,
            "from_app": "gmgn",
            "app_ver": "20250729-1647-ffac485",
            "tz_name": "UTC",
            "tz_offset": "0", 
            "app_lang": "en-US",
            "fp_did": uuid.uuid4().hex,
            "os": "python",
            "uuid": uuid.uuid4().hex,
        }
        
        query_string = urlencode(params)
        return f"{self.ws_url}?{query_string}"

    def _get_connection_headers(self) -> Dict[str, str]:
        """Get WebSocket connection headers."""
        return {
            "User-Agent": self.user_agent,
            "Origin": "https://gmgn.ai",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }

    async def connect(self) -> None:
        """
        Establish WebSocket connection to GMGN API.
        
        Raises:
            ConnectionError: If connection fails
        """
        async with self._connection_lock:
            if self.is_connected:
                logger.warning("Already connected to GMGN WebSocket")
                return

            try:
                url = self._build_connection_url()
                headers = self._get_connection_headers()
                
                logger.info(f"Connecting to GMGN WebSocket: {self.ws_url}")
                
                self._websocket = await websockets.connect(
                    url,
                    extra_headers=headers,
                    ping_interval=self.ping_interval,
                    ping_timeout=self.ping_timeout,
                    max_size=2**20,  # 1MB max message size
                    compression=None,
                )
                
                self._connected = True
                self._reconnect_count = 0
                
                # Start message listener task
                self._listener_task = asyncio.create_task(self._message_listener())
                
                logger.info("Successfully connected to GMGN WebSocket")
                
            except Exception as e:
                logger.error(f"Failed to connect to GMGN WebSocket: {e}")
                raise ConnectionError(f"Failed to connect: {e}")

    async def disconnect(self) -> None:
        """Disconnect from the WebSocket."""
        async with self._connection_lock:
            if not self.is_connected:
                return

            self._connected = False
            
            # Cancel listener task
            if self._listener_task and not self._listener_task.done():
                self._listener_task.cancel()
                try:
                    await self._listener_task
                except asyncio.CancelledError:
                    pass

            # Close WebSocket connection
            if self._websocket:
                await self._websocket.close()
                self._websocket = None

            logger.info("Disconnected from GMGN WebSocket")

    async def _message_listener(self) -> None:
        """Internal message listener task."""
        try:
            async for message in self._websocket:
                try:
                    await self._handle_message(message)
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    
        except ConnectionClosedOK:
            logger.info("WebSocket connection closed normally")
        except ConnectionClosedError as e:
            logger.warning(f"WebSocket connection closed unexpectedly: {e}")
            if self.auto_reconnect:
                await self._attempt_reconnect()
        except Exception as e:
            logger.error(f"Unexpected error in message listener: {e}")
            if self.auto_reconnect:
                await self._attempt_reconnect()

    async def _handle_message(self, raw_message: str) -> None:
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(raw_message)
            
            # Log the raw message for debugging
            logger.debug(f"Raw message received: {data}")
            
            # Handle different message formats
            if isinstance(data, dict):
                channel = data.get("channel", "unknown")
                
                # Handle special message types
                if channel == "ack":
                    logger.debug(f"Received acknowledgment: {data}")
                    return  # Don't process ack messages further
                
                # Create message with flexible validation
                message_data = {
                    "channel": channel,
                    "data": data.get("data", data),  # Use entire data if no 'data' field
                    "action": data.get("action"),
                    "id": data.get("id"),
                }
                
                message = Message(**message_data)
                
                # Add to message queue
                await self._message_queue.put(message)
                
                # Call event handlers
                if channel in self._event_handlers:
                    for handler in self._event_handlers[channel]:
                        try:
                            if asyncio.iscoroutinefunction(handler):
                                await handler(message.data)
                            else:
                                handler(message.data)
                        except Exception as e:
                            logger.error(f"Error in event handler for {channel}: {e}")
            else:
                logger.warning(f"Unexpected message format: {type(data)}")
                        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON message: {e}")
            raise MessageParsingError(f"Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            # Don't raise here to avoid breaking the connection

    async def _attempt_reconnect(self) -> None:
        """Attempt to reconnect with exponential backoff."""
        if self._reconnect_count >= self.max_reconnect_attempts:
            logger.error("Maximum reconnection attempts exceeded")
            return

        self._reconnect_count += 1
        delay = self.reconnect_delay * (2 ** (self._reconnect_count - 1))
        
        logger.info(f"Attempting reconnection {self._reconnect_count}/{self.max_reconnect_attempts} "
                   f"in {delay} seconds")
        
        await asyncio.sleep(delay)
        
        try:
            await self.connect()
            
            # Re-subscribe to all channels
            for subscription in self._subscriptions.values():
                await self._send_subscription(subscription)
                
        except Exception as e:
            logger.error(f"Reconnection attempt {self._reconnect_count} failed: {e}")
            await self._attempt_reconnect()

    async def _send_subscription(self, subscription: SubscriptionRequest) -> None:
        """Send a subscription request."""
        if not self.is_connected:
            raise ConnectionError("Not connected to WebSocket")

        try:
            message = subscription.json()
            await self._websocket.send(message)
            logger.debug(f"Sent subscription: {subscription.channel}")
            
        except Exception as e:
            logger.error(f"Failed to send subscription: {e}")
            raise SubscriptionError(f"Failed to subscribe to {subscription.channel}: {e}")

    async def subscribe_new_pools(self, chain: str = "sol") -> None:
        """Subscribe to new pool information."""
        subscription = SubscriptionRequest(
            channel="new_pool_info",
            data=[{"chain": chain}]
        )
        
        self._subscriptions[subscription.channel] = subscription
        await self._send_subscription(subscription)

    async def subscribe_pair_updates(self, chain: str = "sol") -> None:
        """Subscribe to trading pair updates."""
        subscription = SubscriptionRequest(
            channel="new_pair_update",
            data=[{"chain": chain}]
        )
        
        self._subscriptions[subscription.channel] = subscription
        await self._send_subscription(subscription)

    async def subscribe_token_launches(self, chain: str = "sol") -> None:
        """Subscribe to token launch notifications."""
        subscription = SubscriptionRequest(
            channel="new_launched_info", 
            data=[{"chain": chain}]
        )
        
        self._subscriptions[subscription.channel] = subscription
        await self._send_subscription(subscription)

    async def subscribe_chain_stats(self, chain: str = "sol") -> None:
        """Subscribe to blockchain statistics."""
        subscription = SubscriptionRequest(
            channel="chain_stat",
            data=[{"chain": chain}]
        )
        
        self._subscriptions[subscription.channel] = subscription
        await self._send_subscription(subscription)

    async def subscribe_token_social_info(self, chain: str = "sol") -> None:
        """Subscribe to token social media information."""
        subscription = SubscriptionRequest(
            channel="token_social_info",
            data=[{"chain": chain}]
        )
        
        self._subscriptions[subscription.channel] = subscription
        await self._send_subscription(subscription)

    async def subscribe_wallet_trades(
        self, 
        chain: str = "sol", 
        wallet_address: str = None,
        access_token: str = None
    ) -> None:
        """
        Subscribe to wallet trading activity.
        
        Args:
            chain: Blockchain network
            wallet_address: Wallet address to monitor
            access_token: JWT access token for authentication
        """
        if not wallet_address:
            raise ValueError("wallet_address is required for wallet trade subscription")
            
        token = access_token or self.access_token
        if not token:
            raise AuthenticationError("access_token is required for wallet trade data")

        subscription = SubscriptionRequest(
            channel="wallet_trade_data",
            data=[{"chain": chain, "addresses": wallet_address}],
            access_token=token,
            retry=1
        )
        
        self._subscriptions[subscription.channel] = subscription
        await self._send_subscription(subscription)

    async def subscribe_limit_orders(self, access_token: str = None) -> None:
        """
        Subscribe to limit order updates.
        
        Args:
            access_token: JWT access token for authentication
        """
        token = access_token or self.access_token
        if not token:
            raise AuthenticationError("access_token is required for limit order data")

        subscription = SubscriptionRequest(
            channel="limit_order_info",
            access_token=token
        )
        
        self._subscriptions[subscription.channel] = subscription
        await self._send_subscription(subscription)

    async def subscribe_all_channels(self, chain: str = "sol") -> None:
        """Subscribe to all available public channels."""
        await asyncio.gather(
            self.subscribe_new_pools(chain),
            self.subscribe_pair_updates(chain),
            self.subscribe_token_launches(chain),
            self.subscribe_chain_stats(chain),
            self.subscribe_token_social_info(chain),
        )

    def on(self, channel: str, handler: Callable) -> None:
        """
        Register an event handler for a specific channel.
        
        Args:
            channel: Channel name to listen to
            handler: Function to call when messages are received
        """
        if channel not in self._event_handlers:
            self._event_handlers[channel] = []
        self._event_handlers[channel].append(handler)

    def off(self, channel: str, handler: Callable = None) -> None:
        """
        Remove event handler(s) for a channel.
        
        Args:
            channel: Channel name
            handler: Specific handler to remove (if None, removes all)
        """
        if channel not in self._event_handlers:
            return
            
        if handler is None:
            del self._event_handlers[channel]
        else:
            try:
                self._event_handlers[channel].remove(handler)
            except ValueError:
                pass

    async def listen(self) -> AsyncIterator[Message]:
        """
        Listen for incoming messages.
        
        Yields:
            Message objects as they are received
        """
        while self.is_connected or not self._message_queue.empty():
            try:
                # Wait for message with timeout to allow periodic connection checks
                message = await asyncio.wait_for(
                    self._message_queue.get(), 
                    timeout=1.0
                )
                yield message
            except asyncio.TimeoutError:
                # Continue loop to check connection status
                continue
            except Exception as e:
                logger.error(f"Error in message listener: {e}")
                break

    async def run_forever(self) -> None:
        """Run the client indefinitely, handling reconnections."""
        try:
            async for message in self.listen():
                # Messages are handled by event handlers
                pass
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
        finally:
            await self.disconnect()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
