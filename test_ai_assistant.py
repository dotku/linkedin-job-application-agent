#!/usr/bin/env python3

import json
from ai_assistant import AIJobAssistant

def main():
    # Initialize AI assistant
    assistant = AIJobAssistant()
    
    # Sample job posting HTML
    job_html = """
    <div class="jobs-description">
        <h2>Senior Software Engineer</h2>
        <h3>Tech Company Inc. - San Francisco, CA</h3>
        
        <p>We are seeking a talented Senior Software Engineer to join our growing team. 
        You will be responsible for designing and implementing scalable backend services, 
        leading technical initiatives, and mentoring junior developers.</p>
        
        <h3>Requirements:</h3>
        <ul>
            <li>5+ years of experience in software development</li>
            <li>Strong expertise in Python and JavaScript</li>
            <li>Experience with cloud technologies (AWS/GCP)</li>
            <li>Background in microservices architecture</li>
            <li>Strong communication and leadership skills</li>
        </ul>
    </div>
    """
    
    # Test job details extraction
    print("\nExtracting job details...")
    description, requirements = assistant.extract_job_details(job_html)
    print(f"\nDescription:\n{description}")
    print(f"\nRequirements:\n{requirements}")
    
    # Test job analysis
    print("\nAnalyzing job fit...")
    should_apply, reason = assistant.analyze_job(
        "Senior Software Engineer",
        "Tech Company Inc.",
        description,
        requirements
    )
    print(f"\nShould Apply: {should_apply}")
    print(f"Reason: {reason}")
    
    # Test cover letter generation
    print("\nGenerating cover letter...")
    job_data = {
        "title": "Senior Software Engineer",
        "company": "Tech Company Inc.",
        "description": description,
        "requirements": requirements
    }
    cover_letter = assistant.generate_cover_letter(job_data)
    print(f"\nCover Letter:\n{cover_letter}")
    
    # Test form answer suggestions
    print("\nSuggesting form answers...")
    questions = {
        "years_of_experience": "How many years of experience do you have in software development?",
        "preferred_stack": "What is your preferred technology stack?",
        "leadership": "Describe your experience in leading technical teams.",
        "availability": "When can you start?"
    }
    answers = assistant.suggest_form_answers(questions)
    print("\nForm Answers:")
    print(json.dumps(answers, indent=2))

if __name__ == "__main__":
    main()
