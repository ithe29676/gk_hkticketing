import os
import json
import requests

from playwright.sync_api import sync_playwright

# ============ CONFIG ============

URL = "https://hkt.hkticketing.com/hant/#/allEvents/detail?projectId=50000001568003"
STATUS_KEYWORD = "暫無可售"   # shown while tickets are NOT available
MIN_PAGE_LENGTH = 200         # shorter than this = page didn't really load
MAX_WAIT_SECONDS = 15         # how long to wait for the keyword to appear
STATE_FILE = "last_seen.json"

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# ============ end config ============


def fetch_rendered_text(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=60000)

        text = ""
        for _ in range(MAX_WAIT_SECONDS):
            text = page.inner_text("body")
            if STATUS_KEYWORD in text:
                break  # found it, no need to wait longer
            page.wait_for_timeout(1000)

        browser.close()
        return text


def load_last_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_state(status: str):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"status": status}, f, ensure_ascii=False, indent=2)


def send_telegram_message(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text[:4000],
    }, timeout=30)
    resp.raise_for_status()


def main():
    last = load_last_state()

    full_text = fetch_rendered_text(URL)
    print("---- page text (first 1500 chars) ----")
    print(full_text[:1500])
    print("---- end ----")

    if len(full_text.strip()) < MIN_PAGE_LENGTH:
        print("Page did not load properly - skipping this check, no change saved.")
        return

    current_status = "UNAVAILABLE" if STATUS_KEYWORD in full_text else "AVAILABLE_MAYBE"
    print(f"Current status: {current_status}")

    if last is None:
        print("First run - saving baseline status. No message sent.")
        save_state(current_status)
        return

    if current_status != last["status"]:
        print(f"STATUS CHANGED: {last['status']} -> {current_status} - sending Telegram message.")
        message = (
            f"🎟️ HK Ticketing status changed!\n"
            f"Was: {last['status']} -> Now: {current_status}\n\n"
            f"Check tickets now:\n{URL}"
        )
        send_telegram_message(message)
        save_state(current_status)
    else:
        print("No status change.")


if __name__ == "__main__":
    main()
