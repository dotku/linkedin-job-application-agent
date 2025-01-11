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

system_prompt = "You are a travel agent. Be descriptive and helpful."
user_prompt = "Tell me about San Francisco"


def main():
    completion = api.chat.completions.create(
        model="mistralai/Mistral-7B-Instruct-v0.2",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=256,
    )

    response = completion.choices[0].message.content

    print("User:", user_prompt)
    print("AI:", response)


if __name__ == "__main__":
    main()