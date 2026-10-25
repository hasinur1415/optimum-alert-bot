import os
import json
import time
import requests
import feedparser

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

ACCOUNTS_TO_MONITOR = [
    {"username": "get_optimum", "name": "Optimum"},
    {"username": "hasinur1995", "name": "Hasinur (Developer)"}
]

DB_FILE = "posted_tweets.json"

def load_sent_tweets():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_sent_tweets(tweets_set):
    with open(DB_FILE, "w") as f:
        json.dump(list(tweets_set), f, indent=2)

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
        return res.status_code == 200
    except Exception as e:
        print(f"[Error] Failed to send Telegram alert: {e}")
        return False

def check_account(account, sent_tweets):
    username = account["username"]
    display_name = account["name"]
    rss_url = f"https://rsshub.app/twitter/user/{username}"

    try:
        feed = feedparser.parse(rss_url, request_headers={"User-Agent": "Mozilla/5.0"})
        if not feed.entries:
            print(f"[Info] No new items found for @{username}")
            return

        for entry in reversed(feed.entries[:5]):
            tweet_id = entry.get("id") or entry.get("link")

            if tweet_id not in sent_tweets:
                title = entry.get("title", "")
                link = entry.get("link", f"https://x.com/{username}")

                message = (
                    f"🔔 <b>New Post from {display_name} (@{username})</b>\n\n"
                    f"{title}\n\n"
                    f"🔗 <a href='{link}'>View on X</a>"
                )

                print(f"[+] Alerting for @{username}: {link}")
                if send_telegram(message):
                    sent_tweets.add(tweet_id)
                    time.sleep(1)

    except Exception as e:
        print(f"[Error] Checking @{username} failed: {e}")

def main():
    sent_tweets = load_sent_tweets()
    initial_run = (len(sent_tweets) == 0)

    if initial_run:
        print("[!] Initial run: saving existing tweets to avoid spamming old posts...")
        for acc in ACCOUNTS_TO_MONITOR:
            rss_url = f"https://rsshub.app/twitter/user/{acc['username']}"
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:5]:
                tweet_id = entry.get("id") or entry.get("link")
                if tweet_id:
                    sent_tweets.add(tweet_id)
        save_sent_tweets(sent_tweets)
        print("[✓] Setup complete. Next runs will trigger on fresh tweets.")
        return

    for acc in ACCOUNTS_TO_MONITOR:
        check_account(acc, sent_tweets)

    save_sent_tweets(sent_tweets)

if __name__ == "__main__":
    main()
