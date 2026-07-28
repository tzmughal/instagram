import re
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def is_fake_username(username):
    score = 0
    
    # 1. Check if the username is very short or very long (uncommon for genuine users)
    if len(username) < 12 or len(username) > 15:
        score += 1
    
    # 2. Check if username contains random numbers at the end (e.g., "user12345")
    if re.search(r'\d{4,}$', username):
        score += 4
    
    # 3. Check if username contains repetitive letters (e.g., "aaabbbccc")
    if re.search(r'(.)\1{2,}', username):
        score += 2
    
    # 4. Check if username has excessive underscores or symbols
    if username.count('_') > 2 or username.count('.') > 2:
        score += 1
    
    # 5. Check for multiple consecutive underscores
    if re.search(r'_{2,}', username):
        score += 2
    
    # 6. Check if username starts with an underscore or dot
    if username.startswith('_') or username.startswith('.'):
        score += 1
    
    # 7. Check for excessive mixed underscores and dots
    if re.search(r'[_\.]{2,}', username):
        score += 1
    
    # 8. Check for long series of letters and numbers
    if re.search(r'([a-zA-Z]+[\d]+|[\d]+[a-zA-Z]+)', username) and len(username) > 10:
        score += 1
        
    # 9. Check if username is entirely alphabetic or numeric (with modified criteria)
    if username.isalpha() and len(username) > 10:  # Entirely alphabetic and more than 15 characters
        score += 1
    elif username.isdigit():  # Entirely numeric has no restrictions
        score += 1
    
    # Threshold score: If score is above 0, consider it suspicious
    return score > 0

# Function to read usernames from a file and check for fake ones
def detect_fake_usernames_from_file(filename):
    if not os.path.isabs(filename):
        filename = os.path.join(SCRIPT_DIR, filename)
    with open(filename, 'r') as file:
        usernames = file.read().splitlines()  # Read usernames into a list
    
    fake_usernames = [username for username in usernames if is_fake_username(username)]
    return fake_usernames

# Use the function to detect fake usernames from 'usernames.txt'
fake_usernames = detect_fake_usernames_from_file('test.txt')

# Print the results
print("Potentially fake usernames:", fake_usernames)
print("Number of fake usernames detected:", len(fake_usernames))

# Ask if the user wants to save the results
save_option = input("Do you want to save the suspicious usernames to a text file? (y/n): ").strip().lower()

if save_option == 'y':
    # Get username input for saving the file
    username_input = input("Enter a username to include in the filename: ")
    output_filename = f'suspicious-accounts-{username_input}.txt'
    output_path = os.path.join(SCRIPT_DIR, output_filename)
    
    # Save the suspicious usernames to the file
    with open(output_path, 'w') as output_file:
        for username in fake_usernames:
            output_file.write(username + '\n')
    
    print(f"Suspicious usernames have been saved to {output_path}.")
elif save_option == 'n':
    print("Exiting without saving.")
else:
    print("Invalid option. Exiting.")
