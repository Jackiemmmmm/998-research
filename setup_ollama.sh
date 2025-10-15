#!/bin/bash
# Quick setup script for Ollama

echo "================================================"
echo "  Ollama Setup for Pattern Evaluation"
echo "================================================"
echo ""

# Check if Ollama is installed
if command -v ollama &> /dev/null; then
    echo "✅ Ollama is already installed"
else
    echo "📦 Installing Ollama..."

    # macOS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &> /dev/null; then
            brew install ollama
        else
            echo "Please install Ollama from: https://ollama.com/download"
            exit 1
        fi
    # Linux
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        curl -fsSL https://ollama.com/install.sh | sh
    else
        echo "Please install Ollama from: https://ollama.com/download"
        exit 1
    fi
fi

echo ""
echo "🚀 Starting Ollama service..."
# Start Ollama in background
ollama serve > /dev/null 2>&1 &
OLLAMA_PID=$!
echo "   Ollama PID: $OLLAMA_PID"

# Wait for Ollama to start
sleep 3

echo ""
echo "📥 Downloading recommended models..."
echo ""

# Download recommended models
echo "1. Llama 3.2 (3B) - Fast, good for testing"
ollama pull llama3.2

echo ""
echo "2. Llama 3.1 (8B) - Balanced performance (optional)"
read -p "Download Llama 3.1? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    ollama pull llama3.1
fi

echo ""
echo "================================================"
echo "✅ Ollama Setup Complete!"
echo "================================================"
echo ""
echo "Configuration:"
echo "  - Service running on: http://localhost:11434"
echo "  - Models installed: llama3.2"
echo ""
echo "Next steps:"
echo "1. Update .env file:"
echo "   LLM_PROVIDER=ollama"
echo "   OLLAMA_MODEL=llama3.2"
echo ""
echo "2. Test the setup:"
echo "   python src/llm_config.py"
echo ""
echo "3. Run evaluation:"
echo "   python run_evaluation.py --mode quick --delay 0"
echo ""
echo "To stop Ollama:"
echo "   kill $OLLAMA_PID"
echo ""
