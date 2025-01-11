# Chat Module

This module provides a flexible and extensible chat client interface for interacting with various AI/ML APIs.

## Features

- Abstract `ChatClient` base class for implementing different API clients
- Built-in support for AIML API
- Asynchronous API calls using `aiohttp`
- Streaming chat responses
- Text analysis and generation
- Batch processing
- Health checks
- Structured response handling

## Usage

```python
from scripts.chat import AIMLClient, ChatResponse

# Initialize client
client = AIMLClient(api_key="your_api_key")

# Simple chat
async def chat_example():
    response = await client.chat(
        prompt="What is the weather like?",
        system_prompt="You are a helpful assistant"
    )
    print(response.content)

# Stream chat
async def stream_example():
    async for message in client.stream_chat(
        prompt="Tell me a story",
        temperature=0.8
    ):
        print(message, end="")

# Analyze text
async def analyze_example():
    response = await client.analyze_text(
        text="This is a sample text",
        analysis_type="sentiment"
    )
    print(response.content)

# Batch process
async def batch_example():
    prompts = [
        "What is Python?",
        "What is JavaScript?",
        "What is Java?"
    ]
    responses = await client.batch_process(prompts)
    for resp in responses:
        print(resp.content)
```

## Response Format

The `ChatResponse` class provides a structured way to handle API responses:

```python
ChatResponse(
    content="Response content",
    success=True,
    error=None,
    metadata={
        'model': 'gpt-3.5-turbo',
        'usage': {
            'prompt_tokens': 10,
            'completion_tokens': 20
        }
    }
)
```

## Error Handling

All methods return `ChatResponse` objects that include error information if something goes wrong:

```python
if response.is_error:
    print(f"Error occurred: {response.error}")
else:
    print(f"Success: {response.content}")
```

## Extending

To add support for a new API, extend the `ChatClient` base class:

```python
class NewAPIClient(ChatClient):
    async def chat(self, prompt: str, **kwargs) -> ChatResponse:
        # Implement chat method
        pass

    async def stream_chat(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        # Implement streaming
        pass

    # Implement other required methods
```
