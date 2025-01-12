import sys
from selenium.common.exceptions import WebDriverException
from utils.logger import setup_logger

logger = setup_logger(__name__, "browser")

def check_browser_open(driver):
    """Check if browser is still open"""
    try:
        # Try to get current url - will fail if browser is closed
        driver.current_url
        return True
    except WebDriverException:
        logger.error("Browser was closed by user")
        cleanup_driver(driver)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error checking browser status: {str(e)}")
        cleanup_driver(driver)
        sys.exit(1)
    return False

def cleanup_driver(driver):
    """Clean up driver resources"""
    if driver:
        try:
            driver.quit()
        except:
            pass
