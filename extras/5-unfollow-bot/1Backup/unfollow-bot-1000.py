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
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

# Configure logging
logging.basicConfig(
    filename=os.path.join(SCRIPT_DIR, 'instagram_unfollow_log.txt'),
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load configuration from config.json to get the WebDriver path
def load_config():
    config_path = os.path.join(SCRIPT_DIR, "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading configuration file: {e}")
        exit(1)

config = load_config()
webdriver_path = config.get("webdriver_path")
if not webdriver_path:
    print("Missing 'webdriver_path' in config.json.")
    exit(1)
if not os.path.isabs(webdriver_path):
    webdriver_path = os.path.join(PROJECT_ROOT, webdriver_path)

# Define your cookies (hard-coded for now)
cookies = {
    'csrftoken': 'pypsllVa3avSDoU2uCyYmJICUcDmLThk',
    'datr': 'oCloZ7KqR9j-E9dZrGFANv9j',
    'dpr': '1.5',
    'ds_user_id': '53540114923',
    'ig_did': '8E19E03E-6B47-4820-9036-7E5A716BF635',
    'ig_nrcb': '1',
    'mid': 'Z2gpoAALAAHZ6XgtvVvhbEadJJXh',
    'rur': '"LDC\\05453540114923\\0541766416136:01f737b7e722fbf818d6aac2e25e7705b44e8eb0ad16dfbaae11b528f5052038f39639ec"',
    'sessionid': '53540114923%3AgEEAl7YpBE7xmf%3A4%3AAYdXNAADY18MTcCFVjbUmsyCctj2D6iOJFpO5uTs9g',
    'wd': '721x594'
}

# Initialize Chrome options
chrome_options = Options()
chrome_options.add_argument("--disable-infobars")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--start-maximized")

# Initialize the WebDriver using Selenium Manager first, then fall back to the configured path.
try:
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
except Exception as first_error:
    if os.path.exists(webdriver_path):
        service = Service(webdriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
    else:
        raise RuntimeError(f"Failed to start Chrome browser: {first_error}") from first_error

# WebDriverWait configuration
wait = WebDriverWait(driver, 5)

try:
    # Open Instagram
    logging.info("Opening Instagram...")
    driver.get('https://www.instagram.com/')
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))

    # Add cookies
    logging.info("Adding cookies...")
    for cookie_name, cookie_value in cookies.items():
        driver.add_cookie({'name': cookie_name, 'value': cookie_value})

    logging.info("Refreshing page to apply cookies...")
    driver.refresh()
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))

    # Read usernames from file (the list of accounts you are following that you want to unfollow)
    usernames_path = os.path.join(SCRIPT_DIR, 'a.txt')
    with open(usernames_path, 'r') as file:
        usernames = file.read().splitlines()

    count = 0  # Counter for processed users

    for username in usernames:
        if count >= 1000:  # Stop processing after 1000 users
            logging.info("Reached 1000 accounts. Ending script.")
            break

        profile_url = f'https://www.instagram.com/{username}/'
        logging.info(f"Opening profile: {profile_url}")
        driver.get(profile_url)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))

        try:
            # Check if you are following the user by looking for the "Following" element
            unfollow_status = wait.until(EC.presence_of_element_located((By.XPATH, '//div[text()="Following"]')))
            if unfollow_status:
                logging.info(f"You are following {username}. Proceeding to unfollow...")

                # Click the "Following" button to trigger the unfollow dialog
                unfollow_status.click()

                # Wait for the unfollow confirmation dialog and click "Unfollow"
                logging.info("Confirming unfollow...")
                confirm_button = wait.until(EC.element_to_be_clickable((
                    By.XPATH, '//div[contains(@class, "x9f619")]//span[text()="Unfollow"]'
                )))
                confirm_button.click()

                logging.info(f"Unfollowed user: {username}")

        except Exception as e:
            logging.error(f"Error processing {username}. Skipping unfollow. {e}")

        count += 1  # Increment the counter

        # Wait for 5 minutes after every 500 users processed
        if count > 0 and count % 500 == 0:
            logging.info(f"Processed {count} users. Waiting for 5 minutes...")
            time.sleep(300)  # Wait for 300 seconds (5 minutes)

finally:
    logging.info("Closing the browser...")
    driver.quit()
