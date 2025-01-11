# Scripts Directory

This directory contains utility scripts and modules for the LinkedIn Auto Apply project. Below are the available modules and how to use them.

## Chat Module

The `chat` module provides a flexible interface for interacting with AI/ML APIs to assist with job applications.

### Installation

1. Install required dependencies:
```bash
pip install aiohttp python-dotenv
```

2. Set up your API key in `.env.local`:
```env
AIM_API_KEY=your_api_key_here
```

### Quick Start

```python
import asyncio
from scripts.chat import AIMLClient

async def main():
    # Initialize the client
    client = AIMLClient(
        api_key="your_api_key",
        api_url="https://aimlapi.com/api"
    )
    
    # Simple chat request
    response = await client.chat(
        prompt="What are the key skills for a software engineer?",
        system_prompt="You are a helpful career advisor"
    )
    print(response.content)

# Run the example
asyncio.run(main())
```

### Features

1. **Chat Conversations**
```python
# Regular chat
response = await client.chat(
    prompt="Tell me about Python",
    temperature=0.7
)

# Streaming chat
async for message in client.stream_chat(
    prompt="Explain async programming",
    max_tokens=1000
):
    print(message, end="")
```

2. **Text Analysis**
```python
# Analyze job descriptions
response = await client.analyze_text(
    text="Job description text here",
    analysis_type="job_requirements"
)

# Get required skills
skills = response.content
```

3. **Text Generation**
```python
# Generate cover letter
response = await client.generate_text(
    prompt="Generate a cover letter for software engineer position",
    options={
        "style": "professional",
        "length": "medium"
    }
)
print(response.content)
```

4. **Batch Processing**
```python
# Process multiple job descriptions
job_descriptions = [
    "First job description",
    "Second job description",
    "Third job description"
]

responses = await client.batch_process(
    prompts=job_descriptions,
    system_prompt="Analyze job requirements"
)

for resp in responses:
    print(resp.content)
```

### Error Handling

```python
response = await client.chat("Your prompt")
if response.is_error:
    print(f"Error: {response.error}")
else:
    print(f"Success: {response.content}")
```

### Response Format

The `ChatResponse` class provides a structured way to handle API responses:

```python
response = await client.chat("Your prompt")
print(f"Content: {response.content}")
print(f"Success: {response.success}")
print(f"Error: {response.error}")
print(f"Metadata: {response.metadata}")
```

### Integration with LinkedIn Auto Apply

The chat module is used in the LinkedIn Auto Apply project to:

1. **Analyze Job Postings**
```python
async def analyze_job(job_description: str) -> bool:
    response = await client.analyze_text(
        text=job_description,
        analysis_type="job_match"
    )
    return "suitable" in response.content.lower()
```

2. **Generate Application Responses**
```python
async def generate_answer(question: str) -> str:
    response = await client.chat(
        prompt=f"How should I answer this job application question: {question}",
        system_prompt="You are a professional job application assistant"
    )
    return response.content
```

3. **Fill Application Forms**
```python
async def fill_form_field(field_name: str, context: str) -> str:
    response = await client.generate_text(
        prompt=f"Generate appropriate content for {field_name} field. Context: {context}"
    )
    return response.content
```

### Best Practices

1. **API Key Security**
   - Always store API keys in `.env.local`
   - Never commit API keys to version control

2. **Error Handling**
   - Always check `response.is_error` before using the response
   - Log errors appropriately
   - Implement retry logic for failed requests

3. **Resource Management**
   - Use appropriate `max_tokens` to control response length
   - Implement rate limiting for batch requests
   - Close sessions properly when done

4. **Performance**
   - Use streaming for long responses
   - Batch similar requests together
   - Cache frequently used responses

### Contributing

To add support for a new AI/ML API:

1. Create a new client class in `chat/` directory
2. Inherit from `ChatClient` base class
3. Implement all required methods
4. Add tests for the new client
5. Update documentation

For more detailed information about the chat module, see the [chat module README](chat/README.md).
