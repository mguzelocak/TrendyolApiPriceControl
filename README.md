# TrendyolApiPriceControl

## 📦 Project Overview

This project is an automated price tracking and intelligence system designed for products listed on **Trendyol Marketplace**. It pulls product data using Trendyol’s API, saves it in a structured MySQL database with timestamps (adjusted to Turkey timezone), and supports historical price tracking.

### 🧠 Core Features

- ✅ Fetches active product listings from Trendyol via API
- ✅ Stores barcode, title, price, and timestamp into a `priceTracking` MySQL table
- ✅ Tracks product history across multiple days
- ✅ Built-in support for Turkish timezone using `pytz`
- ✅ Fully environment-safe via `.env` config
- 🛠️ Coming soon: **automated price intelligence and alert system**

---

## 📡 Upcoming: Telegram Alert System (In Progress)

We're building a math-based decision engine that will:

- 📊 Analyze price fluctuations over time (e.g. drops, spikes, competitor activity)
- 📥 Automatically detect "price action triggers"
- 📲 Send instant Telegram messages to team members with price suggestions
- 🙋‍♂️ Allow humans to approve/decline the price change manually via chat

The goal is to combine **automation + human intelligence** to maximize pricing efficiency without losing control.

---

## 🔐 Security & Best Practices

- All credentials and API keys are stored in a `.env` file (never pushed to GitHub)
- Logging and cron jobs are used for automated scheduling (recommended: daily runs)
- Easy to extend for other marketplaces (e.g. Amazon, Hepsiburada)

---

## 🛠️ Tech Stack

- Python  
- MySQL  
- Requests & dotenv  
- Pytz (for timezone awareness)  
- Telegram Bot API *(soon)*

---

This project is under active development 🚧 — contributions, ideas, and collaborations are welcome!# TrendyolApiPriceControl
