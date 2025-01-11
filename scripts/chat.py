#!/usr/bin/env python3

import os
import sys
import asyncio
import argparse
from typing import Optional
from scripts.aiml import api
from dotenv import load_dotenv

class ChatCLI:
    def __init__(self):
        self.setup_environment()
        
    def setup_environment(self):
        """Load environment variables"""
        # Get the directory of this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        
        # Load environment variables
        load_dotenv(os.path.join(project_root, '.env.local'))
        
        # Add project root to Python path
        sys.path.insert(0, project_root)
        
    async def chat(self, args):
        """Handle chat interaction"""
        try:
            message = args.message
            stream = args.stream
            model = "mistralai/Mistral-7B-Instruct-v0.2"
            completion = api.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": message}
                ],
                stream=stream
            )

            if stream:
                async for chunk in completion:
                    if chunk.choices[0].delta.content:
                        print(chunk.choices[0].delta.content, end='', flush=True)
                print()  # New line at end
            else:
                print(completion.choices[0].message.content)

        except Exception as e:
            print(f"Error: {str(e)}", file=sys.stderr)
            sys.exit(1)
    
    async def analyze(self, args):
        """Handle text analysis"""
        try:
            response = await api.analyze_text(
                text=args.text,
                analysis_type=args.type,
                options=args.options
            )
            
            if response.is_error:
                print(f"Error: {response.error}", file=sys.stderr)
                sys.exit(1)
            else:
                if args.json:
                    import json
                    print(json.dumps(response.to_dict(), indent=2))
                else:
                    print(response.content)
        
        except Exception as e:
            print(f"Error: {str(e)}", file=sys.stderr)
            sys.exit(1)
    
    async def generate(self, args):
        """Handle text generation"""
        try:
            response = await api.generate_text(
                prompt=args.prompt,
                options=args.options
            )
            
            if response.is_error:
                print(f"Error: {response.error}", file=sys.stderr)
                sys.exit(1)
            else:
                if args.json:
                    import json
                    print(json.dumps(response.to_dict(), indent=2))
                else:
                    print(response.content)
        
        except Exception as e:
            print(f"Error: {str(e)}", file=sys.stderr)
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Chat with AI using AIML API')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Chat command
    chat_parser = subparsers.add_parser('chat', help='Chat with AI')
    chat_parser.add_argument('-m', '--message', required=True, help='Message to send')
    chat_parser.add_argument('-s', '--system', default='You are a helpful assistant',
                           help='System prompt')
    chat_parser.add_argument('-t', '--temperature', type=float, default=0.7,
                           help='Temperature setting')
    chat_parser.add_argument('--max-tokens', type=int, default=500,
                           help='Maximum tokens in response')
    chat_parser.add_argument('--stream', action='store_true',
                           help='Enable streaming mode')
    chat_parser.add_argument('--json', action='store_true',
                           help='Output in JSON format')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze text')
    analyze_parser.add_argument('text', help='Text to analyze')
    analyze_parser.add_argument('--type', default='general',
                              help='Type of analysis')
    analyze_parser.add_argument('--options', type=dict, default={},
                              help='Analysis options')
    analyze_parser.add_argument('--json', action='store_true',
                              help='Output in JSON format')
    
    # Generate command
    generate_parser = subparsers.add_parser('generate', help='Generate text')
    generate_parser.add_argument('prompt', help='Generation prompt')
    generate_parser.add_argument('--options', type=dict, default={},
                               help='Generation options')
    generate_parser.add_argument('--json', action='store_true',
                               help='Output in JSON format')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    cli = ChatCLI()
    
    if args.command == 'chat':
        asyncio.run(cli.chat(args))
    elif args.command == 'analyze':
        asyncio.run(cli.analyze(args))
    elif args.command == 'generate':
        asyncio.run(cli.generate(args))

if __name__ == '__main__':
    main()
