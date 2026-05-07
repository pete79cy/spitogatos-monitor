#!/usr/bin/env python3
"""
Spitogatos.gr Student Apartment Monitor
Checks for new student apartments in Heraklion (Crete) and sends notifications.

Two fetch paths:
  1. ScrapingBee API (used when SCRAPINGBEE_API_KEY is set) — for VPS/datacenter
     IPs that CloudFront blocks. Routes through Greek residential proxies.
  2. Playwright headed Chromium + stealth — for local dev from a residential IP.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://www.spitogatos.gr/en/to_rent-homes/heraclion-cretes/student_houses/last_update_24h/first_publish_24h"
HOME_URL = "https://www.spitogatos.gr/"
DATA_DIR = Path(os.getenv("DATA_DIR", str(Path(__file__).parent)))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATA_FILE = DATA_DIR / "seen_apartments.json"

SCRAPINGBEE_API_KEY = os.getenv("SCRAPINGBEE_API_KEY", "")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

EMAIL_TO = os.getenv("EMAIL_TO", "")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT") or "587")
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def load_seen_apartments():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"apartments": {}, "last_check": None}


def save_seen_apartments(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _save_debug(html: str, tag: str) -> None:
    try:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = DATA_DIR / f"debug-{tag}-{ts}.html"
        path.write_text(html, encoding="utf-8")
        print(f"🐞 Debug saved: {path.name}")
    except Exception as e:
        print(f"⚠️  Could not save debug: {e}")


def _extract_price_from_alt(alt: str) -> str:
    if not alt:
        return ""
    m = re.search(r"€\s*[\d.,]+\s*/\s*\w+", alt)
    return m.group(0).strip() if m else ""


def fetch_html_via_scrapingbee() -> str:
    """Fetch the search page through ScrapingBee with a Greek residential proxy."""
    print("🐝 Fetching via ScrapingBee (premium proxy, GR)...")
    r = requests.get(
        "https://app.scrapingbee.com/api/v1/",
        params={
            "api_key": SCRAPINGBEE_API_KEY,
            "url": URL,
            "render_js": "true",
            "premium_proxy": "true",
            "country_code": "gr",
            "wait": "5000",
            "wait_for": "article",
        },
        timeout=120,
    )
    if r.status_code != 200:
        raise RuntimeError(f"ScrapingBee returned {r.status_code}: {r.text[:300]}")
    return r.text


def fetch_html_via_playwright() -> str:
    """Local-dev path: headed Chromium with stealth + homepage warm-up."""
    from playwright.sync_api import sync_playwright
    from playwright_stealth import Stealth

    print("🎭 Fetching via Playwright (local, residential IP required)...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(
            user_agent=USER_AGENT,
            locale="el-GR",
            viewport={"width": 1920, "height": 1080},
        )
        Stealth().apply_stealth_sync(ctx)
        page = ctx.new_page()
        try:
            page.goto(HOME_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)
            page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            try:
                page.wait_for_selector("article", timeout=20000)
            except Exception:
                pass
            page.wait_for_timeout(3000)
            return page.content()
        finally:
            browser.close()


def parse_apartments(html: str) -> list:
    """Parse listing data out of the search-results HTML."""
    soup = BeautifulSoup(html, "html.parser")
    apartments = []

    for art in soup.select("article"):
        a = art.select_one("a.tile__link") or art.select_one("a[href*='/property/']")
        if not a:
            continue

        href = a.get("href", "")
        link = href if href.startswith("http") else f"https://www.spitogatos.gr{href}"
        m = re.search(r"/property/(\d+)", link)
        apt_id = m.group(1) if m else link

        def text_of(sel):
            el = art.select_one(sel)
            return el.get_text(strip=True) if el else ""

        title = text_of(".tile__title")
        location = text_of(".tile__location")

        price = ""
        for sel in [".tile__price", "[class*=price]"]:
            price = text_of(sel)
            if price:
                break
        if not price:
            img = art.select_one("img")
            price = _extract_price_from_alt(img.get("alt", "") if img else "")

        size = ""
        sm = re.search(r"(\d+\s*m²)", title)
        if sm:
            size = sm.group(1)

        apartments.append({
            "id": apt_id,
            "title": title or "No title",
            "price": price,
            "location": location,
            "size": size,
            "link": link,
            "found_at": datetime.now().isoformat(),
        })

    return apartments


def fetch_apartments() -> list:
    try:
        if SCRAPINGBEE_API_KEY:
            html = fetch_html_via_scrapingbee()
        else:
            html = fetch_html_via_playwright()
    except Exception as e:
        print(f"❌ Fetch error: {e}")
        return []

    if "Pardon Our" in html or "ERROR: The request could not be satisfied" in html:
        print("⚠️  Got bot-protection / CloudFront page.")
        _save_debug(html, "blocked")
        return []

    apartments = parse_apartments(html)
    print(f"📋 Parsed {len(apartments)} listings")
    if not apartments:
        _save_debug(html, "no_articles")
    return apartments


def send_telegram_notification(apartments):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    message = "🏠 *Νέα Φοιτητικά Διαμερίσματα στο Ηράκλειο*\n\n"
    message += f"Βρέθηκαν {len(apartments)} νέες αγγελίες:\n\n"
    for apt in apartments[:10]:
        message += f"🔹 *{apt['title']}*\n"
        if apt["price"]:
            message += f"💰 {apt['price']}\n"
        if apt["location"]:
            message += f"📍 {apt['location']}\n"
        if apt["size"]:
            message += f"📏 {apt['size']}\n"
        if apt["link"]:
            message += f"🔗 [Δες Αγγελία]({apt['link']})\n"
        message += "\n"
    if len(apartments) > 10:
        message += f"\n... και {len(apartments) - 10} ακόμα αγγελίες"

    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=30,
        )
        r.raise_for_status()
        print("✅ Telegram notification sent")
    except Exception as e:
        print(f"❌ Failed to send Telegram notification: {e}")


def send_email_notification(apartments):
    if not all([EMAIL_TO, SMTP_USER, SMTP_PASSWORD]):
        return
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    subject = f"🏠 {len(apartments)} Νέα Φοιτητικά Διαμερίσματα στο Ηράκλειο"
    html = [
        "<html><head><style>",
        "body{font-family:Arial,sans-serif}",
        ".apartment{border:1px solid #ddd;padding:15px;margin:10px 0;border-radius:5px}",
        ".title{font-size:18px;font-weight:bold;color:#2c3e50}",
        ".price{color:#e74c3c;font-size:16px;font-weight:bold}",
        ".link{color:#3498db;text-decoration:none}",
        "</style></head><body>",
        "<h2>Νέα Φοιτητικά Διαμερίσματα στο Ηράκλειο</h2>",
        f"<p>Βρέθηκαν {len(apartments)} νέες αγγελίες:</p>",
    ]
    for apt in apartments:
        html.append('<div class="apartment">')
        html.append(f'<div class="title">{apt["title"]}</div>')
        if apt["price"]:
            html.append(f'<div class="price">{apt["price"]}</div>')
        if apt["location"]:
            html.append(f'<div>📍 {apt["location"]}</div>')
        if apt["size"]:
            html.append(f'<div>📏 {apt["size"]}</div>')
        if apt["link"]:
            html.append(f'<div><a class="link" href="{apt["link"]}">Δες Αγγελία →</a></div>')
        html.append("</div>")
    html.append("</body></html>")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText("\n".join(html), "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        print("✅ Email notification sent")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")


def main():
    print(f"\n{'='*60}")
    print("🔍 Checking for new student apartments in Heraklion")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    data = load_seen_apartments()
    seen_ids = set(data.get("apartments", {}).keys())

    apartments = fetch_apartments()
    if not apartments:
        print("⚠️  No apartments found.")
        return

    new_apartments = [a for a in apartments if a["id"] not in seen_ids]
    for apt in new_apartments:
        data["apartments"][apt["id"]] = apt

    if new_apartments:
        print(f"\n🎉 {len(new_apartments)} NEW apartments!\n")
        for apt in new_apartments:
            print(f"🏠 {apt['title']}")
            if apt["price"]:
                print(f"   💰 {apt['price']}")
            if apt["location"]:
                print(f"   📍 {apt['location']}")
            if apt["size"]:
                print(f"   📏 {apt['size']}")
            if apt["link"]:
                print(f"   🔗 {apt['link']}")
            print()
        send_telegram_notification(new_apartments)
        send_email_notification(new_apartments)
    else:
        print("✅ No new apartments since last check")

    data["last_check"] = datetime.now().isoformat()
    save_seen_apartments(data)
    print(f"\n{'='*60}\n✅ Check complete\n{'='*60}\n")


if __name__ == "__main__":
    main()
