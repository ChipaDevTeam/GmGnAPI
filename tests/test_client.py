"""
Unit tests for GmGnAPI client.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from gmgnapi import GmGnClient
from gmgnapi.exceptions import ConnectionError, AuthenticationError
from gmgnapi.models import Message, SubscriptionRequest


class TestGmGnClient:
    """Test cases for GmGnClient."""

    def test_client_initialization(self):
        """Test client initialization with default values."""
        client = GmGnClient()
        
        assert client.ws_url == GmGnClient.DEFAULT_WS_URL
        assert client.user_agent == GmGnClient.DEFAULT_USER_AGENT
        assert client.auto_reconnect is True
        assert client.max_reconnect_attempts == 5
        assert not client.is_connected

    def test_client_initialization_with_params(self):
        """Test client initialization with custom parameters."""
        client = GmGnClient(
            ws_url="wss://custom.url",
            device_id="test-device",
            client_id="test-client",
            user_agent="Test/1.0",
            auto_reconnect=False,
            max_reconnect_attempts=3
        )
        
        assert client.ws_url == "wss://custom.url"
        assert client.device_id == "test-device"
        assert client.client_id == "test-client"
        assert client.user_agent == "Test/1.0"
        assert client.auto_reconnect is False
        assert client.max_reconnect_attempts == 3

    def test_build_connection_url(self):
        """Test WebSocket URL building."""
        client = GmGnClient(device_id="test-device", client_id="test-client")
        url = client._build_connection_url()
        
        assert "device_id=test-device" in url
        assert "client_id=test-client" in url
        assert "from_app=gmgn" in url
        assert client.ws_url in url

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_websocket):
        """Test successful WebSocket connection."""
        with patch('gmgnapi.client.websockets.connect') as mock_connect:
            mock_connect.return_value = mock_websocket
            client = GmGnClient()
            await client.connect()
            
            assert client.is_connected
            assert client._websocket == mock_websocket

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test WebSocket connection failure."""
        with patch('gmgnapi.client.websockets.connect', side_effect=Exception("Connection failed")):
            client = GmGnClient()
            
            with pytest.raises(ConnectionError):
                await client.connect()
            
            assert not client.is_connected

    @pytest.mark.asyncio
    async def test_disconnect(self, mock_websocket):
        """Test WebSocket disconnection."""
        with patch('gmgnapi.client.websockets.connect') as mock_connect:
            mock_connect.return_value = mock_websocket
            client = GmGnClient()
            await client.connect()
            
            assert client.is_connected
            
            await client.disconnect()
            
            assert not client.is_connected
            mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscribe_new_pools(self, mock_websocket):
        """Test subscribing to new pools."""
        with patch('gmgnapi.client.websockets.connect') as mock_connect:
            mock_connect.return_value = mock_websocket
            client = GmGnClient()
            await client.connect()
            
            await client.subscribe_new_pools(chain="sol")
            
            # Verify subscription was sent
            mock_websocket.send.assert_called_once()
            sent_data = json.loads(mock_websocket.send.call_args[0][0])
            
            assert sent_data["action"] == "subscribe"
            assert sent_data["channel"] == "new_pool_info"
            assert sent_data["data"] == [{"chain": "sol"}]

    @pytest.mark.asyncio
    async def test_subscribe_wallet_trades_without_token(self, mock_websocket):
        """Test wallet subscription without access token."""
        with patch('gmgnapi.client.websockets.connect') as mock_connect:
            mock_connect.return_value = mock_websocket
            client = GmGnClient()
            await client.connect()
            
            with pytest.raises(AuthenticationError):
                await client.subscribe_wallet_trades(
                    chain="sol",
                    wallet_address="test-wallet"
                )

    @pytest.mark.asyncio
    async def test_subscribe_wallet_trades_with_token(self, mock_websocket):
        """Test wallet subscription with access token."""
        with patch('gmgnapi.client.websockets.connect') as mock_connect:
            mock_connect.return_value = mock_websocket
            client = GmGnClient(access_token="test-token")
            await client.connect()
            
            await client.subscribe_wallet_trades(
                chain="sol",
                wallet_address="test-wallet"
            )
            
            mock_websocket.send.assert_called_once()
            sent_data = json.loads(mock_websocket.send.call_args[0][0])
            
            assert sent_data["channel"] == "wallet_trade_data"
            assert sent_data["access_token"] == "test-token"

    def test_event_handlers(self):
        """Test event handler registration and removal."""
        client = GmGnClient()
        
        def test_handler(data):
            pass
            
        # Register handler
        client.on("new_pool_info", test_handler)
        assert "new_pool_info" in client._event_handlers
        assert test_handler in client._event_handlers["new_pool_info"]
        
        # Remove specific handler
        client.off("new_pool_info", test_handler)
        assert len(client._event_handlers.get("new_pool_info", [])) == 0
        
        # Register and remove all handlers
        client.on("new_pool_info", test_handler)
        client.off("new_pool_info")
        assert "new_pool_info" not in client._event_handlers

    @pytest.mark.asyncio
    async def test_handle_message(self, sample_message_data):
        """Test message handling."""
        client = GmGnClient()
        handler_called = False
        received_data = None
        
        def test_handler(data):
            nonlocal handler_called, received_data
            handler_called = True
            received_data = data
            
        client.on("new_pool_info", test_handler)
        
        # Simulate message handling
        raw_message = json.dumps(sample_message_data)
        await client._handle_message(raw_message)
        
        # Check that handler was called
        assert handler_called
        assert received_data == sample_message_data["data"]
        
        # Check message was added to queue
        assert not client._message_queue.empty()
        message = await client._message_queue.get()
        assert message.channel == "new_pool_info"

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_websocket):
        """Test client as async context manager."""
        with patch('gmgnapi.client.websockets.connect') as mock_connect:
            mock_connect.return_value = mock_websocket
            async with GmGnClient() as client:
                assert client.is_connected
            
            # Should be disconnected after exiting context
            mock_websocket.close.assert_called_once()


class TestModels:
    """Test cases for data models."""

    def test_message_model(self, sample_message_data):
        """Test Message model."""
        message = Message(**sample_message_data)
        
        assert message.action == "message"
        assert message.channel == "new_pool_info"
        assert message.id == "test123"
        assert message.data["token_address"] == "0xabc..."

    def test_subscription_request_model(self, sample_subscription_data):
        """Test SubscriptionRequest model."""
        subscription = SubscriptionRequest(**sample_subscription_data)
        
        assert subscription.action == "subscribe"
        assert subscription.channel == "new_pool_info"
        assert subscription.data == [{"chain": "sol"}]
        assert subscription.f == "w"
        
        # Test JSON serialization
        json_data = subscription.model_dump_json()
        assert isinstance(json_data, str)
        
        # Test that ID is generated if not provided
        subscription_no_id = SubscriptionRequest(
            channel="test",
            data=[{"test": "data"}]
        )
        assert len(subscription_no_id.id) == 16
