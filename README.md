# 📊 Quant Analytics Lab — Real-Time Market Data System

### Developer: **Suryavamsi Abhishek** 

---

## 🎥 Demo Video

> 🎬 Watch the walkthrough demo here:  
> ## 🎥 Project Demo

[![Watch the demo](assets/demo_thumbnail.png)](assets/demo.mp4)
> Click the thumbnail above to view the full demo video.

)

This short video shows the app running live — including the Binance WebSocket connection, real-time analytics, alert generation, and Streamlit dashboard interaction.

---

## 🔍 Project Overview

This project implements a **complete end-to-end quantitative analytics system** that ingests **live Binance Futures tick data** via WebSocket, processes and analyzes it in real time, and displays key insights through an interactive **Streamlit dashboard**.

The design focuses on **clarity, modularity, and extensibility**, mirroring how an actual trading analytics pipeline would function in a live quant environment.

---

## 🎯 Objective

> “Your goal is to build a system that ingests this stream, samples and processes it, computes key analytics, and presents the results through an interactive front-end.”

This project achieves exactly that, using the following architecture:

Binance WebSocket → Ingestion → Storage → Analytics → Streamlit Frontend → Alerts & Export

javascript
Copy code

Everything runs locally with **a single command:**

```bash
python run.py
🧠 Key Features
⚙️ Real-Time Data Ingestion
Live connection to Binance Futures WebSocket API (wss://fstream.binance.com/ws/{symbol}@trade)

Collects tick-level trade data (symbol, price, qty, timestamp)

Asynchronous streaming using asyncio + websockets

Supports multiple trading pairs simultaneously

💾 Data Storage & Resampling
In-memory + SQLite persistence layer

Resampling with Pandas (1s, 1m, 5m)

Auto-buffering for efficient data handling

Supports uploading NDJSON/CSV for offline replay

📈 Quantitative Analytics
Metric	Description	Use
Spread	Price difference between correlated assets	Base metric for pair trading
Z-Score	Normalized spread deviation	Entry/exit signal
Hedge Ratio (OLS / Kalman)	Optimal hedge weight	Neutral portfolio construction
Rolling Correlation	Short-term price co-movement	Detects structural regime shifts
ADF Test	Tests for mean reversion	Validates cointegration

Analytics are automatically computed as live data streams in.

🚨 Alerts
Threshold-based alerts (e.g., Z-score > 2)

On-screen visual alerts with risk color coding

Configurable thresholds in the dashboard

🌐 Streamlit Dashboard
Interactive, real-time visualization with Plotly

Theme toggle: dark & light modes

Auto-refresh: every few seconds

Analysis summary panel: interprets current market state

Animated transitions & smooth charts

Data export: download analytics as CSV

🧩 System Design
Architecture Flow
scss
Copy code
┌────────────────────────┐
│ Binance WebSocket Feed │
└────────────┬───────────┘
             │
             ▼
┌────────────────────────┐
│ Async Ingestion Engine │
│ (Python, websockets)   │
└────────────┬───────────┘
             │
             ▼
┌────────────────────────┐
│ Storage Layer (SQLite) │
│ + Resampling (Pandas)  │
└────────────┬───────────┘
             │
             ▼
┌────────────────────────┐
│ Analytics Engine       │
│ (OLS, Kalman, Z-Score) │
└────────────┬───────────┘
             │
             ▼
┌────────────────────────┐
│ Streamlit Frontend     │
│ (Plotly + UI Alerts)   │
└────────────┬───────────┘
             │
             ▼
┌────────────────────────┐
│ Alert & Export System  │
└────────────────────────┘
🧮 Analytics Overview
Each metric is computed in real-time and visualized dynamically:

Spread & Z-score: detect divergence and reversion.

Rolling correlation: measure relationship strength over time.

ADF Test: check if spread is stationary (cointegrated).

Kalman Hedge Ratio: smooth dynamic hedge adjustment.

These analytics are crucial for pair trading and market-neutral strategy design.

⚡ Quick Start
1️⃣ Installation
bash
Copy code
pip install -r requirements.txt
2️⃣ Run the app
bash
Copy code
python run.py
Open in browser:
👉 http://localhost:8501

🧱 Project Structure
graphql
Copy code
quant_analytics_lab/
 ┣ backend/
 ┃ ┣ __init__.py
 ┃ ┣ ingestion.py        # Live WebSocket data stream
 ┃ ┣ storage.py          # Data storage + resampling
 ┃ ┣ analytics.py        # Quantitative computations
 ┃ ┗ alerts.py           # Alert monitoring
 ┣ frontend/
 ┃ ┗ app.py              # Streamlit dashboard
 ┣ assets/
 ┃ ┗ demo.mp4            # Demo video
 ┣ architecture.drawio
 ┣ requirements.txt
 ┣ run.py
 ┗ README.md
🧠 Methodology Summary
Connects to Binance WebSocket using async I/O for efficiency.

Normalizes tick data → stores locally.

Uses pandas for real-time resampling.

Computes quant analytics like Z-score, spread, correlation, and hedge ratio.

Displays metrics via Streamlit + Plotly in real time.

User-defined alerts trigger visually on threshold events.

📊 Example Insights
Condition	Interpretation
Z-score > 2	Spread divergence detected – potential short opportunity
Z-score < -2	Possible reversion – potential long opportunity
Correlation < 0.3	Weak pair relationship – avoid trade
ADF p-value < 0.05	Series is stationary – valid mean reversion pair

🧩 Design Philosophy
Following the assignment guidelines:

Loosely coupled components: ingestion, analytics, and UI are modular.

Scalable design: can plug in REST APIs or new exchanges.

Readable code: structured and documented for clarity.

Future ready: easily extendable to distributed architecture.

🤖 ChatGPT Usage Transparency
I used ChatGPT (GPT-5) as a coding partner to:

Refine the Streamlit dashboard layout

Suggest efficient use of asyncio and pandas resampling

Improve code clarity and structure

Help write and polish this README

All backend logic (ingestion, analytics, architecture) was built and verified by me.
ChatGPT was used responsibly for speed and presentation quality, not as a code generator.
