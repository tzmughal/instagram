import json
import os
import tempfile
import unittest

from instagram_common import parse_cookie_data, save_cookies_to_config


class InstagramCommonTests(unittest.TestCase):
    def test_parse_cookie_data_from_browser_table(self):
        sample = """csrftoken\td9TFW4knxZQS6AxkvvKCMZvhOGJsZQc0\t.instagram.com\t/\t2027-08-10T22:00:23.172Z\t41\t\t\tMedium
sessionid\t60002686137%3AE1CM5zeruXJdDM%3A3%3AAYiNb3MDOg2cq7nbPxWD57VF5uoIXxIOlclwIlK84po\t.instagram.com\t/\t2027-07-06T20:35:10.838Z\t87\t\t\tMedium
"""

        cookies = parse_cookie_data(sample)

        self.assertEqual(cookies["csrftoken"], "d9TFW4knxZQS6AxkvvKCMZvhOGJsZQc0")
        self.assertEqual(cookies["sessionid"], "60002686137%3AE1CM5zeruXJdDM%3A3%3AAYiNb3MDOg2cq7nbPxWD57VF5uoIXxIOlclwIlK84po")

    def test_save_cookies_to_config_preserves_existing_settings(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = os.path.join(tmp_dir, "config.json")
            with open(config_path, "w", encoding="utf-8") as handle:
                json.dump({"webdriver_path": "chromedriver.exe", "existing": True}, handle)

            save_cookies_to_config(config_path, {"csrftoken": "abc"})

            with open(config_path, "r", encoding="utf-8") as handle:
                saved = json.load(handle)

            self.assertEqual(saved["webdriver_path"], "chromedriver.exe")
            self.assertEqual(saved["existing"], True)
            self.assertEqual(saved["cookies"]["csrftoken"], "abc")


if __name__ == "__main__":
    unittest.main()
