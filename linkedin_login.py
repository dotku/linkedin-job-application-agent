import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import os

from utils.logger import setup_logger
from utils.chrome_setup import ChromeSetup

# Set up logging
logger = setup_logger(__name__, "linkedin_login")

class LinkedInLogin:
    def __init__(self, driver=None):
        """Initialize LinkedIn Login"""
        self.driver = driver or ChromeSetup.initialize_driver()
        self.email = os.getenv('LINKEDIN_EMAIL')
        self.password = os.getenv('LINKEDIN_PASSWORD')
        self.wait = WebDriverWait(self.driver, 3)  # Reduce default wait time to 3 seconds

    def wait_for_element(self, by, value, timeout=10, condition=EC.presence_of_element_located):
        """Wait for an element with custom timeout and condition"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                condition((by, value))
            )
            return element
        except TimeoutException:
            return None

    def check_for_security_verification(self):
        """Check if security verification is needed"""
        try:
            # First check for verification iframe
            iframe_selectors = [
                "//iframe[contains(@title, 'Security verification')]",
                "//iframe[contains(@title, 'verification')]",
                "//iframe[contains(@title, 'challenge')]"
            ]
            
            # Try to find and switch to verification iframe
            iframe_found = False
            for selector in iframe_selectors:
                try:
                    iframe = self.wait_for_element(By.XPATH, selector, timeout=2)
                    if iframe:
                        self.driver.switch_to.frame(iframe)
                        iframe_found = True
                        break
                except:
                    continue
            
            # Check for verification elements either in iframe or main content
            verification_selectors = [
                "//div[contains(text(), 'verification')]",
                "//div[contains(text(), 'security check')]",
                "//button[contains(text(), 'Verify')]",
                "//div[contains(@class, 'challenge')]",
                "//div[contains(@class, 'verification')]",
                "//input[@type='checkbox']",  # Common in reCAPTCHA
                "//div[@role='presentation']"  # Common in reCAPTCHA
            ]
            
            for selector in verification_selectors:
                try:
                    if self.wait_for_element(By.XPATH, selector, timeout=2):
                        return True
                except:
                    continue
            
            # Switch back to default content if we switched to iframe
            if iframe_found:
                try:
                    self.driver.switch_to.default_content()
                except:
                    pass
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking for security verification: {str(e)}")
            # Always try to switch back to default content
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False

    def wait_for_verification_completion(self, timeout=None):
        """Wait until the security verification is completed"""
        try:
            start_time = time.time()
            verification_start = False
            
            while True:
                try:
                    # Check if we're already logged in
                    if self.check_login_status():
                        logger.info("Verification completed successfully")
                        return True
                    
                    # Check if browser is still open
                    self.driver.current_url  # This will raise an exception if browser is closed
                    
                    # Check if verification is needed
                    if self.check_for_security_verification():
                        if not verification_start:
                            logger.info("Security verification detected - waiting for completion...")
                            verification_start = True
                        else:
                            logger.info("Still waiting for verification completion...")
                    
                    # Only check timeout if specified
                    if timeout and time.time() - start_time > timeout:
                        logger.warning("Verification is taking longer than usual, but continuing to wait...")
                    
                    # Sleep a bit before checking again
                    time.sleep(5)
                    
                except Exception as e:
                    if "invalid session id" in str(e).lower() or "no such window" in str(e).lower():
                        logger.error("Browser was closed during verification")
                        return False
                    logger.warning(f"Error during verification check: {str(e)}, continuing to wait...")
                    time.sleep(5)
                
        except Exception as e:
            logger.error(f"Critical error in verification completion: {str(e)}")
            return False

    def check_login_status(self):
        """Check if we are currently logged in"""
        try:
            # Quick check for any of these elements
            quick_indicators = [
                "div.global-nav",  # Nav bar
                "input.search-global-typeahead__input",  # Search box
                ".feed-identity-module"  # Profile section
            ]
            
            for selector in quick_indicators:
                try:
                    if self.driver.find_element(By.CSS_SELECTOR, selector):
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking login status: {str(e)}")
            return False

    def verify_feed_page(self):
        """Verify that the LinkedIn feed page has loaded successfully"""
        try:
            # Wait for feed page elements
            feed_selectors = [
                ".feed-shared-update-v2",  # Feed posts
                ".feed-shared-news-module",  # News module
                ".feed-shared-actor"  # Post author info
            ]
            
            for selector in feed_selectors:
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    logger.info(f"Feed element found: {selector}")
                    return True
                except TimeoutException:
                    continue
            
            logger.warning("Could not verify all feed elements")
            return False
            
        except Exception as e:
            logger.error(f"Error verifying feed page: {str(e)}")
            return False

    def wait_with_countdown(self, seconds):
        """Wait with countdown display"""
        for remaining in range(seconds, 0, -1):
            logger.info(f"Rate limit cooldown: {remaining} seconds remaining...")
            time.sleep(1)

    def wait_for_security_check(self):
        """Wait for security check to be resolved"""
        logger.info("Waiting for security check to be resolved...")
        
        max_attempts = 3
        attempt = 0
        verification_wait = 60  # Wait 60 seconds on verification page
        
        while attempt < max_attempts:
            attempt += 1
            
            try:
                current_url = self.driver.current_url
                
                # Check if we hit rate limit
                if "challengesV2/inapp/tooManyAttempts" in current_url:
                    logger.warning("Hit rate limit, waiting 60 seconds before retry...")
                    self.wait_with_countdown(60)
                    self.driver.get("https://www.linkedin.com/login")
                    time.sleep(3)
                    return self.login()
                
                # Already on feed page
                if "feed" in current_url:
                    logger.info("Security check resolved - feed page loaded")
                    return True
                    
                # Already on jobs page
                if "/jobs" in current_url:
                    logger.info("Security check resolved - jobs page loaded")
                    return True
                
                # Still on verification page
                if any(x in current_url for x in ["checkpoint", "challenge", "verification"]):
                    logger.info(f"Still on verification page, waiting {verification_wait} seconds...")
                    # Check every 5 seconds during wait
                    for remaining in range(verification_wait, 0, -5):
                        current_url = self.driver.current_url
                        if "feed" in current_url or "/jobs" in current_url:
                            logger.info("Security check resolved during wait")
                            return True
                        logger.info(f"Verification page cooldown: {remaining} seconds remaining...")
                        time.sleep(5)
                    continue
                
                # Unknown page
                logger.warning(f"On unknown page: {current_url}")
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"Error checking security status: {str(e)}")
                if attempt == max_attempts:
                    return False
                time.sleep(5)
                
        return False

    def attempt_login(self, max_attempts=3):
        """Attempt to login with retries"""
        attempt = 0
        while attempt < max_attempts:
            attempt += 1
            try:
                logger.info(f"Login attempt {attempt}/{max_attempts}")
                
                # Check if we're on login page
                current_url = self.driver.current_url
                if "linkedin.com/login" not in current_url:
                    logger.info("Not on login page, navigating to it...")
                    self.driver.get("https://www.linkedin.com/login")
                    time.sleep(3)
                
                # Clear fields first
                username = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "username"))
                )
                password = self.driver.find_element(By.ID, "password")
                
                username.clear()
                password.clear()
                time.sleep(1)
                
                # Enter credentials
                email = os.getenv("LINKEDIN_EMAIL")
                pwd = os.getenv("LINKEDIN_PASSWORD")
                
                if not email or not pwd:
                    logger.error("Missing LinkedIn credentials in environment variables")
                    return False
                
                # Enter credentials directly
                username.send_keys(email)
                password.send_keys(pwd)
                time.sleep(1)
                
                # Click login button
                login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                login_button.click()
                
                # Wait for security check
                if self.wait_for_security_check():
                    logger.info("Successfully logged in to LinkedIn")
                    return True
                
                logger.warning(f"Login attempt {attempt} failed, retrying...")
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"Error during login attempt {attempt}: {str(e)}")
                if attempt == max_attempts:
                    return False
                time.sleep(5)
        
        return False

    def login(self):
        """Login to LinkedIn"""
        try:
            logger.info("Starting LinkedIn login process...")
            return self.attempt_login()
            
        except Exception as e:
            logger.error(f"Error during login process: {str(e)}")
            return False
