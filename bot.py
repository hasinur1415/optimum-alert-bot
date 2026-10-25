import os
import json
import time
import html
import requests
import feedparser

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

ACCOUNTS_TO_MONITOR = [
    {
        "username": "hasinur1995",
        "name": "Hasinur (Developer)",
        "rss_url": "https://rss.app/feeds/AtCk8ajlszCfHgXs.xml"
    },
    {
        "username": "get_optimum",
        "name": "Optimum",
        "rss_url": "https://rss.app/feeds/dsQSOcb6QfYarYru.xml"
    }
]

DB_FILE = "posted_tweets.json"

def load_sent_tweets():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception as e:
            print(f"[Warn] Failed to load DB file: {e}")
            return set()
    return set()

def save_sent_tweets(tweets_set):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(tweets_set)), f, indent=2, ensure_ascii=False)

def clean_text(raw_text):
    if not raw_text:
        return ""
    text = html.unescape(raw_text)
    # Escape HTML special chars for Telegram HTML parse_mode
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return text.strip()

def send_telegram(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Error] Missing Telegram Bot Token or Chat ID!")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        res = requests.post(url, json=payload, timeout=15)
        if res.status_code == 200:
            return True
        else:
            print(f"[Error] Telegram API error {res.status_code}: {res.text}")
            return False
    except Exception as e:
        print(f"[Error] Failed to send Telegram alert: {e}")
        return False

def check_account(account, sent_tweets):
    username = account["username"]
    display_name = account["name"]
    rss_url = account["rss_url"]

    print(f"[*] Checking feed for @{username}...")

    try:
        feed = feedparser.parse(rss_url, request_headers={"User-Agent": "Mozilla/5.0"})
        if not feed.entries:
            print(f"[Info] No entries found in feed for @{username}")
            return

        print(f"[i] Found {len(feed.entries)} entries in @{username} feed.")

        # Traverse entries in chronological order (oldest to newest)
        for entry in reversed(feed.entries):
            guid = entry.get("id") or entry.get("guid") or ""
            link = entry.get("link") or ""

            # If either the GUID or the link has been seen, skip it
            if (guid and guid in sent_tweets) or (link and link in sent_tweets):
                continue

            raw_title = entry.get("title", "")
            title = clean_text(raw_title)

            # Determine if it's a repost/retweet or an original post
            if title.startswith("RT by"):
                header = f"🔁 <b>Repost by {display_name} (@{username})</b>"
            else:
                header = f"🔔 <b>New Post from {display_name} (@{username})</b>"

            message = f"{header}\n\n{title}\n\n🔗 <a href='{link}'>View on X</a>"

            print(f"[+] Sending alert for new post from @{username}: {link}")
            if send_telegram(message):
                if guid:
                    sent_tweets.add(guid)
                if link:
                    sent_tweets.add(link)
                save_sent_tweets(sent_tweets)
                time.sleep(1)

    except Exception as e:
        print(f"[Error] Checking @{username} failed: {e}")

def main():
    sent_tweets = load_sent_tweets()
    print(f"[*] Loaded {len(sent_tweets)} seen items from database.")

    # Process all accounts
    for acc in ACCOUNTS_TO_MONITOR:
        check_account(acc, sent_tweets)

    save_sent_tweets(sent_tweets)
    print("[✓] Check completed.")

if __name__ == "__main__":
    main()
