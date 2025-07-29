#!/usr/bin/env python3
"""
PyPI Publishing Script for GmGnAPI
This script automates the process of building and publishing to PyPI.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def run_command(cmd, check=True, capture_output=False):
    """Run a shell command and handle errors."""
    print(f"🔧 Running: {cmd}")
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
            return result.stdout.strip()
        else:
            subprocess.run(cmd, shell=True, check=check)
            return None
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")
        if capture_output:
            print(f"Error output: {e.stderr}")
        sys.exit(1)


def check_prerequisites():
    """Check if all required tools are installed."""
    print("🔍 Checking prerequisites...")
    
    required_tools = ["python", "pip", "git"]
    for tool in required_tools:
        try:
            run_command(f"which {tool}", capture_output=True)
        except subprocess.CalledProcessError:
            print(f"❌ {tool} is not installed or not in PATH")
            sys.exit(1)
    
    # Check if twine is installed
    try:
        run_command("python -m twine --version", capture_output=True)
    except subprocess.CalledProcessError:
        print("📦 Installing twine...")
        run_command("pip install twine")
    
    # Check if build is installed
    try:
        run_command("python -m build --version", capture_output=True)
    except subprocess.CalledProcessError:
        print("📦 Installing build...")
        run_command("pip install build")
    
    print("✅ All prerequisites met!")


def clean_build_artifacts():
    """Clean previous build artifacts."""
    print("🧹 Cleaning build artifacts...")
    
    artifacts = ["build", "dist", "*.egg-info"]
    for artifact in artifacts:
        for path in Path(".").glob(artifact):
            if path.is_dir():
                shutil.rmtree(path)
                print(f"  Removed directory: {path}")
            else:
                path.unlink()
                print(f"  Removed file: {path}")


def validate_package():
    """Validate package configuration."""
    print("🔍 Validating package configuration...")
    
    # Check if required files exist
    required_files = ["pyproject.toml", "README.md", "src/gmgnapi/__init__.py"]
    for file_path in required_files:
        if not Path(file_path).exists():
            print(f"❌ Required file missing: {file_path}")
            sys.exit(1)
    
    # Check if version is set
    init_file = Path("src/gmgnapi/__init__.py")
    content = init_file.read_text()
    if '__version__' not in content:
        print("❌ Version not found in __init__.py")
        sys.exit(1)
    
    print("✅ Package validation passed!")


def run_tests():
    """Run the test suite."""
    print("🧪 Running tests...")
    
    if Path("tests").exists():
        run_command("python -m pytest tests/ -v")
    else:
        print("⚠️  No tests directory found, skipping tests")


def build_package():
    """Build the package for distribution."""
    print("📦 Building package...")
    
    # Build source distribution and wheel
    run_command("python -m build")
    
    # Verify the build
    dist_files = list(Path("dist").glob("*"))
    if not dist_files:
        print("❌ No distribution files created")
        sys.exit(1)
    
    print("✅ Package built successfully!")
    for dist_file in dist_files:
        print(f"  📄 {dist_file}")


def check_distribution():
    """Check the built distribution."""
    print("🔍 Checking distribution...")
    
    run_command("python -m twine check dist/*")
    print("✅ Distribution check passed!")


def publish_to_test_pypi():
    """Publish to Test PyPI first."""
    print("🚀 Publishing to Test PyPI...")
    
    print("Please enter your Test PyPI credentials when prompted.")
    run_command("python -m twine upload --repository testpypi dist/*")
    
    print("✅ Published to Test PyPI!")
    print("🔗 Check your package at: https://test.pypi.org/project/gmgnapi/")


def publish_to_pypi():
    """Publish to production PyPI."""
    response = input("Are you sure you want to publish to production PyPI? (yes/no): ")
    if response.lower() != "yes":
        print("❌ Publication cancelled")
        return
    
    print("🚀 Publishing to PyPI...")
    
    print("Please enter your PyPI credentials when prompted.")
    run_command("python -m twine upload dist/*")
    
    print("✅ Published to PyPI!")
    print("🔗 Check your package at: https://pypi.org/project/gmgnapi/")


def create_git_tag():
    """Create a git tag for the release."""
    # Extract version from __init__.py
    init_file = Path("src/gmgnapi/__init__.py")
    content = init_file.read_text()
    
    for line in content.split('\n'):
        if line.strip().startswith('__version__'):
            version = line.split('=')[1].strip().strip('"\'')
            break
    else:
        print("❌ Could not extract version from __init__.py")
        return
    
    tag_name = f"v{version}"
    
    # Check if tag already exists
    try:
        run_command(f"git rev-parse {tag_name}", capture_output=True)
        print(f"⚠️  Tag {tag_name} already exists")
        return
    except subprocess.CalledProcessError:
        pass  # Tag doesn't exist, which is good
    
    response = input(f"Create git tag {tag_name}? (yes/no): ")
    if response.lower() == "yes":
        run_command(f"git tag -a {tag_name} -m 'Release {tag_name}'")
        run_command(f"git push origin {tag_name}")
        print(f"✅ Created and pushed tag {tag_name}")


def main():
    """Main publishing workflow."""
    print("🚀 GmGnAPI PyPI Publishing Script")
    print("=" * 50)
    
    # Change to project root
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    try:
        check_prerequisites()
        validate_package()
        clean_build_artifacts()
        
        # Optional: run tests
        if input("Run tests before building? (yes/no): ").lower() == "yes":
            run_tests()
        
        build_package()
        check_distribution()
        
        # Publishing options
        print("\nPublishing Options:")
        print("1. Test PyPI (recommended first)")
        print("2. Production PyPI")
        print("3. Both (Test PyPI first, then production)")
        print("4. Skip publishing")
        
        choice = input("Choose option (1-4): ").strip()
        
        if choice == "1":
            publish_to_test_pypi()
        elif choice == "2":
            publish_to_pypi()
        elif choice == "3":
            publish_to_test_pypi()
            if input("Continue to production PyPI? (yes/no): ").lower() == "yes":
                publish_to_pypi()
        elif choice == "4":
            print("⏭️  Skipping publishing")
        else:
            print("❌ Invalid choice")
            sys.exit(1)
        
        # Optional: create git tag
        create_git_tag()
        
        print("\n🎉 Publishing workflow completed!")
        
    except KeyboardInterrupt:
        print("\n❌ Publishing cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
