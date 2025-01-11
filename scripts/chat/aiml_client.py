import aiohttp
import asyncio
from typing import Dict, Any, Optional, List, AsyncGenerator
import logging
import json
from .chat_client import ChatClient
from .chat_response import ChatResponse

logger = logging.getLogger(__name__)

class AIMLClient(ChatClient):
    """Client for AIML API"""
    
    def __init__(self, api_key: str, api_url: str = "https://api.aimlapi.com/v1"):
        super().__init__(api_key, api_url)
        self.headers = {
            'x-api-key': api_key,
            'Content-Type': 'application/json'
        }
        self.model = "mistralai/Mistral-7B-Instruct-v0.2"

    async def chat(self, 
                  prompt: str, 
                  system_prompt: Optional[str] = None,
                  temperature: float = 0.7,
                  max_tokens: int = 500) -> ChatResponse:
        """Send a chat request to AIML API"""
        try:
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            if system_prompt:
                messages.insert(0, {"role": "system", "content": system_prompt})
            
            data = {
                'model': self.model,
                'messages': messages,
                'temperature': temperature,
                'max_tokens': max_tokens
            }
            
            logger.debug(f"Request URL: {self.api_url}/chat/completions")
            logger.debug(f"Request headers: {self.headers}")
            logger.debug(f"Request data: {data}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.api_url}/chat/completions", 
                                     headers=self.headers,
                                     json=data) as response:
                    response.raise_for_status()
                    result = await response.json()
                    logger.debug(f"Response: {result}")
                    
                    return ChatResponse.success(
                        content=result['choices'][0]['message']['content'],
                        metadata={
                            'model': result.get('model'),
                            'usage': result.get('usage')
                        }
                    )
                    
        except Exception as e:
            logger.error(f"Chat request failed: {str(e)}")
            if isinstance(e, aiohttp.ClientResponseError):
                error_text = await e.response.text()
                logger.error(f"Error response: {error_text}")
            return ChatResponse.error(str(e))

    async def stream_chat(self,
                         prompt: str,
                         system_prompt: Optional[str] = None,
                         temperature: float = 0.7,
                         max_tokens: int = 500) -> AsyncGenerator[str, None]:
        """Stream chat responses from AIML API"""
        try:
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            if system_prompt:
                messages.insert(0, {"role": "system", "content": system_prompt})
            
            data = {
                'model': self.model,
                'messages': messages,
                'temperature': temperature,
                'max_tokens': max_tokens,
                'stream': True
            }
            
            logger.debug(f"Request URL: {self.api_url}/chat/completions")
            logger.debug(f"Request headers: {self.headers}")
            logger.debug(f"Request data: {data}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.api_url}/chat/completions",
                                     headers=self.headers,
                                     json=data) as response:
                    response.raise_for_status()
                    async for line in response.content:
                        if line:
                            try:
                                line = line.decode('utf-8').strip()
                                if line.startswith('data: '):
                                    line = line[6:]  # Remove 'data: ' prefix
                                if line and line != '[DONE]':
                                    chunk = json.loads(line)
                                    if chunk['choices'][0]['delta'].get('content'):
                                        logger.debug(f"Stream chunk: {chunk}")
                                        yield chunk['choices'][0]['delta']['content']
                            except Exception as e:
                                logger.error(f"Error parsing stream chunk: {str(e)}")
                                continue
                            
        except Exception as e:
            logger.error(f"Stream chat failed: {str(e)}")
            yield f"Error: {str(e)}"
    
    async def analyze_text(self,
                          text: str,
                          analysis_type: str,
                          options: Optional[Dict[str, Any]] = None) -> ChatResponse:
        """Analyze text using AIML API"""
        try:
            data = {
                'text': text,
                'type': analysis_type,
                'options': options or {}
            }
            
            logger.debug(f"Request URL: {self.api_url}/analyze")
            logger.debug(f"Request headers: {self.headers}")
            logger.debug(f"Request data: {data}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.api_url}/analyze",
                                     headers=self.headers,
                                     json=data) as response:
                    response.raise_for_status()
                    result = await response.json()
                    logger.debug(f"Response: {result}")
                    
                    return ChatResponse.success(
                        content=result['analysis'],
                        metadata=result.get('details')
                    )
                    
        except Exception as e:
            logger.error(f"Text analysis failed: {str(e)}")
            if isinstance(e, aiohttp.ClientResponseError):
                error_text = await e.response.text()
                logger.error(f"Error response: {error_text}")
            return ChatResponse.error(str(e))
    
    async def generate_text(self,
                          prompt: str,
                          options: Optional[Dict[str, Any]] = None) -> ChatResponse:
        """Generate text using AIML API"""
        try:
            data = {
                'prompt': prompt,
                'options': options or {}
            }
            
            logger.debug(f"Request URL: {self.api_url}/generate")
            logger.debug(f"Request headers: {self.headers}")
            logger.debug(f"Request data: {data}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.api_url}/generate",
                                     headers=self.headers,
                                     json=data) as response:
                    response.raise_for_status()
                    result = await response.json()
                    logger.debug(f"Response: {result}")
                    
                    return ChatResponse.success(
                        content=result['generated_text'],
                        metadata=result.get('details')
                    )
                    
        except Exception as e:
            logger.error(f"Text generation failed: {str(e)}")
            if isinstance(e, aiohttp.ClientResponseError):
                error_text = await e.response.text()
                logger.error(f"Error response: {error_text}")
            return ChatResponse.error(str(e))
    
    async def batch_process(self,
                          prompts: List[str],
                          system_prompt: Optional[str] = None) -> List[ChatResponse]:
        """Process multiple prompts in batch"""
        try:
            tasks = []
            for prompt in prompts:
                tasks.append(self.chat(prompt, system_prompt))
            
            return await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"Batch processing failed: {str(e)}")
            return [ChatResponse.error(str(e))] * len(prompts)
    
    async def health_check(self) -> bool:
        """Check if the AIML API is available"""
        try:
            logger.debug(f"Request URL: {self.api_url}/health")
            logger.debug(f"Request headers: {self.headers}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/health",
                                    headers=self.headers) as response:
                    logger.debug(f"Response: {response.status}")
                    return response.status == 200
                    
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False
