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

# Load configuration for webdriver_path
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

# Configure logging
logging.basicConfig(
    filename=os.path.join(SCRIPT_DIR, 'instagram_block_log.txt'),
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Initialize Chrome options
chrome_options = Options()
chrome_options.add_argument("--disable-infobars")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--start-maximized")

# Initialize the WebDriver using the path from config.json
service = Service(webdriver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)

# WebDriverWait configuration
wait = WebDriverWait(driver, 5)

# Define your cookies (hard-coded for now)
cookies = {
    'csrftoken': 'cFDhn3AnyXmhAqc56Q1riitfb4xmaCU8',
    'datr': 'OOJZZ_S8HQTtikbXG5Nwvzt7',
    'dpr': '1.5',
    'ds_user_id': '5609445717',
    'ig_did': 'B12EE7C7-C69E-40FD-9669-F7CC5D1380BD',
    'ig_nrcb': '1',
    'mid': 'Z1niOAALAAHAYIemxy_g3bMfFpue',
    'ps_l': '1',
    'ps_n': '1',
    'rur': '"FRC\\0545609445717\\0541765735437:01f71358b2f80527d95fb7b45393404149af4798a283a996802ec85e16b14970226fd63d"',
    'sessionid': '5609445717%3AxzvKGDat4CyEcq%3A15%3AAYc6QmILdOBHqB6Bv6OlS7p_-mxzy3gh7YnBXYDHuQ',
    'wd': '721x594'
}

try:
    logging.info("Opening Instagram...")
    driver.get('https://www.instagram.com/')
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))

    logging.info("Adding cookies...")
    for cookie_name, cookie_value in cookies.items():
        driver.add_cookie({'name': cookie_name, 'value': cookie_value})

    logging.info("Refreshing page to apply cookies...")
    driver.refresh()
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))

    # Read usernames from file
    usernames_path = os.path.join(SCRIPT_DIR, 'suspicious-accounts-immortalconcepts.txt')
    with open(usernames_path, 'r') as file:
        usernames = file.read().splitlines()

    count = 0  # Counter for processed users

    for username in usernames:
        if count >= 800:
            logging.info("Reached 1000 accounts. Ending script.")
            break

        profile_url = f'https://www.instagram.com/{username}/'
        logging.info(f"Opening profile: {profile_url}")
        driver.get(profile_url)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))

        try:
            # Check if the user is following you
            follow_status = wait.until(EC.presence_of_element_located((By.XPATH, '//div[text()="Follow Back"]')))
            if follow_status:
                logging.info(f"{username} is following you. Proceeding to block...")

                # Proceed to block the user
                logging.info("Clicking on the three dots (options menu)...")
                svg_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'svg[aria-label="Options"]')))
                svg_element.click()

                # Wait for the options menu and click "Block"
                logging.info("Clicking 'Block'...")
                block_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[text()="Block"]')))
                block_button.click()

                # Wait for the confirmation dialog and click "Block" within it
                div_element = wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.x78zum5.xdt5ytf.x1crbq5u.xvrdyt3.x179zr98")))
                block_button = div_element.find_element(By.XPATH, ".//button[contains(text(), 'Block')]")
                block_button.click()

                logging.info(f"Blocked user: {username}")

        except Exception as e:
            logging.error(f"Error processing {username}. Skipping block. {e}")

        count += 1

        # Wait after every 500 users (avoid wait on count=0)
        if count > 0 and count % 400 == 0:
            logging.info(f"Processed {count} users. Waiting for 5 minutes...")
            time.sleep(300)  # Wait 5 minutes

        # Add a small delay between processing each profile
        time.sleep(2)

finally:
    logging.info("Closing the browser...")
    driver.quit()
