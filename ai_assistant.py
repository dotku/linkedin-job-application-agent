import os
import json
import logging
from scripts.aiml import api

logger = logging.getLogger(__name__)

class AIJobAssistant:
    def __init__(self):
        """Initialize the AI assistant"""
        self.resume = self._load_resume()
        
    def _load_resume(self):
        """Load resume data from JSON file"""
        try:
            with open('data/resume_info.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading resume: {str(e)}")
            return {}
        
    def _make_api_request(self, prompt, system_prompt="You are a job application assistant. Be concise."):
        """Make a request to AIML API"""
        try:
            # Truncate prompt if too long
            if len(prompt) > 200:
                prompt = prompt[:197] + "..."
                
            completion = api.chat.completions.create(
                model="mistralai/Mistral-7B-Instruct-v0.2",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"API request failed: {str(e)}")
            return None

    def extract_job_details(self, html_content):
        """Extract job description and requirements from HTML content"""
        try:
            # Extract text content from HTML
            import re
            text = re.sub(r'<[^>]+>', ' ', html_content)
            text = ' '.join(text.split())  # Clean up whitespace
            
            prompt = f"Extract key points from job posting: {text[:150]}"
            response = self._make_api_request(prompt)
            
            if response:
                try:
                    # Split response into description and requirements
                    parts = response.split('\n')
                    desc = parts[0] if len(parts) > 0 else ""
                    reqs = parts[1] if len(parts) > 1 else ""
                    return desc, reqs
                except:
                    pass
            return None, None
            
        except Exception as e:
            logger.error(f"Failed to extract job details: {str(e)}")
            return None, None

    def analyze_job(self, title, company, description, requirements):
        """Analyze if we should apply to this job based on resume match"""
        try:
            # Get key skills from resume
            skills = self.resume.get('skills', {})
            langs = skills.get('programming_languages', [])
            frameworks = skills.get('frameworks', [])
            key_skills = ', '.join(langs[:3] + frameworks[:2])
            
            prompt = f"Job: {title} at {company}. Skills: {key_skills}. Match? (yes/no, reason)"
            response = self._make_api_request(prompt)
            
            if response:
                try:
                    # Parse yes/no from response
                    should_apply = 'yes' in response.lower()
                    reason = response.split(',', 1)[1].strip() if ',' in response else response
                    return should_apply, reason
                except:
                    pass
            return False, "Failed to analyze job"
            
        except Exception as e:
            logger.error(f"Failed to analyze job: {str(e)}")
            return False, str(e)

    def generate_cover_letter(self, job_data):
        """Generate a cover letter for the job"""
        try:
            # Get key experience
            exp = self.resume.get('experience', [])[0] if self.resume.get('experience') else {}
            key_exp = f"{exp.get('title')} at {exp.get('company')}" if exp else ""
            
            prompt = f"Write brief cover letter: {job_data['title']} at {job_data['company']}. My experience: {key_exp}"
            return self._make_api_request(prompt)
            
        except Exception as e:
            logger.error(f"Failed to generate cover letter: {str(e)}")
            return None

    def suggest_form_answers(self, questions):
        """Suggest answers for application form questions"""
        try:
            answers = {}
            for q, text in questions.items():
                prompt = f"Answer job question based on resume. Q: {text[:100]}"
                answer = self._make_api_request(prompt)
                if answer:
                    answers[q] = answer
            return answers
            
        except Exception as e:
            logger.error(f"Failed to suggest form answers: {str(e)}")
            return {}
