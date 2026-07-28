import glob
import os
from bs4 import BeautifulSoup

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Function to extract usernames from HTML and save them to a file
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

# Save the result to a file
with open(os.path.join(SCRIPT_DIR, 'usernames.txt'), 'w', encoding='utf-8') as outfile:
    for username in not_following_back:
        outfile.write(username + '\n')

print(f"Usernames of followers you don't follow back have been saved ")
