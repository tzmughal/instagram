import csv
import json
import logging
import os
import sys
import time
from datetime import datetime

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

# Predicate used both to find a row's toggle and to walk up from any element
# to its enclosing row (the row is the nearest ancestor <div> that contains a
# Toggle checkbox descendant).
TOGGLE_BUTTON_PREDICATE = ".//*[@role='button' and @aria-label='Toggle checkbox']"
ROW_ANCESTOR_XPATH = f"./ancestor::div[{TOGGLE_BUTTON_PREDICATE}][1]"

MAX_RETRIES = 3

# Mode 1/2 read every username from this single file.
HIDE_FROM_STORY_FILENAME = "hide_from_story_usernames.txt"
# Mode 3 (custom) reads two separate files instead.
CHECK_FILENAME = "check.txt"
UNCHECK_FILENAME = "uncheck.txt"

# Replaces the old plain-text log file. Records every username that has been
# successfully resolved (checked / unchecked / already-at-target) so reruns
# can skip straight past them instead of re-searching from the top. Delete
# this file (or a row in it) to have that username processed again.
RECORD_FILENAME = "hide_story_record.csv"
RECORD_FIELDNAMES = ["timestamp", "username", "target_state", "outcome"]


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
    stream=sys.stdout,
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


def prompt_mode():
    """Ask the user in the terminal which run mode to use.

    Returns "1", "2", or "3":
      "1" -- check all usernames in hide_from_story_usernames.txt
      "2" -- uncheck all usernames in hide_from_story_usernames.txt
      "3" -- custom: check everyone in check.txt, uncheck everyone in
             uncheck.txt

    Keeps asking until a valid choice is given.
    """
    print("What would you like to do?")
    print(f"  1) Check all   -- hide your story from every username in {HIDE_FROM_STORY_FILENAME}")
    print(f"  2) Uncheck all -- unhide your story from every username in {HIDE_FROM_STORY_FILENAME}")
    print(f"  3) Custom      -- check everyone in {CHECK_FILENAME}, uncheck everyone in {UNCHECK_FILENAME}")

    labels = {
        "1": "Check all",
        "2": "Uncheck all",
        "3": f"Custom ({CHECK_FILENAME} + {UNCHECK_FILENAME})",
    }

    while True:
        choice = input("Enter 1, 2 or 3: ").strip()
        if choice in labels:
            print(f"Selected: {labels[choice]}.\n")
            return choice
        print("Invalid input. Please enter 1, 2 or 3.")


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


def get_hide_story_search_box(driver):
    """Return the *live* Hide Story search input.

    ``input[placeholder='Search']`` matches THREE elements on this page:
    index 0 is the unrelated Settings sidebar search box (never typed into,
    always empty), and indices 1/2 are two copies of the Hide Story panel
    that Instagram keeps mounted simultaneously (presumably for its slide
    transition) -- one live, one a stale duplicate that still shows the full,
    unfiltered list. Index 1 is consistently the live one.
    """
    boxes = driver.find_elements(By.CSS_SELECTOR, "input[placeholder='Search']")
    if len(boxes) < 2:
        raise NoSuchElementException("Hide Story search box not present yet.")
    return boxes[1]


def find_hide_story_search_box(wait):
    """Wait until the live Hide Story search box is present and interactable."""

    def _find(driver):
        try:
            box = get_hide_story_search_box(driver)
        except NoSuchElementException:
            return False
        return box if box.is_displayed() and box.is_enabled() else False

    return wait.until(_find)


def find_hide_story_panel(driver):
    """Return the single panel that wraps both the live search box and its
    row list, so username/row lookups never cross into Instagram's other
    (stale) duplicate copy of this list, which still contains every
    username unfiltered.
    """
    search_box = get_hide_story_search_box(driver)
    return search_box.find_element(By.XPATH, ROW_ANCESTOR_XPATH)


def search_box_value(driver):
    """Read the value straight from the live Hide Story search box only."""
    return get_hide_story_search_box(driver).get_attribute("value") or ""


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
    """Find the row containing the username and its checkbox.

    Scoped to the live panel only (see find_hide_story_panel) -- a page-wide
    search would risk matching Instagram's stale duplicate panel instead.
    """
    try:
        panel = find_hide_story_panel(driver)
        username_xpath = f".//span[normalize-space(text())={xpath_literal(username)}]"
        username_span = panel.find_element(By.XPATH, username_xpath)
        row = username_span.find_element(By.XPATH, ROW_ANCESTOR_XPATH)
        toggle = row.find_element(By.XPATH, TOGGLE_BUTTON_PREDICATE)
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


def toggle_icon_style(toggle):
    """The small icon whose mask-image/background-color flips when checked."""
    icon = toggle.find_element(By.CSS_SELECTOR, "[data-bloks-name='ig.components.Icon']")
    return icon.get_attribute("style") or ""


def is_toggle_checked(toggle):
    return "circle-check" in toggle_icon_style(toggle)


def click_checkbox(driver, wait, username, row, toggle, target_checked):
    """Click the row -- the only element with pointer-events enabled, since
    the toggle icon itself (and everything else in the row) has
    pointer-events: none -- until the checkbox reaches ``target_checked``,
    rather than trusting a bare click() with no verification.

    Row/toggle are re-fetched fresh before each attempt so a re-render
    triggered by an earlier (possibly successful) attempt can't leave us
    clicking a stale element or, worse, double-toggling past the target
    state.
    """

    def state_reached(_):
        fresh = find_user_row(driver, username)
        if not fresh:
            return False
        _, fresh_toggle = fresh
        return is_toggle_checked(fresh_toggle) == target_checked

    methods = ("row click", "press and hold")
    current_row, current_toggle = row, toggle

    for method in methods:
        fresh = find_user_row(driver, username)
        if fresh:
            current_row, current_toggle = fresh

        # Already at the target state (e.g. reached by a previous attempt) --
        # nothing left to do, and clicking again would just toggle it away.
        if is_toggle_checked(current_toggle) == target_checked:
            return True

        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", current_row
        )
        time.sleep(0.3)

        try:
            if method == "row click":
                current_row.click()
            else:
                (
                    ActionChains(driver)
                    .move_to_element(current_row)
                    .pause(0.1)
                    .click_and_hold()
                    .pause(0.15)
                    .release()
                    .perform()
                )
        except (ElementClickInterceptedException,
                ElementNotInteractableException,
                WebDriverException) as error:
            logging.info("%s failed for %s: %s", method, username, error)
            continue

        try:
            wait.until(state_reached)
            logging.info(
                "%s set the checkbox for %s to %s.",
                method, username, "checked" if target_checked else "unchecked",
            )
            return True
        except TimeoutException:
            logging.info(
                "%s produced no state change for %s; trying next method.",
                method, username,
            )

    logging.error("Could not toggle checkbox for %s after all click methods.", username)
    return False


def hide_user(driver, wait, username, target_checked):
    """Search for one username and make sure its checkbox ends up at
    ``target_checked`` (True = checked/hidden-from, False = unchecked).

    If the username is already at the target state, it is left untouched
    and we simply move on to the next one.

    Returns one of:
      "checked"   -- clicked to turn the checkbox on
      "unchecked" -- clicked to turn the checkbox off
      "skipped"   -- was already at the target state, left untouched
      "not_found" -- the username never showed up in the search results
      "failed"    -- found, but the click never reached the target state
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            search_username(wait, username)
            row, toggle = wait_for_user_result(driver, wait, username)
            if toggle is None:
                return "not_found"

            if is_toggle_checked(toggle) == target_checked:
                logging.info(
                    "%s already %s; skipping.",
                    username, "checked" if target_checked else "unchecked",
                )
                return "skipped"

            if click_checkbox(driver, wait, username, row, toggle, target_checked):
                # Let Instagram finish its selection animation before clearing
                # the query and searching for the next username.
                time.sleep(1)
                return "checked" if target_checked else "unchecked"

            if attempt < MAX_RETRIES:
                logging.warning(
                    "Checkbox did not reach target state for %s. Retrying... (%s/%s)",
                    username, attempt, MAX_RETRIES,
                )
                continue
            logging.error("Giving up on %s after retries.", username)
            return "failed"
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
    return "failed"


def load_usernames_from(filename):
    """Read one username-per-line file from SCRIPT_DIR."""
    path = os.path.join(SCRIPT_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Expected username file not found: {path}")
    with open(path, "r", encoding="utf-8") as usernames_file:
        return [username.strip() for username in usernames_file if username.strip()]


def build_task_list(mode):
    """Turn the chosen mode into an ordered, de-duplicated list of
    (username, target_checked) pairs to work through.
    """
    if mode == "1":
        tasks = [(username, True) for username in load_usernames_from(HIDE_FROM_STORY_FILENAME)]
    elif mode == "2":
        tasks = [(username, False) for username in load_usernames_from(HIDE_FROM_STORY_FILENAME)]
    else:  # mode == "3", custom
        tasks = [(username, True) for username in load_usernames_from(CHECK_FILENAME)]
        tasks += [(username, False) for username in load_usernames_from(UNCHECK_FILENAME)]

    # De-duplicate while preserving order -- the same (username, target)
    # pair only ever needs to be handled once.
    seen = set()
    deduped_tasks = []
    for task in tasks:
        if task not in seen:
            seen.add(task)
            deduped_tasks.append(task)
    return deduped_tasks


def record_path():
    return os.path.join(SCRIPT_DIR, RECORD_FILENAME)


def load_record():
    """Return {(username, target_checked): outcome} for every username
    already resolved in a previous run. Returns an empty dict -- meaning
    "process everything" -- if the record file doesn't exist yet.
    """
    path = record_path()
    processed = {}
    if not os.path.exists(path):
        return processed

    with open(path, "r", newline="", encoding="utf-8") as record_file:
        for row in csv.DictReader(record_file):
            target_checked = row["target_state"] == "checked"
            processed[(row["username"], target_checked)] = row["outcome"]
    return processed


def append_record(username, target_checked, outcome):
    """Append one resolved username to the record CSV, creating it (with a
    header) the first time it's needed. Written and flushed immediately
    after each username so progress survives a crash or a Ctrl+C partway
    through the list -- the next run only has to redo what's genuinely
    unfinished.
    """
    path = record_path()
    is_new_file = not os.path.exists(path)

    with open(path, "a", newline="", encoding="utf-8") as record_file:
        writer = csv.DictWriter(record_file, fieldnames=RECORD_FIELDNAMES)
        if is_new_file:
            writer.writeheader()
        writer.writerow({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "username": username,
            "target_state": "checked" if target_checked else "unchecked",
            "outcome": outcome,
        })
        record_file.flush()


def main():
    mode = prompt_mode()

    try:
        tasks = build_task_list(mode)
    except FileNotFoundError as error:
        print(f"Error: {error}")
        return

    record = load_record()
    remaining_tasks = [task for task in tasks if task not in record]
    already_done = len(tasks) - len(remaining_tasks)

    if already_done:
        print(f"{already_done} username(s) already recorded in {RECORD_FILENAME}; skipping them.")
    print(f"{len(remaining_tasks)} username(s) left to process.\n")

    if not remaining_tasks:
        print("Nothing to do.")
        return

    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")

    driver = webdriver.Chrome(service=Service(webdriver_path), options=options)
    wait = WebDriverWait(driver, 20, ignored_exceptions=(StaleElementReferenceException,))
    processed = 0

    try:
        login_using_cookies(driver, wait)

        for username, target_checked in remaining_tasks:
            outcome = hide_user(driver, wait, username, target_checked)

            if outcome in ("checked", "unchecked", "skipped"):
                append_record(username, target_checked, outcome)
            else:
                # Deliberately NOT written to the record file, so a
                # not-found/failed username gets tried again next run
                # instead of being skipped forever.
                print(f"  [!] {username}: {outcome} -- will be retried on the next run.")

            processed += 1
            logging.info("Finished user: %s (%s)", username, outcome)

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