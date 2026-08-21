#!/usr/bin/env python3
import os
import glob
import shutil
import zipfile
import subprocess
import sys
import json
import logging

# -------------------------
# Configuration & Initialization
# -------------------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def load_config():
    """Load configuration from config.json in the project root.
       Relative paths are resolved relative to the project root."""
    config_path = os.path.join(PROJECT_ROOT, "config.json")
    default_config = {
        "downloads_folder": os.path.join(os.path.expanduser("~"), "Downloads"),
        "dev_dir": PROJECT_ROOT,
        "extracted_zips_dir": os.path.join(PROJECT_ROOT, "data", "extracted-zips"),
        "dump_dir": os.path.join(PROJECT_ROOT, "data", "dump"),
        "logs_dir": os.path.join(PROJECT_ROOT, "data", "logs"),
        "html_to_txt_dir": os.path.join(PROJECT_ROOT, "1-HTML-to-TXT"),
        "fake_by_username_dir": os.path.join(PROJECT_ROOT, "2-fake-by-username"),
        "not_following_back_dir": os.path.join(PROJECT_ROOT, "3-not-following-back"),
        "block_bot_dir": os.path.join(PROJECT_ROOT, "4-block-bot"),
        "unfollow_bot_dir": os.path.join(PROJECT_ROOT, "5-unfollow-bot"),
        "edgedriver_dir": os.path.join(PROJECT_ROOT, "data", "edgedriver_win64")
    }
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                user_config = json.load(f)
            # Resolve relative paths for each key using the project root
            for key in ["downloads_folder", "dev_dir", "extracted_zips_dir", "dump_dir",
                        "logs_dir", "html_to_txt_dir", "fake_by_username_dir",
                        "not_following_back_dir", "block_bot_dir", "unfollow_bot_dir", "edgedriver_dir"]:
                if key in user_config and not os.path.isabs(user_config[key]):
                    user_config[key] = os.path.join(PROJECT_ROOT, user_config[key])
            default_config.update(user_config)
            print(f"Loaded configuration from {config_path}")
        except Exception as e:
            print(f"Error reading config file. Using default config. ({e})")
    return default_config

CONFIG = load_config()

# Ensure necessary directories exist
for key in ["extracted_zips_dir", "dump_dir", "logs_dir"]:
    os.makedirs(CONFIG[key], exist_ok=True)

# Set up logging (logs folder now in data/logs)
logging.basicConfig(
    filename=os.path.join(CONFIG["logs_dir"], "app.log"),
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# -------------------------
# Helper Functions
# -------------------------
def get_valid_username():
    while True:
        username = input("Enter the account username: ").strip()
        if username:
            return username
        print("Username cannot be empty. Please try again.")

def find_zip_file(username):
    downloads_folder = CONFIG["downloads_folder"]
    zip_pattern = os.path.join(downloads_folder, f"instagram-{username}-*.zip")
    zip_files = glob.glob(zip_pattern)
    if not zip_files:
        return None
    if len(zip_files) == 1:
        return zip_files[0]
    else:
        print("Multiple zip files found:")
        for idx, file in enumerate(zip_files, start=1):
            print(f"{idx}: {file}")
        while True:
            try:
                selection = int(input("Select the number corresponding to the desired zip file: "))
                if 1 <= selection <= len(zip_files):
                    return zip_files[selection - 1]
                else:
                    print("Invalid selection. Try again.")
            except ValueError:
                print("Please enter a valid number.")

def safe_copy(src, dest):
    """
    Copies file from src to dest.
    If a file exists at dest, moves it to the global dump folder (preserving subfolder structure).
    """
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if os.path.exists(dest):
            # Compute relative path from dev_dir to destination and use it under dump_dir
            rel_path = os.path.relpath(dest, CONFIG["dev_dir"])
            dump_dest = os.path.join(CONFIG["dump_dir"], rel_path)
            os.makedirs(os.path.dirname(dump_dest), exist_ok=True)
            shutil.move(dest, dump_dest)
            print(f"Existing file moved to dump: {dump_dest}")
        shutil.copy2(src, dest)
        print(f"Copied {src} to {dest}")
    except Exception as e:
        logging.error(f"Error copying {src} to {dest}: {e}")
        print(f"Failed to copy {src} to {dest}. Check log for details.")

def extract_zip(zip_file_path):
    extraction_root = CONFIG["extracted_zips_dir"]
    os.makedirs(extraction_root, exist_ok=True)
    zip_basename = os.path.basename(zip_file_path)
    extract_folder = os.path.join(extraction_root, os.path.splitext(zip_basename)[0])
    os.makedirs(extract_folder, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zf:
            zf.extractall(extract_folder)
        print(f"Extracted zip file to: {extract_folder}")
        return extract_folder
    except Exception as e:
        logging.error(f"Error extracting zip file {zip_file_path}: {e}")
        print(f"Failed to extract {zip_file_path}. Check log for details.")
        return None

def copy_html_files(extract_folder):
    target_dir = os.path.join(extract_folder, "connections", "followers_and_following")
    if not os.path.exists(target_dir):
        print(f"Target folder not found: {target_dir}")
        return False

    # Copy following.html
    following_src = os.path.join(target_dir, "following.html")
    dest_following = os.path.join(CONFIG["html_to_txt_dir"], "Following HTML")
    os.makedirs(dest_following, exist_ok=True)
    if os.path.exists(following_src):
        safe_copy(following_src, os.path.join(dest_following, os.path.basename(following_src)))
    else:
        print(f"'following.html' not found in: {target_dir}")

    # Copy followers_*.html files
    followers_pattern = os.path.join(target_dir, "followers_*.html")
    followers_files = glob.glob(followers_pattern)
    dest_followers = os.path.join(CONFIG["html_to_txt_dir"], "Followers HTML")
    os.makedirs(dest_followers, exist_ok=True)
    if followers_files:
        for f in followers_files:
            safe_copy(f, os.path.join(dest_followers, os.path.basename(f)))
        print(f"Copied {len(followers_files)} followers HTML file(s) to: {dest_followers}")
    else:
        print(f"No followers HTML files found in: {target_dir}")
    return True

def run_script(script_path, username):
    script_dir = os.path.dirname(script_path)
    print(f"Running {script_path} ...")
    try:
        # Run the external script interactively.
        subprocess.run(["python", script_path, username], cwd=script_dir, check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Script {script_path} failed with error: {e}")
        print(f"Error running {script_path}. Check log for details.")


def copy_for_block_bot(username, fake_output_file):
    src_block = os.path.join(CONFIG["block_bot_dir"], "1Backup", "block-bot-1000.py")
    dest_folder = os.path.join(CONFIG["block_bot_dir"], username)
    os.makedirs(dest_folder, exist_ok=True)
    
    # Copy block bot backup file
    safe_copy(src_block, os.path.join(dest_folder, os.path.basename(src_block)))
    
    # Copy fake detection output file if it exists
    if os.path.exists(fake_output_file):
        safe_copy(fake_output_file, os.path.join(dest_folder, os.path.basename(fake_output_file)))
    else:
        print("Fake detection output file not found.")

    # Update the block-bot script to use the new fake detection output filename
    block_script_path = os.path.join(dest_folder, os.path.basename(src_block))
    new_filename = os.path.basename(fake_output_file)
    try:
        with open(block_script_path, 'r') as file:
            content = file.read()
        old_string = "usernames_path = os.path.join(SCRIPT_DIR, 'suspicious-accounts-immortalconcepts.txt')"
        new_string = f"usernames_path = os.path.join(SCRIPT_DIR, '{new_filename}')"
        new_content = content.replace(old_string, new_string)
        with open(block_script_path, 'w') as file:
            file.write(new_content)
        print(f"Updated {block_script_path} to use the fake detection output file name: {new_filename}")
    except Exception as e:
        logging.error(f"Error updating block bot script: {e}")
        print(f"Error updating the block bot script. Check log for details.")

def copy_for_unfollow_bot(username, nb_output_file):
    src_unfollow = os.path.join(CONFIG["unfollow_bot_dir"], "1Backup", "unfollow-bot-1000.py")
    dest_folder = os.path.join(CONFIG["unfollow_bot_dir"], username)
    os.makedirs(dest_folder, exist_ok=True)
    
    # Copy unfollow bot backup file
    safe_copy(src_unfollow, os.path.join(dest_folder, os.path.basename(src_unfollow)))
    
    # Copy not-following-back output file if it exists
    if os.path.exists(nb_output_file):
        safe_copy(nb_output_file, os.path.join(dest_folder, os.path.basename(nb_output_file)))
    else:
        print("Not-following-back output file not found.")
    
    # Update the unfollow bot script to use the dynamic filename
    unfollow_script_path = os.path.join(dest_folder, os.path.basename(src_unfollow))
    new_nb_filename = os.path.basename(nb_output_file)
    try:
        with open(unfollow_script_path, 'r') as file:
            content = file.read()
        old_string = "usernames_path = os.path.join(SCRIPT_DIR, 'a.txt')"
        new_string = f"usernames_path = os.path.join(SCRIPT_DIR, '{new_nb_filename}')"
        new_content = content.replace(old_string, new_string)
        with open(unfollow_script_path, 'w') as file:
            file.write(new_content)
        print(f"Updated {unfollow_script_path} to use the not-following-back output file name: {new_nb_filename}")
    except Exception as e:
        logging.error(f"Error updating unfollow bot script: {e}")
        print(f"Error updating the unfollow bot script. Check log for details.")

def get_valid_file_name(prompt, expected_ext=".txt", default_name=None):
    file_name = input(prompt).strip()
    if not file_name:
        if default_name:
            print(f"No input provided. Using default name: {default_name}")
            return default_name
        else:
            print("No input provided.")
            return None
    if not file_name.endswith(expected_ext):
        file_name += expected_ext
    return file_name

# -------------------------
# Workflow Functions
# -------------------------
def html_flow(username):
    # 1. Find the zip file
    zip_file = find_zip_file(username)
    if not zip_file:
        print(f"No zip file found for account '{username}' in {CONFIG['downloads_folder']}.")
        return
    print(f"Found zip file: {zip_file}")

    # 2. Confirm extraction
    if input("Do you want to extract the zip file? (y/n): ").strip().lower() != 'y':
        print("Extraction cancelled.")
        return

    extract_folder = extract_zip(zip_file)
    if not extract_folder:
        return

    # 3. Copy HTML files from extracted folder
    if not copy_html_files(extract_folder):
        return

    # 4. Run HTML-to-TXT conversion
    html_to_txt_script = os.path.join(CONFIG["html_to_txt_dir"], "html-to-txt-v3.py")
    run_script(html_to_txt_script, username)

    # 5. Optionally run fake detection
    if input("Do you want to detect fake followers? (y/n): ").strip().lower() == 'y':
        fake_script = os.path.join(CONFIG["fake_by_username_dir"], "fake-by-username-v4.py")
        run_script(fake_script, username)
        # Optionally continue to block bot step
        if input("Do you want to continue to block bot? (y/n): ").strip().lower() == 'y':
            default_fake = f"suspicious_usernames-{username}.txt"
            default_fake_path = os.path.join(CONFIG["fake_by_username_dir"], "data", "suspicious", default_fake)
            fake_input = get_valid_file_name(
                f"Enter fake detection output filename (with .txt) or press Enter to use default ({default_fake}): ",
                default_name=default_fake
            )
            custom_fake_path = os.path.join(CONFIG["fake_by_username_dir"], "data", "suspicious", fake_input)
            if os.path.exists(default_fake_path) and not os.path.exists(custom_fake_path):
                os.rename(default_fake_path, custom_fake_path)
            copy_for_block_bot(username, custom_fake_path)
        else:
            print("Block bot step skipped.")
    else:
        print("Fake detection skipped.")

def not_following_flow(username):
    # 1. Run not-following-back detection
    not_following_script = os.path.join(CONFIG["not_following_back_dir"], "not-following-back.py")
    run_script(not_following_script, username)
    
    default_nb = f"not_following_back-{username}.txt"
    nb_output_file = os.path.join(CONFIG["not_following_back_dir"], "data", "not following back", default_nb)
    
    # 2. Optionally run unfollow bot
    if input("Do you want to continue to unfollow bot? (y/n): ").strip().lower() == 'y':
        copy_for_unfollow_bot(username, nb_output_file)
    else:
        print("Unfollow bot step skipped.")

# -------------------------
# Main Menu Loop
# -------------------------
def main_menu():
    while True:
        print("\nMain Menu:")
        print("1. HTML-to-TXT conversion & Fake Detection Flow")
        print("2. Not-Following-Back Detection & Unfollow Bot Flow")
        print("3. Quit")
        choice = input("Enter your choice (1, 2, or 3): ").strip()
        if choice == "1":
            username = get_valid_username()
            html_flow(username)
        elif choice == "2":
            username = get_valid_username()
            not_following_flow(username)
        elif choice == "3":
            print("Exiting script.")
            break
        else:
            print("Invalid option. Please try again.")

# -------------------------
# Main Entry Point
# -------------------------
def main():
    print("Welcome to the Instagram Automation Tool")
    main_menu()

if __name__ == "__main__":
    main()
