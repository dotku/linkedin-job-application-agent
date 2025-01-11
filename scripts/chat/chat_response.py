from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class ChatResponse:
    """Class to represent a chat response"""
    content: str
    success: bool
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @property
    def is_error(self) -> bool:
        """Check if response contains an error"""
        return not self.success or self.error is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary"""
        return {
            'content': self.content,
            'success': self.success,
            'error': self.error,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatResponse':
        """Create response from dictionary"""
        return cls(
            content=data.get('content', ''),
            success=data.get('success', False),
            error=data.get('error'),
            metadata=data.get('metadata')
        )
    
    @classmethod
    def error(cls, error_message: str) -> 'ChatResponse':
        """Create an error response"""
        return cls(
            content='',
            success=False,
            error=error_message
        )
    
    @classmethod
    def success(cls, content: str, metadata: Optional[Dict[str, Any]] = None) -> 'ChatResponse':
        """Create a success response"""
        return cls(
            content=content,
            success=True,
            metadata=metadata
        )
