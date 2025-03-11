#!/bin/bash
# Simple installation script for the Wiki.js Exporter package

# Exit on error
set -e

echo "Installing Wiki.js Exporter..."

# Check if pip is available
if ! command -v pip &> /dev/null; then
    echo "Error: pip is not installed. Please install Python and pip first."
    exit 1
fi

# Create a virtual environment (optional)
read -p "Do you want to create a virtual environment? (y/n) " create_venv
if [[ $create_venv =~ ^[Yy]$ ]]; then
    echo "Creating virtual environment..."
    
    # Check if venv is available
    if ! python -m venv --help &> /dev/null; then
        echo "Error: venv module not available. Please install it first."
        exit 1
    fi
    
    python -m venv venv
    
    # Activate the virtual environment
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        # Windows
        source venv/Scripts/activate
    else
        # Unix-like
        source venv/bin/activate
    fi
    
    echo "Virtual environment created and activated."
fi

# Install the package
echo "Installing the package..."
pip install -e .

echo "Installation complete!"
echo "You can now use the 'wikijs' command to export content from Wiki.js."
echo "For usage information, run: wikijs --help" 