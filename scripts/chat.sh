#!/bin/bash

# Default values
MESSAGE=""
SYSTEM_PROMPT="You are a helpful assistant"
TEMPERATURE=0.7
MAX_TOKENS=500
MODEL="default"
STREAM=false

# Help message
show_help() {
    echo "Usage: chat.sh [OPTIONS]"
    echo "Chat with AI using AIML API"
    echo
    echo "Options:"
    echo "  -m, --message       Message to send (required)"
    echo "  -s, --system        System prompt (default: 'You are a helpful assistant')"
    echo "  -t, --temperature   Temperature setting (default: 0.7)"
    echo "  --max-tokens        Maximum tokens in response (default: 500)"
    echo "  --model            Model to use (default: 'default')"
    echo "  --stream           Enable streaming mode (default: false)"
    echo "  -h, --help         Show this help message"
    echo
    echo "Example:"
    echo "  ./chat.sh -m 'What is Python?'"
    echo "  ./chat.sh -m 'Tell me a joke' -s 'You are a comedian' -t 0.9"
    echo "  ./chat.sh -m 'Write a story' --stream"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--message)
            MESSAGE="$2"
            shift 2
            ;;
        -s|--system)
            SYSTEM_PROMPT="$2"
            shift 2
            ;;
        -t|--temperature)
            TEMPERATURE="$2"
            shift 2
            ;;
        --max-tokens)
            MAX_TOKENS="$2"
            shift 2
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        --stream)
            STREAM=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Check if message is provided
if [ -z "$MESSAGE" ]; then
    echo "Error: Message is required"
    show_help
    exit 1
fi

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Create Python virtual environment if it doesn't exist
if [ ! -d "$PROJECT_ROOT/venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$PROJECT_ROOT/venv"
fi

# Activate virtual environment
source "$PROJECT_ROOT/venv/bin/activate"

# Install required packages if not already installed
pip install -q aiohttp python-dotenv 2>/dev/null

# Create Python script for chat
TEMP_SCRIPT=$(mktemp)
cat << EOF > "$TEMP_SCRIPT"
import asyncio
import os
from scripts.chat import AIMLClient
from dotenv import load_dotenv

async def main():
    # Load environment variables
    load_dotenv("$PROJECT_ROOT/.env.local")
    api_key = os.getenv("AIM_API_KEY")
    
    if not api_key:
        print("Error: AIM_API_KEY not found in .env.local")
        return
    
    # Initialize client
    client = AIMLClient(api_key=api_key)
    
    try:
        if ${STREAM}:
            # Streaming mode
            async for message in client.stream_chat(
                prompt="$MESSAGE",
                system_prompt="$SYSTEM_PROMPT",
                temperature=$TEMPERATURE,
                max_tokens=$MAX_TOKENS
            ):
                print(message, end="", flush=True)
            print()  # New line at end
        else:
            # Regular chat
            response = await client.chat(
                prompt="$MESSAGE",
                system_prompt="$SYSTEM_PROMPT",
                temperature=$TEMPERATURE,
                max_tokens=$MAX_TOKENS
            )
            
            if response.is_error:
                print(f"Error: {response.error}")
            else:
                print(response.content)
    
    except Exception as e:
        print(f"Error: {str(e)}")

asyncio.run(main())
EOF

# Run the Python script
PYTHONPATH="$PROJECT_ROOT" python "$TEMP_SCRIPT"

# Clean up
rm "$TEMP_SCRIPT"
deactivate
