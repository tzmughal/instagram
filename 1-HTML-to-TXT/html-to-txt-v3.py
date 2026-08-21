import os
import glob
import shutil
import sys
import json
from bs4 import BeautifulSoup

# Determine the project root (parent of the parent directory of this script)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

def load_config():
    """Load configuration from config.json in the project root.
       Relative paths are resolved relative to the project root."""
    config_path = os.path.join(PROJECT_ROOT, "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        # Resolve relative paths
        for key in ["followers_html_dir", "following_html_dir", "html_data_dir"]:
            if key in config and not os.path.isabs(config[key]):
                config[key] = os.path.join(PROJECT_ROOT, config[key])
        return config
    except Exception as e:
        print(f"Error loading configuration file: {e}")
        sys.exit(1)

config = load_config()

# Function to extract usernames from HTML files
def extract_usernames_from_html(html_files, file_type="followers"):
    """Extracts Instagram usernames from given HTML files.
    
    file_type: "followers" or "following" - determines parsing strategy
    - followers: extracts from <a> tag text
    - following: extracts from <h2> tag text
    """
    usernames = set()  # Use set to avoid duplicates
    
    for html_file in html_files:
        with open(html_file, 'r', encoding='utf-8') as file:
            # Parse the HTML file
            soup = BeautifulSoup(file, 'html.parser')
            
            if file_type == "following":
                # For following.html: extract from h2 tags with class _a6-h
                for h2_tag in soup.find_all('h2', class_='_a6-h'):
                    username = h2_tag.text.strip().lower()
                    if username:
                        usernames.add(username)
            else:  # followers
                # For followers.html: extract from a tags with instagram.com links (not /_u/ links)
                for a_tag in soup.find_all('a', href=True):
                    href = a_tag['href']
                    if "instagram.com/" in href and "/_u/" not in href:
                        username = a_tag.text.strip().lower()
                        if username:
                            usernames.add(username)
    
    return usernames

# --- Processing HTML files as before ---

# Specify the pattern to match all HTML files in the Followers HTML folder
followers_html_dir = config.get("followers_html_dir")
following_html_dir = config.get("following_html_dir")

followers_html_files = glob.glob(os.path.join(followers_html_dir, 'followers_*.html'))
# Extract usernames from followers
followers = extract_usernames_from_html(followers_html_files, file_type="followers")

# Specify the single following.html file in the Following HTML folder
followings_html_file = os.path.join(following_html_dir, 'following.html')
# Extract usernames from followings
followings = extract_usernames_from_html([followings_html_file], file_type="following")

# Subtract followings from followers to get people who follow you but whom you don’t follow back
not_following_back = followers - followings

# Prompt the user to input the account's username
# account_username = input("Enter the account username: ")
import sys
if len(sys.argv) > 1:
    account_username = sys.argv[1]
else:
    account_username = input("Enter the account username: ")


# Build the output file name as "usernames-<account_username>.txt"
output_filename = "usernames-" + account_username + ".txt"

# Save the result to the output file in the current directory first
with open(output_filename, 'w', encoding='utf-8') as outfile:
    for username in not_following_back:
        outfile.write(username + '\n')

print(f"Usernames have been saved to {output_filename}")

# --- Backup the processed files into a separate folder structure ---

# Use the html_data_dir from config
html_data_dir = config.get("html_data_dir")
account_backup_dir = os.path.join(html_data_dir, account_username)
followers_backup_dir = os.path.join(account_backup_dir, "Followers HTML")
followings_backup_dir = os.path.join(account_backup_dir, "Following HTML")

# Create directories if they do not exist
os.makedirs(followers_backup_dir, exist_ok=True)
os.makedirs(followings_backup_dir, exist_ok=True)

# Move each followers HTML file to the backup followers folder
for f in followers_html_files:
    if os.path.exists(f):
        shutil.move(f, os.path.join(followers_backup_dir, os.path.basename(f)))

# Move the following HTML file to the backup followings folder (if it exists)
if os.path.exists(followings_html_file):
    shutil.move(followings_html_file, os.path.join(followings_backup_dir, os.path.basename(followings_html_file)))

# Move the output file into the account backup directory
if os.path.exists(output_filename):
    shutil.move(output_filename, os.path.join(account_backup_dir, os.path.basename(output_filename)))

print(f"All processed files have been moved to the backup folder: {account_backup_dir}")
