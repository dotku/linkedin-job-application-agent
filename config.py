import os
from dotenv import load_dotenv

# Default to development if not set
ENV = os.getenv('PYTHON_ENV', 'development')

# Load the appropriate .env file
if ENV == 'production':
    load_dotenv('.env.production')
elif ENV == 'staging':
    load_dotenv('.env.staging')
else:  # development
    load_dotenv('.env.local')

# Common configurations
class Config:
    ENV = ENV
    DEBUG = ENV != 'production'
    TESTING = ENV == 'test'
    
    # LinkedIn credentials
    LINKEDIN_EMAIL = os.getenv('LINKEDIN_EMAIL')
    LINKEDIN_PASSWORD = os.getenv('LINKEDIN_PASSWORD')
    
    # Job search parameters
    JOB_SEARCH_KEYWORDS = os.getenv('JOB_SEARCH_KEYWORDS')
    JOB_SEARCH_LOCATION = os.getenv('JOB_SEARCH_LOCATION')
    MAX_JOBS = int(os.getenv('MAX_JOBS', '25'))
    
    # Browser settings
    BROWSER_HEADLESS = ENV == 'production'
    BROWSER_TIMEOUT = int(os.getenv('BROWSER_TIMEOUT', '10'))
    
    # Logging settings
    LOG_LEVEL = 'INFO' if ENV == 'production' else 'DEBUG'
    LOG_MODE = os.getenv('LOG_MODE', 'file').lower()
    LOG_DIR = '.logs' if LOG_MODE != 'print' else None
    
    @classmethod
    def is_production(cls):
        return cls.ENV == 'production'
    
    @classmethod
    def is_development(cls):
        return cls.ENV == 'development'
    
    @classmethod
    def is_staging(cls):
        return cls.ENV == 'staging'
    
    @classmethod
    def should_log_to_file(cls):
        return cls.LOG_MODE != 'print'
