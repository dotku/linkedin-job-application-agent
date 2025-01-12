import sqlite3
import os
from datetime import datetime
from utils.logger import setup_logger

# Set up logging
logger = setup_logger(__name__, "database")

class DatabaseManager:
    def __init__(self, db_path="jobs.db"):
        """Initialize DatabaseManager with database path"""
        self.db_path = db_path
        self.setup_database()
    
    def setup_database(self):
        """Setup SQLite database and create necessary tables"""
        try:
            # Create database directory if it doesn't exist
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)
            
            # Connect to database and create tables
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create jobs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS jobs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id TEXT UNIQUE,
                        title TEXT,
                        company TEXT,
                        location TEXT,
                        date_applied TIMESTAMP,
                        application_status TEXT,
                        job_url TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create job_details table for additional job information
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS job_details (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id TEXT UNIQUE,
                        description TEXT,
                        requirements TEXT,
                        salary_range TEXT,
                        employment_type TEXT,
                        seniority_level TEXT,
                        industry TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (job_id) REFERENCES jobs(job_id)
                    )
                ''')
                
                # Create application_responses table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS application_responses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id TEXT,
                        question TEXT,
                        answer TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (job_id) REFERENCES jobs(job_id)
                    )
                ''')
                
                conn.commit()
                logger.info("Database setup completed successfully")
                
        except Exception as e:
            logger.error(f"Error setting up database: {str(e)}")
            raise
    
    def add_job(self, job_data):
        """Add a job to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO jobs 
                    (job_id, title, company, location, date_applied, application_status, job_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    job_data.get('job_id'),
                    job_data.get('title'),
                    job_data.get('company'),
                    job_data.get('location'),
                    datetime.now(),
                    job_data.get('status', 'applied'),
                    job_data.get('url')
                ))
                conn.commit()
                logger.info(f"Added job: {job_data.get('title')} at {job_data.get('company')}")
                return True
        except Exception as e:
            logger.error(f"Error adding job to database: {str(e)}")
            return False
    
    def job_exists(self, job_id):
        """Check if a job already exists in the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM jobs WHERE job_id = ?', (job_id,))
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            logger.error(f"Error checking job existence: {str(e)}")
            return False
    
    def get_applied_jobs(self):
        """Get all applied jobs from the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM jobs ORDER BY date_applied DESC')
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting applied jobs: {str(e)}")
            return []
