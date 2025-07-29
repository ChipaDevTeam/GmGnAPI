"""
Test configuration and utilities.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

# Ensure asyncio is configured for testing
pytest_plugins = ['pytest_asyncio']


@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection."""
    mock = AsyncMock()
    mock.send = AsyncMock()
    mock.close = AsyncMock()
    mock.__aiter__ = AsyncMock(return_value=iter([]))
    # Fix for async context issues
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def sample_message_data():
    """Sample message data for testing."""
    return {
        "action": "message",
        "channel": "new_pool_info",
        "id": "test123",
        "data": {
            "pool_address": "0x123...",
            "token_address": "0xabc...",
            "chain": "sol",
            "initial_liquidity_usd": "10000.00"
        }
    }


@pytest.fixture
def sample_subscription_data():
    """Sample subscription request data."""
    return {
        "action": "subscribe",
        "channel": "new_pool_info", 
        "f": "w",
        "id": "sub123",
        "data": [{"chain": "sol"}]
    }
