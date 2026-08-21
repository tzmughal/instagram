import re
import os
import shutil
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

# Use command-line argument if provided, otherwise prompt
if len(sys.argv) > 1:
    account_username = sys.argv[1]
else:
    account_username = input("Enter the account username: ")


# Function to load common keywords from a file
def load_common_keywords(filename="keywords.txt"):
    if not os.path.isabs(filename):
        filename = os.path.join(SCRIPT_DIR, filename)
    try:
        with open(filename, 'r') as file:
            return {line.strip().lower() for line in file if line.strip()}  # Load words into a set
    except FileNotFoundError:
        print(f"Warning: {filename} not found. Using an empty whitelist.")
        return set()  # Return an empty set if file not found

# Load keywords from file
COMMON_KEYWORDS = load_common_keywords()

def is_fake_username(username):
    score = 0
    username_lower = username.lower()  # Convert to lowercase for uniform matching
    
    # 1. Length-based filtering (very short or unusual length)
    if len(username) < 6 or len(username) > 16:
        score += 2  # Stronger weight for extreme lengths

    # 2. Detect if username ends with random numbers (common bot pattern)
    if re.search(r'\d{4,}$', username):
        score += 3

    # 3. Detect repetitive characters (e.g., "aaa", "111", "xyzxyz")
    if re.search(r'(.)\1{3,}', username):  # 4+ repeated characters
        score += 2

    # 4. Detect excessive symbols (more than 2 underscores or dots)
    if username.count('_') > 2 or username.count('.') > 2:
        score += 2

    # 5. Check for multiple consecutive underscores or dots (e.g., "__user", "user..name")
    if re.search(r'[_\.]{2,}', username):
        score += 2

    # 6. Detect if username starts or ends with an underscore or dot
    if username.startswith(('_', '.')) or username.endswith(('_', '.')):
        score += 1

    # 7. Detect usernames that mix long letters and numbers unnaturally
    if re.search(r'([a-zA-Z]{6,}\d{4,}|\d{4,}[a-zA-Z]{6,})', username):
        score += 2

    # 8. Detect purely numeric usernames (highly unlikely for real users)
    if username.isdigit() and len(username) > 6:
        score += 3  # Strong bot indicator

    # 9. Detect gibberish patterns (common fake account behavior)
    if re.search(r'([a-zA-Z]{4,}){3,}', username):  # Three+ random letter groups
        score += 2

    # 10. Check for presence of whitelisted words (but only allow them if not fully fake)
    contains_common_keyword = any(word in username_lower for word in COMMON_KEYWORDS)
    
    if contains_common_keyword and score <= 4:  # Allow if score is low (likely real)
        return False
    
    return score > 2  # Final threshold: Higher bar for flagging

# Function to read usernames from a file and check for fake ones
def detect_fake_usernames_from_file(filename):
    with open(filename, 'r') as file:
        usernames = file.read().splitlines()  # Read usernames into a list
    
    fake_usernames = [username for username in usernames if is_fake_username(username)]
    return fake_usernames

# Use the function to detect fake usernames from 'usernames.txt'
# fake_usernames = detect_fake_usernames_from_file('usernames.txt')
# Construct the input filename based on the account username.
# Expected file location: C:\Dev\Instagram\1-HTML-to-TXT\data\<account_username>\usernames-<account_username>.txt
base_dir = os.path.join(PROJECT_ROOT, "1-HTML-to-TXT", "data")
input_filename = os.path.join(base_dir, account_username, f"usernames-{account_username}.txt")
fake_usernames = detect_fake_usernames_from_file(input_filename)


# Print the results
print("Potentially fake usernames:", fake_usernames)
print("Number of fake usernames detected:", len(fake_usernames))

# Ask if the user wants to save the results
save_option = input("Do you want to save the suspicious usernames to a text file? (y/n): ").strip().lower()

if save_option == 'y':
    # Prompt for account username to add to file name
    account_username = input("Enter the account username: ")
    
    # Build the output file name with the account username
    output_filename = "suspicious_usernames-" + account_username + ".txt"
    output_path = os.path.join(SCRIPT_DIR, output_filename)
    
    # Save the suspicious usernames to the file
    with open(output_path, 'w') as output_file:
        for username in fake_usernames:
            output_file.write(username + '\n')
    
    print(f"Suspicious usernames have been saved to {output_path}.")
    
    # Define the destination directory for suspicious data (no username subfolder needed)
    suspicious_data_folder = os.path.join(PROJECT_ROOT, "2-fake-by-username", "data", "suspicious")
    os.makedirs(suspicious_data_folder, exist_ok=True)
    
    # Move the output file to the suspicious data folder
    shutil.move(output_path, os.path.join(suspicious_data_folder, output_filename))
    print(f"The file has been moved to {suspicious_data_folder}.")
    
elif save_option == 'n':
    print("Exiting without saving.")
else:
    print("Invalid option. Exiting.")
