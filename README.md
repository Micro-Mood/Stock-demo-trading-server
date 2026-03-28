# Stock Demo Trading Server

<div align="center">

**China A-Share Simulated Trading System**

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Flask](https://img.shields.io/badge/Flask-Backend-lightgrey.svg)](https://flask.palletsprojects.com/)

[**中文文档**](README_CN.md)

</div>

## Introduction

A complete China A-share simulated trading platform featuring a backend trading engine, real-time data crawler, and frontend trading interface. Simulates a realistic trading environment with T+1 rules, price limit restrictions, and trading fee calculations.

![Screenshot](image/img1.png)

## Features

- **Realistic Trading Rules**: T+1, call auction, price limits, commission / stamp duty / transfer fees
- **Real-Time Data**: Live stock quotes from East Money (东方财富)
- **Trading Session Management**: Auto-detects pre-market / in-session / post-market / closed states
- **Position Management**: Multiple buys, partial sells, cost price calculation
- **Order Matching**: Limit orders with automatic matching, supports order cancellation
- **Data Persistence**: Auto-saves trading state, survives restarts
- **Desktop Control Panel**: tkinter control window, one-click launch

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Launch

```bash
python app.pyw
```

A control panel window will appear. Click "Open Browser" to access the trading interface at `http://127.0.0.1:5000`.

## Project Structure

```
Stock-demo-trading-server/
├── app.pyw             # Flask app entry + tkinter control panel
├── trading_api.py      # Trading engine core (orders/matching/positions/T+1)
├── crawler.py          # East Money real-time quote crawler
├── common.py           # Trading session rules, fee calculation, holiday detection
├── requirements.txt    # Python dependencies
├── static/
│   ├── css/style.css   # Frontend styles
│   └── js/app.js       # Frontend logic
├── templates/
│   └── index.html      # Trading interface
├── data/               # Runtime data (auto-generated)
└── image/              # Screenshots
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/portfolio` | Get portfolio (funds / positions / P&L) |
| GET | `/api/stock/<code>` | Get real-time stock quote |
| POST | `/api/buy` | Buy stock |
| POST | `/api/sell` | Sell stock |
| POST | `/api/cancel_order` | Cancel order |
| GET | `/api/orders` | Get all orders |
| GET | `/api/history` | Get trade history |
| GET | `/api/trading_phase` | Get current trading phase |
| GET | `/api/equity_history` | Get equity curve |

## Trading Rules

| Rule | Description |
|------|-------------|
| T+1 | Shares bought today can be sold on the next trading day |
| Trading Hours | 9:30–11:30 / 13:00–15:00 (CST) |
| Call Auction | 9:15–9:25 |
| Buy Commission | 0.025% (min ¥5) + transfer fee 0.001% |
| Sell Commission | 0.025% + stamp duty 0.1% + transfer fee 0.001% |

## License

MIT License
