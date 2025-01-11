import os
import requests
from dotenv import load_dotenv

def make_api_request(prompt, api_key):
    """Make a request to AIML API"""
    try:
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'messages': [
                {'role': 'system', 'content': 'You are a professional resume writer. Be concise and professional.'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.7,
            'max_tokens': 500
        }
        
        response = requests.post('https://aimlapi.com/api/chat', headers=headers, json=data)
        response.raise_for_status()
        
        return response.json()['choices'][0]['message']['content'].strip()
        
    except Exception as e:
        print(f"API request failed: {str(e)}")
        return None

def generate_resume_content():
    """Generate resume content using AI"""
    load_dotenv('.env.local')
    api_key = os.getenv('AIM_API_KEY')
    
    if not api_key:
        print("Error: AIM_API_KEY not found in .env.local")
        return
    
    # Prepare prompts for each resume section
    sections = {
        'RESUME_NAME': "Generate a professional full name for a software engineer",
        'RESUME_EMAIL': "Generate a professional email address based on the name",
        'RESUME_PHONE': "Generate a US phone number in format: (XXX) XXX-XXXX",
        'RESUME_EXPERIENCE': """Generate a brief work experience summary for a software engineer with the following format:
- Senior Software Engineer at Tech Corp (2020-Present): Full-stack development, team leadership
- Software Engineer at StartupX (2018-2020): Backend development, API design""",
        'RESUME_EDUCATION': """Generate an education summary in this format:
- M.S. Computer Science, Top University (2018)
- B.S. Computer Science, Another University (2016)""",
        'RESUME_SKILLS': "List 10-15 relevant technical skills for a full-stack software engineer, comma-separated",
        'RESUME_SUMMARY': "Write a 2-3 sentence professional summary for a full-stack software engineer",
        'RESUME_WORK_AUTH': "Generate a work authorization status (e.g., 'Authorized to work in the US')",
        'RESUME_LINKEDIN': "Generate a LinkedIn URL",
        'RESUME_GITHUB': "Generate a GitHub URL",
        'RESUME_PORTFOLIO': "Generate a portfolio website URL",
        'RESUME_YEARS_OF_EXPERIENCE': "Generate number of years of experience as a software engineer (just the number)",
        'RESUME_PREFERRED_LOCATION': "Generate preferred work location (e.g., 'San Francisco Bay Area, CA')",
        'RESUME_CURRENT_TITLE': "Generate current job title for a software engineer"
    }
    
    # Generate content for each section
    resume_content = {}
    for key, prompt in sections.items():
        print(f"\nGenerating {key}...")
        content = make_api_request(prompt, api_key)
        if content:
            resume_content[key] = content
            print(f"{key} = {content}")
        else:
            print(f"Failed to generate {key}")
    
    # Format as environment variables
    env_content = "\n# Resume Information - AI Generated\n"
    for key, value in resume_content.items():
        # Escape quotes and format value
        value = value.replace('"', '\\"')
        env_content += f'{key}="{value}"\n'
    
    print("\nGenerated content for .env.local:")
    print(env_content)
    print("\nAdd these lines to your .env.local file")

if __name__ == "__main__":
    generate_resume_content()
