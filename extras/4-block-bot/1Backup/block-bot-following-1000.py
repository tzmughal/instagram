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
    filename=os.path.join(SCRIPT_DIR, 'instagram_block_log.txt'),
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load configuration from config.json
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

# Define your cookies
cookies = {
    'csrftoken': 'bzXQYbM59GE3iU-21aWxjS',
    'datr': 'jPRdZxXkVKx3kAGxiXG78MOL',
    'dpr': '1.5',
    'ds_user_id': '8125093404',
    'ig_did': '2D446FDC-6CD9-40CD-A162-6E52C07FEA44',
    'mid': 'Z130jAALAAEb2h3xCV196YZHAsfw',
    'ps_l': '1',
    'ps_n': '1',
    'rur': '"CLN\\0548125093404\\0541765797878:01f767191893c8f3a37059a868f1f4b261ec9b42b3aadefd0d7a0ba8791b0ebc29ad97ba"',
    'sessionid': '8125093404%3AIiuL0U0hdwiLWM%3A10%3AAYf68jARqPN_N9fu1aJrXS-ybtqSMS-Z-wD4ZJ-gUQ',
    'wd': '723x644'
}

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

    # Read usernames from file
    usernames_path = os.path.join(SCRIPT_DIR, "Accounts Not Following back.txt")
    with open(usernames_path, 'r') as file:
        usernames = file.read().splitlines()

    count = 0  # Counter for processed users

    for username in usernames:
        if count >= 1000:  # Stop after processing 1000 users
            logging.info("Reached 1000 accounts. Ending script.")
            break

        profile_url = f'https://www.instagram.com/{username}/'
        logging.info(f"Opening profile: {profile_url}")
        driver.get(profile_url)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))

        try:
            # Check if the user is following you by looking for "Following" status
            follow_status = wait.until(EC.presence_of_element_located((By.XPATH, '//div[text()="Following"]')))
            if follow_status:
                logging.info(f"{username} is following you. Proceeding to block...")

                # Click on the options menu (three dots)
                logging.info("Clicking on the three dots (options menu)...")
                svg_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'svg[aria-label="Options"]')))
                svg_element.click()

                # Click the 'Block' button
                logging.info("Clicking 'Block'...")
                block_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[text()="Block"]')))
                block_button.click()

                # Wait for the block confirmation dialog and click "Block" inside it
                div_element = wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.x78zum5.xdt5ytf.x1crbq5u.xvrdyt3.x179zr98")))
                block_button = div_element.find_element(By.XPATH, ".//button[contains(text(), 'Block')]")
                block_button.click()

                logging.info(f"Blocked user: {username}")

        except Exception as e:
            logging.error(f"Error processing {username}. Skipping block. {e}")

        count += 1

        # Wait for 5 minutes after every 500 users processed
        if count > 0 and count % 500 == 0:
            logging.info(f"Processed {count} users. Waiting for 5 minutes...")
            time.sleep(300)  # Wait 300 seconds (5 minutes)

finally:
    logging.info("Closing the browser...")
    driver.quit()
