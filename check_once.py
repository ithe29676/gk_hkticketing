
import os
import json
import requests

from playwright.sync_api import sync_playwright

# ============ CONFIG ============

URL = "https://hkt.hkticketing.com/hant/#/allEvents/detail?projectId=50000001568003"
STATUS_KEYWORD = "暫無可售"  # "currently unavailable"
STATE_FILE = "last_seen_hkt.json"

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# ============ end config ============


def fetch_rendered_text(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)
        text = page.inner_text("body")
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
    is_unavailable = STATUS_KEYWORD in full_text
    current_status = "UNAVAILABLE" if is_unavailable else "AVAILABLE_MAYBE"

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
