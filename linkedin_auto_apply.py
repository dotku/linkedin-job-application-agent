import os
import time
import sys
import logging
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException

from utils.logger import setup_logger
from utils.chrome_setup import ChromeSetup
from utils.database import DatabaseManager
from linkedin_login import LinkedInLogin
from linkedin_jobs import LinkedInJobs
from linkedin_apply import LinkedInApply

# Set up logging
logger = setup_logger(__name__, "linkedin_auto_apply")

class LinkedInAutoApply:
    def __init__(self):
        """Initialize the LinkedIn Auto Apply Bot"""
        # Load environment variables
        load_dotenv('.env.local')
        
        self.driver = ChromeSetup.initialize_driver()
        if not self.driver:
            raise Exception("Failed to initialize Chrome driver")
        
        # Get parameters from environment
        self.keywords = os.getenv("JOB_SEARCH_KEYWORDS")
        self.location = os.getenv("JOB_SEARCH_LOCATION")
        self.max_jobs = int(os.getenv("MAX_JOBS", "25"))
        
        if not self.keywords or not self.location:
            raise ValueError("Missing JOB_SEARCH_KEYWORDS or JOB_SEARCH_LOCATION in .env.local")
        
        logger.info(f"Initialized with keywords='{self.keywords}', location='{self.location}', max_jobs={self.max_jobs}")

    def get_database_stats(self):
        """Get statistics about the database"""
        try:
            self.db.get_stats()
            
            logger.info(f"""
Database Statistics:
- Total Jobs: {self.db.total_jobs}
- Unique Jobs: {self.db.unique_jobs}
- Total Form Fields: {self.db.total_fields}
- Successfully Applied: {self.db.applied_jobs}
            """)
            
        except Exception as e:
            logger.error(f"Error getting database stats: {str(e)}")

    def load_applied_jobs(self):
        """Load already applied jobs from database"""
        try:
            # Initialize the set
            self.applied_jobs = set()
            
            # Get all job IDs with status 'APPLIED'
            self.applied_jobs = self.db.get_applied_jobs()
            
            logger.info(f"Loaded {len(self.applied_jobs)} previously applied jobs")
            
        except Exception as e:
            logger.error(f"Error loading applied jobs: {str(e)}")
            self.applied_jobs = set()  # Reset to empty set on error

    def is_already_applied(self, job_url):
        """Check if we've already applied to this job"""
        try:
            # Extract job ID from URL
            job_id = job_url.split('jobs/view/')[-1].split('?')[0]
            
            # First check memory cache
            if job_id in self.applied_jobs:
                logger.info(f"Already applied to job {job_id} (found in memory)")
                return True
            
            # Then check database
            if self.db.is_job_applied(job_id):
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
        try:
            if max_applications is None:
                max_applications = self.max_jobs
            
            logger.info(f"Starting to apply for up to {max_applications} jobs")
            applications_submitted = 0
            
            # Wait for job listings to be visible
            job_listings_selector = ".jobs-search-results__list"
            try:
                job_listings = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, job_listings_selector))
                )
                logger.info("Found job listings container")
            except TimeoutException:
                logger.error("Could not find job listings container")
                return False
            
            # Get all job cards
            job_cards = self.driver.find_elements(By.CSS_SELECTOR, ".job-card-container")
            if not job_cards:
                logger.warning("No job cards found")
                return False
            
            logger.info(f"Found {len(job_cards)} job cards")
            
            for index, job_card in enumerate(job_cards):
                if applications_submitted >= max_applications:
                    logger.info(f"Reached maximum applications limit ({max_applications})")
                    break
                
                try:
                    # Check if already applied
                    if self.check_job_status(job_card):
                        logger.info("Already applied to this job, skipping")
                        continue
                    
                    # Click on job card
                    self.driver.execute_script("arguments[0].click();", job_card)
                    time.sleep(2)  # Wait for job details to load
                    
                    # Get job details
                    job_title = job_card.find_element(By.CSS_SELECTOR, ".job-card-list__title").text
                    company_name = job_card.find_element(By.CSS_SELECTOR, ".job-card-container__company-name").text
                    
                    logger.info(f"Processing job: {job_title} at {company_name}")
                    
                    # Check for Easy Apply button
                    easy_apply_button = self.check_easy_apply_button()
                    if not easy_apply_button:
                        logger.info("No Easy Apply button found, skipping")
                        continue
                    
                    # Click Easy Apply and process application
                    try:
                        self.driver.execute_script("arguments[0].click();", easy_apply_button)
                        time.sleep(2)  # Wait for application modal
                        
                        if self.handle_easy_apply_process():
                            applications_submitted += 1
                            logger.info(f"Successfully applied to job ({applications_submitted}/{max_applications})")
                        else:
                            logger.warning("Failed to complete application, moving to next job")
                        
                    except Exception as e:
                        logger.error(f"Error in application process: {str(e)}")
                        continue
                    
                except Exception as e:
                    logger.error(f"Error processing job card {index}: {str(e)}")
                    continue
                
                time.sleep(2)  # Wait between applications
            
            logger.info(f"Completed job applications. Submitted {applications_submitted} applications")
            return True
            
        except Exception as e:
            logger.error(f"Error in apply_to_jobs: {str(e)}")
            return False

    def save_job_details(self, job_id, company_name, job_title, job_url, status="PENDING", failure_reason=None):
        """Save job application details to database"""
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
            self.db.save_job_details(job_id, company_name, job_title, job_description, job_location, salary_range, job_url, num_applicants, is_remote, status, failure_reason)
            
            logger.info(f"Saved job details for {job_title} at {company_name} - Status: {status}")
            if failure_reason:
                logger.warning(f"Failed to apply: {failure_reason}")
                
        except Exception as e:
            logger.error(f"Error saving job details: {str(e)}")
            logger.warning("Continuing without saving to database")

    def log_application_attempt(self, job_id, status, error_message=None, step_reached=None, form_data=None):
        """Log an application attempt"""
        try:
            self.db.log_application_attempt(job_id, status, error_message, step_reached, form_data)
            logger.info(f"Logged application attempt for job {job_id} - Status: {status}")
        except Exception as e:
            logger.error(f"Error logging application attempt: {str(e)}")
            logger.warning("Continuing without logging to database")

    def save_form_field(self, job_id, field_type, field_label, field_options=None, is_required=False):
        """Save form field to database"""
        try:
            self.db.save_form_field(job_id, field_type, field_label, field_options, is_required)
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

    def check_browser_open(self):
        """Check if browser is still open"""
        try:
            # Try to get current url - will fail if browser is closed
            self.driver.current_url
            return True
        except WebDriverException:
            logger.error("Browser was closed by user")
            self.cleanup()
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error checking browser status: {str(e)}")
            self.cleanup()
            sys.exit(1)
        return False

    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

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

    def run(self):
        """Run the LinkedIn auto apply process"""
        try:
            if not self.driver:
                logger.error("Chrome driver not initialized")
                return False
            
            # Initialize components
            self.login = LinkedInLogin(self.driver)
            self.jobs = LinkedInJobs(self.driver)
            
            # Start from login page
            self.check_browser_open()
            self.driver.get("https://www.linkedin.com/login")
            time.sleep(3)
            
            # Login to LinkedIn
            self.check_browser_open()
            if not self.login.login():
                logger.error("Failed to login")
                return False
                
            # Search for jobs
            self.check_browser_open()
            if not self.jobs.search_jobs():
                logger.error("Failed to search for jobs")
                return False
                
            # Start applying to jobs
            self.check_browser_open()
            self.apply_to_jobs()
            
            return True
            
        except Exception as e:
            logger.error(f"Error in auto apply process: {str(e)}")
            return False
            
        finally:
            self.cleanup()

    def wait_for_element(self, by, selector, timeout=10):
        """Wait for an element to be present"""
        try:
            self.wait.until(EC.presence_of_element_located((by, selector)))
            return True
        except TimeoutException:
            return False

    def check_easy_apply_button(self):
        """Check if Easy Apply button is present and clickable"""
        try:
            # Check for Easy Apply button with various selectors
            button_selectors = [
                "button.jobs-apply-button[aria-label*='Easy Apply']",
                "button[aria-label*='Easy Apply']",
                ".jobs-apply-button",
                "[data-control-name='jobdetails_topcard_inapply']"
            ]
            
            for selector in button_selectors:
                buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for button in buttons:
                    if button.is_displayed() and "Easy Apply" in button.get_attribute("innerHTML"):
                        return button
            
            # If no Easy Apply button found, log the reason
            apply_buttons = self.driver.find_elements(By.CSS_SELECTOR, ".jobs-apply-button")
            if apply_buttons:
                for button in apply_buttons:
                    logger.info(f"Found non-Easy Apply button: {button.get_attribute('innerHTML')}")
            else:
                logger.info("No apply button found on page")
            
            return None
            
        except Exception as e:
            logger.warning(f"Error checking Easy Apply button: {str(e)}")
            return None

    def check_job_status(self, job_card):
        """Check if job has already been applied to"""
        try:
            # Check for "Applied" status in various locations
            status_selectors = [
                ".job-card-container__footer-item",
                ".artdeco-entity-lockup__subtitle",
                ".job-card-list__footer-wrapper",
                ".jobs-applied-badge"
            ]
            
            for selector in status_selectors:
                elements = job_card.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if "Applied" in element.text:
                        logger.info("Found 'Applied' status on job card")
                        return True
            return False
            
        except Exception as e:
            logger.warning(f"Error checking job status: {str(e)}")
            return False

def main():
    try:
        logger.info("Initializing LinkedIn Auto Apply bot...")
        bot = LinkedInAutoApply()
        bot.run()
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
    finally:
        logger.info("Process completed")
    
if __name__ == "__main__":
    try:
        bot = LinkedInAutoApply()
        bot.run()
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)
