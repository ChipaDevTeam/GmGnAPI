# GmGnAPI

**Professional Python client library for GMGN.ai WebSocket API**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Discord](https://img.shields.io/discord/YOUR_DISCORD_ID?color=7289da&label=Discord&logo=discord&logoColor=white)](https://discord.gg/ub46R9Dk)

GmGnAPI provides real-time access to Solana blockchain data through GMGN.ai's WebSocket API with advanced features including intelligent filtering, data export capabilities, monitoring statistics, and automated alerting.

## 🔗 Quick Links

- 📚 **[Documentation](https://yourusername.github.io/GmGnAPI/)** - Complete guides and API reference
- 💬 **[Discord Community](https://discord.gg/ub46R9Dk)** - Get help and discuss strategies
- 🌐 **[Create GMGN Account](https://gmgn.ai/?ref=9dLKvFyE&chain=sol)** - Sign up with our referral link to support the project

## 🚀 Features

### Core Functionality
- **Real-time WebSocket connection** to GMGN.ai API
- **Multiple data channels**: New pools, token launches, pair updates, chain statistics, social info, wallet trades, limit orders
- **Automatic reconnection** with exponential backoff
- **Comprehensive error handling** and logging
- **Type-safe** with full Pydantic model validation
- **Async/await** support for modern Python applications

### Advanced Features
- **🔍 Intelligent Filtering**: Advanced token filtering by market cap, liquidity, volume, holder count, exchange, and risk scores
- **📊 Data Export**: Export to JSON, CSV, or SQLite database with automatic file rotation and compression
- **📈 Monitoring & Statistics**: Real-time connection metrics, message counts, unique token/pool tracking
- **🚨 Alert System**: Configurable alerts for market conditions with rate limiting and webhook support
- **⚡ Rate Limiting**: Configurable message processing limits to prevent overwhelming
- **🔄 Queue Management**: Buffered message processing with configurable queue sizes

## 📦 Installation

```bash
pip install gmgnapi
```

### Development Installation

```bash
git clone https://github.com/yourusername/gmgnapi.git
cd gmgnapi
pip install -e .
```

## 🔑 Account Setup

### 1. Create GMGN Account
Create your GMGN account using our referral link to support the project:
👉 **[Create GMGN Account](https://gmgn.ai/?ref=9dLKvFyE&chain=sol)**

### 2. Get API Token
1. Log in to your GMGN account
2. Navigate to Account Settings
3. Generate an API token
4. Copy and securely store your token

### 3. Join Community
Join our Discord server for support and updates:
👉 **[Discord Community](https://discord.gg/ub46R9Dk)**

## 🎯 Quick Start

### Basic Usage

```python
import asyncio
from gmgnapi import GmGnClient

async def on_new_pool(pool_info):
    if pool_info.pools:
        pool = pool_info.pools[0]
        token_info = pool.bti
        if token_info:
            print(f"New pool: {token_info.s} ({token_info.n})")

async def main():
    client = GmGnClient()
    client.on_new_pool(on_new_pool)
    
    await client.connect()
    await client.subscribe_new_pools()
    
    # Keep running
    while True:
        await asyncio.sleep(1)

asyncio.run(main())
```

### Advanced Usage with Filtering and Export

```python
import asyncio
from decimal import Decimal
from gmgnapi import (
    GmGnEnhancedClient, 
    TokenFilter, 
    DataExportConfig,
    AlertConfig
)

async def main():
    # Configure advanced token filtering
    token_filter = TokenFilter(
        min_market_cap=Decimal("50000"),       # $50k minimum market cap
        min_liquidity=Decimal("10000"),        # $10k minimum liquidity
        min_volume_24h=Decimal("5000"),        # $5k minimum daily volume
        min_holder_count=10,                   # 10+ holders
        exchanges=["raydium", "orca"],         # Specific exchanges only
        exclude_symbols=["SCAM", "TEST"],      # Exclude potential scams
        max_risk_score=0.7,                    # Maximum risk threshold
    )
    
    # Configure data export
    export_config = DataExportConfig(
        enabled=True,
        format="json",                         # "json", "csv", or "database"
        file_path="./gmgn_data",              # Export directory
        max_file_size_mb=50,                  # File rotation at 50MB
        rotation_interval_hours=6,            # Rotate every 6 hours
        compress=True,                        # Enable compression
    )
    
    # Configure alerts
    alert_config = AlertConfig(
        enabled=True,
        webhook_url="https://hooks.slack.com/...",  # Optional webhook
        conditions=[
            {
                "type": "high_value_pool",
                "min_market_cap": 100000,
                "description": "Alert for pools > $100k"
            }
        ],
        rate_limit_seconds=300,               # Max 1 alert per 5 minutes
    )
    
    # Initialize enhanced client
    client = GmGnEnhancedClient(
        token_filter=token_filter,
        export_config=export_config,
        alert_config=alert_config,
        rate_limit=100,                       # Max 100 messages/second
    )
    
    # Event handlers
    async def on_new_pool(pool_info):
        if pool_info.pools:
            pool = pool_info.pools[0]
            token_info = pool.bti
            if token_info:
                print(f"🔥 Filtered pool: {token_info.s} - ${token_info.mc:,}")
    
    async def on_volume_spike(pair_data):
        if pair_data.volume_24h_usd > Decimal("500000"):
            print(f"📈 Volume spike: ${pair_data.volume_24h_usd:,}")
    
    client.on_new_pool(on_new_pool)
    client.on_pair_update(on_volume_spike)
    
    # Connect and subscribe
    await client.connect()
    await client.subscribe_all_channels()
    
    # Monitor and get statistics
    while True:
        await asyncio.sleep(60)
        
        stats = client.get_monitoring_stats()
        print(f"📊 Stats: {stats.total_messages:,} messages, "
              f"{stats.unique_tokens_seen} tokens, "
              f"{stats.unique_pools_seen} pools")

asyncio.run(main())
```

## 📋 Available Channels

### Public Channels
- **`new_pools`**: New liquidity pool creation events
- **`pair_update`**: Trading pair price and volume updates  
- **`token_launch`**: New token launch notifications
- **`chain_stats`**: Blockchain statistics and metrics

### Authenticated Channels (require access token)
- **`token_social`**: Token social media and community information
- **`wallet_trades`**: Wallet trading activity and transactions
- **`limit_orders`**: Limit order updates and fills

## 🔧 Configuration Options

### TokenFilter
Filter tokens based on various criteria:

```python
TokenFilter(
    min_market_cap=Decimal("10000"),          # Minimum market cap in USD
    max_market_cap=Decimal("1000000"),        # Maximum market cap in USD
    min_liquidity=Decimal("5000"),            # Minimum liquidity in USD
    min_volume_24h=Decimal("1000"),           # Minimum 24h volume in USD
    min_holder_count=10,                      # Minimum number of holders
    exchanges=["raydium", "orca"],            # Allowed exchanges
    symbols=["SOL", "USDC"],                  # Specific symbols to include
    exclude_symbols=["SCAM", "TEST"],         # Symbols to exclude
    max_risk_score=0.5,                       # Maximum risk score (0-1)
)
```

### DataExportConfig
Configure data export and storage:

```python
DataExportConfig(
    enabled=True,                             # Enable/disable export
    format="json",                            # "json", "csv", or "database"
    file_path="./exports",                    # Export directory
    max_file_size_mb=100,                     # File size limit for rotation
    rotation_interval_hours=24,               # Time-based rotation
    compress=True,                            # Enable compression
    include_metadata=True,                    # Include extra metadata
)
```

### AlertConfig
Set up alerts and notifications:

```python
AlertConfig(
    enabled=True,                             # Enable/disable alerts
    webhook_url="https://hooks.slack.com/...", # Webhook URL for notifications
    email="alerts@example.com",               # Email for alerts
    conditions=[                              # Custom alert conditions
        {
            "type": "new_pool",
            "min_liquidity": 100000,
            "description": "High liquidity pool alert"
        }
    ],
    rate_limit_seconds=300,                   # Minimum time between alerts
)
```

## 📊 Monitoring and Statistics

Get real-time monitoring statistics:

```python
stats = client.get_monitoring_stats()

print(f"Total messages: {stats.total_messages:,}")
print(f"Messages per minute: {stats.messages_per_minute:.1f}")
print(f"Unique tokens seen: {stats.unique_tokens_seen}")
print(f"Unique pools seen: {stats.unique_pools_seen}")
print(f"Connection uptime: {stats.connection_uptime:.0f}s")
print(f"Error count: {stats.error_count}")
```

## 📁 Data Export Formats

### JSON Export
```json
{
    "timestamp": "2024-01-15T10:30:00",
    "channel": "new_pools",
    "data": {
        "c": "sol",
        "p": [{
            "a": "pool_address_here",
            "ba": "base_token_address", 
            "qa": "quote_token_address",
            "bti": {
                "s": "TOKEN",
                "n": "Token Name",
                "mc": 150000
            }
        }]
    }
}
```

### CSV Export
```csv
timestamp,channel,data
2024-01-15T10:30:00,new_pools,"{""c"":""sol"",""p"":[...]}"
```

### SQLite Database
Tables: `messages`, `new_pools`, `trades` with structured data storage.

## 🚨 Error Handling

GmGnAPI provides comprehensive error handling:

```python
from gmgnapi import (
    GmGnAPIError,
    ConnectionError,
    AuthenticationError,
    SubscriptionError,
    MessageParsingError,
)

try:
    await client.connect()
    await client.subscribe_wallet_trades()
except AuthenticationError:
    print("Invalid access token")
except ConnectionError:
    print("Failed to connect to WebSocket")
except SubscriptionError as e:
    print(f"Subscription failed: {e}")
except GmGnAPIError as e:
    print(f"API error: {e}")
```

## 📚 Examples

The `examples/` directory contains comprehensive examples:

- **`basic_usage.py`**: Simple connection and data streaming
- **`advanced_monitoring.py`**: Full-featured monitoring with statistics
- **`data_export.py`**: Data export in multiple formats
- **`filtering_alerts.py`**: Advanced filtering and alerting
- **`multiple_channels.py`**: Subscribe to multiple data channels

## 🧪 Testing

Run the test suite:

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=gmgnapi

# Run specific test file
pytest tests/test_client.py
```

## 🛠️ Development

### Code Quality
```bash
# Format code
black src/ tests/ examples/

# Sort imports  
isort src/ tests/ examples/

# Type checking
mypy src/

# Linting
flake8 src/ tests/
```

### Building Documentation
```bash
# Install docs dependencies
pip install -e ".[docs]"

# Build docs
cd docs/
make html
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`pytest`)
6. Format your code (`black`, `isort`)
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to the branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [GMGN.ai](https://gmgn.ai/) for providing the WebSocket API
- [Pydantic](https://pydantic-docs.helpmanual.io/) for data validation
- [websockets](https://websockets.readthedocs.io/) for WebSocket client implementation

## 🔗 Links

- **Documentation**: [https://gmgnapi.readthedocs.io/](https://gmgnapi.readthedocs.io/)
- **PyPI Package**: [https://pypi.org/project/gmgnapi/](https://pypi.org/project/gmgnapi/)
- **GitHub Issues**: [https://github.com/yourusername/gmgnapi/issues](https://github.com/yourusername/gmgnapi/issues)
- **GMGN.ai**: [https://gmgn.ai/](https://gmgn.ai/)

---

**⚡ Built for speed, designed for reliability, crafted for the Solana ecosystem.**
