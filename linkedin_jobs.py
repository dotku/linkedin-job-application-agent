import logging
import os
import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from urllib.parse import quote
import time
import os
from dotenv import load_dotenv

from utils.logger import setup_logger
from utils.chrome_setup import ChromeSetup

# Set up logging
logger = setup_logger(__name__, "linkedin_jobs")

class LinkedInJobs:
    def __init__(self, driver=None):
        """Initialize LinkedIn Jobs"""
        self.driver = driver or ChromeSetup.initialize_driver()
        self.wait = WebDriverWait(self.driver, 10)  # Default 10 second wait
        
        # Get search parameters from environment
        load_dotenv('.env.local')
        self.keywords = os.getenv("JOB_SEARCH_KEYWORDS")
        self.location = os.getenv("JOB_SEARCH_LOCATION")
        self.max_jobs = int(os.getenv("MAX_JOBS", "25"))
        
        if not self.keywords or not self.location:
            raise ValueError("Missing JOB_SEARCH_KEYWORDS or JOB_SEARCH_LOCATION in .env.local")
        
        logger.info(f"Initialized with keywords='{self.keywords}', location='{self.location}', max_jobs={self.max_jobs}")

    def log_event(self, level, message, extra_fields=None):
        """Log event with context"""
        if extra_fields is None:
            extra_fields = {}
            
        # Add common fields
        extra_fields.update({
            "url": self.driver.current_url,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.log(level, message, extra=extra_fields)

    def wait_for_search_page(self, timeout=60):
        """Wait for jobs search page to load"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                current_url = self.driver.current_url
                
                # If on jobs search page, we can proceed
                if "linkedin.com/jobs/search" in current_url:
                    logger.info("Jobs search page loaded")
                    return True
                    
                # Still loading, keep waiting
                logger.info("Waiting for jobs search page to load...")
                time.sleep(2)
                
            except Exception as e:
                logger.warning(f"Error checking page status: {str(e)}")
                time.sleep(2)
        
        logger.error("Jobs search page load timeout exceeded")
        return False

    def verify_and_apply_filters(self, keywords, location):
        """Verify and apply search filters"""
        try:
            # Wait for search inputs with multiple possible selectors
            keyword_selectors = [
                "input[aria-label='Search by title, skill, or company']",
                "input.jobs-search-box__text-input[aria-label='Search by title, skill, or company']",
                "input[name='keywords']",
                "#jobs-search-box-keyword-id-ember",
                ".jobs-search-box__keyboard-text-input"
            ]
            
            location_selectors = [
                "input[aria-label='City, state, or zip code']",
                "input.jobs-search-box__text-input[aria-label='City, state, or zip code']",
                "input[name='location']",
                "#jobs-search-box-location-id-ember",
                ".jobs-search-box__location-input"
            ]
            
            # Try each keyword selector
            keyword_input = None
            for selector in keyword_selectors:
                try:
                    keyword_input = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    logger.info(f"Found keyword input with selector: {selector}")
                    break
                except:
                    continue
            
            if not keyword_input:
                logger.error("Could not find keyword input")
                return False
            
            # Try each location selector
            location_input = None
            for selector in location_selectors:
                try:
                    location_input = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    logger.info(f"Found location input with selector: {selector}")
                    break
                except:
                    continue
            
            if not location_input:
                logger.error("Could not find location input")
                return False
            
            # Clear and update keywords if needed
            current_keywords = keyword_input.get_attribute('value')
            if current_keywords != keywords:
                logger.info(f"Updating keywords from '{current_keywords}' to '{keywords}'")
                try:
                    # Try JavaScript clear first
                    self.driver.execute_script("arguments[0].value = ''", keyword_input)
                    time.sleep(1)
                    keyword_input.send_keys(keywords)
                except:
                    # Fall back to regular clear
                    keyword_input.clear()
                    time.sleep(1)
                    keyword_input.send_keys(Keys.CONTROL + "a")  # Select all
                    keyword_input.send_keys(Keys.DELETE)         # Delete selected
                    keyword_input.send_keys(keywords)
                time.sleep(1)
            
            # Clear and update location if needed
            current_location = location_input.get_attribute('value')
            if current_location != location:
                logger.info(f"Updating location from '{current_location}' to '{location}'")
                try:
                    # Try JavaScript clear first
                    self.driver.execute_script("arguments[0].value = ''", location_input)
                    time.sleep(1)
                    location_input.send_keys(location)
                except:
                    # Fall back to regular clear
                    location_input.clear()
                    time.sleep(1)
                    location_input.send_keys(Keys.CONTROL + "a")  # Select all
                    location_input.send_keys(Keys.DELETE)         # Delete selected
                    location_input.send_keys(location)
                time.sleep(1)
            
            # Submit search if changes were made
            if current_keywords != keywords or current_location != location:
                # Try different ways to submit
                try:
                    # Try search button first
                    search_button = self.driver.find_element(By.CSS_SELECTOR, "button[data-tracking-control-name='public_jobs_jobs-search-bar_base-search-bar-search-submit']")
                    search_button.click()
                except:
                    # Fall back to Enter key
                    location_input.send_keys(Keys.RETURN)
                time.sleep(3)
            
            # Verify Easy Apply filter
            if "f_LF=f_AL" not in self.driver.current_url:
                logger.info("Applying Easy Apply filter...")
                try:
                    # Try direct Easy Apply button
                    easy_apply_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Easy Apply filter']"))
                    )
                    easy_apply_button.click()
                    time.sleep(2)
                except:
                    # Try through All Filters
                    try:
                        all_filters = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='All filters']"))
                        )
                        all_filters.click()
                        time.sleep(2)
                        
                        easy_apply_checkbox = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, "//label[contains(., 'Easy Apply')]"))
                        )
                        easy_apply_checkbox.click()
                        
                        show_results = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-test-modal-close-btn]"))
                        )
                        show_results.click()
                        time.sleep(2)
                    except Exception as e:
                        logger.error(f"Could not apply Easy Apply filter: {str(e)}")
                        return False
            
            # Verify final URL has all filters
            final_url = self.driver.current_url
            if not all(x in final_url for x in ["f_LF=f_AL", quote(keywords), quote(location)]):
                logger.error("Failed to verify all filters in URL")
                return False
            
            logger.info("All filters verified and applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying/applying filters: {str(e)}")
            return False

    def search_jobs(self):
        """Search for jobs with configured parameters"""
        max_attempts = 3
        attempt = 0
        
        logger.info(f"Starting job search with keywords='{self.keywords}', location='{self.location}'")
        
        while attempt < max_attempts:
            attempt += 1
            logger.info(f"Search attempt {attempt}/{max_attempts}")
            
            try:
                # Go to jobs search page with Easy Apply filter
                search_url = (
                    "https://www.linkedin.com/jobs/search/?"
                    f"keywords={quote(self.keywords)}&"
                    f"location={quote(self.location)}&"
                    "f_AL=true"  # Easy Apply filter
                )
                logger.info(f"Navigating to search URL: {search_url}")
                self.driver.get(search_url)
                time.sleep(3)
                
                # Wait for search page to load
                if not self.wait_for_search_page():
                    logger.error("Jobs search page did not load")
                    continue
                
                # Wait for job listings to appear
                try:
                    job_list = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "ul.jobs-search-results__list"))
                    )
                    job_count = len(job_list.find_elements(By.CSS_SELECTOR, "li"))
                    logger.info(f"Found {job_count} job listings")
                    
                    # Verify jobs match search criteria
                    first_job = job_list.find_element(By.CSS_SELECTOR, "li")
                    job_title = first_job.find_element(By.CSS_SELECTOR, "h3.job-card-list__title").text.lower()
                    job_company = first_job.find_element(By.CSS_SELECTOR, "h4.job-card-container__company-name").text.lower()
                    job_location = first_job.find_element(By.CSS_SELECTOR, "span.job-card-container__metadata-item").text.lower()
                    
                    keywords_lower = self.keywords.lower()
                    location_lower = self.location.lower()
                    
                    if not (keywords_lower in job_title or keywords_lower in job_company):
                        logger.warning("Jobs don't match search keywords, retrying...")
                        continue
                        
                    if location_lower not in job_location:
                        logger.warning("Jobs don't match search location, retrying...")
                        continue
                    
                    logger.info("Search conditions verified successfully")
                    return True
                    
                except TimeoutException:
                    logger.warning(f"Search results taking longer to load (attempt {attempt}/{max_attempts})")
                    if attempt == max_attempts:
                        logger.warning("Proceeding despite load issues")
                        return True
                    time.sleep(5)
                    continue
                    
            except Exception as e:
                logger.error(f"Error during job search attempt {attempt}: {str(e)}")
                if attempt == max_attempts:
                    return False
                time.sleep(5)
        
        return False

    def apply_to_jobs(self, max_jobs=25):
        """Apply to jobs from search results"""
        try:
            jobs_applied = 0
            retries = 0
            max_retries = 3
            
            while jobs_applied < max_jobs and retries < max_retries:
                try:
                    # Try to find job listings
                    job_list = self.driver.find_elements(By.CSS_SELECTOR, "ul.jobs-search-results__list li")
                    
                    if not job_list:
                        logger.warning(f"No job listings found (attempt {retries + 1}/{max_retries})")
                        retries += 1
                        time.sleep(5)
                        continue
                    
                    logger.info(f"Found {len(job_list)} job listings")
                    
                    # Process found jobs
                    for job in job_list:
                        if jobs_applied >= max_jobs:
                            break
                            
                        try:
                            # Click job to view details
                            job.click()
                            time.sleep(2)
                            
                            # Find and click Easy Apply button
                            easy_apply_buttons = self.driver.find_elements(By.CSS_SELECTOR, 
                                "button[data-control-name='jobdetails_topcard_inapply']"
                            )
                            
                            if not easy_apply_buttons:
                                logger.warning("No Easy Apply button found, skipping job")
                                continue
                                
                            easy_apply_buttons[0].click()
                            time.sleep(2)
                            
                            # Process application
                            if self.process_application():
                                jobs_applied += 1
                                logger.info(f"Successfully applied to job ({jobs_applied}/{max_jobs})")
                            
                        except Exception as e:
                            logger.warning(f"Error processing job: {str(e)}")
                            continue
                    
                    # If we found and processed jobs, reset retries
                    if job_list:
                        retries = 0
                    
                    # Try to load more jobs if available
                    try:
                        load_more = self.driver.find_element(By.CSS_SELECTOR, "button.infinite-scroller__show-more-button")
                        load_more.click()
                        time.sleep(3)
                    except:
                        logger.info("No more jobs to load")
                        break
                    
                except Exception as e:
                    logger.warning(f"Error in job application loop: {str(e)}")
                    retries += 1
                    time.sleep(5)
            
            logger.info(f"Applied to {jobs_applied} jobs")
            return True
            
        except Exception as e:
            logger.error(f"Error in apply_to_jobs: {str(e)}")
            return False
            
    def process_application(self):
        """Process a single job application"""
        try:
            # Wait for application modal
            application_modal = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.jobs-easy-apply-modal"))
            )
            
            # Find next/submit button
            next_button = application_modal.find_element(By.CSS_SELECTOR, 
                "button[aria-label='Submit application']"
            )
            
            if next_button:
                next_button.click()
                time.sleep(2)
                return True
                
            return False
            
        except Exception as e:
            logger.warning(f"Error processing application: {str(e)}")
            return False

    def apply_easy_apply_filter(self):
        """Apply the Easy Apply filter"""
        try:
            # Wait for filters to be clickable
            logger.info("Looking for filter options...")
            filter_button = None
            filter_selectors = [
                "button[aria-label='Easy Apply filter']",
                "button.jobs-search-box__easy-apply-button",
                "[aria-label='Easy Apply filter.']",
                "button[data-tracking-control-name='public_jobs_f_LF']"
            ]
            
            for selector in filter_selectors:
                try:
                    filter_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    if filter_button.is_displayed():
                        break
                except:
                    continue
            
            if not filter_button:
                # Try to find and click the "All filters" button first
                try:
                    all_filters_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='All filters']"))
                    )
                    all_filters_button.click()
                    logger.info("Clicked 'All filters' button")
                    time.sleep(2)
                    
                    # Look for Easy Apply checkbox in the modal
                    easy_apply_checkbox = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//label[contains(., 'Easy Apply')]"))
                    )
                    easy_apply_checkbox.click()
                    logger.info("Selected Easy Apply filter in modal")
                    
                    # Click Show Results
                    show_results_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-test-modal-close-btn]"))
                    )
                    show_results_button.click()
                    logger.info("Applied filters")
                    time.sleep(2)
                    return True
                    
                except Exception as e:
                    logger.warning(f"Could not apply Easy Apply filter through modal: {str(e)}")
                    return False
            
            # Click the Easy Apply filter button if found
            filter_button.click()
            logger.info("Applied Easy Apply filter")
            time.sleep(2)
            return True
            
        except Exception as e:
            logger.warning(f"Error applying Easy Apply filter: {str(e)}")
            return False

    def verify_search_applied(self, max_attempts=5):
        """Verify that the search was properly applied"""
        for attempt in range(max_attempts):
            try:
                # Wait for results to load
                time.sleep(3)
                
                # Check URL parameters
                current_url = self.driver.current_url.lower()
                keywords_in_url = any(kw.lower() in current_url for kw in self.keywords.split())
                location_in_url = self.location.lower().replace(" ", "").replace(",", "") in current_url.replace("%20", "").replace(",", "")
                
                if keywords_in_url and location_in_url:
                    logger.info("Search parameters verified in URL")
                    
                    # Verify search results are showing
                    results_selectors = [
                        ".jobs-search-results-list",
                        ".jobs-search-results",
                        "div[data-job-search-results]"
                    ]
                    
                    results_found = False
                    for selector in results_selectors:
                        try:
                            results = WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                            )
                            if results.is_displayed():
                                # Try to find at least one job title containing the keywords
                                job_titles = self.driver.find_elements(By.CSS_SELECTOR, ".job-card-list__title")
                                if job_titles:
                                    logger.info(f"Found {len(job_titles)} job listings")
                                    return True
                                else:
                                    logger.warning("No job titles found in results")
                        except:
                            continue
                
                logger.warning(f"Search not fully applied yet (attempt {attempt + 1}/{max_attempts})")
                # Try to reapply search if needed
                if attempt < max_attempts - 1:
                    logger.info("Attempting to reapply search...")
                    self.search_jobs()
                
            except Exception as e:
                logger.warning(f"Error verifying search (attempt {attempt + 1}): {str(e)}")
            
            time.sleep(3)
        
        logger.warning("Could not fully verify search, but proceeding...")
        return False

    def verify_search_filters(self, max_attempts=10):
        """Verify that search filters are properly applied"""
        attempt = 0
        while attempt < max_attempts:
            attempt += 1
            try:
                # Check URL parameters
                current_url = self.driver.current_url.lower()
                if "keywords=" in current_url or "keywords%3D" in current_url:
                    logger.info("Search parameters detected in URL")
                    return True
                
                # Check input fields
                keywords_input = None
                location_input = None
                
                # Try to find the input fields
                input_selectors = {
                    'keywords': [
                        "input[aria-label='Search by title, skill, or company']",
                        "#jobs-search-box-keyword-id-ember",
                        "[name='keywords']"
                    ],
                    'location': [
                        "input[aria-label='City, state, or zip code']",
                        "#jobs-search-box-location-id-ember",
                        "[name='location']"
                    ]
                }
                
                # Check keywords field
                for selector in input_selectors['keywords']:
                    try:
                        keywords_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if keywords_input.is_displayed():
                            current_keywords = keywords_input.get_attribute('value')
                            if current_keywords and self.keywords.lower() in current_keywords.lower():
                                logger.info(f"Keywords filter verified: {current_keywords}")
                                break
                    except:
                        continue
                
                # Check location field
                for selector in input_selectors['location']:
                    try:
                        location_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if location_input.is_displayed():
                            current_location = location_input.get_attribute('value')
                            if current_location and self.location.lower() in current_location.lower():
                                logger.info(f"Location filter verified: {current_location}")
                                break
                    except:
                        continue
                
                # Verify search results are showing
                results_selectors = [
                    ".jobs-search-results-list",
                    ".jobs-search-results",
                    "div[data-job-search-results]",
                    ".jobs-search__results-list"
                ]
                
                results_found = False
                for selector in results_selectors:
                    try:
                        results = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if results.is_displayed():
                            results_found = True
                            logger.info("Search results container found")
                            break
                    except:
                        continue
                
                if not results_found:
                    logger.warning(f"Search results not found yet (attempt {attempt}/{max_attempts})")
                    time.sleep(3)
                    continue
                
                # Check if we need to apply filters again
                if not (keywords_input and location_input):
                    logger.info("Search filters not found, applying them again...")
                    self.search_jobs()
                    time.sleep(5)  # Wait for filters to apply
                    continue
                
                return True
                
            except Exception as e:
                logger.warning(f"Error verifying search filters (attempt {attempt}/{max_attempts}): {str(e)}")
                time.sleep(3)
                continue
        
        logger.warning("Could not fully verify search filters, but proceeding...")
        return False

    def verify_page_loaded(self, verification_selectors, max_attempts=3, wait_time=3):
        """Verify if page elements are loaded correctly"""
        for attempt in range(max_attempts):
            for selector in verification_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element.is_displayed():
                        return True
                except:
                    continue
            
            # Always wait on failure, even on last attempt
            logger.warning(f"Page verification failed, attempt {attempt + 1}/{max_attempts}")
            time.sleep(wait_time)
        
        logger.error("Page verification failed after all attempts")
        return False

    def get_job_listings(self, max_jobs=25):
        """Get list of jobs from search results and start application process"""
        try:
            jobs_processed = 0
            retry_count = 0
            max_retries = 3
            
            while jobs_processed < max_jobs and retry_count < max_retries:
                # Find all job cards with multiple selectors
                job_card_selectors = [
                    "div.job-card-container",
                    "div.jobs-search-results__list-item",
                    "li.jobs-search-results__list-item",
                    "div.job-card-list__entity",
                    "div[data-job-id]"
                ]
                
                job_cards = []
                for selector in job_card_selectors:
                    cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if cards:
                        job_cards = cards
                        logger.info(f"Found job cards with selector: {selector}")
                        break
                
                # Verify job cards are present
                if not job_cards:
                    if retry_count < max_retries - 1:
                        logger.warning(f"No job cards found (attempt {retry_count + 1}/{max_retries})")
                        retry_count += 1
                        time.sleep(3)
                        continue
                    else:
                        logger.error("Failed to find job cards after all attempts")
                        if self.db_manager:
                            self.db_manager.log_error("JOB_SEARCH_FAILED", "No job cards found after max retries")
                        return False
                
                # Process each job card
                for card in job_cards:
                    if jobs_processed >= max_jobs:
                        break
                        
                    try:
                        # Extract job details with multiple possible selectors
                        title_selectors = [
                            "h3.job-card-title",
                            "h3.job-card-list__title",
                            "a.job-card-list__title",
                            "h3.base-search-card__title",
                            ".job-card-container__link",
                            "a[data-control-name='job_card_title']"
                        ]
                        
                        company_selectors = [
                            "h4.job-card-company-name",
                            "h4.base-search-card__subtitle",
                            "a.job-card-container__company-name",
                            ".job-card-container__company-link",
                            "a[data-control-name='job_card_company']"
                        ]
                        
                        location_selectors = [
                            "div.job-card-location",
                            ".job-card-container__metadata-item",
                            ".base-search-card__metadata",
                            "span.job-card-container__location"
                        ]
                        
                        # Try to find title
                        title = None
                        for selector in title_selectors:
                            try:
                                title_elem = card.find_element(By.CSS_SELECTOR, selector)
                                title = title_elem.text.strip()
                                if title:
                                    break
                            except:
                                continue
                        
                        if not title:
                            logger.warning("Could not find job title, skipping...")
                            continue
                        
                        # Try to find company
                        company = None
                        for selector in company_selectors:
                            try:
                                company_elem = card.find_element(By.CSS_SELECTOR, selector)
                                company = company_elem.text.strip()
                                if company:
                                    break
                            except:
                                continue
                        
                        if not company:
                            company = "Unknown Company"
                        
                        # Try to find location
                        location = None
                        for selector in location_selectors:
                            try:
                                location_elem = card.find_element(By.CSS_SELECTOR, selector)
                                location = location_elem.text.strip()
                                if location:
                                    break
                            except:
                                continue
                        
                        if not location:
                            location = "Unknown Location"
                        
                        job_data = {
                            'title': title,
                            'company': company,
                            'location': location
                        }
                        
                        logger.info(f"Processing job: {title} at {company}")
                        
                        # Click on the job card and verify details page loaded
                        click_success = False
                        for attempt in range(3):
                            try:
                                # Try clicking with multiple methods
                                click_methods = [
                                    lambda: card.find_element(By.CSS_SELECTOR, "a.job-card-list__title").click(),
                                    lambda: card.find_element(By.CSS_SELECTOR, ".job-card-container__link").click(),
                                    lambda: self.driver.execute_script("arguments[0].click();", 
                                        card.find_element(By.CSS_SELECTOR, "a[data-control-name='job_card_title']")),
                                    lambda: self.driver.execute_script("arguments[0].click();", card)
                                ]
                                
                                for click_method in click_methods:
                                    try:
                                        click_method()
                                        # Verify job details page loaded
                                        details_selectors = [
                                            "div.jobs-description",
                                            "div.job-view-layout",
                                            "div.jobs-details",
                                            ".jobs-unified-top-card",
                                            "#job-details"
                                        ]
                                        
                                        if self.verify_page_loaded(details_selectors):
                                            click_success = True
                                            break
                                    except:
                                        continue
                                
                                if click_success:
                                    break
                                
                            except:
                                if attempt < 2:
                                    logger.warning(f"Failed to click job card, attempt {attempt + 1}/3")
                                    time.sleep(3)
                                continue
                        
                        if not click_success:
                            logger.error(f"Failed to load job details for: {title}")
                            if self.db_manager:
                                self.db_manager.log_job_status(job_data, "FAILED", "Could not load job details")
                            continue
                        
                        # Look for Easy Apply button
                        easy_apply_found = False
                        for attempt in range(3):
                            easy_apply_selectors = [
                                "button.jobs-apply-button",
                                "button[aria-label*='Easy Apply']",
                                "button.jobs-apply-button--top-card",
                                "button[data-control-name='jobdetails_topcard_inapply']",
                                ".jobs-apply-button--top-card",
                                ".jobs-s-apply button"
                            ]
                            
                            for selector in easy_apply_selectors:
                                try:
                                    easy_apply_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                                    if easy_apply_button.is_displayed() and easy_apply_button.is_enabled():
                                        # Scroll to button
                                        self.driver.execute_script("arguments[0].scrollIntoView(true);", easy_apply_button)
                                        
                                        # Click the button
                                        self.driver.execute_script("arguments[0].click();", easy_apply_button)
                                        logger.info(f"Clicked Easy Apply for: {title}")
                                        
                                        # Verify application modal appeared
                                        modal_selectors = [
                                            "div[data-test-modal-id='easy-apply-modal']",
                                            ".jobs-easy-apply-modal",
                                            "div[role='dialog'][aria-label*='apply']"
                                        ]
                                        
                                        if self.verify_page_loaded(modal_selectors):
                                            logger.info("Application modal opened")
                                            easy_apply_found = True
                                            
                                            # Click Next on modal first
                                            next_selectors = [
                                                "button[aria-label='Continue to next step']",
                                                "button[aria-label*='Next']",
                                                "button[data-control-name='continue_unify']",
                                                "//*[contains(text(), 'Next')]",
                                                "//*[contains(text(), 'Continue')]",
                                                "footer button[aria-label*='Continue']",
                                                "footer button[aria-label*='Next']"
                                            ]
                                            
                                            next_clicked = False
                                            for selector in next_selectors:
                                                try:
                                                    if selector.startswith("//"):
                                                        next_button = self.driver.find_element(By.XPATH, selector)
                                                    else:
                                                        next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                                                        
                                                    if next_button.is_displayed() and next_button.is_enabled():
                                                        logger.info("Found and clicking Next button on modal")
                                                        self.driver.execute_script("arguments[0].click();", next_button)
                                                        next_clicked = True
                                                        time.sleep(1)
                                                        break
                                                except:
                                                    continue
                                            
                                            if next_clicked:
                                                # Process the application steps
                                                if self.process_application_steps(job_data):
                                                    logger.info(f"Successfully completed application for: {title}")
                                                else:
                                                    logger.warning(f"Failed to complete application for: {title}")
                                            else:
                                                logger.warning("Could not find Next button on modal")
                                                if self.db_manager:
                                                    self.db_manager.log_job_status(job_data, "FAILED", "Could not find Next button on modal")
                                            
                                            break
                                except:
                                    continue
                            
                            if easy_apply_found:
                                break
                                
                            if attempt < 2:
                                logger.warning(f"Easy Apply button not found/clickable, attempt {attempt + 1}/3")
                                time.sleep(3)
                        
                        if not easy_apply_found:
                            logger.error(f"Failed to start application for: {title}")
                            if self.db_manager:
                                self.db_manager.log_job_status(job_data, "FAILED", "Could not start application")
                        
                        jobs_processed += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing job card: {str(e)}")
                        if self.db_manager:
                            self.db_manager.log_error("JOB_PROCESSING_ERROR", str(e))
                        continue
                
                if jobs_processed < max_jobs:
                    # Scroll to load more
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView(true);", 
                        job_cards[-1]
                    )
                    time.sleep(3)  # Always wait after scroll to load more jobs
            
            logger.info(f"Processed {jobs_processed} jobs")
            return True
            
        except Exception as e:
            logger.error(f"Error processing job listings: {str(e)}")
            if self.db_manager:
                self.db_manager.log_error("JOB_LISTING_ERROR", str(e))
            return False

    def scroll_to_job(self, job_element):
        """Scroll job into view"""
        try:
            self.driver.execute_script("arguments[0].scrollIntoView(true);", job_element)
            time.sleep(1)
        except Exception as e:
            logger.error(f"Error scrolling to job: {str(e)}")

    def click_job(self, job_element):
        """Click on a job to view details"""
        try:
            # Scroll to job first
            self.driver.execute_script("arguments[0].scrollIntoView(true);", job_element)
            time.sleep(3)  # Wait after scroll
            
            # Try JavaScript click first
            self.driver.execute_script("arguments[0].click();", job_element)
            time.sleep(3)  # Wait after click
            
            # Check for page not found error
            if self.check_page_not_found():
                return False
            
            # Wait for job details with multiple selectors
            detail_selectors = [
                "div.jobs-description",
                "div.job-view-layout",
                "div.jobs-details",
                ".jobs-unified-top-card",
                "#job-details"
            ]
            
            # Try each selector
            for selector in detail_selectors:
                try:
                    self.wait.until(EC.presence_of_element_located(
                        (By.CSS_SELECTOR, selector)))
                    time.sleep(3)  # Wait after details load
                    logger.info("Job details loaded")
                    return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error clicking job: {str(e)}")
            return False

    def check_page_not_found(self):
        """Check if we hit a page not found error and handle it"""
        try:
            error_indicators = [
                "//*[contains(text(), 'Page not found')]",
                "//*[contains(text(), 'This job is no longer available')]",
                "//*[contains(text(), 'This job has expired')]"
            ]
            
            for indicator in error_indicators:
                if len(self.driver.find_elements(By.XPATH, indicator)) > 0:
                    logger.info("Page not found error detected")
                    
                    # Try to find and click the feed button
                    try:
                        feed_button = self.driver.find_element(By.CSS_SELECTOR, "[data-test-app-aware-link='feed']")
                        try:
                            self.driver.execute_script("arguments[0].click();", feed_button)
                        except:
                            feed_button.click()
                        
                        logger.info("Clicked 'Go to your feed' button")
                        time.sleep(1)  # Short wait for feed navigation
                    except Exception as e:
                        logger.error(f"Error clicking feed button: {str(e)}")
                    
                    # Always go back to jobs page
                    logger.info("Redirecting to jobs page...")
                    self.driver.get("https://www.linkedin.com/jobs/search")
                    logger.info("Waiting 5 seconds for jobs page load...")
                    time.sleep(5)  # Wait 5 seconds for jobs page
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking for page not found: {str(e)}")
            return False

    def process_application_steps(self, job_data):
        """Handle the multi-step application process with AI form filling"""
        try:
            max_steps = 10  # Maximum number of steps to prevent infinite loops
            current_step = 0
            
            while current_step < max_steps:
                # Wait for any loading to finish
                self.wait_for_loading_modal()
                
                # First check for success message
                success_selectors = [
                    "//*[contains(text(), 'application was sent')]",
                    "//*[contains(text(), 'Application submitted')]",
                    "//*[contains(text(), 'successfully submitted')]",
                    "//span[contains(text(), 'Done')]",
                    "//div[contains(@class, 'artdeco-modal__dismiss')]",
                    "//*[contains(text(), 'Your application was sent to')]"
                ]
                
                for selector in success_selectors:
                    try:
                        success_elem = self.driver.find_element(By.XPATH, selector)
                        if success_elem.is_displayed():
                            logger.info(f"Application submitted successfully for: {job_data['title']}")
                            if self.db_manager:
                                self.db_manager.log_job_status(job_data, "APPLIED", "Application submitted successfully")
                            return True
                    except:
                        continue
                
                # Check for any required fields that need filling
                required_fields = self.get_required_fields()
                
                if required_fields:
                    logger.info(f"Found {len(required_fields)} required fields to fill")
                    if not self.fill_form_fields(required_fields, job_data):
                        logger.warning("Failed to fill required fields")
                        if self.db_manager:
                            self.db_manager.log_job_status(job_data, "FAILED", "Could not fill required fields")
                        return False
                
                # Look for Submit button first
                submit_selectors = [
                    "button[aria-label='Submit application']",
                    "button[data-control-name='submit_unify']",
                    "button.jobs-apply-button",
                    "button[type='submit']",
                    "//*[contains(text(), 'Submit application')]",
                    "footer button[aria-label*='Submit']",
                    "button.artdeco-button--primary"
                ]
                
                submit_found = False
                for selector in submit_selectors:
                    try:
                        if selector.startswith("//"):
                            submit_button = self.driver.find_element(By.XPATH, selector)
                        else:
                            submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                            
                        if submit_button.is_displayed() and submit_button.is_enabled():
                            logger.info("Found Submit button")
                            self.driver.execute_script("arguments[0].click();", submit_button)
                            submit_found = True
                            time.sleep(2)  # Wait for submission
                            break
                    except:
                        continue
                
                if not submit_found:
                    # Look for Next button
                    next_selectors = [
                        "button[aria-label='Continue to next step']",
                        "button[aria-label*='Next']",
                        "button[data-control-name='continue_unify']",
                        "//*[contains(text(), 'Next')]",
                        "//*[contains(text(), 'Continue')]",
                        "footer button[aria-label*='Continue']",
                        "footer button[aria-label*='Next']",
                        "button.artdeco-button--primary"
                    ]
                    
                    next_found = False
                    for selector in next_selectors:
                        try:
                            if selector.startswith("//"):
                                next_button = self.driver.find_element(By.XPATH, selector)
                            else:
                                next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                                
                            if next_button.is_displayed() and next_button.is_enabled():
                                logger.info("Found Next button")
                                self.driver.execute_script("arguments[0].click();", next_button)
                                next_found = True
                                time.sleep(1)  # Short wait after clicking Next
                                break
                        except:
                            continue
                    
                    if not next_found:
                        logger.warning("Could not find Next or Submit button")
                        if self.db_manager:
                            self.db_manager.log_job_status(job_data, "FAILED", "Could not find Next or Submit button")
                        return False
                
                current_step += 1
                
            logger.warning("Reached maximum number of steps without completing application")
            if self.db_manager:
                self.db_manager.log_job_status(job_data, "FAILED", "Too many steps")
            return False
            
        except Exception as e:
            logger.error(f"Error processing application steps: {str(e)}")
            if self.db_manager:
                self.db_manager.log_job_status(job_data, "ERROR", str(e))
            return False
    
    def get_required_fields(self):
        """Get all required form fields"""
        required_fields = []
        field_selectors = {
            'input': "input[required], input[aria-required='true']",
            'select': "select[required], select[aria-required='true']",
            'textarea': "textarea[required], textarea[aria-required='true']"
        }
        
        for field_type, selector in field_selectors.items():
            try:
                fields = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for field in fields:
                    if field.is_displayed():
                        required_fields.append({
                            'element': field,
                            'type': field_type,
                            'name': field.get_attribute('name') or field.get_attribute('id') or field.get_attribute('aria-label'),
                            'current_value': field.get_attribute('value')
                        })
            except:
                continue
        
        return required_fields
    
    def fill_form_fields(self, required_fields, job_data):
        """Fill form fields using AI assistance"""
        try:
            for field in required_fields:
                # Skip if field already has a value
                if field['current_value'] and len(field['current_value'].strip()) > 0:
                    continue
                
                element = field['element']
                field_type = field['type']
                field_name = field['name'].lower() if field['name'] else ''
                
                # Use AI to determine appropriate value based on field name
                if any(term in field_name for term in ['year', 'years', 'experience']):
                    value = "3"  # Default years of experience
                elif any(term in field_name for term in ['salary', 'compensation']):
                    value = "80000"  # Default salary expectation
                elif 'phone' in field_name:
                    value = "1234567890"  # Default phone number
                elif 'website' in field_name:
                    value = "https://linkedin.com/in/myprofile"  # Default website
                elif any(term in field_name for term in ['resume', 'cv']):
                    # Handle resume upload if needed
                    continue
                else:
                    # For other fields, try to determine type and set appropriate value
                    if field_type == 'select':
                        # Select first option for dropdown
                        options = element.find_elements(By.TAG_NAME, "option")
                        if len(options) > 1:
                            self.driver.execute_script(
                                "arguments[0].value = arguments[1]", 
                                element, 
                                options[1].get_attribute('value')
                            )
                            continue
                    elif field_type == 'input':
                        input_type = element.get_attribute('type')
                        if input_type == 'text':
                            value = "Yes"  # Default text response
                        elif input_type == 'number':
                            value = "3"  # Default number
                        elif input_type == 'tel':
                            value = "1234567890"  # Default phone
                        elif input_type == 'url':
                            value = "https://linkedin.com"  # Default URL
                        else:
                            value = "Yes"  # Default for other types
                    elif field_type == 'textarea':
                        value = "I am highly interested in this position and believe my skills and experience make me a strong candidate."
                
                try:
                    # Clear and fill the field
                    element.clear()
                    element.send_keys(value)
                    logger.info(f"Filled field {field_name} with value")
                except:
                    logger.warning(f"Failed to fill field {field_name}")
                    continue
            
            return True
            
        except Exception as e:
            logger.error(f"Error filling form fields: {str(e)}")
            return False

    def wait_for_loading_modal(self):
        """Wait for loading modal to disappear"""
        try:
            loading_selectors = [
                "div.loading-modal",
                "div.artdeco-loading-modal",
                ".loading-icon",
                ".artdeco-modal__loading"
            ]
            
            for selector in loading_selectors:
                try:
                    loading_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if loading_element.is_displayed():
                        time.sleep(3)  # Always wait 3 seconds if loading indicator found
                        break
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Error checking loading modal: {str(e)}")
            time.sleep(3)  # Wait 3 seconds on error just to be safe
