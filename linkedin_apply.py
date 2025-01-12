import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
import time
import os
import json
from ai_assistant import AIJobAssistant
from selenium.webdriver.support.select import Select

from utils.logger import setup_logger
from utils.chrome_setup import ChromeSetup

# Set up logger
logger = setup_logger("linkedin_apply")

class LinkedInApply:
    def __init__(self, driver=None, db_manager=None):
        """Initialize LinkedIn Apply"""
        self.driver = driver or ChromeSetup.initialize_driver()
        self.wait = WebDriverWait(self.driver, 10)
        self.db_manager = db_manager
        self.ai_assistant = AIJobAssistant()

    def apply_to_job(self, job_data):
        """Apply to a job"""
        try:
            # First, get the job description
            try:
                # Wait for job details to load
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.jobs-description")))
                time.sleep(2)  # Give extra time for content to load
                
                description_elem = self.driver.find_element(By.CSS_SELECTOR, "div.jobs-description")
                page_source = description_elem.get_attribute('innerHTML')
                
                # Extract job details using AI
                description, requirements = self.ai_assistant.extract_job_details(page_source)
                
                if description and requirements:
                    # Analyze job with AI
                    should_apply, reason = self.ai_assistant.analyze_job(
                        job_data['title'],
                        job_data['company'],
                        description,
                        requirements
                    )
                    
                    if not should_apply:
                        logger.info(f"AI suggests not applying: {reason}")
                        return False
                    
                    logger.info(f"AI suggests applying: {reason}")
                
            except Exception as e:
                logger.warning(f"Could not analyze job with AI: {str(e)}")
            
            # Check for Easy Apply button with multiple selectors and strategies
            easy_apply_selectors = [
                "button.jobs-apply-button",
                "button[aria-label*='Easy Apply']",
                "button.jobs-apply-button--top-card",
                "button[data-control-name='jobdetails_topcard_inapply']",
                ".jobs-apply-button--top-card",
                ".jobs-s-apply button",
                "//*[contains(@class, 'jobs-apply-button')]",  # XPath
                "//*[contains(text(), 'Easy Apply')]"  # XPath for text content
            ]
            
            time.sleep(3)  # Wait before looking for button
            
            # Try each selector
            for selector in easy_apply_selectors:
                try:
                    # Try both CSS and XPath selectors
                    if selector.startswith("/"):
                        easy_apply_button = self.driver.find_element(By.XPATH, selector)
                    else:
                        easy_apply_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if easy_apply_button and easy_apply_button.is_displayed() and easy_apply_button.is_enabled():
                        logger.info(f"Found Easy Apply button with selector: {selector}")
                        
                        # Scroll to button to ensure it's in view
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", easy_apply_button)
                        time.sleep(2)  # Wait after scroll
                        
                        # Try multiple click strategies
                        click_successful = False
                        click_methods = [
                            lambda: self.driver.execute_script("arguments[0].click();", easy_apply_button),
                            lambda: easy_apply_button.click(),
                            lambda: self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector))).click()
                        ]
                        
                        for click_method in click_methods:
                            try:
                                click_method()
                                time.sleep(2)  # Wait after click
                                
                                # Verify if the Easy Apply modal appeared
                                if self.wait.until(EC.presence_of_element_located(
                                    (By.CSS_SELECTOR, "div[data-test-modal-id='easy-apply-modal']"))):
                                    click_successful = True
                                    break
                            except Exception as e:
                                logger.debug(f"Click method failed: {str(e)}")
                                continue
                        
                        if click_successful:
                            logger.info("Successfully clicked Easy Apply button and modal appeared")
                            
                            # Handle the application process
                            if self.handle_easy_apply_process():
                                time.sleep(2)
                                return True
                            break
                except Exception as e:
                    logger.debug(f"Button not found with selector {selector}: {str(e)}")
                    continue
            
            logger.info("No enabled Easy Apply button found or failed to click it")
            return False
            
        except Exception as e:
            logger.error(f"Error applying to job: {str(e)}")
            if self.db_manager:
                self.db_manager.log_application(
                    job_id=job_data.get('id', ''),
                    status="ERROR",
                    job_data=job_data,
                    error=str(e)
                )
            return False

    def fill_application_form(self):
        """Fill out the application form"""
        try:
            # Wait for form to load
            time.sleep(3)
            
            while True:
                try:
                    # Look for form fields
                    form_fields = self.driver.find_elements(By.CSS_SELECTOR, 
                        "input[type], select, textarea, div[role='textbox']")
                    
                    if not form_fields:
                        break
                    
                    # Process each field
                    for field in form_fields:
                        try:
                            # Get field properties
                            field_type = field.get_attribute('type') or field.tag_name
                            field_label = self._get_field_label(field)
                            
                            # Get options for select fields
                            options = None
                            if field_type == 'select':
                                options = [opt.text for opt in field.find_elements(By.TAG_NAME, 'option')]
                            
                            # Get AI suggestion for field value
                            value = self.ai_assistant.get_form_field_value(field_label, field_type, options)
                            
                            if value and value != 'SKIP':
                                # Fill in the field
                                if field_type == 'select':
                                    select = Select(field)
                                    try:
                                        select.select_by_visible_text(value)
                                    except:
                                        select.select_by_index(0)  # Default to first option
                                else:
                                    # Clear and fill text fields
                                    field.clear()
                                    field.send_keys(value)
                                
                                logger.info(f"Filled field '{field_label}' with '{value}'")
                                time.sleep(1)  # Short wait between fields
                            
                        except Exception as e:
                            logger.debug(f"Error filling field: {str(e)}")
                            continue
                    
                    # Look for screening questions
                    questions = self.driver.find_elements(By.CSS_SELECTOR,
                        "div.jobs-easy-apply-form-section__grouping")
                    
                    for question in questions:
                        try:
                            question_text = question.find_element(By.CSS_SELECTOR, 
                                "label, span.jobs-easy-apply-form-element__label").text
                            
                            # Get options if multiple choice
                            options = None
                            try:
                                options = [opt.text for opt in question.find_elements(By.CSS_SELECTOR,
                                    "input[type='radio'] + label, select option")]
                            except:
                                pass
                            
                            # Get AI answer
                            answer = self.ai_assistant.handle_screening_question(question_text, options)
                            
                            if answer and answer != 'SKIP':
                                # Find input field
                                input_field = question.find_element(By.CSS_SELECTOR,
                                    "input[type='text'], textarea, select, input[type='radio']")
                                
                                # Fill in the answer
                                if input_field.get_attribute('type') == 'radio':
                                    # Find radio button with matching label
                                    radio_buttons = question.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                                    for radio in radio_buttons:
                                        label = radio.find_element(By.XPATH, "following-sibling::label").text
                                        if label.lower() == answer.lower():
                                            radio.click()
                                            break
                                else:
                                    input_field.clear()
                                    input_field.send_keys(answer)
                                
                                logger.info(f"Answered question '{question_text}' with '{answer}'")
                                time.sleep(1)
                            
                        except Exception as e:
                            logger.debug(f"Error handling question: {str(e)}")
                            continue
                    
                    # Look for next/submit button
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, 
                        "button[aria-label*='Submit'], button[aria-label*='Next'], button[aria-label*='Review']")
                    
                    if not buttons:
                        break
                        
                    for button in buttons:
                        if button.is_enabled():
                            button.click()
                            time.sleep(3)  # Wait after button click
                            break
                            
                except Exception as e:
                    logger.debug(f"Error in form filling loop: {str(e)}")
                    break
            
            # Check for success indicators
            time.sleep(3)  # Wait before checking success
            success_indicators = [
                "//span[contains(text(), 'Application sent')]",
                "//span[contains(text(), 'Done')]",
                "//div[contains(text(), 'successfully submitted')]"
            ]
            
            for indicator in success_indicators:
                if len(self.driver.find_elements(By.XPATH, indicator)) > 0:
                    logger.info("Application submitted successfully")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error filling application form: {str(e)}")
            return False
            
    def _get_field_label(self, field):
        """Get the label text for a form field"""
        try:
            # Try to find label by for attribute
            field_id = field.get_attribute('id')
            if field_id:
                label = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{field_id}']")
                return label.text.strip()
            
            # Try to find label in parent elements
            parent = field.find_element(By.XPATH, ".//ancestor::div[contains(@class, 'form-group')]")
            label = parent.find_element(By.TAG_NAME, 'label')
            return label.text.strip()
            
        except:
            # Return placeholder or name if label not found
            return field.get_attribute('placeholder') or field.get_attribute('name') or ''

    def click_next_or_submit(self):
        """Click Next or Submit button"""
        try:
            # Look for Next or Submit button
            button_selectors = [
                "button[aria-label='Submit application']",
                "button[aria-label='Continue to next step']",
                "button[aria-label='Review your application']",
                "button[type='submit']"
            ]
            
            for selector in button_selectors:
                try:
                    button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if button.is_enabled():
                        button.click()
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error clicking next/submit: {str(e)}")
            return False

    def check_application_completed(self):
        """Check if application is completed"""
        try:
            success_indicators = [
                "//div[contains(text(), 'Application submitted')]",
                "//span[contains(text(), 'Applied')]",
                "//h3[contains(text(), 'Application submitted')]",
                "//span[contains(text(), 'Done')]"
            ]
            
            return any(len(self.driver.find_elements(By.XPATH, indicator)) > 0 
                      for indicator in success_indicators)
            
        except Exception as e:
            logger.error(f"Error checking application completion: {str(e)}")
            return False

    def handle_easy_apply_process(self):
        """Handle the Easy Apply process after clicking the button"""
        try:
            # Wait for the modal to appear and any loading to finish
            self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div[data-test-modal-id='easy-apply-modal']")))
            time.sleep(2)  # Wait for modal to fully load
            
            while True:  # Loop through all steps
                # Wait for any loading to finish
                self.wait_for_loading_modal()
                time.sleep(1)  # Extra wait to ensure form is loaded
                
                # First try to find Submit Application button
                try:
                    submit_buttons = self.driver.find_elements(By.CSS_SELECTOR, 
                        "button[aria-label='Submit application'], " + 
                        "button[type='submit']")
                    
                    for button in submit_buttons:
                        if button.is_displayed() and button.is_enabled() and (
                            "submit" in button.text.lower() or 
                            "submit" in button.get_attribute("aria-label").lower()):
                            logger.info("Found Submit Application button")
                            
                            # Try to click the submit button
                            try:
                                self.driver.execute_script("arguments[0].click();", button)
                            except:
                                button.click()
                            
                            time.sleep(2)  # Wait after submit
                            
                            # Check for success modal
                            try:
                                success = self.wait.until(EC.presence_of_element_located(
                                    (By.XPATH, "//*[contains(text(), 'application was sent')]")))
                                if success:
                                    logger.info("Application submitted successfully")
                                    return True
                            except:
                                logger.warning("No success message found after submit")
                            
                            return False
                    
                except Exception as e:
                    logger.debug(f"Submit button not found: {str(e)}")
                
                # If no Submit button, look for Next button
                try:
                    next_buttons = self.driver.find_elements(By.CSS_SELECTOR,
                        "button[aria-label*='Continue to next step'], " +
                        "button[aria-label*='Next'], " +
                        "button[type='button']")
                    
                    for button in next_buttons:
                        if button.is_displayed() and button.is_enabled() and (
                            "next" in button.text.lower() or 
                            "continue" in button.text.lower() or
                            "next" in button.get_attribute("aria-label").lower()):
                            
                            logger.info("Found Next button, continuing to next step")
                            
                            # Try to click the next button
                            try:
                                self.driver.execute_script("arguments[0].click();", button)
                            except:
                                button.click()
                            
                            time.sleep(2)  # Wait after clicking next
                            continue  # Go to next step
                            
                except Exception as e:
                    logger.debug(f"Next button not found: {str(e)}")
                
                # If we get here, we couldn't find either button
                logger.warning("Could not find Submit or Next button")
                return False
                
        except Exception as e:
            logger.error(f"Error in Easy Apply process: {str(e)}")
            return False
