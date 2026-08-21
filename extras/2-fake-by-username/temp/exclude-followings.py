import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Load usernames from both files
with open(os.path.join(SCRIPT_DIR, 'usernames.txt'), 'r') as f:
    usernames = set(f.read().splitlines())  # Using a set for faster lookup

with open(os.path.join(SCRIPT_DIR, 'followings.txt'), 'r') as f:
    followings = set(f.read().splitlines())

# Exclude usernames in followings.txt from usernames.txt
final_usernames = usernames - followings

# Save the result to final-usernames.txt
with open(os.path.join(SCRIPT_DIR, 'final-usernames.txt'), 'w') as f:
    for username in sorted(final_usernames):  # Sorted for consistency
        f.write(username + '\n')

print("final-usernames.txt has been created with the excluded usernames.")
