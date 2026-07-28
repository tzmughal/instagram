import logging
import time
import json
import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from instagram_common import load_cookies_from_config

logging.basicConfig(
    filename=os.path.join(SCRIPT_DIR, 'instagram_unfollow_log.txt'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def load_config():
    config_path = os.path.join(SCRIPT_DIR, "config.json")
    if not os.path.exists(config_path):
        config_path = os.path.join(PROJECT_ROOT, "config.json")
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

cookie_config_path = os.path.join(SCRIPT_DIR, "config.json")
cookies = load_cookies_from_config(cookie_config_path)
if not cookies:
    raise RuntimeError("No cookies were found in config.json. Add a 'cookies' object or paste cookie data first.")

chrome_options = Options()
chrome_options.add_argument("--disable-infobars")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--start-maximized")

try:
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
except Exception as first_error:
    if os.path.exists(webdriver_path):
        service = Service(webdriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
    else:
        raise RuntimeError(f"Failed to start Chrome browser: {first_error}") from first_error

wait = WebDriverWait(driver, 5)

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

    usernames_path = os.path.join(SCRIPT_DIR, 'a.txt')
    with open(usernames_path, 'r') as file:
        usernames = file.read().splitlines()

    count = 0
    for username in usernames:
        if count >= 1000:
            logging.info("Reached 1000 accounts. Ending script.")
            break

        profile_url = f'https://www.instagram.com/{username}/'
        logging.info(f"Opening profile: {profile_url}")
        driver.get(profile_url)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))

        try:
            unfollow_status = wait.until(EC.presence_of_element_located((By.XPATH, '//div[text()="Following"]')))
            if unfollow_status:
                logging.info(f"You are following {username}. Proceeding to unfollow...")
                unfollow_status.click()
                logging.info("Confirming unfollow...")
                confirm_button = wait.until(EC.element_to_be_clickable((
                    By.XPATH, '//div[contains(@class, "x9f619")]//span[text()="Unfollow"]'
                )))
                confirm_button.click()
                logging.info(f"Unfollowed user: {username}")
        except Exception as e:
            logging.error(f"Error processing {username}. Skipping unfollow. {e}")

        count += 1
        if count > 0 and count % 500 == 0:
            logging.info(f"Processed {count} users. Waiting for 5 minutes...")
            time.sleep(300)

finally:
    logging.info("Closing the browser...")
    driver.quit()
