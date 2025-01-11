import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, NoSuchFrameException
import time

logger = logging.getLogger(__name__)

class LinkedInLogin:
    def __init__(self, driver, email, password):
        self.driver = driver
        self.email = email
        self.password = password
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

    def wait_for_verification_completion(self, timeout=300):
        """Wait until the security verification is completed"""
        try:
            start_time = time.time()
            while True:
                try:
                    # Check if we're already logged in
                    if self.check_login_status():
                        logger.info("Verification completed successfully")
                        return True
                    
                    # Check if browser is still open
                    self.driver.current_url  # This will raise an exception if browser is closed
                    
                    # Check if we've exceeded the timeout
                    if time.time() - start_time > timeout:
                        logger.error("Verification timed out")
                        return False
                    
                    # Sleep a bit before checking again
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Browser closed during verification: {str(e)}")
                    return False
                
        except Exception as e:
            logger.error(f"Error in verification completion: {str(e)}")
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

    def login(self):
        """Login to LinkedIn"""
        try:
            # Navigate to login page if not already there
            current_url = self.driver.current_url
            if not current_url.startswith("https://www.linkedin.com"):
                self.driver.get("https://www.linkedin.com/login")
            
            # Quick check if already logged in
            if self.check_login_status():
                logger.info("Already logged in")
                return True
            
            # Try to find login form elements without waiting
            try:
                # Find all elements in one go to reduce lookups
                form_elements = {
                    'username': self.driver.find_element(By.ID, "username"),
                    'password': self.driver.find_element(By.ID, "password"),
                    'submit': self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                }
                
                # Input credentials and submit quickly
                form_elements['username'].send_keys(self.email)
                form_elements['password'].send_keys(self.password)
                form_elements['submit'].click()
                
                # Quick check for successful login (reduced wait)
                for _ in range(2):  # Try twice with 0.5s interval
                    if self.check_login_status():
                        logger.info("Login successful")
                        return True
                    time.sleep(0.5)
                
                # If not logged in, check for verification
                if self.check_for_security_verification():
                    logger.info("Security verification required - proceeding without waiting")
                    return True
                    
                return False
                
            except Exception as e:
                logger.error(f"Error during quick login: {str(e)}")
                return False
            
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False
