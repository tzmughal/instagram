import glob
import os
from bs4 import BeautifulSoup

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Function to extract usernames from HTML files
def extract_usernames_from_html(html_files):
    usernames = []
    
    for html_file in html_files:
        with open(html_file, 'r', encoding='utf-8') as file:
            # Parse the HTML file
            soup = BeautifulSoup(file, 'html.parser')
            
            # Find all anchor tags with href containing "instagram.com"
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                if "instagram.com" in href:
                    # Extract the username from the anchor tag text
                    username = a_tag.text.strip()
                    usernames.append(username)
    
    return usernames

# Specify the pattern to match all HTML files in the Followers HTML folder
followers_html_files = glob.glob(os.path.join(SCRIPT_DIR, 'Followers HTML', 'followers_*.html'))
# Extract usernames from followers
followers = set(extract_usernames_from_html(followers_html_files))

# Specify the single following.html file in the Following HTML folder
followings_html_file = os.path.join(SCRIPT_DIR, 'Following HTML', 'following.html')
# Extract usernames from followings
followings = set(extract_usernames_from_html([followings_html_file]))

# Subtract followings from followers to get people who follow you but whom you don’t follow back
not_following_back = followers - followings

# Prompt the user to input the account's username
account_username = input("Enter the account username: ")

# Build the output file name as "username" + (account_username) + ".txt"
output_filename = "usernames"+ "-" + account_username + ".txt"
output_path = os.path.join(SCRIPT_DIR, output_filename)

# Save the result to the output file
with open(output_path, 'w', encoding='utf-8') as outfile:
    for username in not_following_back:
        outfile.write(username + '\n')

print(f"Usernames have been saved to {output_path}")
