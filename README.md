# LinkedIn Auto Apply Bot

This Python script automates the process of applying to "Easy Apply" jobs on LinkedIn for Frontend Engineer positions in the San Francisco Bay Area.

## Features

- Automatically logs into LinkedIn (with 2FA support)
- Searches for Frontend Engineer positions with "Easy Apply" enabled
- Automatically fills common application questions:
  - Sponsorship requirements
  - Citizenship status
  - Race/ethnicity
  - Gender/pronouns
  - Sexual orientation
- Tracks applied jobs to prevent duplicate applications
- Sorts jobs by most recent first
- Handles pagination to process all available jobs

## Setup

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. Create a `.env.local` file in the project directory with your LinkedIn credentials:

```bash
LINKEDIN_EMAIL=your_email@example.com
LINKEDIN_PASSWORD=your_password
```

3. Run the script:

```bash
python linkedin_auto_apply.py
```

## Configuration

The script has several configurable parameters:

- Job search keywords (default: "Frontend Engineer")
- Location (default: "San Francisco Bay Area")
- Maximum applications per run (optional)
- Application preferences (in the `handle_application_questions` method)

## Usage Notes

1. When you first run the script, LinkedIn will request mobile verification
2. The script will wait up to 60 seconds for you to approve the login
3. After successful login, it will:
   - Navigate to the jobs search page
   - Filter for Easy Apply positions
   - Start processing job applications

## Security Notes

- Credentials are stored in `.env.local` (not tracked by git)
- The script supports 2-factor authentication
- Never share your `.env.local` file
- Review LinkedIn's terms of service regarding automation

## Troubleshooting

1. Login Issues:
   - Ensure your credentials in `.env.local` are correct
   - Allow enough time to approve the mobile verification

2. Application Issues:
   - The script logs all actions and errors
   - Check the console output for specific error messages
   - Some jobs may require manual review

## Disclaimer

This bot is for educational purposes only. Use it responsibly and in accordance with LinkedIn's terms of service.
