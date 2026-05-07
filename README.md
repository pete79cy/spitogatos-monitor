# 🏠 Spitogatos.gr Student Apartment Monitor

Αυτόματη παρακολούθηση νέων φοιτητικών διαμερισμάτων στο Ηράκλειο από το spitogatos.gr

## 🎯 Χαρακτηριστικά

- ✅ Έλεγχος για νέες αγγελίες φοιτητικών διαμερισμάτων
- ✅ Καθημερινή εκτέλεση στις 6πμ
- ✅ Ειδοποιήσεις μέσω Telegram και/ή Email
- ✅ Αποφυγή διπλών ειδοποιήσεων
- ✅ Αυτόματη αποθήκευση δεδομένων

## 📋 Προαπαιτούμενα

- Python 3.8+
- Git
- Λογαριασμός GitHub (για automation)
- (Προαιρετικά) Telegram Bot ή Email account για ειδοποιήσεις

---

## 🚀 Μέθοδος 1: GitHub Actions (Συνιστώμενο)

Πλήρως αυτόματο - τρέχει στο cloud καθημερινά χωρίς να χρειάζεται να έχεις ανοιχτό υπολογιστή.

### Βήμα 1: Setup Repository

```bash
# Clone ή δημιούργησε νέο repository
git clone https://github.com/YOUR_USERNAME/apartment-monitor.git
cd apartment-monitor

# ή δημιούργησε νέο
mkdir apartment-monitor
cd apartment-monitor
git init
```

### Βήμα 2: Προσθήκη αρχείων

Αντέγραψε όλα τα αρχεία του project:
- `spitogatos_monitor.py`
- `requirements.txt`
- `.github/workflows/daily_monitor.yml`
- `README.md` (αυτό το αρχείο)

```bash
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/apartment-monitor.git
git push -u origin main
```

### Βήμα 3: Ρύθμιση Ειδοποιήσεων

#### Επιλογή A: Telegram (Προτεινόμενο)

1. **Δημιούργησε Telegram Bot:**
   - Μίλησε στον [@BotFather](https://t.me/botfather)
   - Στείλε `/newbot`
   - Ακολούθησε τις οδηγίες και πάρε το **Bot Token**

2. **Βρες το Chat ID σου:**
   - Μίλησε στο bot σου (στείλε οποιοδήποτε μήνυμα)
   - Άνοιξε: `https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates`
   - Βρες το **chat id** στο JSON response

3. **Πρόσθεσε τα Secrets στο GitHub:**
   - Πήγαινε στο: `Settings` → `Secrets and variables` → `Actions`
   - Πάτα `New repository secret`
   - Πρόσθεσε:
     - `TELEGRAM_BOT_TOKEN` = το bot token σου
     - `TELEGRAM_CHAT_ID` = το chat id σου

#### Επιλογή B: Email

Πρόσθεσε τα εξής secrets:
- `EMAIL_TO` = your-email@example.com
- `SMTP_SERVER` = smtp.gmail.com (ή άλλο)
- `SMTP_PORT` = 587
- `SMTP_USER` = your-email@gmail.com
- `SMTP_PASSWORD` = app-specific password

**Για Gmail:**
1. Ενεργοποίησε 2FA
2. Δημιούργησε App Password: https://myaccount.google.com/apppasswords

### Βήμα 4: Ενεργοποίηση Actions

- Πήγαινε στο tab `Actions` του repository
- Επιβεβαίωσε ότι τα workflows είναι ενεργοποιημένα
- Μπορείς να τρέξεις χειροκίνητα: `Actions` → `Daily Apartment Monitor` → `Run workflow`

### ⏰ Προγραμματισμός

Το workflow τρέχει αυτόματα **κάθε μέρα στις 04:00 UTC** (περίπου 6-7πμ ώρα Ελλάδας).

Για να αλλάξεις την ώρα, τροποποίησε το `.github/workflows/daily_monitor.yml`:

```yaml
on:
  schedule:
    - cron: '0 4 * * *'  # Άλλαξε αυτό (MM HH * * *)
```

Παραδείγματα:
- `0 3 * * *` = 5-6πμ Ελλάδα
- `0 5 * * *` = 7-8πμ Ελλάδα
- `0 6 * * *` = 8-9πμ Ελλάδα

---

## 🖥️ Μέθοδος 2: Local Execution με Cron

Για εκτέλεση στον δικό σου υπολογιστή/server.

### Βήμα 1: Εγκατάσταση

```bash
git clone https://github.com/YOUR_USERNAME/apartment-monitor.git
cd apartment-monitor

# Δημιούργησε virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ή
venv\Scripts\activate  # Windows

# Εγκατάστησε dependencies
pip install -r requirements.txt
```

### Βήμα 2: Ρύθμιση Environment Variables

Δημιούργησε αρχείο `.env`:

```bash
# Telegram (προαιρετικά)
export TELEGRAM_BOT_TOKEN="your_token_here"
export TELEGRAM_CHAT_ID="your_chat_id"

# Email (προαιρετικά)
export EMAIL_TO="your-email@example.com"
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USER="your-email@gmail.com"
export SMTP_PASSWORD="your_app_password"
```

### Βήμα 3: Test Εκτέλεση

```bash
source .env  # Load variables
python spitogatos_monitor.py
```

### Βήμα 4: Setup Cron (Linux/Mac)

```bash
crontab -e
```

Πρόσθεσε (αντικατέστησε `/path/to/` με το πραγματικό path):

```cron
# Εκτέλεση κάθε μέρα στις 6:00πμ
0 6 * * * cd /path/to/apartment-monitor && source venv/bin/activate && source .env && python spitogatos_monitor.py >> /path/to/apartment-monitor/logs.txt 2>&1
```

### Βήμα 5: Setup Task Scheduler (Windows)

1. Άνοιξε Task Scheduler
2. Δημιούργησε Basic Task
3. Trigger: Daily στις 6:00πμ
4. Action: Start a Program
   - Program: `C:\path\to\apartment-monitor\venv\Scripts\python.exe`
   - Arguments: `spitogatos_monitor.py`
   - Start in: `C:\path\to\apartment-monitor`

---

## 📊 Χρήση

### Χειροκίνητη εκτέλεση

```bash
python spitogatos_monitor.py
```

### Έλεγχος δεδομένων

Το αρχείο `seen_apartments.json` αποθηκεύει όλες τις αγγελίες που έχεις δει:

```bash
cat seen_apartments.json
```

### Logs

```bash
# Αν χρησιμοποιείς cron
tail -f logs.txt

# GitHub Actions
# Δες στο tab "Actions" του repository
```

---

## 🔧 Troubleshooting

### Δεν βρίσκει αγγελίες

1. **Έλεγξε αν υπάρχουν πραγματικά νέες αγγελίες:**
   - Επισκέψου το URL χειροκίνητα
   - Βεβαιώσου ότι υπάρχουν αποτελέσματα

2. **Το site μπορεί να άλλαξε structure:**
   - Το script θα χρειαστεί ενημέρωση
   - Τρέξε με debug mode για να δεις τι παίρνει

### Δεν λαμβάνεις ειδοποιήσεις

1. **Telegram:**
   - Βεβαιώσου ότι έστειλες μήνυμα στο bot
   - Έλεγξε το Bot Token και Chat ID

2. **Email:**
   - Για Gmail, χρησιμοποίησε App Password, όχι κανονικό password
   - Έλεγξε spam folder

### GitHub Actions δεν τρέχει

1. Βεβαιώσου ότι τα Actions είναι enabled
2. Έλεγξε το tab "Actions" για errors
3. Τρέξε χειροκίνητα για test

---

## 🎨 Προσαρμογή

### Αλλαγή περιοχής ή κριτηρίων

Τροποποίησε το `URL` στο `spitogatos_monitor.py`:

```python
# Για διαφορετική περιοχή
URL = "https://www.spitogatos.gr/en/to_rent-homes/AREA/student_houses/last_update_24h/first_publish_24h"

# Χωρίς φίλτρο φοιτητικών
URL = "https://www.spitogatos.gr/en/to_rent-homes/heraklion-cretes/last_update_24h/first_publish_24h"

# Προσθήκη φίλτρων (τιμή, τετραγωνικά, κλπ)
URL = "https://www.spitogatos.gr/en/to_rent-homes/heraklion-cretes/student_houses/max_price_500/last_update_24h/first_publish_24h"
```

### Αλλαγή συχνότητας

**GitHub Actions:**
```yaml
# Κάθε 6 ώρες
- cron: '0 */6 * * *'

# Δύο φορές τη μέρα (6πμ και 6μμ)
- cron: '0 4,16 * * *'

# Μόνο καθημερινές
- cron: '0 4 * * 1-5'
```

**Cron:**
```cron
# Κάθε 3 ώρες
0 */3 * * * /path/to/script

# Μόνο Σαββατοκύριακα
0 6 * * 6,0 /path/to/script
```

---

## 📝 Παραδείγματα Output

### Όταν βρει νέες αγγελίες:

```
============================================================
🔍 Checking for new student apartments in Heraklion
⏰ 2026-05-07 06:00:00
============================================================

📋 Found 15 total listings

🎉 3 NEW apartments found!

🏠 Φοιτητικό Studio - Κέντρο
   💰 350€/μήνα
   📍 Ηράκλειο Κέντρο
   📏 35 m²
   🔗 https://www.spitogatos.gr/...

🏠 Μονόχωρο με μπαλκόνι
   💰 400€/μήνα
   📍 Κνωσσός
   📏 40 m²
   🔗 https://www.spitogatos.gr/...

✅ Telegram notification sent
✅ Email notification sent

============================================================
✅ Check complete
============================================================
```

### Όταν δεν υπάρχει τίποτα νέο:

```
============================================================
🔍 Checking for new student apartments in Heraklion
⏰ 2026-05-07 06:00:00
============================================================

📋 Found 12 total listings
✅ No new apartments since last check

============================================================
✅ Check complete
============================================================
```

---

## 🛡️ Privacy & Security

- Τα credentials (Bot Token, Email Password) **ΠΟΤΕ** δεν πρέπει να κάνουν commit
- Χρησιμοποίησε GitHub Secrets για sensitive data
- Το `seen_apartments.json` δεν περιέχει προσωπικά δεδομένα

---

## 📄 License

Free to use and modify.

## 🤝 Contributing

Αν βρεις bug ή θέλεις να προσθέσεις feature, κάνε PR!

---

## 💡 Tips

1. **Test πρώτα χειροκίνητα** πριν ενεργοποιήσεις automation
2. **Κράτα backup** του `seen_apartments.json`
3. **Έλεγξε τα logs** τακτικά για errors
4. **Προσάρμοσε τα φίλτρα** στην αναζήτηση για καλύτερα αποτελέσματα

---

Καλή τύχη στην αναζήτηση! 🏠🎓
