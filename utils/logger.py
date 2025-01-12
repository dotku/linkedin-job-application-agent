import logging
import logging.handlers
import os
from datetime import datetime
from typing import Any, Dict

def setup_logger(name: str = "linkedin_auto_apply", log_name: str = None, level: int = logging.INFO) -> logging.Logger:
    """
    Set up logger with file and console handlers
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear any existing handlers
    logger.handlers = []
    
    # Get log mode from environment
    log_mode = os.getenv('LOG_MODE', 'file').lower()
    
    # Create formatters
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
    console_formatter = logging.Formatter('%(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
    
    # Always add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Add file handler only if not in print mode
    if log_mode != 'print':
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # Create file handler
        log_file = os.path.join(log_dir, f"{log_name}_{datetime.now().strftime('%Y%m%d')}.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger

def log_with_context(logger: logging.Logger, level: str, message: str, extra_fields: Dict[str, Any] = None):
    """
    Log message with additional context fields
    """
    if extra_fields is None:
        extra_fields = {}
        
    # Add timestamp to extra fields
    extra_fields['timestamp'] = datetime.now().isoformat()
    
    # Log the message
    getattr(logger, level.lower())(message, extra=extra_fields)

# Create default logger instance
logger = setup_logger()
