import os
import json
import logging
import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class AIJobAssistant:
    def __init__(self):
        """Initialize the AI assistant"""
        load_dotenv('.env.local')
        self.api_key = os.getenv('AIM_API_KEY')
        self.api_url = "https://aimlapi.com/api/chat"
        self.resume = self._load_resume()
        
    def _load_resume(self):
        """Load resume data from JSON file"""
        try:
            with open('data/resume_info.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading resume: {str(e)}")
            return {}
        
    def _make_api_request(self, prompt):
        """Make a request to AIML API"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'messages': [
                    {'role': 'system', 'content': 'You are a helpful job application assistant. Be concise and direct.'},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.7,
                'max_tokens': 500
            }
            
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            
            return response.json()['choices'][0]['message']['content']
            
        except Exception as e:
            logger.error(f"API request failed: {str(e)}")
            return None
            
    def get_form_field_value(self, field_label, field_type, options=None):
        """Get appropriate value for a form field based on resume"""
        field_label = field_label.lower()
        
        # Direct mappings from resume to common field labels
        direct_mappings = {
            'name': self.resume.get('personal_info', {}).get('name'),
            'email': self.resume.get('personal_info', {}).get('email'),
            'phone': self.resume.get('personal_info', {}).get('phone'),
            'linkedin': self.resume.get('personal_info', {}).get('linkedin'),
            'github': self.resume.get('personal_info', {}).get('github'),
            'portfolio': self.resume.get('personal_info', {}).get('portfolio'),
            'location': self.resume.get('personal_info', {}).get('location'),
            'work authorization': self.resume.get('personal_info', {}).get('work_authorization'),
            'years of experience': str(self.resume.get('preferences', {}).get('years_of_experience')),
            'current title': self.resume.get('preferences', {}).get('current_title')
        }
        
        # Check for direct mapping first
        for key, value in direct_mappings.items():
            if key in field_label and value:
                return value
        
        # Use AI for more complex fields
        try:
            prompt = f"""
            Based on this resume information:
            {json.dumps(self.resume, indent=2)}
            
            What should I fill in for this form field?
            Field Label: {field_label}
            Field Type: {field_type}
            Options (if any): {options}
            
            Return ONLY the value to fill in, nothing else.
            For multiple choice questions, return EXACTLY one of the provided options.
            For yes/no questions, return only 'yes' or 'no'.
            For numeric fields, return only numbers.
            If you can't determine a value, return 'SKIP'.
            """
            
            result = self._make_api_request(prompt)
            if not result:
                return None
                
            return result.strip()
            
        except Exception as e:
            logger.error(f"Error getting field value: {str(e)}")
            return None
            
    def handle_screening_question(self, question_text, options=None):
        """Handle a screening question based on resume"""
        try:
            prompt = f"""
            Based on this resume information:
            {json.dumps(self.resume, indent=2)}
            
            Please answer this screening question:
            Question: {question_text}
            Options (if any): {options}
            
            Return ONLY your answer, nothing else.
            For multiple choice, return EXACTLY one of the provided options.
            For yes/no questions, return only 'yes' or 'no'.
            For open-ended questions, be brief but professional.
            If you can't determine an answer, return 'SKIP'.
            """
            
            result = self._make_api_request(prompt)
            if not result:
                return None
                
            return result.strip()
            
        except Exception as e:
            logger.error(f"Error handling screening question: {str(e)}")
            return None
            
    def suggest_cover_letter(self, job_title, company, job_description):
        """Generate a cover letter based on resume and job details"""
        try:
            prompt = f"""
            Based on this resume information:
            {json.dumps(self.resume, indent=2)}
            
            Please write a brief cover letter for this job:
            Title: {job_title}
            Company: {company}
            Description: {job_description}
            
            Keep it professional but personalized.
            Focus on relevant experience and skills.
            Keep it under 200 words.
            """
            
            result = self._make_api_request(prompt)
            if not result:
                return None
                
            return result.strip()
            
        except Exception as e:
            logger.error(f"Error generating cover letter: {str(e)}")
            return None
            
    def analyze_job(self, job_title, company, job_description, requirements):
        """Analyze job posting and determine if it's a good fit"""
        if not self.api_key:
            logger.warning("AIML API key not found, skipping AI analysis")
            return True, "AI analysis skipped"
            
        try:
            prompt = f"""
            Based on this resume information:
            {json.dumps(self.resume, indent=2)}
            
            Please analyze this job posting and determine if it's a good fit:
            
            Job Title: {job_title}
            Company: {company}
            
            Job Description:
            {job_description}
            
            Requirements:
            {requirements}
            
            Please provide:
            1. Should I apply? (Yes/No)
            2. Brief reason why
            3. Key skills that match
            4. Any potential concerns
            
            Format your response as: apply|reason|matching_skills|concerns
            """
            
            result = self._make_api_request(prompt)
            if not result:
                return True, "AI analysis failed, proceeding anyway"
                
            should_apply, reason, skills, concerns = result.split('|')
            should_apply = should_apply.lower().strip() == 'yes'
            
            logger.info(f"AI Analysis for {job_title}:")
            logger.info(f"Should Apply: {should_apply}")
            logger.info(f"Reason: {reason}")
            logger.info(f"Matching Skills: {skills}")
            logger.info(f"Concerns: {concerns}")
            
            return should_apply, reason
            
        except Exception as e:
            logger.error(f"Error in AI analysis: {str(e)}")
            return True, "AI analysis failed, proceeding anyway"
            
    def extract_job_details(self, job_page_source):
        """Extract job details from the page source"""
        if not self.api_key:
            return None, None
            
        try:
            # Ask AI to extract job details
            prompt = f"""
            Please extract the job description and requirements from this HTML:
            {job_page_source[:4000]}  # Limit to first 4000 chars
            
            Format your response as: description|requirements
            Only include the actual text content, ignore HTML tags.
            """
            
            result = self._make_api_request(prompt)
            if not result:
                return None, None
                
            description, requirements = result.split('|')
            return description.strip(), requirements.strip()
            
        except Exception as e:
            logger.error(f"Error extracting job details: {str(e)}")
            return None, None
