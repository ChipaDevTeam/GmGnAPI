# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure and core functionality
- WebSocket client for GMGN.ai API connection
- Support for all major data channels (pools, launches, trades, etc.)
- Comprehensive Pydantic models for type safety
- Async/await support with automatic reconnection
- Event-driven architecture with handler registration
- Professional documentation and examples
- Full test suite with pytest
- Development tools configuration (black, isort, mypy, etc.)

## [0.1.0] - 2025-07-29

### Added
- Initial release of GmGnAPI
- Core WebSocket client implementation
- Support for Solana blockchain data streams:
  - New pool information (`new_pool_info`)
  - Trading pair updates (`new_pair_update`)
  - Token launches (`new_launched_info`)
  - Chain statistics (`chain_stat`)
  - Token social information (`token_social_info`)
  - Wallet trading data (`wallet_trade_data`) - requires authentication
  - Limit order information (`limit_order_info`) - requires authentication
- Professional project structure with:
  - Type-safe Pydantic models
  - Comprehensive error handling
  - Automatic reconnection with exponential backoff
  - Event handler system
  - Async context manager support
- Development environment setup:
  - pytest test framework
  - Black code formatting
  - isort import sorting
  - mypy type checking
  - flake8 linting
  - pre-commit hooks
- Documentation:
  - Comprehensive README with examples
  - API documentation
  - Contributing guidelines
  - MIT license
- Example scripts:
  - Basic usage example
  - Advanced monitoring with analytics
- CI/CD ready configuration
