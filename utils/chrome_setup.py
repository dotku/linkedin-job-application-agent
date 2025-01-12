from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from utils.logger import logger

class ChromeSetup:
    @staticmethod
    def initialize_driver():
        """Initialize and configure Chrome WebDriver"""
        try:
            logger.info("Setting up Chrome WebDriver...")
            
            # Initialize Chrome options
            chrome_options = Options()
            
            # Set basic Chrome options
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            
            # Initialize driver
            service = Service()
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.implicitly_wait(10)
            
            logger.info("Chrome WebDriver setup successful")
            return driver
            
        except Exception as e:
            logger.error(f"Failed to setup Chrome WebDriver: {str(e)}")
            raise
