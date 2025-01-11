from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, AsyncGenerator
from .chat_response import ChatResponse

class ChatClient(ABC):
    """Abstract base class for chat clients"""
    
    def __init__(self, api_key: str, api_url: str):
        self.api_key = api_key
        self.api_url = api_url
    
    @abstractmethod
    async def chat(self, 
                  prompt: str, 
                  system_prompt: Optional[str] = None,
                  temperature: float = 0.7,
                  max_tokens: int = 500) -> ChatResponse:
        """Send a chat request to the API"""
        pass
    
    @abstractmethod
    async def stream_chat(self,
                         prompt: str,
                         system_prompt: Optional[str] = None,
                         temperature: float = 0.7,
                         max_tokens: int = 500) -> AsyncGenerator[str, None]:
        """Stream chat responses from the API"""
        pass
    
    @abstractmethod
    async def analyze_text(self,
                          text: str,
                          analysis_type: str,
                          options: Optional[Dict[str, Any]] = None) -> ChatResponse:
        """Analyze text using the API"""
        pass
    
    @abstractmethod
    async def generate_text(self,
                          prompt: str,
                          options: Optional[Dict[str, Any]] = None) -> ChatResponse:
        """Generate text using the API"""
        pass
    
    @abstractmethod
    async def batch_process(self,
                          prompts: List[str],
                          system_prompt: Optional[str] = None) -> List[ChatResponse]:
        """Process multiple prompts in batch"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the API is available"""
        pass
