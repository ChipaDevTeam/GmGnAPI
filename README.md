# GmGnAPI 🚀

[![PyPI version](https://badge.fury.io/py/gmgnapi.svg)](https://badge.fury.io/py/gmgnapi)
[![Python versions](https://img.shields.io/pypi/pyversions/gmgnapi.svg)](https://pypi.org/project/gmgnapi/)
[![License](https://img.shields.io/github/license/gmgnapi/gmgnapi.svg)](https://github.com/gmgnapi/gmgnapi/blob/main/LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Tests](https://github.com/gmgnapi/gmgnapi/workflows/Tests/badge.svg)](https://github.com/gmgnapi/gmgnapi/actions)
[![Coverage](https://codecov.io/gh/gmgnapi/gmgnapi/branch/main/graph/badge.svg)](https://codecov.io/gh/gmgnapi/gmgnapi)

**Professional Python client for GMGN.ai WebSocket API** - Get real-time Solana blockchain data streams with ease.

## 🌟 Features

- **Real-time WebSocket Connection**: Connect to GMGN's live data streams
- **Multiple Data Channels**: Subscribe to pools, pairs, launches, trades, and more
- **Async/Await Support**: Built with modern Python async patterns
- **Type Safety**: Full type hints and Pydantic models
- **Automatic Reconnection**: Robust connection handling with retry logic
- **Professional Grade**: Production-ready with comprehensive error handling
- **Easy to Use**: Simple, intuitive API design
- **Well Documented**: Extensive documentation and examples

## 🎯 Supported Data Streams

- **New Pool Info** (`new_pool_info`): Real-time new liquidity pool creations
- **Pair Updates** (`new_pair_update`): Live trading pair information updates  
- **Token Launches** (`new_launched_info`): Newly launched token notifications
- **Chain Statistics** (`chain_stat`): Blockchain network statistics
- **Social Info** (`token_social_info`): Token social media and community data
- **Wallet Trades** (`wallet_trade_data`): Individual wallet trading activity
- **Limit Orders** (`limit_order_info`): Limit order book updates

## 🚀 Quick Start

### Installation

```bash
pip install gmgnapi
```

### Basic Usage

```python
import asyncio
from gmgnapi import GmGnClient

async def main():
    client = GmGnClient()
    
    # Connect to GMGN WebSocket
    await client.connect()
    
    # Subscribe to new pool information
    await client.subscribe_new_pools(chain="sol")
    
    # Subscribe to token launches
    await client.subscribe_token_launches(chain="sol")
    
    # Listen for messages
    async for message in client.listen():
        print(f"Received: {message}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Advanced Usage with Custom Handlers

```python
import asyncio
from gmgnapi import GmGnClient
from gmgnapi.models import NewPoolInfo, TokenLaunchInfo

async def handle_new_pool(data: NewPoolInfo):
    print(f"New pool created: {data.token_address}")
    print(f"Initial liquidity: ${data.initial_liquidity_usd:,.2f}")

async def handle_token_launch(data: TokenLaunchInfo):
    print(f"Token launched: {data.name} ({data.symbol})")
    print(f"Market cap: ${data.market_cap_usd:,.2f}")

async def main():
    client = GmGnClient()
    
    # Register event handlers
    client.on("new_pool_info", handle_new_pool)
    client.on("new_launched_info", handle_token_launch)
    
    await client.connect()
    await client.subscribe_all_channels(chain="sol")
    
    # Keep listening
    await client.run_forever()

if __name__ == "__main__":
    asyncio.run(main())
```

### Wallet-Specific Trading Data

```python
import asyncio
from gmgnapi import GmGnClient

async def main():
    client = GmGnClient()
    await client.connect()
    
    # Monitor specific wallet trades (requires access token)
    wallet_address = "9F5WjUyPaRmFbnwJofAVhPWjCPUQ9Xaiss3ErsJRjGNf"
    await client.subscribe_wallet_trades(
        chain="sol",
        wallet_address=wallet_address,
        access_token="your_access_token_here"
    )
    
    async for message in client.listen():
        if message.channel == "wallet_trade_data":
            print(f"Wallet trade: {message.data}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 📊 Data Models

All data is returned as typed Pydantic models for easy access and validation:

```python
from gmgnapi.models import NewPoolInfo, PairUpdate, TokenLaunchInfo

# Type-safe data access
pool_info: NewPoolInfo = message.data
print(f"Token: {pool_info.token_address}")
print(f"Liquidity: ${pool_info.initial_liquidity_usd}")
print(f"Chain: {pool_info.chain}")
```

## 🔧 Configuration

### Environment Variables

```bash
# Optional: Set custom WebSocket URL
GMGN_WS_URL=wss://ws.gmgn.ai/quotation

# Optional: Set custom user agent
GMGN_USER_AGENT="Your-App/1.0.0"

# Optional: Set access token for authenticated endpoints
GMGN_ACCESS_TOKEN=your_jwt_token_here
```

### Client Configuration

```python
from gmgnapi import GmGnClient

client = GmGnClient(
    ws_url="wss://ws.gmgn.ai/quotation",
    device_id="your-device-id",
    client_id="your-client-id", 
    user_agent="Your-App/1.0.0",
    auto_reconnect=True,
    max_reconnect_attempts=5,
    reconnect_delay=5.0
)
```

## 🧪 Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/gmgnapi/gmgnapi.git
cd gmgnapi

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=gmgnapi --cov-report=html

# Run only unit tests
pytest -m unit

# Run only integration tests  
pytest -m integration
```

### Code Quality

```bash
# Format code
black src tests examples

# Sort imports
isort src tests examples

# Lint code
flake8 src tests examples

# Type checking
mypy src
```

## 📚 Documentation

- **[API Reference](https://gmgnapi.readthedocs.io/en/latest/api.html)**: Complete API documentation
- **[User Guide](https://gmgnapi.readthedocs.io/en/latest/guide.html)**: Detailed usage examples
- **[Examples](examples/)**: Ready-to-run example scripts
- **[Contributing](CONTRIBUTING.md)**: How to contribute to the project

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Quick Contribution Steps

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for your changes
5. Ensure all tests pass (`pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📋 Requirements

- Python 3.8+
- `websockets>=11.0.3`
- `aiohttp>=3.8.0`
- `pydantic>=2.0.0`

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This is an unofficial client library for the GMGN.ai API. Use at your own risk. The authors are not responsible for any financial losses incurred through the use of this library.

## 🔗 Links

- **Website**: [https://gmgnapi.dev](https://gmgnapi.dev)
- **Documentation**: [https://gmgnapi.readthedocs.io](https://gmgnapi.readthedocs.io)
- **PyPI**: [https://pypi.org/project/gmgnapi/](https://pypi.org/project/gmgnapi/)
- **GitHub**: [https://github.com/gmgnapi/gmgnapi](https://github.com/gmgnapi/gmgnapi)
- **Issues**: [https://github.com/gmgnapi/gmgnapi/issues](https://github.com/gmgnapi/gmgnapi/issues)

## 🙏 Acknowledgments

- Thanks to GMGN.ai for providing the WebSocket API
- Inspired by the Solana and DeFi community
- Built with ❤️ for developers and traders

---

**Star ⭐ this repository if you find it useful!**
