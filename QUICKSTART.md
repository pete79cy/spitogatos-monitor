# 🚀 Quick Start Guide

## Γρήγορο Setup σε 5 λεπτά

### Επιλογή 1: GitHub Actions (Αυτόματο - Συνιστάται)

1. **Δημιούργησε GitHub Repository**
   ```bash
   # Ανέβασε τα αρχεία στο GitHub
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/apartment-monitor.git
   git push -u origin main
   ```

2. **Setup Telegram Bot (5 λεπτά)**
   - Μίλα στον [@BotFather](https://t.me/botfather) στο Telegram
   - Στείλε: `/newbot`
   - Πάρε το **Bot Token**
   - Στείλε μήνυμα στο bot σου
   - Επισκέψου: `https://api.telegram.org/botYOUR_TOKEN/getUpdates`
   - Πάρε το **Chat ID**

3. **Πρόσθεσε Secrets στο GitHub**
   - Πήγαινε: `Settings` → `Secrets and variables` → `Actions`
   - Πρόσθεσε:
     - `TELEGRAM_BOT_TOKEN` = το token σου
     - `TELEGRAM_CHAT_ID` = το chat id σου

4. **✅ Τέλος!**
   - Το script θα τρέχει αυτόματα κάθε μέρα στις 6πμ
   - Θα λαμβάνεις ειδοποιήσεις στο Telegram

---

### Επιλογή 2: Local/Cron (Για προχωρημένους)

1. **Εγκατάσταση**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

2. **Ρύθμιση**
   - Άνοιξε το `.env` αρχείο
   - Βάλε τα Telegram ή Email credentials

3. **Test**
   ```bash
   python test_notifications.py  # Test notifications
   python spitogatos_monitor.py  # Test πραγματικό script
   ```

4. **Setup Cron**
   ```bash
   crontab -e
   # Πρόσθεσε:
   0 6 * * * cd /path/to/apartment-monitor && source venv/bin/activate && source .env && python spitogatos_monitor.py
   ```

---

## 📱 Telegram Setup (Λεπτομέρειες)

### Βήμα 1: Δημιουργία Bot

1. Άνοιξε Telegram και ψάξε για `@BotFather`
2. Στείλε: `/newbot`
3. Δώσε όνομα: π.χ. "Apartment Monitor"
4. Δώσε username: π.χ. "my_apartment_bot"
5. **Αποθήκευσε το Bot Token** (π.χ. 1234567890:ABCdefGHIjklMNOpqrSTUvwxyz)

### Βήμα 2: Εύρεση Chat ID

1. Στείλε μήνυμα στο bot σου (οτιδήποτε)
2. Άνοιξε στον browser:
   ```
   https://api.telegram.org/bot1234567890:ABCdefGHIjklMNOpqrSTUvwxyz/getUpdates
   ```
   (Αντικατέστησε με το δικό σου token)

3. Βρες το `"chat":{"id":123456789}` στο JSON
4. **Αποθήκευσε το Chat ID** (π.χ. 123456789)

---

## 📧 Email Setup (Gmail)

1. **Ενεργοποίησε 2-Step Verification**
   - https://myaccount.google.com/security

2. **Δημιούργησε App Password**
   - https://myaccount.google.com/apppasswords
   - Επίλεξε "Mail" και "Other (Custom name)"
   - **Αποθήκευσε το password** (16 χαρακτήρες)

3. **Χρησιμοποίησε στο .env**
   ```
   EMAIL_TO=where-to-send@gmail.com
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=the-16-char-app-password
   ```

---

## ⚡ Γρήγορες Εντολές

```bash
# Test notifications
python test_notifications.py

# Εκτέλεση monitor
python spitogatos_monitor.py

# Δες δεδομένα
cat seen_apartments.json

# Reset δεδομένα
rm seen_apartments.json

# Cron logs
tail -f logs.txt
```

---

## 🎯 Συχνές Ερωτήσεις

**Q: Πότε θα τρέξει η πρώτη φορά;**
A: GitHub Actions: Επόμενη μέρα στις 6πμ. Cron: Επόμενη μέρα στις 6πμ.

**Q: Θα με ειδοποιήσει για όλες τις αγγελίες;**
A: Όχι, μόνο για τις ΝΕΕΣ από την τελευταία φορά που έτρεξε.

**Q: Μπορώ να αλλάξω την ώρα;**
A: Ναι! Δες το README.md για οδηγίες.

**Q: Δεν λαμβάνω ειδοποιήσεις**
A: Τρέξε `python test_notifications.py` για debugging.

**Q: Κοστίζει κάτι;**
A: Όχι! Τα GitHub Actions είναι δωρεάν για public repos.

---

Για περισσότερες λεπτομέρειες, δες το [README.md](README.md)
