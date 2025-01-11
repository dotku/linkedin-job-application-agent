#!/usr/bin/env python3

import os
import sys
import argparse
from typing import Optional
from dotenv import load_dotenv

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from scripts.aiml import api

class ChatCLI:
    """CLI for interacting with AIML API"""
    
    async def chat(self, message: str, stream: bool = False):
        """Send chat message"""
        try:
            completion = api.chat.completions.create(
                model="mistralai/Mistral-7B-Instruct-v0.2",
                messages=[
                    {"role": "user", "content": message}
                ],
                stream=stream
            )

            if stream:
                for chunk in completion:
                    if chunk.choices[0].delta.content:
                        print(chunk.choices[0].delta.content, end='', flush=True)
                print()  # New line at end
            else:
                print(completion.choices[0].message.content)

        except Exception as e:
            print(f"Error: {str(e)}", file=sys.stderr)
            sys.exit(1)

def main():
    """Main entry point"""
    load_dotenv('.env.local')
    
    parser = argparse.ArgumentParser(description='Chat with AI using AIML API')
    parser.add_argument('-m', '--message', type=str, help='Message to send')
    parser.add_argument('-s', '--stream', action='store_true', help='Stream response')
    
    args = parser.parse_args()
    
    if not args.message:
        parser.print_help()
        sys.exit(1)
    
    cli = ChatCLI()
    import asyncio
    asyncio.run(cli.chat(args.message, args.stream))

if __name__ == "__main__":
    main()
