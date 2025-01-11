import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from urllib.parse import quote
from selenium.webdriver.common.keys import Keys

logger = logging.getLogger(__name__)

class LinkedInJobs:
    def __init__(self, driver, db_manager=None):
        self.driver = driver
        self.wait = WebDriverWait(self.driver, 10)
        self.db_manager = db_manager

    def search_jobs(self, keywords, location):
        """Search for jobs with given keywords and location"""
        try:
            # Navigate to jobs page
            self.driver.get("https://www.linkedin.com/jobs/")
            time.sleep(3)  # Wait for page load
            logger.info("Navigated to jobs page")
            
            # Find and fill keywords field
            keywords_input = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[aria-label*='Search by title'], input[aria-label*='Search job titles']")))
            keywords_input.clear()
            time.sleep(3)  # Wait after clear
            keywords_input.send_keys(keywords)
            time.sleep(3)  # Wait after keywords
            logger.info(f"Entered keywords: {keywords}")
            
            # Find and fill location field
            location_input = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[aria-label*='City'], input[aria-label*='location']")))
            location_input.clear()
            time.sleep(3)  # Wait after clear
            location_input.send_keys(location)
            time.sleep(3)  # Wait after location
            location_input.send_keys(Keys.RETURN)
            time.sleep(3)  # Wait after search
            logger.info(f"Entered location: {location} and started search")
            
            # Add Easy Apply filter
            try:
                easy_apply_button = self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(., 'Easy Apply')]")))
                easy_apply_button.click()
                time.sleep(3)  # Wait after filter
                logger.info("Applied Easy Apply filter")
            except Exception as e:
                logger.warning(f"Could not find Easy Apply filter: {str(e)}")
            
            # Verify search results with multiple selectors
            result_selectors = [
                "ul.jobs-search__results-list",  # Main results list
                "div.jobs-search-results-list",  # Alternative results container
                "div.jobs-search__job-card-list",  # Job card list
                "li.jobs-search-results__list-item",  # Individual result items
                "div.job-card-container",  # Job cards
                "div.jobs-search__results-grid"  # Grid view results
            ]
            
            # Log page source for debugging
            logger.debug("Current page HTML structure:")
            logger.debug(self.driver.page_source[:500])  # Log first 500 chars for debugging
            
            # Try each selector
            for selector in result_selectors:
                try:
                    results = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if results:
                        logger.info(f"Found {len(results)} search results with selector: {selector}")
                        time.sleep(3)  # Wait for results to fully load
                        return True
                except Exception as e:
                    logger.debug(f"Selector {selector} not found: {str(e)}")
                    continue
            
            # If no results found with CSS selectors, try XPath alternatives
            xpath_selectors = [
                "//div[contains(@class, 'jobs-search')]//div[contains(@class, 'job-card')]",
                "//div[contains(@class, 'jobs-search-results')]",
                "//ul[contains(@class, 'jobs-search__results-list')]",
                "//div[contains(@class, 'job-card-list')]"
            ]
            
            for xpath in xpath_selectors:
                try:
                    results = self.driver.find_elements(By.XPATH, xpath)
                    if results:
                        logger.info(f"Found {len(results)} search results with XPath: {xpath}")
                        time.sleep(3)
                        return True
                except Exception as e:
                    logger.debug(f"XPath {xpath} not found: {str(e)}")
                    continue
            
            # Last resort: check if we're on the correct URL and page has job-related content
            current_url = self.driver.current_url
            if 'jobs' in current_url and 'linkedin.com' in current_url:
                # Try to find any job-related content
                job_indicators = [
                    "//div[contains(text(), 'jobs')]",
                    "//span[contains(text(), 'results')]",
                    "//div[contains(@class, 'jobs')]"
                ]
                
                for indicator in job_indicators:
                    if len(self.driver.find_elements(By.XPATH, indicator)) > 0:
                        logger.info("Found job-related content on page")
                        time.sleep(3)
                        return True
            
            logger.warning("Could not verify search results. Current URL: " + current_url)
            logger.warning("Please check if the search page is loading correctly")
            return False
            
        except Exception as e:
            logger.error(f"Error searching jobs: {str(e)}")
            return False
            
    def get_job_listings(self, max_jobs=25):
        """Get list of jobs from search results"""
        try:
            jobs = []
            retry_count = 0
            max_retries = 3
            
            while len(jobs) < max_jobs and retry_count < max_retries:
                # Find all job cards
                job_cards = self.driver.find_elements(By.CSS_SELECTOR, "div.job-card-container")
                time.sleep(3)  # Wait after finding cards
                
                if not job_cards:
                    logger.warning(f"No job cards found (attempt {retry_count + 1}/{max_retries})")
                    retry_count += 1
                    time.sleep(3)  # Wait before retry
                    continue
                
                # Process each job card
                for card in job_cards:
                    if len(jobs) >= max_jobs:
                        break
                        
                    try:
                        title = card.find_element(By.CSS_SELECTOR, "h3.job-card-title").text
                        company = card.find_element(By.CSS_SELECTOR, "h4.job-card-company-name").text
                        location = card.find_element(By.CSS_SELECTOR, "div.job-card-location").text
                        
                        jobs.append({
                            'element': card,
                            'title': title,
                            'company': company,
                            'location': location
                        })
                        time.sleep(1)  # Short wait between processing cards
                    except:
                        continue
                
                if len(jobs) < max_jobs:
                    # Scroll to load more
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView(true);", 
                        job_cards[-1]
                    )
                    time.sleep(3)  # Wait after scroll
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error getting job listings: {str(e)}")
            return []

    def scroll_to_job(self, job_element):
        """Scroll job into view"""
        try:
            self.driver.execute_script("arguments[0].scrollIntoView(true);", job_element)
            time.sleep(1)
        except Exception as e:
            logger.error(f"Error scrolling to job: {str(e)}")

    def check_page_not_found(self):
        """Check if we're on a Page not found error and handle it"""
        try:
            # Check for various "Page not found" indicators
            error_indicators = [
                "//h1[contains(text(), 'Page not found')]",  # Updated to h1
                "//div[contains(@class, 'not-found')]",
                "//div[contains(@class, 'error-page')]",
                "//div[contains(text(), 'Uh oh, we can')]"  # Part of the error message
            ]
            
            for indicator in error_indicators:
                if len(self.driver.find_elements(By.XPATH, indicator)) > 0:
                    logger.info("Page not found error detected")
                    
                    # Try to find and click the feed button
                    try:
                        # Wait for the button to be clickable
                        feed_button = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, "//a[text()='Go to your feed']"))
                        )
                        # Try JavaScript click first
                        try:
                            self.driver.execute_script("arguments[0].click();", feed_button)
                        except:
                            feed_button.click()
                        
                        logger.info("Clicked 'Go to your feed' button")
                        time.sleep(1)  # Short wait for navigation
                        
                        # Verify we're back on feed or jobs page
                        if "/feed" in self.driver.current_url or "/jobs" in self.driver.current_url:
                            return True
                            
                    except Exception as e:
                        logger.error(f"Error clicking feed button: {str(e)}")
                    
                    # If button click failed, go back to jobs page
                    logger.info("Redirecting to jobs page")
                    self.driver.get("https://www.linkedin.com/jobs/")
                    time.sleep(1)  # Short wait for navigation
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking for page not found: {str(e)}")
            return False

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
                "div.jobs-details",
                "div.jobs-search__job-details",
                "div.jobs-search__job-details--container",
                "div[data-job-id]"
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
