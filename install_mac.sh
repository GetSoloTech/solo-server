#!/bin/bash

# Solo CLI Installation Script for Mac
# This script installs uv package manager, creates a virtual environment,
# clones the solo-cli repository, and installs it in development mode.

set -e  # Exit on any error

echo "🚀 Starting Solo CLI installation for Mac..."

# Step 1: Install uv package manager version 0.9.3
echo "📦 Installing uv package manager version 0.9.3..."
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH for current session
export PATH="$HOME/.cargo/bin:$PATH"

# Verify uv installation
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv installation failed"
    exit 1
fi

echo "✅ uv package manager installed successfully"

# Step 2: Create virtual environment with Python 3.12.12
echo "🐍 Creating virtual environment with Python 3.12.12..."
uv venv solo_venv --python 3.12.12

# Step 3: Activate virtual environment
echo "🔧 Activating virtual environment..."
source solo_venv/bin/activate


# Step 6: Set up environment variables for dependencies
echo "🔧 Setting up environment variables for dependencies..."
export MUJOCO_PATH=""
export MUJOCO_GL=osmesa

# Step 7: Install solo-cli in development mode
echo "⚙️ Installing solo-cli in development mode..."
# Try to install with mujoco environment variables set
uv pip install -e . || {
    echo "⚠️  Installation failed with mujoco dependency. Trying alternative approach..."
    echo "📦 Installing core dependencies first..."
    uv pip install typer GPUtil psutil requests rich huggingface_hub pydantic transformers accelerate num2words
    echo "📦 Installing lerobot without mujoco dependencies..."
    uv pip install lerobot --no-deps
    echo "📦 Installing lerobot dependencies manually..."
    uv pip install torch torchvision torchaudio
    uv pip install gymnasium
    uv pip install opencv-python
    uv pip install pillow
    echo "⚙️ Retrying solo-cli installation..."
    uv pip install -e .
}

echo "🎉 Solo CLI installation completed successfully!"
echo ""
echo "To activate the virtual environment in the future, run:"
echo "source solo_venv/bin/activate"
echo ""
echo "To test the installation, run:"
echo "solo --help"