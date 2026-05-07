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
    r.encoding = "utf-8"  # response has UTF-8 bytes but no charset header → force it
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
        description = text_of(".tile__description")

        price = ""
        for sel in [".tile__price", "[class*=price]"]:
            price = text_of(sel)
            if price:
                break
        if not price:
            img_alt_for_price = art.select_one("img")
            price = _extract_price_from_alt(img_alt_for_price.get("alt", "") if img_alt_for_price else "")

        size = ""
        sm = re.search(r"(\d+\s*m²)", title)
        if sm:
            size = sm.group(1)

        # Extract floor / bedrooms / bathrooms from .tile__info <li title="...">
        floor = bedrooms = bathrooms = ""
        for li in art.select(".tile__info li"):
            label = (li.get("title") or "").lower()
            value = re.sub(r"\s+", " ", li.get_text(" ", strip=True))
            if label == "floor":
                floor = value
            elif label == "bedrooms":
                bedrooms = value
            elif label == "bathrooms":
                bathrooms = value

        # Image URL: prefer src, fall back to data-src
        image = ""
        img = art.select_one("img")
        if img:
            image = img.get("src") or img.get("data-src") or ""

        apartments.append({
            "id": apt_id,
            "title": title or "No title",
            "price": price,
            "location": location,
            "size": size,
            "description": description,
            "floor": floor,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "image": image,
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


def _to_greek(s: str) -> str:
    """Translate common English terms to Greek for display."""
    if not s:
        return s
    rules = [
        (r"Heraklion Cretes", "Ηράκλειο Κρήτης"),
        (r"Heraklion Prefecture", "Νομός Ηρακλείου"),
        (r"\bStudio\b", "Στούντιο"),
        (r"\bApartment\b", "Διαμέρισμα"),
        (r"\bMaisonette\b", "Μεζονέτα"),
        (r"\bLoft\b", "Λοφτ"),
        (r"\bHouse\b", "Σπίτι"),
        (r"\bDetached House\b", "Μονοκατοικία"),
        (r"\bCenter\b", "Κέντρο"),
        (r"/\s*month\b", "/ μήνα"),
        (r"(\d+)\s*m²", r"\1 τμ"),
        (r"(\d+)\s*sq\.?m\.?", r"\1 τμ"),
        (r"(\d+)\s*br\b", r"\1 υπν."),
        (r"(\d+)\s*ba\b", r"\1 μπ."),
        (r"(\d+)\s*(?:st|nd|rd|th)\b", r"\1ος"),
    ]
    for pat, rep in rules:
        s = re.sub(pat, rep, s)
    return s


def _html_escape(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _build_caption(apt: dict, max_len: int = 1024) -> str:
    """Build an HTML-formatted Telegram caption for one apartment (≤1024 chars)."""
    parts = [f"<b>🏠 {_html_escape(_to_greek(apt['title']))}</b>"]
    if apt.get("price"):
        parts.append(f"💰 <b>{_html_escape(_to_greek(apt['price']))}</b>")
    if apt.get("location"):
        parts.append(f"📍 {_html_escape(_to_greek(apt['location']))}")

    specs = []
    if apt.get("bedrooms"):
        specs.append(f"🛏 {_html_escape(_to_greek(apt['bedrooms']))}")
    if apt.get("bathrooms"):
        specs.append(f"🛁 {_html_escape(_to_greek(apt['bathrooms']))}")
    if apt.get("floor"):
        specs.append(f"🏢 {_html_escape(_to_greek(apt['floor']))}")
    if specs:
        parts.append(" · ".join(specs))

    desc = (apt.get("description") or "").strip()
    if desc:
        desc = re.sub(r"\s+", " ", desc)
        budget = max_len - sum(len(p) + 1 for p in parts) - 80
        if budget > 60:
            preview = desc[:budget].rstrip()
            if len(desc) > budget:
                preview += "…"
            parts.append(f"\n📝 {_html_escape(preview)}")

    if apt.get("link"):
        parts.append(f'\n<a href="{_html_escape(apt["link"])}">🔗 Δες αγγελία</a>')

    return "\n".join(parts)[:max_len]


def _telegram_send_photo(photo_url: str, caption: str) -> bool:
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "photo": photo_url,
            "caption": caption,
            "parse_mode": "HTML",
        },
        timeout=30,
    )
    return r.ok


def _telegram_send_message(text: str) -> bool:
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    return r.ok


def send_telegram_notification(apartments):
    """Send one Telegram message per apartment (photo + rich caption)."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    MAX_MESSAGES = 15  # avoid spamming on first run / huge result sets

    header = (
        f"🏠 <b>Νέα Φοιτητικά Διαμερίσματα στο Ηράκλειο</b>\n"
        f"Βρέθηκαν <b>{len(apartments)}</b> νέες αγγελίες"
    )
    if len(apartments) > MAX_MESSAGES:
        header += f" — στέλνω τις πρώτες {MAX_MESSAGES}"
    _telegram_send_message(header)

    sent = 0
    for apt in apartments[:MAX_MESSAGES]:
        caption = _build_caption(apt)
        ok = False
        if apt.get("image"):
            ok = _telegram_send_photo(apt["image"], caption)
        if not ok:
            # Fall back to text-only if photo failed (e.g. invalid URL)
            ok = _telegram_send_message(caption)
        if ok:
            sent += 1
        else:
            print(f"❌ Telegram send failed for {apt.get('id')}")

    print(f"✅ Telegram: sent {sent}/{min(len(apartments), MAX_MESSAGES)} listings")


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
