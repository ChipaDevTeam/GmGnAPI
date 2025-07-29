# PyPI Publishing Guide for GmGnAPI

This guide walks you through publishing GmGnAPI to PyPI, making it available for users to install with `pip install gmgnapi`.

## Prerequisites

### 1. Install Required Tools

```bash
# Install build tools
pip install build twine

# Verify installations
python -m build --version
python -m twine --version
```

### 2. Create PyPI Accounts

1. **Test PyPI Account**: https://test.pypi.org/account/register/
2. **Production PyPI Account**: https://pypi.org/account/register/

### 3. Generate API Tokens

For secure authentication, generate API tokens instead of using passwords:

#### Test PyPI Token:
1. Go to https://test.pypi.org/manage/account/token/
2. Create a new API token with scope "Entire account"
3. Save the token (starts with `pypi-`)

#### Production PyPI Token:
1. Go to https://pypi.org/manage/account/token/
2. Create a new API token with scope "Entire account"
3. Save the token securely

### 4. Configure Credentials

Create a `.pypirc` file in your home directory:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = pypi-YOUR_PRODUCTION_TOKEN_HERE

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR_TEST_TOKEN_HERE
```

## Automated Publishing (Recommended)

Use the provided automated script:

```bash
# Make script executable (if not already)
chmod +x scripts/publish_to_pypi.py

# Run the publishing script
python scripts/publish_to_pypi.py
```

The script will:
1. ✅ Check prerequisites
2. 🧹 Clean build artifacts
3. 🔍 Validate package configuration
4. 🧪 Optionally run tests
5. 📦 Build the package
6. 🔍 Check distribution
7. 🚀 Publish to PyPI (with options)
8. 🏷️ Optionally create git tag

## Manual Publishing Steps

### Step 1: Prepare the Release

1. **Update Version Number**:
   ```python
   # In src/gmgnapi/__init__.py
   __version__ = "0.2.0"  # Update version
   ```

2. **Update Changelog**:
   ```bash
   # Add release notes to CHANGELOG.md
   echo "## [0.2.0] - $(date +%Y-%m-%d)" >> CHANGELOG.md
   ```

3. **Commit Changes**:
   ```bash
   git add .
   git commit -m "Prepare release v0.2.0"
   git push origin main
   ```

### Step 2: Build the Package

1. **Clean Previous Builds**:
   ```bash
   rm -rf build/ dist/ *.egg-info/
   ```

2. **Build Source Distribution and Wheel**:
   ```bash
   python -m build
   ```

3. **Verify Build**:
   ```bash
   ls dist/
   # Should show: gmgnapi-0.2.0.tar.gz and gmgnapi-0.2.0-py3-none-any.whl
   ```

### Step 3: Test the Package

1. **Check Distribution**:
   ```bash
   python -m twine check dist/*
   ```

2. **Test Installation Locally**:
   ```bash
   pip install dist/gmgnapi-0.2.0-py3-none-any.whl
   python -c "import gmgnapi; print(gmgnapi.__version__)"
   ```

### Step 4: Publish to Test PyPI

1. **Upload to Test PyPI**:
   ```bash
   python -m twine upload --repository testpypi dist/*
   ```

2. **Test Installation from Test PyPI**:
   ```bash
   # Create a new virtual environment
   python -m venv test_env
   source test_env/bin/activate  # On Windows: test_env\Scripts\activate

   # Install from Test PyPI
   pip install --index-url https://test.pypi.org/simple/ gmgnapi

   # Test the package
   python -c "import gmgnapi; print('Success!')"
   ```

### Step 5: Publish to Production PyPI

1. **Upload to PyPI**:
   ```bash
   python -m twine upload dist/*
   ```

2. **Verify Publication**:
   - Visit: https://pypi.org/project/gmgnapi/
   - Test installation: `pip install gmgnapi`

### Step 6: Create Release Tag

1. **Create Git Tag**:
   ```bash
   git tag -a v0.2.0 -m "Release v0.2.0"
   git push origin v0.2.0
   ```

2. **Create GitHub Release**:
   - Go to: https://github.com/theshadow76/GmGnAPI/releases
   - Click "Create a new release"
   - Select tag `v0.2.0`
   - Add release notes

## Post-Publication Checklist

### 1. Verify Installation

```bash
# Test in clean environment
python -m venv verify_env
source verify_env/bin/activate
pip install gmgnapi
python -c "
import gmgnapi
print(f'Version: {gmgnapi.__version__}')
print('✅ Package installed successfully!')
"
```

### 2. Update Documentation

1. **Update README badges**:
   ```markdown
   ![PyPI version](https://badge.fury.io/py/gmgnapi.svg)
   ![Python versions](https://img.shields.io/pypi/pyversions/gmgnapi.svg)
   ![Downloads](https://pepy.tech/badge/gmgnapi)
   ```

2. **Deploy documentation**:
   ```bash
   # If using GitHub Pages
   git checkout gh-pages
   cp -r docs/* .
   git add .
   git commit -m "Update documentation for v0.2.0"
   git push origin gh-pages
   ```

### 3. Announce the Release

1. **GitHub Discussions**: Announce in project discussions
2. **Social Media**: Share on relevant platforms
3. **Community**: Post in relevant Discord/Telegram channels

## Troubleshooting

### Common Issues

1. **Build Fails**:
   ```bash
   # Check pyproject.toml syntax
   python -c "import tomli; tomli.load(open('pyproject.toml', 'rb'))"
   
   # Update build tools
   pip install --upgrade build setuptools wheel
   ```

2. **Upload Fails**:
   ```bash
   # Check credentials
   python -m twine upload --repository testpypi dist/* --verbose
   
   # Clear cache
   rm -rf ~/.cache/pip/
   ```

3. **Version Conflicts**:
   ```bash
   # Check existing versions
   pip index versions gmgnapi
   
   # Update version in __init__.py
   # Increment: 0.1.0 → 0.1.1 (patch) or 0.2.0 (minor)
   ```

### Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.0.0): Breaking API changes
- **MINOR** (0.2.0): New features, backward compatible
- **PATCH** (0.1.1): Bug fixes, backward compatible

## Security Best Practices

1. **Never commit API tokens** to version control
2. **Use token authentication** instead of passwords
3. **Set token scopes** to minimum required
4. **Rotate tokens regularly**
5. **Use 2FA** on PyPI accounts

## Continuous Integration

Consider setting up GitHub Actions for automated publishing:

```yaml
# .github/workflows/publish.yml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: '3.x'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine
    - name: Build package
      run: python -m build
    - name: Publish to PyPI
      uses: pypa/gh-action-pypi-publish@release/v1
      with:
        password: ${{ secrets.PYPI_API_TOKEN }}
```

## Support

For issues with publishing:

1. Check [PyPI Help](https://pypi.org/help/)
2. Review [Packaging Python Projects](https://packaging.python.org/tutorials/packaging-projects/)
3. Open an issue in the [GmGnAPI repository](https://github.com/theshadow76/GmGnAPI/issues)

---

Happy publishing! 🚀
