import webbrowser
import time
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# File paths
input_file = os.path.join(SCRIPT_DIR, "suspicious-accounts-lanareech1.txt")
output_file = os.path.join(SCRIPT_DIR, "accepted_usernames.txt")

# Instagram base URL
base_url = "https://www.instagram.com/"

# Initialize list for accepted usernames
accepted_usernames = []

# Read the input file
with open(input_file, "r") as file:
    usernames = file.readlines()

# Initialize browser
browser = webbrowser.get()

# Process each username
for i, username in enumerate(usernames):
    username = username.strip()  # Remove any trailing whitespace
    if not username:  # Skip empty lines
        continue

    # Construct the Instagram URL
    profile_url = f"{base_url}{username}"

    # Open the first profile in a new tab, reuse the same tab for subsequent profiles
    if i == 0:
        print(f"Opening {profile_url} in the web browser...")
        browser.open(profile_url)
    else:
        print(f"Navigating to {profile_url}...")
        browser.open(profile_url, new=0)  # Reuse the current tab

    # Give the browser some time to load the page (adjust if necessary)
    time.sleep(2)

    # Prompt user decision
    while True:
        decision = input(f"Keep '{username}'? (y/n): ").strip().lower()
        if decision in ['y', 'n']:
            break
        print("Invalid input. Please enter 'y' or 'n'.")

    # Add to accepted list if 'y'
    if decision == 'y':
        accepted_usernames.append(username)

# Save the accepted usernames to a new file
with open(output_file, "w") as file:
    for username in accepted_usernames:
        file.write(username + "\n")

print(f"Accepted usernames saved to {output_file}.")
