#!/bin/bash
# MemoryBridge Ubuntu Environment Setup Script
# Configures Python virtual environment, dependencies, GPU drivers, and Ollama LLaMA-3 model.

echo "============================================================"
echo "  🚀 MemoryBridge: Ubuntu Hackathon Environment Setup"
echo "============================================================"
echo ""

# 1. Update and install Ubuntu system packages
echo "📦 Step 1: Installing Ubuntu System Dependencies..."
sudo apt update
sudo apt install -y python3-pip python3-venv ffmpeg libsndfile1 portaudio19-dev build-essential curl wget git

# 2. Setup Python Virtual Environment
echo "🐍 Step 2: Setting up Python Virtual Environment (.venv)..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "✅ Created .venv directory."
fi

source .venv/bin/activate

# 3. Upgrade pip and install PyTorch with CUDA support
echo "⚡ Step 3: Installing PyTorch with CUDA Support for GPU Acceleration..."
pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 4. Install requirements
echo "📚 Step 4: Installing MemoryBridge Dependencies..."
pip install -r requirements.txt

# 5. Check Ollama installation
echo "🦙 Step 5: Setting up Ollama for Local LLaMA-3..."
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "✅ Ollama is already installed."
fi

# Pull LLaMA-3
echo "🔥 Step 6: Pulling LLaMA-3 8B Model for local edge AI..."
ollama pull llama3

echo ""
echo "============================================================"
echo "  🎉 Setup Complete!"
echo "  To start MemoryBridge:"
echo "  1. source .venv/bin/activate"
echo "  2. python server.py"
echo "============================================================"
