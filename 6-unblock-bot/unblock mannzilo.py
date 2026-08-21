import logging
import time
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

# Load config
def load_config():
    config_path = os.path.join(SCRIPT_DIR, "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        exit(1)

config = load_config()
webdriver_path = config.get("webdriver_path")
if not webdriver_path:
    print("Missing 'webdriver_path' in config.json.")
    exit(1)
if not os.path.isabs(webdriver_path):
    webdriver_path = os.path.join(PROJECT_ROOT, webdriver_path)

# Logging
logging.basicConfig(
    filename=os.path.join(SCRIPT_DIR, 'instagram_unblock_log.txt'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Edge options
chrome_options = Options()
chrome_options.add_argument("--disable-infobars")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--start-maximized")

# Initialize WebDriver
service = Service(webdriver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)
wait = WebDriverWait(driver, 10)

# Define your cookies (hard-coded for now)
cookies = {
    'csrftoken": "YOUR_CSRF_TOKEN",
    'datr': '_b88aTaGhhYILPAFvA9WN-2l',
    'dpr': '1.5',
    'ds_user_id": "YOUR_USER_ID",
    'ig_did': 'DDDA2325-7042-4C2F-86F1-BEDD3DD6E4A4',
    'mid': 'aTy__gALAAGAN8Cjant3McTYAZEP',
    'ps_l': '1',
    'ps_n': '1',
    'rur': '"EAG\\05438060280664\\0541797181099:01feaf9ac2aa3a2cdc3ab89dc62f92757033f1a79b14bf7349f4bdc12ecaffbc7120672a"',
    'sessionid": "YOUR_SESSION_ID",
    'wd': '717x588'
}



try:
    logging.info("Opening Instagram...")
    driver.get("https://www.instagram.com/")
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    # Add cookies
    for name, value in cookies.items():
        driver.add_cookie({'name': name, 'value': value})

    logging.info("Cookies added, refreshing...")
    driver.refresh()
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    # Navigate to blocked accounts page
    logging.info("Navigating to blocked accounts page...")
    driver.get("https://www.instagram.com/accounts/blocked_accounts/")
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    time.sleep(15)  # Give time for the blocked list to load

    count = 0
    while True:
        try:
            # Find all visible "Unblock" buttons
            unblock_buttons = driver.find_elements(By.XPATH, '//span[text()="Unblock"]')

            if not unblock_buttons:
                logging.info("No more accounts to unblock.")
                break

            for button in unblock_buttons:
                try:
                    driver.execute_script("arguments[0].scrollIntoView(true);", button)
                    button.click()
                    logging.info("Clicked initial 'Unblock'")

                    # Wait for confirmation div to appear and click it
                    confirm_div = wait.until(EC.element_to_be_clickable(
                        (By.XPATH, '//div[text()="Unblock"]')))
                    confirm_div.click()
                    logging.info("Clicked confirmation 'Unblock'")

                    count += 1
                    time.sleep(2)  # Delay between each unblock
                except Exception as e:
                    logging.warning(f"Failed to unblock one account: {e}")
                    continue

            # Scroll to load more users
            driver.execute_script("window.scrollBy(0, 600);")
            time.sleep(3)

        except Exception as e:
            logging.error(f"Error in main loop: {e}")
            break

    logging.info(f"Finished. Total accounts unblocked: {count}")

finally:
    logging.info("Closing browser...")
    driver.quit()
