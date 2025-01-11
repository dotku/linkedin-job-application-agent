import os
import time
import logging
import sqlite3
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    StaleElementReferenceException
)
import json
import re
import requests
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from linkedin_login import LinkedInLogin
from linkedin_jobs import LinkedInJobs
from linkedin_apply import LinkedInApply
import datetime
import base64
import io
from PIL import Image
import cv2
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LinkedInAutoApply:
    def __init__(self):
        """Initialize the LinkedIn Auto Apply bot"""
        self.driver = None
        try:
            load_dotenv('.env.local')
            self.email = os.getenv('LINKEDIN_EMAIL')
            self.password = os.getenv('LINKEDIN_PASSWORD')
            self.job_search_keywords = os.getenv('JOB_SEARCH_KEYWORDS', 'Full Stack')
            self.job_search_location = os.getenv('JOB_SEARCH_LOCATION', 'San Francisco Bay Area')
            self.max_jobs = int(os.getenv('MAX_JOBS', '25'))
            
            if not self.email or not self.password:
                raise ValueError("LinkedIn credentials not found in .env.local file")
            
            self.setup_driver()
            self.login_handler = LinkedInLogin(self.driver, self.email, self.password)
            self.jobs_handler = LinkedInJobs(self.driver)
            self.apply_handler = LinkedInApply(self.driver)
            
        except Exception as e:
            logger.error(f"Initialization failed: {str(e)}")
            raise

    def setup_database(self):
        """Setup SQLite database for storing form fields"""
        try:
            db_file = 'linkedin_applications.db'
            # Log database location
            db_path = os.path.abspath(db_file)
            logger.info(f"Setting up database at: {db_path}")
            
            # Create database connection
            self.conn = sqlite3.connect(db_file)
            self.cursor = self.conn.cursor()
            
            # Create tables if they don't exist
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    company_name TEXT,
                    company_url TEXT,
                    job_title TEXT,
                    job_description TEXT,
                    job_location TEXT,
                    salary_range TEXT,
                    experience_level TEXT,
                    employment_type TEXT,
                    application_date TIMESTAMP,
                    last_updated TIMESTAMP,
                    status TEXT CHECK(status IN ('PENDING', 'SKIPPED', 'APPLIED', 'FAILED', 'ERROR')),
                    failure_reason TEXT,
                    job_url TEXT,
                    num_applicants INTEGER,
                    is_remote BOOLEAN,
                    easy_apply BOOLEAN
                )
            ''')
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS form_fields (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT,
                    field_type TEXT CHECK(field_type IN ('text', 'select', 'radio', 'checkbox', 'textarea', 'file', 'other')),
                    field_name TEXT,
                    field_label TEXT,
                    field_value TEXT,
                    field_options TEXT,
                    is_required BOOLEAN,
                    is_filled BOOLEAN,
                    error_message TEXT,
                    FOREIGN KEY (job_id) REFERENCES jobs (job_id)
                )
            ''')
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS application_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT,
                    attempt_date TIMESTAMP,
                    status TEXT CHECK(status IN ('SUCCESS', 'FAILED', 'ERROR')),
                    error_message TEXT,
                    step_reached TEXT,
                    form_data TEXT,
                    FOREIGN KEY (job_id) REFERENCES jobs (job_id)
                )
            ''')
            
            # Create indexes for better performance
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_application_date ON jobs(application_date)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_form_fields_job_id ON form_fields(job_id)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_application_attempts_job_id ON application_attempts(job_id)')
            
            self.conn.commit()
            logger.info("Database setup completed successfully")
            self.db_enabled = True
            
        except Exception as e:
            logger.error(f"Database setup error: {str(e)}")
            logger.warning("Continuing without database functionality")
            self.db_enabled = False

    def get_database_stats(self):
        """Get statistics about the database"""
        try:
            self.cursor.execute('SELECT COUNT(*), COUNT(DISTINCT job_id) FROM jobs')
            total_jobs, unique_jobs = self.cursor.fetchone()
            
            self.cursor.execute('SELECT COUNT(*) FROM form_fields')
            total_fields = self.cursor.fetchone()[0]
            
            self.cursor.execute('SELECT COUNT(*) FROM jobs WHERE status = "APPLIED"')
            applied_jobs = self.cursor.fetchone()[0]
            
            logger.info(f"""
Database Statistics:
- Total Jobs: {total_jobs}
- Unique Jobs: {unique_jobs}
- Total Form Fields: {total_fields}
- Successfully Applied: {applied_jobs}
            """)
            
        except Exception as e:
            logger.error(f"Error getting database stats: {str(e)}")

    def setup_driver(self):
        """Setup Chrome WebDriver"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            service = Service('/usr/local/bin/chromedriver')
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Chrome WebDriver setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup Chrome WebDriver: {str(e)}")
            raise

    def load_applied_jobs(self):
        """Load already applied jobs from database"""
        try:
            # Initialize the set
            self.applied_jobs = set()
            
            # Get all job IDs with status 'APPLIED'
            self.cursor.execute('SELECT job_id FROM jobs WHERE status = "APPLIED"')
            applied_jobs = self.cursor.fetchall()
            
            # Add to set
            for (job_id,) in applied_jobs:
                self.applied_jobs.add(job_id)
            
            logger.info(f"Loaded {len(self.applied_jobs)} previously applied jobs")
            
        except Exception as e:
            logger.error(f"Error loading applied jobs: {str(e)}")
            self.applied_jobs = set()  # Reset to empty set on error

    def is_already_applied(self, job_url):
        """Check if we've already applied to this job"""
        if not hasattr(self, 'db_enabled') or not self.db_enabled:
            logger.warning("Database is disabled, assuming not applied")
            return False
            
        try:
            # Extract job ID from URL
            job_id = job_url.split('jobs/view/')[-1].split('?')[0]
            
            # First check memory cache
            if job_id in self.applied_jobs:
                logger.info(f"Already applied to job {job_id} (found in memory)")
                return True
            
            # Then check database
            self.cursor.execute('SELECT status FROM jobs WHERE job_id = ?', (job_id,))
            result = self.cursor.fetchone()
            
            if result and result[0] == "APPLIED":
                # Add to memory cache
                self.applied_jobs.add(job_id)
                logger.info(f"Already applied to job {job_id} (found in database)")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error checking if already applied: {str(e)}")
            logger.warning("Continuing assuming not applied")
            return False

    def apply_to_jobs(self, max_applications=None):
        """Apply to jobs"""
        applications_submitted = 0
        try:
            # Wait for job cards to be present
            job_cards = self.wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "div.job-card-container")))
            
            logger.info(f"Found {len(job_cards)} job cards")
            
            for job_card in job_cards:
                try:
                    # Check for security verification before each action
                    if self.handle_security_check():
                        continue  # Retry this job card after security check
                    
                    # Click the job card to view details
                    self.driver.execute_script("arguments[0].click();", job_card)
                    time.sleep(2)
                    
                    # Check for security verification after clicking
                    if self.handle_security_check():
                        continue
                    
                    # Get job details
                    job_url = self.driver.current_url
                    job_id = job_url.split('jobs/view/')[-1].split('?')[0]
                    
                    try:
                        company_name = self.driver.find_element(By.CSS_SELECTOR, "[data-test-employer-name]").text
                        job_title = self.driver.find_element(By.CSS_SELECTOR, "[data-test-job-title]").text
                    except:
                        logger.error("Could not find job details")
                        continue
                    
                    # Check if already applied
                    if self.is_already_applied(job_url):
                        continue
                    
                    # Look for any apply button first
                    try:
                        apply_button = self.wait.until(EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "button[data-control-name*='apply']")))
                        
                        # Check if it's an Easy Apply button
                        if "easy-apply" not in apply_button.get_attribute("class").lower():
                            logger.info("Found regular apply button, not Easy Apply")
                            self.save_job_details(
                                job_id,
                                company_name,
                                job_title,
                                job_url,
                                status="SKIPPED",
                                failure_reason="Not an Easy Apply job"
                            )
                            continue
                        
                        logger.info("Found Easy Apply button")
                        
                        # Click the Easy Apply button
                        self.driver.execute_script("arguments[0].click();", apply_button)
                        
                        # Handle the application process
                        if self.handle_easy_apply_process():
                            applications_submitted += 1
                            self.save_job_details(
                                job_id,
                                company_name,
                                job_title,
                                job_url,
                                status="APPLIED"
                            )
                            logger.info(f"Successfully applied to job {applications_submitted}")
                            
                            if max_applications and applications_submitted >= max_applications:
                                logger.info(f"Reached maximum applications limit ({max_applications})")
                                break
                        else:
                            # Log failed application
                            self.save_job_details(
                                job_id, 
                                company_name, 
                                job_title, 
                                job_url, 
                                status="FAILED",
                                failure_reason="Failed during application process"
                            )
                        
                    except TimeoutException:
                        logger.info("No apply button found")
                        self.save_job_details(
                            job_id,
                            company_name,
                            job_title,
                            job_url,
                            status="SKIPPED",
                            failure_reason="No apply button found"
                        )
                        continue
                    
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Error processing job card: {error_msg}")
                    # Try to save failed job if we have the ID
                    if 'job_id' in locals():
                        self.save_job_details(
                            job_id,
                            company_name if 'company_name' in locals() else "Unknown",
                            job_title if 'job_title' in locals() else "Unknown",
                            job_url if 'job_url' in locals() else "Unknown",
                            status="ERROR",
                            failure_reason=error_msg
                        )
                    continue
                
            return applications_submitted
            
        except Exception as e:
            logger.error(f"Error in apply_to_jobs: {str(e)}")
            return applications_submitted

    def save_job_details(self, job_id, company_name, job_title, job_url, status="PENDING", failure_reason=None):
        """Save job application details to database"""
        if not hasattr(self, 'db_enabled') or not self.db_enabled:
            logger.warning("Database is disabled, skipping save operation")
            return
            
        try:
            # Get additional job details if available
            try:
                job_description = self.driver.find_element(By.CSS_SELECTOR, ".job-description").text
            except:
                job_description = None
                
            try:
                company_url = self.driver.find_element(By.CSS_SELECTOR, "a[data-tracking-control-name='public_jobs_company-name']").get_attribute("href")
            except:
                company_url = None
                
            try:
                job_location = self.driver.find_element(By.CSS_SELECTOR, ".job-details-jobs-unified-top-card__bullet").text
            except:
                job_location = None
                
            try:
                salary_range = self.driver.find_element(By.CSS_SELECTOR, ".compensation__salary").text
            except:
                salary_range = None
                
            try:
                num_applicants = self.driver.find_element(By.CSS_SELECTOR, ".num-applicants__caption").text
                num_applicants = int(''.join(filter(str.isdigit, num_applicants)))
            except:
                num_applicants = None
                
            try:
                is_remote = "remote" in job_title.lower() or "remote" in job_location.lower() if job_location else False
            except:
                is_remote = False
                
            # Insert or update job details
            self.cursor.execute('''
                INSERT OR REPLACE INTO jobs (
                    job_id, company_name, company_url, job_title, job_description,
                    job_location, salary_range, application_date, last_updated,
                    status, failure_reason, job_url, num_applicants, is_remote, easy_apply
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                job_id, company_name, company_url, job_title, job_description,
                job_location, salary_range, datetime.now(), datetime.now(),
                status, failure_reason, job_url, num_applicants, is_remote, True
            ))
            
            self.conn.commit()
            logger.info(f"Saved job details for {job_title} at {company_name} - Status: {status}")
            if failure_reason:
                logger.warning(f"Failed to apply: {failure_reason}")
                
        except Exception as e:
            logger.error(f"Error saving job details: {str(e)}")
            logger.warning("Continuing without saving to database")

    def log_application_attempt(self, job_id, status, error_message=None, step_reached=None, form_data=None):
        """Log an application attempt"""
        if not hasattr(self, 'db_enabled') or not self.db_enabled:
            logger.warning("Database is disabled, skipping log operation")
            return
            
        try:
            self.cursor.execute('''
                INSERT INTO application_attempts (
                    job_id, attempt_date, status, error_message, step_reached, form_data
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                job_id, datetime.now(), status, error_message, step_reached,
                json.dumps(form_data) if form_data else None
            ))
            self.conn.commit()
            logger.info(f"Logged application attempt for job {job_id} - Status: {status}")
        except Exception as e:
            logger.error(f"Error logging application attempt: {str(e)}")
            logger.warning("Continuing without logging to database")

    def save_form_field(self, job_id, field_type, field_label, field_options=None, is_required=False):
        """Save form field to database"""
        if not hasattr(self, 'db_enabled') or not self.db_enabled:
            logger.warning("Database is disabled, skipping form field save")
            return
            
        try:
            self.cursor.execute('''
                INSERT INTO form_fields (job_id, field_type, field_label, field_options, is_required)
                VALUES (?, ?, ?, ?, ?)
            ''', (job_id, field_type, field_label, str(field_options) if field_options else None, is_required))
            self.conn.commit()
            logger.info(f"Saved form field: {field_label}")
        except Exception as e:
            logger.error(f"Error saving form field: {str(e)}")
            logger.warning("Continuing without saving form field")

    def wait_for_loading_modal(self):
        """Wait for any loading modals to disappear"""
        try:
            # Common loading modal selectors in LinkedIn
            loading_selectors = [
                "div.artdeco-loader", 
                "div.artdeco-modal__loader",
                "div.loading-icon",
                "div.loading-animation",
                "div[role='progressbar']",
                "div.artdeco-spinner",
                ".artdeco-modal__loading"
            ]
            
            # Wait for any loading indicators to disappear
            for selector in loading_selectors:
                try:
                    loading_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if loading_element.is_displayed():
                        logger.info(f"Waiting for loading modal {selector} to resolve")
                        self.wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, selector)))
                except NoSuchElementException:
                    continue
                
            # Additional wait to ensure content is loaded
            time.sleep(1)
            return True
            
        except Exception as e:
            logger.error(f"Error waiting for loading modal: {str(e)}")
            return False

    def handle_easy_apply_process(self):
        """Handle the Easy Apply process after clicking the button"""
        try:
            # Get job details
            job_id = self.driver.current_url.split('jobs/view/')[-1].split('?')[0]
            company_name = self.driver.find_element(By.CSS_SELECTOR, "[data-test-employer-name]").text
            job_title = self.driver.find_element(By.CSS_SELECTOR, "[data-test-job-title]").text
            job_url = self.driver.current_url
            
            # Save initial job details
            self.save_job_details(job_id, company_name, job_title, job_url)
            
            # Wait for the modal to appear and any loading to finish
            self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div[data-test-modal-id='easy-apply-modal']")))
            self.wait_for_loading_modal()
            
            while True:  # Loop through all steps
                # First check if we have a success modal
                if self.check_for_sent_modal():
                    # Update job status to APPLIED
                    self.save_job_details(job_id, company_name, job_title, job_url, "APPLIED")
                    return True
                
                # Wait for any loading to finish
                self.wait_for_loading_modal()
                
                # Collect form fields on current page
                self.collect_form_fields(job_id)
                
                # First try to find Submit Application button
                try:
                    submit_button = self.wait.until(EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "footer button[aria-label='Submit application']")))
                    logger.info("Found Submit Application button")
                    self.driver.execute_script("arguments[0].click();", submit_button)
                    
                    # Wait for loading after submit
                    self.wait_for_loading_modal()
                    
                    # Check for success modal
                    if self.check_for_sent_modal():
                        # Update job status to APPLIED
                        self.save_job_details(job_id, company_name, job_title, job_url, "APPLIED")
                        return True
                    
                except TimeoutException:
                    # If no Submit button, look for Next button
                    try:
                        next_button = self.wait.until(EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, "footer button[aria-label='Continue to next step']")))
                        logger.info("Found Next button, continuing to next step")
                        self.driver.execute_script("arguments[0].click();", next_button)
                        
                        # Wait for loading after clicking next
                        self.wait_for_loading_modal()
                        continue  # Go to next step
                    except TimeoutException:
                        logger.warning("Could not find Submit or Next button")
                        return False
                
        except Exception as e:
            logger.error(f"Error in Easy Apply process: {str(e)}")
            return False

    def check_for_sent_modal(self):
        """Check if the 'Your application was sent' modal appears"""
        try:
            # Wait for any loading to finish first
            self.wait_for_loading_modal()
            
            # Look for the success message text
            success_message = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, "//*[contains(text(), 'Your application was sent to')]")))
            
            if success_message:
                logger.info("Application submitted successfully")
                
                # Look for and click "Not now" or "Done" button if present
                try:
                    done_button = self.wait.until(EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "button[aria-label='Dismiss']")))
                    self.driver.execute_script("arguments[0].click();", done_button)
                    logger.info("Clicked dismiss button")
                    
                    # Wait for any loading after dismissing
                    self.wait_for_loading_modal()
                except:
                    logger.info("No dismiss button found")
                
                return True
                
        except TimeoutException:
            logger.info("No success message found")
            return False
        except Exception as e:
            logger.error(f"Error checking for success modal: {str(e)}")
            return False

    def collect_form_fields(self, job_id):
        """Collect all form fields on current page"""
        try:
            # Look for input fields
            input_fields = self.driver.find_elements(By.CSS_SELECTOR, "input:not([type='hidden'])")
            for field in input_fields:
                field_type = field.get_attribute("type")
                field_label = self.get_field_label(field)
                is_required = field.get_attribute("required") == "true"
                self.save_form_field(job_id, field_type, field_label, is_required=is_required)
            
            # Look for select fields
            select_fields = self.driver.find_elements(By.TAG_NAME, "select")
            for field in select_fields:
                options = [opt.text for opt in field.find_elements(By.TAG_NAME, "option")]
                field_label = self.get_field_label(field)
                is_required = field.get_attribute("required") == "true"
                self.save_form_field(job_id, "select", field_label, options, is_required)
            
            # Look for textareas
            textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
            for field in textareas:
                field_label = self.get_field_label(field)
                is_required = field.get_attribute("required") == "true"
                self.save_form_field(job_id, "textarea", field_label, is_required=is_required)
            
            # Look for radio button groups
            radio_groups = self.driver.find_elements(By.CSS_SELECTOR, "fieldset")
            for group in radio_groups:
                try:
                    legend = group.find_element(By.TAG_NAME, "legend").text
                    options = [opt.get_attribute("value") for opt in group.find_elements(By.CSS_SELECTOR, "input[type='radio']")]
                    self.save_form_field(job_id, "radio", legend, options)
                except:
                    continue
            
        except Exception as e:
            logger.error(f"Error collecting form fields: {str(e)}")

    def get_field_label(self, field):
        """Get label text for a form field"""
        try:
            # Try to find label by for attribute
            field_id = field.get_attribute("id")
            if field_id:
                label = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{field_id}']")
                return label.text
            
            # Try to find label as parent or ancestor
            parent = field.find_element(By.XPATH, "./ancestor::label")
            return parent.text
        except:
            # If no label found, try to get aria-label or name
            return field.get_attribute("aria-label") or field.get_attribute("name") or "Unknown Field"

    def solve_orientation_captcha(self):
        """Attempt to solve orientation-based image CAPTCHAs"""
        try:
            # Get all images in the current iframe context
            image_elements = self.driver.find_elements(By.TAG_NAME, "img")
            
            # Get the instruction text
            instruction_elements = self.driver.find_elements(By.XPATH, 
                "//div[contains(text(), 'Pick the image') or contains(text(), 'Select the image')]")
            
            if instruction_elements:
                instruction = instruction_elements[0].text.lower()
                logger.info(f"CAPTCHA instruction: {instruction}")
            else:
                logger.warning("Could not find instruction text")
                return False
            
            # Process each image
            for idx, img_element in enumerate(image_elements):
                try:
                    # Skip if not displayed
                    if not img_element.is_displayed():
                        continue
                        
                    # Get image source
                    img_src = img_element.get_attribute('src')
                    if not img_src or not img_src.startswith('data:image'):
                        continue
                        
                    # Convert base64 to image
                    img_data = base64.b64decode(img_src.split(',')[1])
                    img = Image.open(io.BytesIO(img_data))
                    
                    # Convert to OpenCV format
                    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                    
                    # Detect orientation using image processing
                    orientation = self.detect_orientation(cv_img)
                    logger.info(f"Image {idx} orientation: {orientation}")
                    
                    # Check if this image matches the instruction
                    if "up" in instruction and orientation == "up":
                        img_element.click()
                        logger.info(f"Clicked image {idx} that appears to be oriented upright")
                        time.sleep(1)
                        
                except Exception as e:
                    logger.error(f"Error processing image {idx}: {str(e)}")
                    continue
            
            # After processing all images, click verify
            verify_button = self.driver.find_element(By.XPATH, "//button[text()='Verify']")
            verify_button.click()
            time.sleep(2)
            
            # Check if verification succeeded
            self.driver.switch_to.default_content()
            if self.wait_for_verification_completion():
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error solving orientation CAPTCHA: {str(e)}")
            return False

    def detect_orientation(self, img):
        """Detect image orientation using OpenCV"""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Edge detection
            edges = cv2.Canny(gray, 50, 150)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return "unknown"
                
            # Get the largest contour
            largest_contour = max(contours, key=cv2.contourArea)
            
            # Get bounding box
            rect = cv2.minAreaRect(largest_contour)
            box = cv2.boxPoints(rect)
            box = np.int0(box)
            
            # Calculate center of mass
            M = cv2.moments(largest_contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
            else:
                return "unknown"
                
            # Analyze the distribution of pixels relative to center
            height, width = img.shape[:2]
            if cy < height/2:
                return "up"
            else:
                return "down"
                
        except Exception as e:
            logger.error(f"Error detecting orientation: {str(e)}")
            return "unknown"

    def check_for_security_verification(self):
        """Check and handle LinkedIn security verification"""
        try:
            # Wait for any iframe to be present
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
            
            # Find all iframes
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            logger.info(f"Found {len(iframes)} iframes")
            
            for iframe in iframes:
                try:
                    # Switch to iframe
                    self.driver.switch_to.frame(iframe)
                    logger.info("Switched to iframe")
                    
                    # First look for verification text to confirm we're in the right iframe
                    verification_texts = [
                        "//h1[contains(text(), 'Verification')]",
                        "//div[contains(text(), 'Please solve this puzzle')]",
                        "//div[contains(text(), 'security check')]"
                    ]
                    
                    if not any(len(self.driver.find_elements(By.XPATH, text)) > 0 for text in verification_texts):
                        logger.debug("Not a verification iframe, skipping")
                        continue
                        
                    logger.info("Found verification iframe")
                    
                    # Look for the verify button
                    verify_selectors = [
                        "//button[text()='Verify']",
                        "//button[contains(text(), 'Verify')]",
                        "//button[@type='submit']"
                    ]
                    
                    verify_button = None
                    for selector in verify_selectors:
                        try:
                            elements = self.driver.find_elements(By.XPATH, selector)
                            for element in elements:
                                if element.is_displayed() and element.text.strip().lower() == "verify":
                                    verify_button = element
                                    break
                            if verify_button:
                                break
                        except:
                            continue
                    
                    if verify_button:
                        logger.info("Found verify button")
                        
                        # Check for puzzle elements before clicking
                        puzzle_images = self.driver.find_elements(By.TAG_NAME, "img")
                        if len(puzzle_images) > 1:  # More than one image indicates a puzzle
                            logger.info("Found puzzle images, attempting to solve")
                            # Process puzzle images with OpenCV
                            if self.solve_orientation_captcha():
                                logger.info("Puzzle solved successfully")
                                return False
                        else:
                            # Simple verification, just click the button
                            logger.info("Simple verification, clicking verify button")
                            verify_button.click()
                            time.sleep(2)
                            
                            # Check if verification succeeded
                            self.driver.switch_to.default_content()
                            if self.wait_for_verification_completion():
                                return False
                            
                            # If not succeeded, switch back to iframe
                            self.driver.switch_to.frame(iframe)
                    
                    # If we get here, either no verify button found or verification failed
                    logger.info("Automated verification failed, waiting for manual completion")
                    self.wait_for_verification_completion()
                    return True
                    
                except Exception as e:
                    logger.error(f"Error processing iframe: {str(e)}")
                    continue
                    
                finally:
                    try:
                        self.driver.switch_to.default_content()
                    except:
                        pass
            
            return False
            
        except Exception as e:
            logger.error(f"Error in security verification: {str(e)}")
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False

    def wait_for_verification_completion(self, timeout=300):  # 5 minutes timeout
        """Wait until the security verification is completed"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check if we're back on a normal LinkedIn page
                normal_page_indicators = [
                    "//div[contains(@class, 'jobs-search-box')]",
                    "[data-control-name='feed_nav_home']",
                    ".feed-identity-module",
                    ".search-global-typeahead__input"
                ]
                
                for indicator in normal_page_indicators:
                    if len(self.driver.find_elements(By.XPATH, indicator)) > 0:
                        logger.info("Verification completed - back on normal LinkedIn page")
                        time.sleep(2)  # Give a moment for page to fully load
                        return True
                
                # Check if we're still on verification page
                verification_indicators = [
                    "//iframe",
                    "//div[contains(text(), 'verification')]",
                    "//div[contains(text(), 'security check')]",
                    "//button[contains(text(), 'Verify')]"
                ]
                
                if not any(len(self.driver.find_elements(By.XPATH, ind)) > 0 for ind in verification_indicators):
                    logger.info("No verification elements found - assuming completed")
                    time.sleep(2)
                    return True
                
                logger.info("Still waiting for verification to complete...")
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"Error while waiting for verification: {str(e)}")
                time.sleep(5)
        
        logger.warning("Verification wait timeout reached")
        return False

    def handle_security_check(self):
        """Handle security check if encountered"""
        try:
            if self.check_for_security_verification():
                # After verification, wait a bit and refresh the page
                time.sleep(5)
                self.driver.refresh()
                time.sleep(3)
                return True
            return False
        except Exception as e:
            logger.error(f"Error handling security check: {str(e)}")
            return False

    def handle_security_verification(self):
        """Wait for manual security verification"""
        print("="*50)
        print("Security verification required!")
        print("Please complete the verification manually in the browser.")
        print("Press Enter once you have completed the verification.")
        print("="*50 + "\n")
        
        try:
            # Wait for user input
            input("Press Enter to continue after completing verification...")
            time.sleep(3)  # Give extra time for the page to load after verification
            return True
        except (EOFError, KeyboardInterrupt) as e:
            logger.error(f"Manual verification interrupted: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error during manual verification: {str(e)}")
            return False

    def close(self):
        """Close the browser"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.error(f"Error closing browser: {str(e)}")

    def check_if_logged_in(self):
        """Check if we are already logged in"""
        try:
            # Check for successful login indicators
            success_indicators = [
                ".global-nav",
                "[data-control-name='feed_nav_home']",
                ".feed-identity-module",
                ".search-global-typeahead__input"
            ]
            
            for selector in success_indicators:
                if self.wait_for_element(By.CSS_SELECTOR, selector, timeout=5):
                    logger.info("Already logged in")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking login status: {str(e)}")
            return False

    def run(self, keywords, location, max_jobs=25):
        """Run the job application process"""
        try:
            # Step 1: Login with username/password
            logger.info("Step 1: Logging in with username/password...")
            if not self.login_handler.login():
                logger.error("Failed to login")
                return
            
            logger.info("Successfully logged in")
            time.sleep(3)  # Wait after login
            
            while True:  # Main application loop
                try:
                    # Step 2: Search and apply for Easy Apply jobs
                    logger.info(f"Step 2: Searching for {keywords} jobs in {location}...")
                    search_result = self.jobs_handler.search_jobs(keywords, location)
                    if not search_result:
                        logger.warning("Job search verification failed. Current URL: " + self.driver.current_url)
                        logger.warning("Attempting to continue anyway...")
                        time.sleep(5)  # Extra wait time if search verification fails
                    
                    # Get job listings
                    logger.info("Getting job listings...")
                    jobs = self.jobs_handler.get_job_listings(max_jobs)
                    if not jobs:
                        logger.warning("No jobs found. Current page state:")
                        logger.warning("URL: " + self.driver.current_url)
                        try:
                            # Try to find any job-related elements for debugging
                            job_elements = self.driver.find_elements(By.CSS_SELECTOR, "div[class*='job']")
                            logger.info(f"Found {len(job_elements)} elements with 'job' in class name")
                        except Exception as e:
                            logger.error(f"Error checking for job elements: {str(e)}")
                        return
                        
                    logger.info(f"Found {len(jobs)} jobs to apply to")
                    time.sleep(3)  # Wait after getting listings
                    
                    # Apply to each job
                    for job in jobs:
                        try:
                            logger.info(f"Attempting to apply to: {job['title']} at {job['company']}")
                            # Click on job
                            self.jobs_handler.scroll_to_job(job['element'])
                            if not self.jobs_handler.click_job(job['element']):
                                # If job click failed (possibly due to page not found)
                                logger.warning("Failed to click job, skipping to next...")
                                continue
                            
                            time.sleep(3)  # Wait after job click
                            
                            # Try to apply
                            if self.apply_handler.apply_to_job(job):
                                logger.info(f"Successfully applied to {job['title']} at {job['company']}")
                            else:
                                logger.warning(f"Failed to apply to {job['title']} at {job['company']}")
                                
                            time.sleep(3)  # Wait between applications
                                
                        except Exception as e:
                            logger.error(f"Error applying to job: {str(e)}")
                            continue
                            
                    # If we've processed all jobs without errors, break the main loop
                    break
                    
                except Exception as e:
                    logger.error(f"Error in job search/apply process: {str(e)}")
                    # Try to go back to jobs page
                    try:
                        self.driver.get("https://www.linkedin.com/jobs/")
                        time.sleep(3)  # Wait after navigation
                    except:
                        pass
                    continue  # Retry the whole process
            
        except Exception as e:
            logger.error(f"Error in run process: {str(e)}")
        finally:
            logger.info("Job application process completed")

def main():
    try:
        bot = LinkedInAutoApply()
        bot.run(bot.job_search_keywords, bot.job_search_location, bot.max_jobs)
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
    finally:
        logger.info("Process finished")

if __name__ == "__main__":
    main()
