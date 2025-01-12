import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

# Get API key from environment
api_key = os.getenv('AIML_API_KEY')
if not api_key:
    raise ValueError("AIML_API_KEY not found in environment")

# Initialize OpenAI client with AIML API
api = OpenAI(
    api_key=api_key,
    base_url="https://api.aimlapi.com/v1"
)