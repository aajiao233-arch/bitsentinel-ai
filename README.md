# 🤖 BitSentinel AI

<div align="center">

**AI-Powered Crypto Trading Agent on Bitget Agent Hub**

*Sentiment-aware. Momentum-driven. Fully automated.*

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Bitget](https://img.shields.io/badge/Bitget-Agent_Hub-00A86B.svg)](https://www.bitget.com)

</div>

---

## 📖 Overview

**BitSentinel AI** is an autonomous trading agent built on **Bitget Agent Hub** that fuses real-time crypto sentiment analysis with technical indicators to execute high-conviction trades.

The agent continuously monitors:

- 🐦 **Social Sentiment** — Scrapes X (Twitter) posts from verified Crypto KOLs, runs NLP sentiment classification, and computes a weighted Fear & Greed Index.
- 📊 **Technical Signals** — Tracks BTC/USDT price action, RSI, EMA crossovers, and volume anomalies via Bitget market data.
- 🎯 **Trade Execution** — When sentiment hits *"Extreme Fear"* AND the price dips below the 200-period EMA, BitSentinel fires a **limit buy order** through Bitget API. Conversely, *"Extreme Greed"* + RSI > 85 triggers a take-profit sell.

> Built for the **Bitget AI Hackathon 2026**.

---

## ✨ Features

- 🧠 **KOL Sentiment Engine** — Real-time NLP pipeline analyzing 50+ Crypto Twitter accounts for bullish/bearish signals.
- 📈 **Multi-Factor Entry Logic** — Combines Fear & Greed, EMA, RSI, and volume spike detection.
- ⚡ **Bitget Agent Hub Integration** — Leverages Bitget's native agent framework for strategy deployment & signal routing.
- 🔐 **Risk-First Design** — Configurable stop-loss, max position size, and daily trade cap.
- 📬 **Telegram Alerts** — Sends trade notifications via Telegram Bot API.
- 🐳 **Docker-Ready** — One-command deployment with Docker Compose.

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  X (Twitter)    │────▶│  Sentiment Engine │────▶│                 │
│  KOL Scraper    │     │  (NLP + Scoring)  │     │  Bitget Agent   │
└─────────────────┘     └──────────────────┘     │      Hub        │
                                                  │                 │
┌─────────────────┐     ┌──────────────────┐     │  ┌───────────┐  │
│  Bitget Market  │────▶│  Technical       │────▶│  │ Strategy  │  │
│  Data (WS)      │     │  Indicators      │     │  │ Execution │  │
└─────────────────┘     └──────────────────┘     │  └───────────┘  │
                                                  │        │        │
┌─────────────────┐                              │        ▼        │
│  Risk Manager   │──────────────────────────────│  ┌───────────┐  │
│  (Circuit Brkr) │                              │  │  Bitget   │  │
└─────────────────┘                              │  │  API      │  │
                                                  │  └───────────┘  │
                                                  └─────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Bitget API Key (with Trade permissions)
- Bitget Agent Hub account

### Installation

```bash
# Clone the repo
git clone https://github.com/your-org/bitsentinel-ai.git
cd bitsentinel-ai

# Create virtual environment
python -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install bitget-ai-agent bitget-api-sdk python-telegram-bot tweepy nltk

# Set environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Configuration

Edit `.env`:

```env
BITGET_API_KEY=your_api_key_here
BITGET_SECRET_KEY=your_secret_here
BITGET_PASSPHRASE=your_passphrase
AGENT_HUB_TOKEN=your_agent_hub_token
TELEGRAM_BOT_TOKEN=optional_telegram_token
TELEGRAM_CHAT_ID=optional_chat_id
```

### Run

```bash
# Dry-run mode (no real trades)
python agent_bot.py --mode dry-run

# Live trading
python agent_bot.py --mode live --symbol BTC/USDT --max-position 0.01
```

### Docker

```bash
docker-compose up -d
```

---

## 📁 Project Structure

```
bitsentinel-ai/
├── agent_bot.py          # Core trading agent
├── sentiment/            # NLP sentiment pipeline
│   ├── scraper.py        # X/Twitter KOL scraper
│   └── classifier.py     # Sentiment classification model
├── indicators/           # Technical analysis
│   └── signals.py        # RSI, EMA, volume indicators
├── risk/                 # Risk management
│   └── manager.py        # Position sizing & circuit breaker
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## ⚠️ Disclaimer

This project is a **hackathon demo prototype**. It is NOT financial advice. Cryptocurrency trading carries substantial risk of loss. Always do your own research. The authors assume no liability for any financial losses incurred through the use of this software.

---

## 📄 License

MIT © 2026 BitSentinel AI Team

---

<div align="center">
  <sub>Built with ❤️ for the Bitget AI Hackathon</sub>
</div>
