import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import cv2
import numpy as np
from PIL import Image
import base64
import io
import time

logger = logging.getLogger(__name__)

class LinkedInCaptcha:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(self.driver, 10)

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

    def wait_for_verification_completion(self, timeout=300):  # 5 minutes timeout
        """Wait until the security verification is completed"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check if we're back on a normal LinkedIn page
                normal_page_indicators = [
                    "//div[contains(@class, 'jobs-search-box')]",
                    "//header[contains(@class, 'global-nav')]",
                    "//div[contains(@class, 'jobs-search-results')]",
                    "//div[contains(@class, 'jobs-search-two-pane')]"
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
                
                if not any(len(self.driver.find_elements(By.XPATH, ind)) > 0 
                          for ind in verification_indicators):
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
