# Contributing to GmGnAPI

Thank you for your interest in contributing to GmGnAPI! This document provides guidelines for contributing to this open-source project.

## 🚀 Quick Start

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/yourusername/gmgnapi.git
   cd gmgnapi
   ```
3. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. **Install development dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```
5. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

## 🎯 How to Contribute

### Reporting Bugs

Before creating bug reports, please check the [issue tracker](https://github.com/gmgnapi/gmgnapi/issues) to see if the problem has already been reported.

When creating a bug report, please include:
- **Clear title** and description
- **Steps to reproduce** the behavior
- **Expected behavior** vs actual behavior  
- **Python version** and **operating system**
- **Code sample** that demonstrates the issue
- **Error messages** or stack traces

### Suggesting Enhancements

Enhancement suggestions are welcome! Please:
- Use a **clear and descriptive title**
- Provide a **detailed description** of the suggested enhancement
- Explain **why this enhancement would be useful**
- Provide **code examples** if applicable

### Code Contributions

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/amazing-feature
   ```

2. **Make your changes** following our coding standards

3. **Write tests** for your changes

4. **Run the test suite**:
   ```bash
   pytest
   ```

5. **Check code quality**:
   ```bash
   black src tests examples
   isort src tests examples
   flake8 src tests examples
   mypy src
   ```

6. **Commit your changes**:
   ```bash
   git commit -m 'Add amazing feature'
   ```

7. **Push to your branch**:
   ```bash
   git push origin feature/amazing-feature
   ```

8. **Open a Pull Request**

## 📝 Coding Standards

### Python Style
- Follow **PEP 8** style guidelines
- Use **Black** for code formatting (line length: 88)
- Use **isort** for import sorting
- Maximum line length: **88 characters**

### Type Hints
- Use **type hints** for all function parameters and return values
- Import types from `typing` module when needed
- Use `Optional[T]` for nullable types

### Documentation
- Use **Google-style docstrings** for all public methods
- Include **parameter descriptions** and **return value descriptions**
- Document **raised exceptions**
- Provide **usage examples** where helpful

### Error Handling
- Use **custom exception classes** from `gmgnapi.exceptions`
- Provide **meaningful error messages**
- Log errors appropriately using the `logging` module

### Async Code
- Use **async/await** syntax consistently
- Handle **asyncio exceptions** properly
- Use **async context managers** where appropriate

## 🧪 Testing Guidelines

### Test Structure
- Place tests in the `tests/` directory
- Name test files with `test_*.py` pattern
- Use **descriptive test method names**

### Writing Tests
- Use **pytest** as the testing framework
- Use **pytest-asyncio** for async tests
- **Mock external dependencies** (WebSocket connections, etc.)
- Test **both success and failure scenarios**
- Aim for **high test coverage**

### Test Categories
- **Unit tests**: Test individual components in isolation
- **Integration tests**: Test component interactions
- **End-to-end tests**: Test complete workflows

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=gmgnapi --cov-report=html

# Run specific test categories
pytest -m unit
pytest -m integration

# Run tests in parallel
pytest -n auto
```

## 📚 Documentation

### API Documentation
- Document all **public methods and classes**
- Include **parameter types and descriptions**
- Provide **usage examples**
- Document **exceptions** that can be raised

### Examples
- Create **realistic examples** in the `examples/` directory
- Include **proper error handling** in examples
- Add **comments** explaining complex parts
- Test examples to ensure they work

### README Updates
- Update the README when adding **new features**
- Keep **installation instructions** current
- Update **usage examples** as needed

## 🔄 Development Workflow

### Branch Naming
- `feature/description` - New features
- `bugfix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring

### Commit Messages
Use clear, descriptive commit messages:
```
Add WebSocket reconnection with exponential backoff

- Implement automatic reconnection on connection loss
- Add configurable retry attempts and delay
- Include tests for reconnection scenarios
- Update documentation with new parameters
```

### Pull Request Process
1. **Update documentation** if needed
2. **Add tests** for new functionality
3. **Ensure all tests pass**
4. **Update CHANGELOG.md** if applicable
5. **Request review** from maintainers

## 🛠 Development Tools

### Required Tools
- **Python 3.8+**
- **Git**
- **pip** or **pipenv**

### Recommended Tools
- **VS Code** with Python extension
- **pre-commit** for automated checks
- **pytest** for testing
- **mypy** for type checking

### IDE Configuration
For VS Code, recommended settings in `.vscode/settings.json`:
```json
{
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "editor.formatOnSave": true
}
```

## 🏷 Release Process

1. **Update version** in `pyproject.toml`
2. **Update CHANGELOG.md** with release notes
3. **Create release tag**: `git tag v0.1.0`
4. **Push tag**: `git push origin v0.1.0`
5. **Create GitHub release** with release notes
6. **Publish to PyPI** (maintainers only)

## 📧 Communication

- **GitHub Issues** - Bug reports and feature requests
- **GitHub Discussions** - General questions and discussions
- **Email** - contact@gmgnapi.dev for sensitive issues

## 📜 License

By contributing to GmGnAPI, you agree that your contributions will be licensed under the MIT License.

## 🙏 Recognition

Contributors will be:
- **Listed in CONTRIBUTORS.md**
- **Mentioned in release notes** for significant contributions
- **Added to GitHub contributors** list

## ❓ Questions?

If you have questions about contributing, please:
1. Check the **documentation**
2. Search **existing issues**
3. Ask in **GitHub Discussions**
4. Contact the **maintainers**

Thank you for contributing to GmGnAPI! 🚀
