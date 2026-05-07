# Coolify Deployment

Deploy το spitogatos monitor σε δικό σου server μέσω Coolify.

## Πώς δουλεύει

- Το container τρέχει συνέχεια αλλά είναι idle (`sleep infinity`).
- Coolify **Scheduled Task** εκτελεί το script κάθε μέρα στις 04:00 UTC (~07:00 Ελλάδα).
- Volume στο `/app/data` διατηρεί το `seen_apartments.json` ανάμεσα σε runs (αλλιώς θα έπαιρνες κάθε μέρα ειδοποιήσεις για όλες τις αγγελίες).

## Setup steps

### 1. Νέα Application στο Coolify

- `+ New` → `Public Repository` (ή Private αν συνδέσεις GitHub)
- Repository: `https://github.com/pete79cy/spitogatos-monitor`
- Branch: `main`
- Build Pack: **Dockerfile**
- Port: άσε κενό ή `0` (δεν εκθέτει port)

### 2. Persistent Storage

Στο Storage tab:
- `+ Add` → **Volume**
- Source name: `spitogatos-data`
- Destination path: `/app/data`

Χωρίς αυτό θα χάνεις το `seen_apartments.json` σε κάθε redeploy.

### 3. Environment Variables

Στο Environment Variables tab πρόσθεσε:

| Key | Value |
|-----|-------|
| `TELEGRAM_BOT_TOKEN` | το token από @BotFather |
| `TELEGRAM_CHAT_ID` | το chat id σου |

(Email vars `EMAIL_TO`, `SMTP_USER`, `SMTP_PASSWORD` αν θες και email — προαιρετικά.)

### 4. Deploy

`Deploy` button. Περίμενε να γίνει build & start. Στα logs θα δεις απλώς ότι κάνει `sleep infinity` — αυτό είναι σωστό.

### 5. Scheduled Task

Στο **Scheduled Tasks** tab της εφαρμογής:
- `+ Add Scheduled Task`
- Name: `daily-check`
- Command:
  ```
  xvfb-run --auto-servernum --server-args='-screen 0 1920x1080x24' python /app/spitogatos_monitor.py
  ```
- Frequency: `0 4 * * *` (καθημερινά στις 04:00 UTC)

### 6. Manual test

Πριν περιμένεις 24 ώρες, τεστάρεις άμεσα:

- Στο Coolify, στην εφαρμογή → `Terminal` (ή `Execute Command`)
- Τρέξε:
  ```bash
  xvfb-run --auto-servernum --server-args='-screen 0 1920x1080x24' python /app/spitogatos_monitor.py
  ```

Θα δεις στα logs τις αγγελίες που βρέθηκαν και θα έρθει Telegram (την πρώτη φορά για **όλες** τις τρέχουσες — από εκεί και πέρα μόνο νέες).

## GH Actions vs Coolify

⚠️ Διάλεξε ένα από τα δύο για να μη παίρνεις διπλές ειδοποιήσεις:
- Αν χρησιμοποιείς Coolify, **disable το GitHub Actions workflow** (Actions tab → `Daily Apartment Monitor` → `...` → `Disable workflow`).
- Ή απλά διέγραψε το `.github/workflows/daily_monitor.yml`.

## Troubleshooting

- **"Pardon Our Interruption" στα logs** → το xvfb δεν τρέχει σωστά. Έλεγξε ότι το command αρχίζει με `xvfb-run`.
- **Δεν στέλνει Telegram** → έλεγξε ότι έχεις βάλει σωστά τα env vars στο Coolify (όχι στο GitHub).
- **Παίρνεις κάθε μέρα ίδιες αγγελίες** → το volume δεν είναι σωστά mounted στο `/app/data`.
