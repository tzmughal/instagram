import re
import os
import shutil
import sys
import json

# Determine the project root (parent of the parent directory of this script)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# -------------------------
# Configuration Loader
# -------------------------
def load_config():
    """Load configuration from config.json in the project root.
       Relative paths are resolved relative to the project root."""
    config_path = os.path.join(PROJECT_ROOT, "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        # Resolve relative paths
        for key in ["html_data_dir", "fake_suspicious_folder"]:
            if key in config and not os.path.isabs(config[key]):
                config[key] = os.path.join(PROJECT_ROOT, config[key])
        return config
    except Exception as e:
        print(f"Error loading configuration file: {e}")
        sys.exit(1)

# -------------------------
# Default Threshold Values
# -------------------------
DEFAULT_MIN_LENGTH = 6
DEFAULT_MAX_LENGTH = 16
DEFAULT_SCORE_RULE1 = 2   # Score for invalid length
DEFAULT_SCORE_RULE2 = 3   # Score for username ending with random numbers
DEFAULT_SCORE_RULE3 = 2   # Score for repetitive characters
DEFAULT_SCORE_RULE4 = 2   # Score for excessive symbols (more than 2 underscores or dots)
DEFAULT_SCORE_RULE5 = 2   # Score for multiple consecutive underscores/dots
DEFAULT_SCORE_RULE6 = 1   # Score for starting/ending with underscore or dot
DEFAULT_SCORE_RULE7 = 2   # Score for mix of long letters and numbers
DEFAULT_SCORE_RULE8 = 3   # Score for purely numeric username
DEFAULT_SCORE_RULE9 = 2   # Score for gibberish patterns
DEFAULT_KEYWORD_ALLOWANCE_THRESHOLD = 0  # Allow if username contains a keyword and score <= this
DEFAULT_FINAL_THRESHOLD = 0              # Flag username if score > this

# Global threshold variables (will be reinitialized on each run)
min_length = DEFAULT_MIN_LENGTH
max_length = DEFAULT_MAX_LENGTH
score_rule1 = DEFAULT_SCORE_RULE1
score_rule2 = DEFAULT_SCORE_RULE2
score_rule3 = DEFAULT_SCORE_RULE3
score_rule4 = DEFAULT_SCORE_RULE4
score_rule5 = DEFAULT_SCORE_RULE5
score_rule6 = DEFAULT_SCORE_RULE6
score_rule7 = DEFAULT_SCORE_RULE7
score_rule8 = DEFAULT_SCORE_RULE8
score_rule9 = DEFAULT_SCORE_RULE9
keyword_allowance_threshold = DEFAULT_KEYWORD_ALLOWANCE_THRESHOLD
final_threshold = DEFAULT_FINAL_THRESHOLD

# -------------------------
# Threshold Configuration Functions
# -------------------------
def show_current_thresholds():
    print("\nCurrent threshold values:")
    print("1.  Minimum length:                       ", min_length)
    print("2.  Maximum length:                       ", max_length)
    print("3.  Score for invalid length:             ", score_rule1)
    print("4.  Score for username ending with numbers: ", score_rule2)
    print("5.  Score for repetitive characters:      ", score_rule3)
    print("6.  Score for excessive symbols:          ", score_rule4)
    print("7.  Score for multiple consecutive underscores/dots: ", score_rule5)
    print("8.  Score for starting/ending with underscore/dot:     ", score_rule6)
    print("9.  Score for mix of long letters and numbers:         ", score_rule7)
    print("10. Score for purely numeric username:     ", score_rule8)
    print("11. Score for gibberish patterns:          ", score_rule9)
    print("12. Keyword allowance threshold:           ", keyword_allowance_threshold)
    print("13. Final score threshold:                 ", final_threshold)

def configure_thresholds():
    global min_length, max_length, score_rule1, score_rule2, score_rule3, score_rule4, score_rule5, score_rule6, score_rule7, score_rule8, score_rule9, keyword_allowance_threshold, final_threshold
    while True:
        choice = input("\nEnter the number of the threshold to change (or 'n' to finish): ").strip().lower()
        if choice == 'n':
            break
        try:
            num = int(choice)
        except ValueError:
            print("Invalid input. Please enter a number or 'n'.")
            continue
        
        new_val = input("Enter new value: ").strip()
        try:
            new_val = int(new_val)
        except ValueError:
            print("Invalid value; please enter an integer.")
            continue
        
        if num == 1:
            min_length = new_val
        elif num == 2:
            max_length = new_val
        elif num == 3:
            score_rule1 = new_val
        elif num == 4:
            score_rule2 = new_val
        elif num == 5:
            score_rule3 = new_val
        elif num == 6:
            score_rule4 = new_val
        elif num == 7:
            score_rule5 = new_val
        elif num == 8:
            score_rule6 = new_val
        elif num == 9:
            score_rule7 = new_val
        elif num == 10:
            score_rule8 = new_val
        elif num == 11:
            score_rule9 = new_val
        elif num == 12:
            keyword_allowance_threshold = new_val
        elif num == 13:
            final_threshold = new_val
        else:
            print("Invalid threshold number.")
            continue

        show_current_thresholds()
        further = input("Do you want further changes? (y/n): ").strip().lower()
        if further != 'y':
            break
    print("\nThresholds updated.\n")

# -------------------------
# Common Keywords Loader
# -------------------------
def load_common_keywords(filename="keywords.txt"):
    if not os.path.isabs(filename):
        filename = os.path.join(SCRIPT_DIR, filename)
    try:
        with open(filename, 'r') as file:
            return {line.strip().lower() for line in file if line.strip()}
    except FileNotFoundError:
        print(f"Warning: {filename} not found. Using an empty whitelist.")
        return set()

# -------------------------
# Fake Username Detection Functions
# -------------------------
def is_fake_username(username, COMMON_KEYWORDS):
    score = 0
    username_lower = username.lower()
    if len(username) < min_length or len(username) > max_length:
        score += score_rule1
    if re.search(r'\d{4,}$', username):
        score += score_rule2
    if re.search(r'(.)\1{3,}', username):
        score += score_rule3
    if username.count('_') > 2 or username.count('.') > 2:
        score += score_rule4
    if re.search(r'[_\.]{2,}', username):
        score += score_rule5
    if username.startswith(('_', '.')) or username.endswith(('_', '.')):
        score += score_rule6
    if re.search(r'([a-zA-Z]{6,}\d{4,}|\d{4,}[a-zA-Z]{6,})', username):
        score += score_rule7
    if username.isdigit() and len(username) > 6:
        score += score_rule8
    if re.search(r'([a-zA-Z]{4,}){3,}', username):
        score += score_rule9
    contains_common_keyword = any(word in username_lower for word in COMMON_KEYWORDS)
    if contains_common_keyword and score <= keyword_allowance_threshold:
        return False
    return score > final_threshold

def detect_fake_usernames_from_file(input_filename, COMMON_KEYWORDS):
    with open(input_filename, 'r') as file:
        usernames = file.read().splitlines()
    fake_usernames = [username for username in usernames if is_fake_username(username, COMMON_KEYWORDS)]
    return fake_usernames

# -------------------------
# Main Detection Flow
# -------------------------
def run_detection():
    global min_length, max_length, score_rule1, score_rule2, score_rule3, score_rule4, score_rule5, score_rule6, score_rule7, score_rule8, score_rule9, keyword_allowance_threshold, final_threshold

    # Reinitialize thresholds to defaults on each run
    min_length = DEFAULT_MIN_LENGTH
    max_length = DEFAULT_MAX_LENGTH
    score_rule1 = DEFAULT_SCORE_RULE1
    score_rule2 = DEFAULT_SCORE_RULE2
    score_rule3 = DEFAULT_SCORE_RULE3
    score_rule4 = DEFAULT_SCORE_RULE4
    score_rule5 = DEFAULT_SCORE_RULE5
    score_rule6 = DEFAULT_SCORE_RULE6
    score_rule7 = DEFAULT_SCORE_RULE7
    score_rule8 = DEFAULT_SCORE_RULE8
    score_rule9 = DEFAULT_SCORE_RULE9
    keyword_allowance_threshold = DEFAULT_KEYWORD_ALLOWANCE_THRESHOLD
    final_threshold = DEFAULT_FINAL_THRESHOLD

    # Load configuration from config.json
    config = load_config()

    # Use command-line argument for account username if provided; otherwise, prompt.
    if len(sys.argv) > 1:
        account_username = sys.argv[1].strip()
    else:
        account_username = input("Enter the account username: ").strip()

    # Determine the input file path using the config key "html_data_dir".
    base_dir = config.get("html_data_dir")
    if not base_dir:
        print("Missing 'html_data_dir' in config.")
        sys.exit(1)
    input_filename = os.path.join(base_dir, account_username, f"usernames-{account_username}.txt")
    if not os.path.exists(input_filename):
        print(f"Input file not found for username '{account_username}' at {input_filename}.")
        sys.exit(1)

    # Show current thresholds and allow configuration.
    show_current_thresholds()
    if input("\nDo you want to configure threshold values? (y/n): ").strip().lower() == 'y':
        configure_thresholds()

    # Load common keywords.
    COMMON_KEYWORDS = load_common_keywords()

    # Run detection.
    fake_usernames = detect_fake_usernames_from_file(input_filename, COMMON_KEYWORDS)
    print("\nPotentially fake usernames:", fake_usernames)
    print("Number of fake usernames detected:", len(fake_usernames))

    # Ask if the user wants to save the results.
    save_option = input("\nDo you want to save the suspicious usernames to a text file? (y/n): ").strip().lower()
    if save_option == 'y':
        custom_name = input("Enter custom output filename (without extension), or press Enter to use default: ").strip()
        if custom_name:
            output_filename = custom_name + ".txt"
        else:
            output_filename = "suspicious_usernames-" + account_username + ".txt"

        output_path = os.path.join(SCRIPT_DIR, output_filename)
        with open(output_path, 'w') as output_file:
            for username in fake_usernames:
                output_file.write(username + '\n')
        print(f"\nSuspicious usernames have been saved to {output_path}.")

        # Get destination folder from config (key: "fake_suspicious_folder")
        suspicious_data_folder = config.get("fake_suspicious_folder")
        if not suspicious_data_folder:
            print("Missing 'fake_suspicious_folder' in config.")
            sys.exit(1)
        os.makedirs(suspicious_data_folder, exist_ok=True)
        destination = os.path.join(suspicious_data_folder, output_filename)
        shutil.move(output_path, destination)
        abs_destination = os.path.abspath(destination)
        print(f"The file has been moved to {abs_destination}.")
    elif save_option == 'n':
        print("Exiting without saving.")
    else:
        print("Invalid option. Exiting.")

# -------------------------
# Main Loop: After one complete detection run, prompt for next action.
while True:
    run_detection()
    choice = input("\nDo you want to (r) re-run fake detection with new threshold settings or (m) return to the main menu? (r/m): ").strip().lower()
    if choice == 'r':
        continue  # Loop again to re-run detection.
    elif choice == 'm':
        input("\nPress Enter to return to the main menu...")
        sys.exit(0)
    else:
        print("Invalid option. Returning to main menu.")
        sys.exit(0)
