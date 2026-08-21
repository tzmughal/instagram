import csv
import json
import logging
import os
import sys
import time
from datetime import datetime

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from instagram_common import load_cookies_from_config


# main-v5.py replaces this line in the copy it creates for each account.
USERNAMES_FILENAME = "not_following_back-high.octvne.txt"
RECORD_FILENAME = "unfollow_record.csv"
RECORD_FIELDNAMES = ["timestamp", "username", "status", "detail"]
MAX_USERS_PER_RUN = 1000

# Entries in these states are intentionally offered by menu option 3. They
# need another look because Instagram did not give the script a reliable
# confirmation that the account was already unfollowed.
RETRYABLE_STATUSES = {"not_found", "following_not_visible", "error"}

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def load_config():
    config_path = os.path.join(SCRIPT_DIR, "config.json")
    if not os.path.exists(config_path):
        config_path = os.path.join(PROJECT_ROOT, "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as config_file:
            return json.load(config_file)
    except Exception as error:
        raise RuntimeError(f"Error loading configuration file: {error}") from error


def record_path():
    return os.path.join(SCRIPT_DIR, RECORD_FILENAME)


def load_record():
    """Return the latest status recorded for each username."""
    latest = {}
    path = record_path()
    if not os.path.exists(path):
        return latest

    with open(path, "r", newline="", encoding="utf-8") as record_file:
        for row in csv.DictReader(record_file):
            username = (row.get("username") or "").strip()
            status = (row.get("status") or "").strip()
            if username and status:
                latest[username] = status
    return latest


def append_record(username, status, detail=""):
    """Save each result immediately, so Ctrl+C or a crash loses no progress."""
    path = record_path()
    new_file = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as record_file:
        writer = csv.DictWriter(record_file, fieldnames=RECORD_FIELDNAMES)
        if new_file:
            writer.writeheader()
        writer.writerow({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "username": username,
            "status": status,
            "detail": detail,
        })
        record_file.flush()


def load_usernames():
    usernames_path = os.path.join(SCRIPT_DIR, USERNAMES_FILENAME)
    if not os.path.exists(usernames_path):
        raise FileNotFoundError(f"Username file not found: {usernames_path}")
    with open(usernames_path, "r", encoding="utf-8") as usernames_file:
        usernames = [line.strip() for line in usernames_file if line.strip()]
    return list(dict.fromkeys(usernames))


def prompt_run_mode():
    print("How would you like to run the unfollow bot?")
    print(f"  1) Continue          -- skip usernames already in {RECORD_FILENAME}")
    print(f"  2) Start from scratch -- erase {RECORD_FILENAME} and process the full list")
    print("  3) Retry problems    -- retry only not found, missing Following button, or error entries")
    while True:
        choice = input("Enter 1, 2, or 3: ").strip()
        if choice in {"1", "2", "3"}:
            return choice
        print("Invalid input. Please enter 1, 2, or 3.")


def build_tasks(usernames, choice, record):
    if choice == "1":
        return [username for username in usernames if username not in record]
    if choice == "2":
        return usernames
    return [username for username in usernames if record.get(username) in RETRYABLE_STATUSES]


def login_using_cookies(driver, wait, cookies):
    logging.info("Opening Instagram...")
    driver.get("https://www.instagram.com/")
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))

    logging.info("Adding cookies...")
    for name, value in cookies.items():
        driver.add_cookie({"name": name, "value": value, "domain": ".instagram.com", "path": "/"})

    driver.refresh()
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))


def profile_is_not_found(driver):
    page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
    return "sorry, this page isn't available" in page_text or "page isn't available" in page_text


def process_username(driver, wait, username):
    """Unfollow one username and return (status, detail) for the CSV."""
    try:
        driver.get(f"https://www.instagram.com/{username}/")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))

        try:
            following_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//div[normalize-space(text())="Following"]'))
            )
        except TimeoutException:
            if profile_is_not_found(driver):
                return "not_found", "Instagram reported that this profile is unavailable."
            if driver.find_elements(By.XPATH, '//*[normalize-space(text())="Follow"]'):
                return "already_unfollowed", "Instagram shows Follow rather than Following."
            # This is deliberately separate from already_unfollowed: Instagram
            # can hide the button for several reasons, so it is safe to retry.
            return "following_not_visible", "Could not find a visible Following button."

        following_button.click()
        confirm_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((
            By.XPATH, '//div[contains(@class, "x9f619")]//span[normalize-space(text())="Unfollow"]'
        )))
        confirm_button.click()
        return "unfollowed", "Unfollow confirmation clicked."
    except TimeoutException as error:
        return "error", f"Timed out: {error}"
    except WebDriverException as error:
        return "error", f"Browser error: {error}"
    except Exception as error:
        return "error", f"Unexpected error: {error}"


def main():
    config = load_config()
    webdriver_path = config.get("webdriver_path")
    if not webdriver_path:
        raise RuntimeError("Missing 'webdriver_path' in config.json.")
    if not os.path.isabs(webdriver_path):
        webdriver_path = os.path.join(PROJECT_ROOT, webdriver_path)

    cookies = load_cookies_from_config(os.path.join(SCRIPT_DIR, "config.json"))
    if not cookies:
        raise RuntimeError("No cookies were found in config.json.")

    try:
        usernames = load_usernames()
    except FileNotFoundError as error:
        print(f"Error: {error}")
        return

    choice = prompt_run_mode()
    record = load_record()
    if choice == "2" and os.path.exists(record_path()):
        os.remove(record_path())
        record = {}
        print(f"Deleted {RECORD_FILENAME}; starting from scratch.")

    tasks = build_tasks(usernames, choice, record)
    if choice == "3" and not tasks:
        print("No retryable usernames are recorded yet.")
        return
    if not tasks:
        print("Nothing to do.")
        return
    if len(tasks) > MAX_USERS_PER_RUN:
        print(f"Limiting this run to the first {MAX_USERS_PER_RUN} usernames.")
        tasks = tasks[:MAX_USERS_PER_RUN]
    print(f"{len(tasks)} username(s) to process.\n")

    options = Options()
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(webdriver_path), options=options)
    wait = WebDriverWait(driver, 10)

    try:
        login_using_cookies(driver, wait, cookies)
        for count, username in enumerate(tasks, start=1):
            status, detail = process_username(driver, wait, username)
            append_record(username, status, detail)
            print(f"[{count}/{len(tasks)}] {username}: {status}")
            logging.info("%s: %s (%s)", username, status, detail)

            if count % 500 == 0 and count < len(tasks):
                logging.info("Processed 500 users. Waiting for 5 minutes...")
                time.sleep(300)
    finally:
        logging.info("Closing the browser...")
        driver.quit()


if __name__ == "__main__":
    main()
