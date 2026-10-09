# QuestPlatform ⚔️

QuestPlatform is a gamified referral web app where users perform web quests, get rewarded, build a 2-tier referral network, and cash out directly to their bank accounts on Fridays.

---

## 💎 Platform Economics Model ($X$)

| Parameter | Formula | Default ($X = ₦5,000 / $10) | Description |
| :--- | :--- | :--- | :--- |
| **Base Access Code Price** | $X$ | `₦5,000.00` | Required access code purchased for new user registration |
| **Direct Referral (Tier 1)** | $X / 5$ | `₦1,000.00` (20%) | Paid instantly to direct sponsor upon account activation |
| **2nd-Tier Referral (Tier 2)** | $X / 20$ | `₦250.00` (5%) | Paid to sponsor's sponsor on downline recruits |
| **House Net Margin** | Remainder | `~₦3,750.00` (75%) | Retained by the platform when referrers are absent/present |
| **Task Completion Reward** | $X / 40$ | `₦125.00` (2.5%) | Paid to user upon admin approval of screenshot proof |
| **Withdrawal Qualification** | $2X$ | `₦10,000.00` | Minimum lifetime referral commissions required to qualify |
| **Payout Window** | Fridays | 00:00 - 23:59 UTC | Cashouts are processed strictly on Fridays |

> **Privacy Rule:** Users can only view the aggregated counts of their direct referrals (Tier 1) and 2nd-tier referrals (Tier 2).

---

## 🚀 Key Features

### 👤 User Portal
* **Gamified Dashboard:** Live balances, 2X referral milestone progress bar, quick referral card, and live quest shortcuts.
* **Quests Hub:** Categorized task catalog (Social Media, App Downloads, Ratings, Discord/Telegram) with step instructions and target link launcher.
* **Proof Uploader:** Image screenshot uploader with live thumbnail preview and real-time review status tracking.
* **2-Tier Referral Center:** Direct link and code copy, WhatsApp/Telegram/Twitter/Facebook 1-click viral sharing, and scannable QR Code modal.
* **Leaderboard:** Hall of Fame podium for Top Referrers (Gold 🥇, Silver 🥈, Bronze 🥉) and Top Questers.
* **Wallet & Cashout:** Payout profile integration, Friday-only lock guard, and complete financial ledger history.
* **Profile Settings:** Bank Name, Account Number, Account Name updates, and secure password changes.

### 🛡️ Admin Control Center
* **Executive Dashboard:** Live KPIs for Gross Code Revenue, Total Commissions Paid, Task Rewards Paid, House Net Profit, and queue counters.
* **Batch Access Code Generator & Exporter:** Generate 10 to 1,000 codes in seconds and export immediately as **CSV** or **TXT** files.
* **Seamless Review Queue:** Lightbox proof screenshot inspection with 1-click instant approvals and preset rejection reasons ("Invalid proof", "Blurry", "Duplicate").
* **Quest Manager:** Publish new tasks with custom/dynamic rewards, pause/activate toggles, and deletion.
* **Friday Payouts Manager:** Review bank payout queue, 1-click "Mark Paid", rejection with automatic wallet refund, and CSV export for batch bank transfers.
* **Dynamic Economy Settings:** Change $X$ (Base Price), currency symbol, Friday lock toggle, and Google AdSense credentials in real time.

---

## 🛠️ Tech Stack

* **Backend:** Python 3.12, Flask, Flask-Login, Flask-SQLAlchemy, Werkzeug, Pillow
* **Database:** SQLite with SQLAlchemy ORM (ACID-compliant transactions)
* **Frontend:** Responsive Vanilla CSS (Dark Mode, Glassmorphism, Micro-Animations, Plus Jakarta Sans & Outfit fonts) and Vanilla JavaScript
* **Testing:** Python `unittest` suite (100% passing test coverage)

---

## ⚡ Quick Start Guide

### 1. Setup & Activate Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # or: pip install flask flask-sqlalchemy flask-login werkzeug pillow python-dotenv
```

### 2. Initialize and Seed the Database
```bash
python seed.py
```

### 3. Run the Development Server
```bash
python run.py
```
Open **[http://localhost:5000](http://localhost:5000)** in your browser.

---

## 🔑 Default Accounts & Access Codes

* **Admin Portal:**
  * URL: `/admin`
  * Username: `admin`
  * Password: `admin1234`

* **Demo User Accounts:**
  * Username: `victor_quest` | Password: `password123` (Qualified for Friday withdrawals)
  * Username: `sarah_pro` | Password: `password123`
  * Username: `emmanuel_k` | Password: `password123`

* **Fresh Unused Access Codes (for registration):**
  * `QP-QDLY-4T8C`
  * `QP-HSGK-5URV`
  * `QP-RJ54-CR6H`
  * `QP-G89R-K4D2`
  * `QP-WLY6-ENXF`

---

## 🧪 Running the Automated Test Suite

To run all 5 unit and integration test suites:
```bash
./.venv/bin/python -m unittest discover -s tests
```
Tests verify:
1. 2-Tier referral commission calculations ($X/5$ and $X/20$).
2. 2X Referral milestone and Friday withdrawal guards.
3. Task screenshot proof submissions and admin approval ($X/40$).
4. Batch access code generation and CSV/TXT exports.
5. User bank profile updates and withdrawal rejection/refund ledger flows.