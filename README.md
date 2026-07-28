# Instagram Automation Toolkit

This project contains multiple Instagram automation scripts for working with exported Instagram data and running browser-based actions such as unfollowing, blocking, unblocking, and hiding stories.

## What changed

The automation scripts now support using cookies from each account's own configuration file instead of requiring you to edit Python source code.

You can now run the main launcher, paste cookies in the browser-style format, and the tool will automatically convert them and save them to the correct account folder's config.json so the bot can use them.

---

## Folder structure overview

- main-v5.py: main launcher for the workflow
- 1-HTML-to-TXT/: converts exported Instagram HTML files into text lists
- 2-fake-by-username/: detects suspicious or fake-looking usernames
- 3-not-following-back/: finds accounts that are not following you back
- 4-block-bot/: block bot scripts
- 5-unfollow-bot/: unfollow bot scripts
- 6-unblock-bot/: unblock bot scripts
- 7-hide-from-story-bot/: hide-from-story bot scripts
- data/: browser driver and extracted data

---

## Requirements

Before running anything, make sure you have:

1. Python installed
2. The virtual environment created and activated
3. The required Python packages installed

You can install the project dependencies with:

```bash
pip install -r requirements.txt
```

If you are using the project virtual environment, activate it first:

On Windows PowerShell:

```powershell
.
\venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate again.

---

## How the cookie-based setup works

Each bot now reads cookies from its own config.json file.

That means:

- you do not need to edit the Python script
- you can keep separate cookie data for different accounts
- the bot reads the cookies automatically when it starts

### Where to put cookies

For example, for the unfollow bot, use the file:

- 5-unfollow-bot/high.octvne/config.json

For other bots, use the relevant folder's config.json file.

### What to put inside config.json

Open the config.json file for the account you want to use and add a top-level "cookies" object.

Example:

```json
{
  "webdriver_path": "data/chromedriver-win64/chromedriver.exe",
  "cookies": {
    "csrftoken": "your_value_here",
    "sessionid": "your_value_here",
    "ds_user_id": "your_value_here"
  }
}
```

You can also paste cookies in the browser table format directly during the main launcher flow. The tool will parse the pasted rows and save them in the correct config.json for that account.

> Important: the cookie values must be the actual values from your browser session. If the cookies are wrong or expired, Instagram may reject the login.

---

## How to run the main launcher

The main launcher is:

- main-v5.py

Run it with:

```bash
python main-v5.py
```

If you are using the virtual environment:

```bash
.
\venv\Scripts\python.exe main-v5.py
```

The launcher will ask you for:

- the account username
- whether you want to save cookies for that account
- the cookie data to paste
- whether to continue with the next step in the workflow
- the relevant file names and options

When prompted for cookies, you can paste data in any of these forms:

- browser-style tab-separated table
- JSON object
- JSON list
- key=value lines

The launcher will automatically convert the pasted content and store it in the selected account's bot folder config.json.

This is useful if you want to go through the full process of:

1. preparing export data
2. converting HTML files
3. detecting fake followers
4. finding accounts not following back
5. running the bot flow

---

## How to run the unfollow bot

The unfollow bot script is:

- 5-unfollow-bot/high.octvne/unfollow-bot-1000.py

### Recommended way

1. Run [main-v5.py](main-v5.py)
2. Enter the account username
3. When asked, paste the cookie block for that account
4. The launcher saves the cookies into the account folder config automatically
5. Run the bot script

### Manual alternative

If you already placed the cookies in the config.json file, you can run the script directly:

```bash
python 5-unfollow-bot/high.octvne/unfollow-bot-1000.py
```

Make sure the input file exists. The script expects a text file such as:

- 5-unfollow-bot/high.octvne/not_following_back-high.octvne.txt

```bash
python 5-unfollow-bot/high.octvne/unfollow-bot-1000.py
```

Or from the project root with the virtual environment:

```bash
.
\venv\Scripts\python.exe 5-unfollow-bot/high.octvne/unfollow-bot-1000.py
```

---

## How to run the block bot

The block bot script is located in:

- 4-block-bot/1Backup/block-bot-1000.py

### Steps

1. Open the folder:
   - 4-block-bot/1Backup/

2. Add the cookies in the config.json file inside that folder, or use the main launcher flow to save them there automatically.

3. Make sure the target username list file exists.

4. Run:

```bash
python 4-block-bot/1Backup/block-bot-1000.py
```

---

## How to run the unblock bot

The unblock bot script is:

- 6-unblock-bot/unblock.py

### Steps

1. Open the folder:
   - 6-unblock-bot/

2. Add the cookies in its config.json file, or use the main launcher flow to save them there automatically.

3. Run:

```bash
python 6-unblock-bot/unblock.py
```

---

## How to run the hide-from-story bot

The script is:

- 7-hide-from-story-bot/rj/hide_story_users.py

### Steps

1. Open the folder:
   - 7-hide-from-story-bot/rj/

2. Add the cookies in its config.json file, or use the main launcher flow to save them there automatically.

3. Make sure the username list file exists:
   - 7-hide-from-story-bot/rj/hide_from_story_usernames.txt

4. Run:

```bash
python 7-hide-from-story-bot/rj/hide_story_users.py
```

---

## Important notes

- The scripts use Selenium and Chrome/ChromeDriver.
- Make sure the ChromeDriver path is correct in config.json.
- If the browser session is not logged in, the bot may fail.
- Cookies are sensitive. Keep them private and do not share them.
- If Instagram changes its UI, the bot selectors may need to be updated.

---

## Troubleshooting

### Problem: "No cookies were found"

This means the config.json file in the bot folder does not contain a valid "cookies" object.

Fix:

- open the relevant config.json
- add the cookies under "cookies"

### Problem: browser does not start

Check:

- webdriver_path in config.json
- whether chromedriver.exe exists at that path
- whether Chrome is installed

### Problem: login fails

This usually means:

- the cookies are expired
- the cookies belong to a different account
- the cookies are incomplete

---

## Recommended workflow

1. Create or open the account folder you want to use.
2. Add cookies to that folder's config.json.
3. Run the relevant bot script.
4. If needed, use the main launcher to prepare the input files first.

---

## Example: run for one account

If you want to use the unfollow bot for the account in:

- 5-unfollow-bot/high.octvne/

then:

1. open [5-unfollow-bot/high.octvne/config.json](5-unfollow-bot/high.octvne/config.json)
2. add your cookies
3. run:

```bash
python 5-unfollow-bot/high.octvne/unfollow-bot-1000.py
```

That is all you need to do.
