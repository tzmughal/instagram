import pandas as pd
import re
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Load CSV data
df = pd.read_csv(os.path.join(SCRIPT_DIR, "instagram_profiles.csv"))

# Helper function to extract numeric values
def extract_numeric(value):
    value = re.sub(r'\D', '', str(value))  # Remove non-numeric characters
    return int(value) if value else 0

# Criteria for detecting fake followers
def detect_fake_follower(row):
    # Parse followers, following, and posts columns
    followers = extract_numeric(row['followers'])
    following = extract_numeric(row['following'])
    posts = extract_numeric(row['posts'])
    
    # Calculate follower-to-following ratio
    if following > 0:
        follow_ratio = followers / following
    else:
        follow_ratio = 0

    # Username pattern
    username_pattern = r"(.)\1{2,}|[\W_]{2,}"
    is_suspicious_username = bool(re.search(username_pattern, row['username']))

    # Fake account criteria
    if (follow_ratio < 0.1 and following > 500) or posts < 5 or is_suspicious_username:
        return True  # Flagged as fake
    else:
        return False

# Apply the function to each row
df['is_fake'] = df.apply(detect_fake_follower, axis=1)

# Filter flagged accounts and drop duplicates by username
fake_accounts = df[df['is_fake']].drop_duplicates(subset='username')

# Select required columns and save to CSV
fake_accounts[['username', 'followers', 'following']].to_csv(
    os.path.join(SCRIPT_DIR, "suspicious-accounts.csv"),
    index=False,
)

# Print flagged accounts and the total number of fake followers
print(fake_accounts[['username', 'followers', 'following']])
print("Total number of fake followers:", fake_accounts.shape[0])
