import re
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def is_fake_username(username):
    # Check length of username
    if len(username) < 5 or len(username) > 21:
        return True

    # Check if username contains two consecutive underscores
    if '__' in username:
        return True

    # Allow up to 2 underscores
    if username.count('_') > 4:
        return True

    # Allow up to 2 digits
    if sum(c.isdigit() for c in username) > 6:
        return True

    # Allow up to 2 periods
    if username.count('.') > 3:
        return True

    # Check if there is a reasonable mix of alphabetic and non-alphabetic characters
    letters = sum(c.isalpha() for c in username)
    digits = sum(c.isdigit() for c in username)
    underscores = username.count('_')
    periods = username.count('.')

    # Ratio of letters to non-letter characters (underscores, digits, periods)
    if digits + underscores + periods > letters:
        return True

    # Disallow usernames with no letters (just digits, underscores, periods)
    if letters == 0:
        return True

    return False

# Read usernames from the file
with open(os.path.join(SCRIPT_DIR, 'usernames.txt'), 'r') as file:
    usernames = file.read().splitlines()

# Read followings from followings.txt and create a set for efficient lookup
with open(os.path.join(SCRIPT_DIR, 'followings.txt'), 'r') as file:
    followings = set(file.read().splitlines())

# Identify fake users, excluding those in followings.txt
fake_users = [username for username in usernames if username not in followings and is_fake_username(username)]

# Save the potential fake accounts to a file
with open(os.path.join(SCRIPT_DIR, 'suspicious-usernames.txt'), 'w', encoding='utf-8') as outfile:
    for user in fake_users:
        outfile.write(user + '\n')

print(f"Potential fake accounts have been saved to suspicious-usernames.txt.")
