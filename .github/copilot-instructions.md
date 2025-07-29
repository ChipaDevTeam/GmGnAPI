# Copilot Instructions for GmGnAPI

<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

## Project Overview

This is **GmGnAPI**, a professional Python client library for connecting to GMGN.ai's WebSocket API to receive real-time Solana blockchain data streams.

## Key Technologies & Libraries

- **Python 3.8+** with modern async/await patterns
- **WebSockets** for real-time communication
- **Pydantic v2** for data validation and serialization
- **asyncio** for asynchronous operations
- **pytest** for testing framework
- **Black** for code formatting
- **mypy** for type checking

## Code Style & Standards

- Follow **PEP 8** style guidelines
- Use **type hints** for all function parameters and return values
- Prefer **async/await** over callbacks for asynchronous operations
- Use **Pydantic models** for all data structures
- Include comprehensive **docstrings** for all public methods
- Handle **exceptions** gracefully with custom exception classes
- Use **logging** instead of print statements

## Architecture Patterns

### Client Design
- **Singleton-like WebSocket connection** with automatic reconnection
- **Event-driven architecture** with handler registration
- **Async context manager** support for resource management
- **Queue-based message buffering** for reliable message handling

### Data Models
- **Pydantic BaseModel** for all data structures
- **Decimal types** for financial data to avoid floating-point errors
- **Optional fields** with proper validation
- **Custom validators** for data transformation

### Error Handling
- **Custom exception hierarchy** inheriting from GmGnAPIError
- **Graceful degradation** on connection issues
- **Retry logic** with exponential backoff
- **Comprehensive logging** for debugging

## API Design Principles

- **Intuitive method names** (e.g., `subscribe_new_pools()`)
- **Consistent parameter naming** across all methods
- **Optional chain parameter** defaulting to "sol"
- **Authentication handled transparently** where required
- **Event handlers** for real-time data processing

## Development Guidelines

### When adding new features:
1. Create **Pydantic models** for new data types
2. Add **subscription methods** following existing patterns
3. Include **comprehensive tests** with mocks
4. Update **examples** to demonstrate usage
5. Add **type hints** and **docstrings**

### For WebSocket channels:
- Add channel name to `SUPPORTED_CHANNELS` set
- Create dedicated subscription method
- Include proper error handling for authentication
- Document required parameters clearly

### For data processing:
- Use **Decimal** for all monetary values
- Handle **None/null** values gracefully
- Validate data using **Pydantic validators**
- Convert timestamps to **datetime objects**

## Testing Strategy

- **Unit tests** for individual components
- **Integration tests** with mocked WebSocket connections
- **Async test patterns** using pytest-asyncio
- **Mock external dependencies** (websockets, network calls)
- **Test both success and failure scenarios**

## Documentation

- Use **Google-style docstrings** for all public methods
- Include **usage examples** in docstrings
- Document **exception types** that methods can raise
- Provide **type information** for all parameters

## Examples

When creating examples:
- Show **both basic and advanced usage patterns**
- Include **proper error handling**
- Demonstrate **event handler registration**
- Use **realistic data scenarios**
- Include **logging setup** for better user experience
