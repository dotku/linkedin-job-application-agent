from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import platform
import subprocess

from utils.logger import setup_logger

logger = setup_logger(__name__, "chrome_setup")

class ChromeSetup:
    @staticmethod
    def get_chrome_version():
        """Get Chrome version on Mac"""
        try:
            if platform.system() == "Darwin":  # macOS
                cmd = ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--version']
                version = subprocess.check_output(cmd).decode('utf-8').strip()
                logger.info(f"Chrome version: {version}")
                return version.split()[-1]  # Returns just the version number
        except Exception as e:
            logger.warning(f"Could not get Chrome version: {str(e)}")
            return None

    def initialize_driver(self, headless=False):
        """Initialize Chrome WebDriver with options"""
        try:
            chrome_options = Options()
            
            # Add headless mode if specified
            if headless:
                chrome_options.add_argument('--headless=new')  # Updated headless syntax
            
            # Common options
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-notifications')
            chrome_options.add_argument('--start-maximized')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
            
            # Initialize driver with options
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            logger.info("Chrome WebDriver initialized successfully")
            return driver
            
        except Exception as e:
            logger.error(f"Failed to initialize Chrome WebDriver: {str(e)}")
            return None
