import logging
import logging.handlers
import os
from datetime import datetime
from typing import Any, Dict

def setup_logger(name: str = "linkedin_auto_apply", log_file: str = None) -> logging.Logger:
    """
    Set up logger with file and console handlers
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Only add handlers if they haven't been added yet
    if not logger.handlers:
        # Create formatters
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_formatter = logging.Formatter('%(levelname)s - %(message)s')
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # Create file handler if log_file specified
        if log_file:
            # Create .log directory if it doesn't exist
            log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.logs')
            os.makedirs(log_dir, exist_ok=True)
            
            # Set up file handler with full path
            log_path = os.path.join(log_dir, f"{log_file}.log")
            file_handler = logging.FileHandler(log_path)
            file_handler.setLevel(logging.INFO)
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
