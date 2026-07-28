import json
import os


def load_json_file(path):
    if not path or not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_cookie_data(cookie_data):
    if not cookie_data:
        return {}

    if isinstance(cookie_data, dict):
        if "cookies" in cookie_data and isinstance(cookie_data["cookies"], dict):
            return cookie_data["cookies"]
        return cookie_data

    if isinstance(cookie_data, list):
        cookies = {}
        for item in cookie_data:
            if isinstance(item, dict):
                name = item.get("name") or item.get("key")
                value = item.get("value")
                if name and value is not None:
                    cookies[str(name)] = str(value)
        return cookies

    if isinstance(cookie_data, str):
        cookies = {}
        for raw_line in cookie_data.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("{") or line.startswith("["):
                try:
                    parsed = json.loads(line)
                    return parse_cookie_data(parsed)
                except Exception:
                    pass

            if "\t" in line:
                parts = [part.strip() for part in line.split("\t")]
                if len(parts) >= 2:
                    name = parts[0]
                    value = parts[1]
                    if name and value:
                        cookies[name] = value
                continue

            if "=" in line:
                name, value = line.split("=", 1)
                cookies[name.strip()] = value.strip()
        return cookies

    return {}


def load_cookies_from_config(config_path):
    config_data = load_json_file(config_path)
    if not config_data:
        return {}
    cookies = config_data.get("cookies")
    if cookies:
        return parse_cookie_data(cookies)
    return parse_cookie_data(config_data)


def save_cookies_to_path(path, cookies):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(cookies, handle, indent=4)


def save_cookies_to_config(config_path, cookies):
    if not config_path:
        return

    config_data = load_json_file(config_path) or {}
    if not isinstance(config_data, dict):
        config_data = {}

    config_data["cookies"] = cookies
    with open(config_path, "w", encoding="utf-8") as handle:
        json.dump(config_data, handle, indent=4)
