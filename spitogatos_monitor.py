#!/usr/bin/env python3
"""
Spitogatos.gr Student Apartment Monitor
Checks for new student apartments in Heraklion (Crete) and sends notifications.

Uses Playwright (headed Chromium + stealth) to bypass the bot-protection page.
On Linux/CI run via xvfb-run so a virtual display is available.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

URL = "https://www.spitogatos.gr/en/to_rent-homes/heraclion-cretes/student_houses/last_update_24h/first_publish_24h"
HOME_URL = "https://www.spitogatos.gr/"
DATA_DIR = Path(os.getenv("DATA_DIR", str(Path(__file__).parent)))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATA_FILE = DATA_DIR / "seen_apartments.json"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

EMAIL_TO = os.getenv("EMAIL_TO", "")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
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


def _extract_price_from_alt(alt: str) -> str:
    if not alt:
        return ""
    m = re.search(r"€\s*[\d.,]+\s*/\s*\w+", alt)
    return m.group(0).strip() if m else ""


def fetch_apartments():
    """Fetch apartments from Spitogatos using Playwright."""
    apartments = []

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
            # Warm-up homepage so the bot-protection sets cookies
            page.goto(HOME_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)

            page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(6000)

            if "Pardon Our" in page.content():
                print("⚠️  Hit bot-protection page. Aborting.")
                return apartments

            articles = page.locator("article")
            count = articles.count()
            print(f"📋 Page rendered, {count} article elements found")

            for i in range(count):
                art = articles.nth(i)

                link = ""
                a = art.locator("a.tile__link").first
                if a.count() > 0:
                    href = a.get_attribute("href") or ""
                    link = href if href.startswith("http") else f"https://www.spitogatos.gr{href}"

                m = re.search(r"/property/(\d+)", link)
                apt_id = m.group(1) if m else link

                def text_of(selector):
                    loc = art.locator(selector).first
                    return loc.inner_text().strip() if loc.count() > 0 else ""

                title = text_of(".tile__title")
                location = text_of(".tile__location")

                # Price: try a price element, fall back to image alt
                price = ""
                for sel in [".tile__price", "[class*=price]"]:
                    price = text_of(sel)
                    if price:
                        break
                if not price:
                    img = art.locator("img").first
                    alt = img.get_attribute("alt") if img.count() > 0 else ""
                    price = _extract_price_from_alt(alt or "")

                # Size: parse from title ("Studio, 40m²") or use whole title
                size = ""
                sm = re.search(r"(\d+\s*m²)", title)
                if sm:
                    size = sm.group(1)

                if apt_id:
                    apartments.append({
                        "id": apt_id,
                        "title": title or "No title",
                        "price": price,
                        "location": location,
                        "size": size,
                        "link": link,
                        "found_at": datetime.now().isoformat(),
                    })
        finally:
            browser.close()

    return apartments


def send_telegram_notification(apartments):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    import requests

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

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, json=data, timeout=30)
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
        f"<h2>Νέα Φοιτητικά Διαμερίσματα στο Ηράκλειο</h2>",
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
    print(f"🔍 Checking for new student apartments in Heraklion")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    data = load_seen_apartments()
    seen_ids = set(data.get("apartments", {}).keys())

    apartments = fetch_apartments()

    if not apartments:
        print("⚠️  No apartments found. Could mean: no new listings, site changed, or blocked.")
        return

    print(f"📋 Parsed {len(apartments)} listings")

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
