# LIVE STOCK Dashboard

A Streamlit dashboard for tracking and visualizing Livestock and Precious Metals, with companion pages for Crypto and Stocks inspired by CoinMarketCap-style UX.


<img width="1575" height="787" alt="image" src="https://github.com/user-attachments/assets/6e1207e6-d8e1-448d-8ad4-9bc38c58704a" />

## Features
- Livestock & Metals page with global time-range selector and multi-asset line charts
- Candlestick view for the primary selected asset
- Crypto Prices page with clickable market cards (BTC, ETH, BNB, SOL, XRP)
- Dynamic line chart with time ranges (1D, 1W, 1M, 3M, 1Y) and auto color
- Market sentiment widgets (Fear & Greed Index, Bitcoin Dominance, Altcoin Season)
- Crypto Markets table listing exchanges, pairs, prices, volumes, liquidity score, and volume %
- Crypto Stocks page for comparative charts of crypto and stocks

## live Streamlit Link
https://live-stock-using-the-python-app-fvt9xhgqwusrxjejuo8glu.streamlit.app/
## Quick Start

### Prerequisites
- Python `3.10+`
- `pip`

### Install dependencies
```bash
pip install -r requirements.txt
```

### Run the app
```bash
streamlit run streamlit_app.py --server.port 8505
```
Open `http://localhost:8505` in your browser.

## Configuration

### Secrets
Add API keys in `.streamlit/secrets.toml` if needed. Example:
```toml
# .streamlit/secrets.toml
ALPHAVANTAGE_API_KEY = "your_alpha_vantage_key"
```
- Crypto prices and markets use CoinGecko (no API key required).
- Fear & Greed Index uses Alternative.me (no API key required).
- Stocks integration may use Alpha Vantage for certain endpoints (API key required).

## Pages & Usage

### Livestock & Precious Metals (main)
- Sidebar:
  - Choose `Asset Type` (Livestock or Metal)
  - Select one or more specific assets
- Main:
  - `Time Range` control applies to all charts
  - `Closing Price Trend` line chart compares selected assets
  - `High vs Low Comparison` candlestick for the primary asset

Notes:
- Sheep and Poultry are proxied to futures symbols where direct data isn’t available (Feeder Cattle, Lean Hogs).

### Crypto Prices
- Top cards: clickable cards for BTC, ETH, BNB, SOL, XRP; select a card to update the page
- Main chart: line chart with time range (`1D`, `1W`, `1M`, `3M`, `1Y`); title reflects selected asset and metric
- Sentiment widgets: Fear & Greed Index and other optional indicators
- Markets table: exchanges, trading pairs, price, 24h volume, liquidity score, and volume %, filtered by the selected cryptocurrency

### Crypto Stocks
- Comparative line charts for selected crypto and stock assets
- Time range filters similar to Crypto Prices

## Troubleshooting
- Service Unavailable:
  - Restart the server: `Ctrl+C` in the terminal, then rerun `streamlit run streamlit_app.py --server.port 8505`
- After installing packages, the dev server may stop; simply restart it.
- If charts fail due to API anomalies, try clearing cached data:
```python
# Inside the app (Python REPL or a small button handler)
st.cache_data.clear()
```
- Deprecation notices:
  - Streamlit is deprecating `use_container_width` after `2025-12-31`. Replace with `width='stretch'` (or `width='content'`).

## Notes
- Data sources have rate limits; heavy usage may occasionally return partial or delayed data.
- Historical data from Yahoo Finance (via `yfinance`) may have column variations; the app flattens MultiIndex columns for Plotly compatibility.
