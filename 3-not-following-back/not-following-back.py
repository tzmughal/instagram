import os
import glob
import sys
import shutil
import json
from bs4 import BeautifulSoup

# Determine the project root (parent directory of the script's parent)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_config():
    """Load configuration from config.json located in the project root.
       Relative paths are resolved relative to the project root."""
    config_path = os.path.join(PROJECT_ROOT, "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        # Resolve relative paths
        for key in ["followers_html_dir", "following_html_dir", "not_following_back_output_folder", 
                    "html_data_dir", "fake_suspicious_folder"]:
            if key in config and not os.path.isabs(config[key]):
                config[key] = os.path.join(PROJECT_ROOT, config[key])
        return config
    except Exception as e:
        print(f"Error loading configuration file: {e}")
        sys.exit(1)

def extract_usernames_from_html(html_files, file_type="followers"):
    """Extracts Instagram usernames from given HTML files.
    
    file_type: "followers" or "following" - determines parsing strategy
    - followers: extracts from <a> tag text
    - following: extracts from <h2> tag text
    """
    usernames = set()  # Use set to avoid duplicates during extraction
    for html_file in html_files:
        try:
            with open(html_file, 'r', encoding='utf-8') as file:
                soup = BeautifulSoup(file, 'html.parser')
                
                if file_type == "following":
                    # For following.html: extract from h2 tags
                    for h2_tag in soup.find_all('h2', class_='_a6-h'):
                        username = h2_tag.text.strip().lower()  # Normalize: lowercase and strip
                        if username and len(username) > 0:  # Ensure non-empty
                            usernames.add(username)
                else:  # followers
                    # For followers.html: extract from a tags with instagram.com links
                    for a_tag in soup.find_all('a', href=True):
                        href = a_tag['href']
                        if "instagram.com/" in href and not "/_u/" in href:
                            username = a_tag.text.strip().lower()  # Normalize: lowercase and strip
                            if username and len(username) > 0:  # Ensure non-empty
                                usernames.add(username)
        except Exception as e:
            print(f"Error processing {html_file}: {e}")
    return usernames

def main():
    # Load configuration
    config = load_config()

    # Get directories from config
    followers_html_dir = config.get("followers_html_dir")
    following_html_dir = config.get("following_html_dir")
    output_folder = config.get("not_following_back_output_folder")

    if not followers_html_dir or not following_html_dir or not output_folder:
        print("One or more required configuration keys are missing.")
        sys.exit(1)

    # Accept account username as a command-line argument or prompt
    if len(sys.argv) > 1:
        account_username = sys.argv[1].strip()
    else:
        account_username = input("Enter the account username: ").strip()

    # Build list of followers HTML files and path to following HTML file
    followers_files = glob.glob(os.path.join(followers_html_dir, "followers_*.html"))
    following_file = os.path.join(following_html_dir, "following.html")

    # Check if necessary files exist
    if not followers_files:
        print(f"No followers HTML files found in {followers_html_dir}. Exiting.")
        sys.exit(1)
    if not os.path.exists(following_file):
        print(f"Following HTML file not found in {following_html_dir}. Exiting.")
        sys.exit(1)

    # Extract usernames from HTML files
    followers = extract_usernames_from_html(followers_files, file_type="followers")
    followings = extract_usernames_from_html([following_file], file_type="following")
    
    # Debug output
    print(f"\nDebug Info:")
    print(f"Total followers: {len(followers)}")
    print(f"Total following: {len(followings)}")
    
    # Calculate not following back: people you follow who don't follow you back
    not_following_back = followings - followers
    
    print(f"Not following you back: {len(not_following_back)}")
    
    if len(not_following_back) > len(followings):
        print(f"\nWarning: Not following back count ({len(not_following_back)}) exceeds following count ({len(followings)})!")
        print("This should not happen. Check for data corruption.")
    
    print()  # Blank line for readability
    # Build output filename
    output_filename = f"not_following_back-{account_username}.txt"
    destination_path = os.path.join(output_folder, output_filename)
    
    # Ensure the destination folder exists
    os.makedirs(output_folder, exist_ok=True)
    
    # Write output directly to the destination folder
    with open(destination_path, 'w', encoding='utf-8') as outfile:
        for username in sorted(not_following_back):
            outfile.write(username + "\n")
    print(f"Not following back usernames have been saved to {destination_path}.")

if __name__ == "__main__":
    main()
