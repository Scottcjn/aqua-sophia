#!/bin/bash
# Aqua Elya — Quick Setup
# Installs Python deps and optionally downloads Gemma 4

set -e

echo "=== Aqua Elya Setup ==="
echo ""

# Python deps
echo "[1/3] Installing Python dependencies..."
pip install requests opencv-python 2>/dev/null || pip install requests

# Check for Ollama
echo ""
echo "[2/3] Checking for Ollama (local LLM runtime)..."
if command -v ollama &> /dev/null; then
    echo "  Ollama found: $(ollama --version)"
    echo ""
    echo "  To download Gemma 4:"
    echo "    ollama pull gemma3:12b    # 12B — best for function calling"
    echo "    ollama pull gemma3:4b     # 4B — faster, lighter"
    echo ""
    echo "  To start the API server:"
    echo "    ollama serve              # Runs on http://localhost:11434"
    echo ""
    echo "  Then update config.py:"
    echo "    GEMMA_API_URL = 'http://localhost:11434/v1'"
    echo "    GEMMA_MODEL_NAME = 'gemma3:12b'"
else
    echo "  Ollama not found. Install from: https://ollama.ai"
    echo "  Or use llama.cpp / vLLM — any OpenAI-compatible API works."
fi

# Test run
echo ""
echo "[3/3] Testing with stub sensors (no hardware needed)..."
python3 scada_loop.py --no-gemma --fast --once

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Quick start:"
echo "  python3 scada_loop.py --no-gemma --fast     # Demo with fake data"
echo "  python3 scada_loop.py --fast                 # With Gemma 4 (needs Ollama)"
echo "  python3 scada_loop.py --mode esp32           # With real ESP32 sensors"
