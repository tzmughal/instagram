import json
import logging
import os
import sys
import time

from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from instagram_common import load_cookies_from_config


HIDE_STORY_URL = "https://www.instagram.com/accounts/hide_story_and_live_from/"
# This deliberately does not use the shared Settings sidebar's placeholder-only
# search input.  It targets the Bloks input used by this specific page.
HIDE_STORY_SEARCH_BOX = (
    By.CSS_SELECTOR,
     "input[placeholder='Search']",
)
TOGGLE_BUTTON_XPATH = ".//*[@role='button' and @aria-label='Toggle checkbox']"
MAX_RETRIES = 3


def load_config():
    """Load the existing local config, with the project's config as fallback."""
    config_path = os.path.join(SCRIPT_DIR, "config.json")
    if not os.path.exists(config_path):
        config_path = os.path.join(PROJECT_ROOT, "config.json")

    with open(config_path, "r", encoding="utf-8") as config_file:
        return json.load(config_file)


config = load_config()
webdriver_path = config["webdriver_path"]
if not os.path.isabs(webdriver_path):
    webdriver_path = os.path.join(PROJECT_ROOT, webdriver_path)

# Keep the existing cookie-loading mechanism and config location.
cookies = load_cookies_from_config(os.path.join(SCRIPT_DIR, "config.json"))
if not cookies:
    raise RuntimeError("Cookies not found in config.json")


logging.basicConfig(
    filename=os.path.join(SCRIPT_DIR, "instagram_hide_story_log.txt"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def xpath_literal(value):
    """Return an XPath string literal that is safe for usernames."""
    if "'" not in value:
        return "'%s'" % value
    if '"' not in value:
        return '"%s"' % value
    return "concat(%s)" % ", \"'\", ".join("'%s'" % part for part in value.split("'"))


def login_using_cookies(driver, wait):
    """Open Instagram, install the configured cookies, and load the target page."""
    logging.info("Opening Instagram...")
    driver.get("https://www.instagram.com/")
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    logging.info("Loading cookies...")
    for name, value in cookies.items():
        driver.add_cookie({
            "name": name,
            "value": value,
            "domain": ".instagram.com",
            "path": "/",
        })

    driver.get(HIDE_STORY_URL)
    find_hide_story_search_box(wait)


def find_hide_story_search_box(wait):
    """Return the second Search input (Hide Story search box)."""

    def _find(driver):
        boxes = driver.find_elements(By.CSS_SELECTOR, "input[placeholder='Search']")

        # Wait until both search boxes exist
        if len(boxes) < 2:
            return False

        box = boxes[1]

        if box.is_displayed() and box.is_enabled():
            return box

        return False

    return wait.until(_find)


def search_box_value(driver):
    """Read the value from the page-specific search field without a nested wait."""
    return driver.find_element(*HIDE_STORY_SEARCH_BOX).get_attribute("value") or ""


def clear_search_box(wait):
    """Clear the current query reliably; Instagram does not always honor clear()."""
    search_box = find_hide_story_search_box(wait)
    search_box.click()
    search_box.send_keys(Keys.CONTROL, "a")
    search_box.send_keys(Keys.DELETE)
    wait.until(lambda driver: search_box_value(driver) == "")


def search_username(wait, username):
    """Clear the previous query and wait until the new query is in the Bloks input."""
    logging.info("Searching username: %s", username)
    clear_search_box(wait)
    search_box = find_hide_story_search_box(wait)
    search_box.send_keys(username)
    wait.until(lambda driver: username.lower() in search_box_value(driver).lower())


def find_user_row(driver, username):
    """Find the row containing the username and its checkbox."""

    username_xpath = f"//span[normalize-space(text())='{username}']"

    try:
        username_span = driver.find_element(By.XPATH, username_xpath)

        # Find the nearest row containing the checkbox
        row = username_span.find_element(
            By.XPATH,
            "./ancestor::div[.//*[@aria-label='Toggle checkbox']][1]"
        )

        toggle = row.find_element(
            By.XPATH,
            ".//*[@aria-label='Toggle checkbox']"
        )

        return row, toggle

    except NoSuchElementException:
        return False


def wait_for_user_result(driver, wait, username):
    """Wait for Instagram's asynchronously refreshed search result."""
    try:
        row, toggle = wait.until(lambda current_driver: find_user_row(current_driver, username))
        logging.info("Found result: %s", username)
        return row, toggle
    except TimeoutException:
        logging.warning("User not found: %s", username)
        return None, None


def click_checkbox(driver, row, toggle):
    """Click the row first, then the toggle, then JavaScript as a fallback."""

    driver.execute_script(
        "arguments[0].scrollIntoView({block: 'center'});",
        row
    )

    time.sleep(0.3)

    # First try clicking the entire row
    try:
        row.click()
        return
    except (ElementClickInterceptedException,
            ElementNotInteractableException,
            WebDriverException):
        logging.info("Row click failed; trying toggle.")

    # Then try clicking the toggle
    try:
        toggle.click()
        return
    except (ElementClickInterceptedException,
            ElementNotInteractableException,
            WebDriverException):
        logging.info("Toggle click failed; trying ActionChains.")

    # Then ActionChains on the row
    try:
        ActionChains(driver).move_to_element(row).click().perform()
        return
    except (ElementClickInterceptedException,
            ElementNotInteractableException,
            WebDriverException):
        logging.info("ActionChains failed; trying JavaScript.")

    # Final fallback: JavaScript click on the row
    driver.execute_script("arguments[0].click();", row)

def hide_user(driver, wait, username):
    """Search for one username and toggle its Hide story checkbox exactly once."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            search_username(wait, username)
            row, toggle = wait_for_user_result(driver, wait, username)
            if toggle is None:
                return False

            click_checkbox(driver, row, toggle)
            logging.info("Clicked checkbox: %s", username)
            # Let Instagram finish its selection animation before clearing the
            # query and searching for the next username.
            time.sleep(2)
            return True
        except StaleElementReferenceException:
            if attempt < MAX_RETRIES:
                logging.warning("Stale element for %s. Retrying... (%s/%s)", username, attempt, MAX_RETRIES)
                continue
            logging.error("Finished retries after stale element: %s", username)
        except TimeoutException:
            if attempt < MAX_RETRIES:
                logging.warning("Timed out processing %s. Retrying... (%s/%s)", username, attempt, MAX_RETRIES)
                continue
            logging.error("Finished retries after timeout: %s", username)
        except WebDriverException as error:
            if attempt < MAX_RETRIES:
                logging.warning("WebDriver error for %s (%s). Retrying... (%s/%s)", username, error, attempt, MAX_RETRIES)
                continue
            logging.error("Could not process %s after retries: %s", username, error)
    return False


def load_usernames():
    usernames_path = os.path.join(SCRIPT_DIR, "hide_from_story_usernames.txt")
    with open(usernames_path, "r", encoding="utf-8") as usernames_file:
        return [username.strip() for username in usernames_file if username.strip()]


def main():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")

    driver = webdriver.Chrome(service=Service(webdriver_path), options=options)
    wait = WebDriverWait(driver, 20, ignored_exceptions=(StaleElementReferenceException,))
    processed = 0

    try:
        login_using_cookies(driver, wait)

        for username in load_usernames():
            hide_user(driver, wait, username)
            processed += 1
            logging.info("Finished user: %s", username)

            # Preserve the existing rate-limit pause while avoiding arbitrary
            # per-user sleeps; all UI synchronization above uses explicit waits.
            if processed % 400 == 0:
                logging.info("Processed 400 users. Sleeping 5 minutes...")
                time.sleep(300)
    finally:
        logging.info("Finished.")
        driver.quit()


if __name__ == "__main__":
    main()
