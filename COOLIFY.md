# Coolify Deployment

Deploy το spitogatos monitor σε δικό σου server μέσω Coolify, χρησιμοποιώντας **ScrapingBee** ως residential proxy (αναγκαίο γιατί το spitogatos μπλοκάρει όλες τις datacenter IPs μέσω CloudFront WAF).

## Πώς δουλεύει

- Το container τρέχει συνέχεια αλλά είναι idle (`sleep infinity`).
- Coolify **Scheduled Task** εκτελεί το script κάθε μέρα στις 04:00 UTC (~07:00 Ελλάδα).
- Το script κάνει request στο **ScrapingBee API** με Greek residential proxy και παίρνει το rendered HTML.
- Volume στο `/app/data` διατηρεί το `seen_apartments.json` ανάμεσα σε runs.

## Setup steps

### 1. ScrapingBee account (δωρεάν)

- Φτιάξε account στο [scrapingbee.com](https://www.scrapingbee.com/) — δωρεάν 1.000 credits/μήνα
- Κάθε run κοστίζει 25 credits (premium proxy + JS rendering) → ~40 runs/μήνα, αρκεί για daily
- Στο dashboard, αντίγραψε το **API Key**

### 2. Νέα Application στο Coolify

- `+ New` → `Public Repository`
- Repository: `https://github.com/pete79cy/spitogatos-monitor`
- Branch: `main`
- Build Pack: **Dockerfile**
- Port: άσε κενό (δεν εκθέτει port)

### 3. Persistent Storage

Storage tab → `+ Add` → **Volume**
- Source name: `spitogatos-data`
- Destination path: `/app/data`

### 4. Environment Variables

| Key | Value |
|-----|-------|
| `SCRAPINGBEE_API_KEY` | API key από το ScrapingBee dashboard |
| `TELEGRAM_BOT_TOKEN` | token από @BotFather |
| `TELEGRAM_CHAT_ID` | chat id σου |

### 5. Deploy

`Deploy` button. Στα logs θα δεις `sleep infinity` — σωστό.

### 6. Scheduled Task

Στο **Scheduled Tasks** tab:
- `+ Add Scheduled Task`
- Name: `daily-check`
- Command: `python /app/spitogatos_monitor.py`
- Frequency: `0 4 * * *`

### 7. Manual test

Στο Terminal της εφαρμογής:
```bash
python /app/spitogatos_monitor.py
```

Θα δεις `🐝 Fetching via ScrapingBee...` και θα παρθούν οι αγγελίες.

## Troubleshooting

- **`ScrapingBee returned 401`** → λάθος ή λείπει το `SCRAPINGBEE_API_KEY`.
- **`ScrapingBee returned 402`** → τέλειωσαν τα δωρεάν credits του μήνα (πάνε στο dashboard για πληροφορίες).
- **`Got bot-protection / CloudFront page`** → δοκίμασε `country_code=eu` αντί για `gr` στον κώδικα, ή γύρισε το `premium_proxy` σε `stealth_proxy`.
- **Cron δεν τρέχει** → έλεγξε ότι το Scheduled Task είναι enabled και βλέπει το ίδιο container.

## GH Actions vs Coolify

⚠️ Διάλεξε ένα. Αν χρησιμοποιείς Coolify, disable το GitHub Actions workflow:
[github.com/pete79cy/spitogatos-monitor/actions](https://github.com/pete79cy/spitogatos-monitor/actions) → `Daily Apartment Monitor` → `...` → `Disable workflow`.
