#!/bin/bash
# Setup script for pre-commit hooks

set -e

echo "🔧 Setting up pre-commit hooks for AniVault..."

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "📦 Installing pre-commit..."
    pip install pre-commit
fi

# Install pre-commit hooks
echo "🔗 Installing pre-commit hooks..."
pre-commit install

# Install pre-commit hooks for commit-msg
echo "🔗 Installing commit-msg hooks..."
pre-commit install --hook-type commit-msg

# Run pre-commit on all files to test
echo "🧪 Testing pre-commit hooks on all files..."
pre-commit run --all-files

echo "✅ Pre-commit setup complete!"
echo ""
echo "📋 Available commands:"
echo "  pre-commit run --all-files    # Run all hooks on all files"
echo "  pre-commit run <hook-id>      # Run specific hook"
echo "  pre-commit clean              # Clean pre-commit cache"
echo "  pre-commit uninstall          # Uninstall pre-commit hooks"
echo ""
echo "🎯 Pre-commit hooks will now run automatically on git commit!"
