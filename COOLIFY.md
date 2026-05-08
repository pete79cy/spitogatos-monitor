# Coolify Deployment

Deploy το spitogatos monitor + dashboard στο δικό σου Coolify server.

## Αρχιτεκτονική

```
[Coolify Cron 04:00 UTC] ──► spitogatos_monitor.py
                              ├─ Fetch via ScrapingBee (residential proxy)
                              ├─ Parse → seen_apartments.json
                              ├─ Render → /app/data/web/{index.html, YYYY-MM-DD.html}
                              └─ Telegram: photos + dashboard link

[24/7 container]  ──►  serve.py (port 8000, HTTP Basic Auth)
                       └─ exposed by Coolify σε https://<assigned-domain>
```

## Setup steps

### 1. ScrapingBee account

[scrapingbee.com](https://www.scrapingbee.com/) → δωρεάν 1.000 credits/μήνα. Αντίγραψε το API key.

### 2. Νέα Application στο Coolify

- `+ New` → **Public Repository**: `https://github.com/pete79cy/spitogatos-monitor`
- Branch: `main` · Build Pack: **Dockerfile**
- **Port: 8000** (το dashboard server ακούει εκεί)
- Στο tab **Domains**, άσε το Coolify να generate-άρει domain (ένα κλικ → SSL αυτόματα)

### 3. Persistent Storage

Storage tab → `+ Add` → **Volume**
- Source name: `spitogatos-data`
- Destination path: `/app/data`

### 4. Environment Variables

| Key | Value | Notes |
|-----|-------|-------|
| `SCRAPINGBEE_API_KEY` | … | Από ScrapingBee dashboard |
| `TELEGRAM_BOT_TOKEN` | … | Από @BotFather |
| `TELEGRAM_CHAT_ID` | … | Από `getUpdates` |
| `DASHBOARD_USER` | π.χ. `pete` | Username για το web dashboard |
| `DASHBOARD_PASSWORD` | … | Password για το web dashboard |
| `DASHBOARD_URL` | π.χ. `https://spitogatos-xxx.coolify.your` | Coolify-assigned URL — βάλ' το ΜΕΤΑ τη πρώτη deployment |

### 5. Deploy

`Deploy` → Στα logs θα δεις: `[serve] Root: /app/data/web  Port: 8000  Auth: on`.
Επίσκεψε το assigned domain → θα ζητήσει user/password → θα δεις το dashboard
(άδειο μέχρι να τρέξει το πρώτο cron).

### 6. Πρόσθεσε το `DASHBOARD_URL` στα env vars

Αφού το Coolify εκχωρήσει domain, αντίγραψέ το και βάλε σε νέο env var
`DASHBOARD_URL`. Redeploy. Από εδώ και πέρα κάθε Telegram header θα έχει link
στο dashboard.

### 7. Scheduled Task

Scheduled Tasks tab → `+ Add`:
- Name: `daily-check`
- Command: `python /app/spitogatos_monitor.py`
- Frequency: `0 4 * * *`

### 8. Manual test

Coolify Terminal → `python /app/spitogatos_monitor.py`. Στα logs:
```
🐝 Fetching via ScrapingBee...
📋 Parsed 30 listings
📄 Dashboard written: index.html, 2026-05-08.html (30 listings)
✅ Telegram: sent 15/15 listings
```

## Dashboard features

- Συγκριτικός πίνακας με sort σε όλες τις στήλες
- Filter ανά συνοικία, τύπο, μέγιστη τιμή, ελάχιστα τμ, μόνο νέες
- Στατιστικά: σύνολο, εύρος, μέσος όρος, νέες σήμερα
- Charts: κατανομή τιμών + μέση τιμή ανά συνοικία
- Ημερήσια snapshots (`YYYY-MM-DD.html`) — link στο footer
- Mobile responsive

## Troubleshooting

- **Dashboard 401**: Λάθος credentials ή λείπουν env vars. Άδεια `DASHBOARD_USER` = no auth.
- **Dashboard 404**: Δεν έχει τρέξει ακόμα το cron. Run το manual test.
- **`502 Bad Gateway`** στο Coolify domain: Άσε λίγο μετά το deploy να ξεκινήσει ο server, ή έλεγξε ότι το EXPOSE 8000 ταιριάζει με το Coolify port setting.
