#!/bin/bash

# Release script for fzf-ai
# This script builds and tests the package for release

set -e

echo "Building fzf-ai package..."

# Clean previous builds
rm -rf build/ dist/ *.egg-info/

# Build source distribution
python3 setup.py sdist

# Build wheel distribution
python3 setup.py bdist_wheel

# Test the package
echo "Testing package installation..."
pip3 install --user --break-system-packages --force-reinstall dist/*.whl

# Verify installation
echo "Verifying installation..."
which fzf-ai || echo "Warning: fzf-ai not found in PATH"
which fzf-ai-index || echo "Warning: fzf-ai-index not found in PATH"

echo "Package built successfully!"
echo "Distribution files:"
ls -la dist/

echo ""
echo "To upload to PyPI:"
echo "twine upload dist/*"

echo ""
echo "To test locally:"
echo "pip3 install --user --break-system-packages dist/*.whl"