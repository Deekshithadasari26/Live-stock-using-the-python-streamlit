import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
import os
from datetime import datetime, timedelta

st.set_page_config(page_title="Crypto & Stocks", layout="wide")

st.title("Crypto & Stock Prices")

API_KEY = st.secrets.get("ALPHAVANTAGE_API_KEY") or os.environ.get("ALPHAVANTAGE_API_KEY")
if not API_KEY:
    st.warning("Alpha Vantage API key is missing. Add it to `.streamlit/secrets.toml` as `ALPHAVANTAGE_API_KEY`.")

# -----------------------------
# Sidebar – selections
# -----------------------------
with st.sidebar:
    st.header("Crypto/Stock Filters")
    assets = st.multiselect(
        "Assets",
        options=["BTC-USD", "ETH-USD", "AAPL", "MSFT", "GOOGL", "AMZN"],
        default=["BTC-USD", "ETH-USD", "AAPL"],
    )
    days_back = st.radio("Time Range", ["1W", "1M", "3M"], index=1)

DAYS_MAP = {"1W": 7, "1M": 30, "3M": 90}
end_date = datetime.now()
start_date = end_date - timedelta(days=DAYS_MAP[days_back])

BASE_URL = "https://www.alphavantage.co/query"

# -----------------------------
# Fetch functions (cached)
# -----------------------------
@st.cache_data(ttl=600)
def av_fetch_daily_series(symbol: str, api_key: str) -> pd.DataFrame:
    """Fetch daily series for stock or crypto (auto-detect via '-USD')."""
    try:
        if symbol.endswith("-USD"):
            crypto_symbol, market = symbol.split("-")
            params = {
                "function": "DIGITAL_CURRENCY_DAILY",
                "symbol": crypto_symbol,
                "market": market,
                "apikey": api_key,
            }
            r = requests.get(BASE_URL, params=params, timeout=20)
            data = r.json()
            ts = data.get("Time Series (Digital Currency Daily)", {})
            rows = []
            for date_str, vals in ts.items():
                # Use USD close
                close = float(vals.get("4a. close (USD)", "nan"))
                high = float(vals.get("2a. high (USD)", "nan"))
                low = float(vals.get("3a. low (USD)", "nan"))
                volume = float(vals.get("5. volume", "nan"))
                rows.append({"Date": pd.to_datetime(date_str), "Open": np.nan, "High": high, "Low": low, "Close": close, "Volume": volume})
            df = pd.DataFrame(rows).sort_values("Date")
            return df
        else:
            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "outputsize": "compact",
                "apikey": api_key,
            }
            r = requests.get(BASE_URL, params=params, timeout=20)
            data = r.json()
            ts = data.get("Time Series (Daily)", {})
            rows = []
            for date_str, vals in ts.items():
                rows.append({
                    "Date": pd.to_datetime(date_str),
                    "Open": float(vals.get("1. open", "nan")),
                    "High": float(vals.get("2. high", "nan")),
                    "Low": float(vals.get("3. low", "nan")),
                    "Close": float(vals.get("4. close", "nan")),
                    "Volume": float(vals.get("5. volume", "nan")),
                })
            df = pd.DataFrame(rows).sort_values("Date")
            return df
    except Exception:
        return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])  # empty


def compute_snapshot_from_series(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"Current Price": np.nan, "% Change": np.nan}
    last = df.iloc[-1]["Close"]
    prev = df.iloc[-2]["Close"] if len(df) > 1 else np.nan
    pct = ((last - prev) / prev * 100.0) if not np.isnan(prev) else np.nan
    return {"Current Price": float(last), "% Change": float(pct) if not np.isnan(pct) else np.nan}

# -----------------------------
# Build snapshot table
# -----------------------------
rows = []
series_by_asset = {}
for t in assets:
    df = av_fetch_daily_series(t, API_KEY) if API_KEY else pd.DataFrame()
    series_by_asset[t] = df
    snap = compute_snapshot_from_series(df)
    rows.append({"Asset Name": t, **snap})

snap_df = pd.DataFrame(rows)
if not snap_df.empty:
    def color_change(val):
        try:
            if np.isnan(val):
                return ""
            return "color: green;" if val >= 0 else "color: red;"
        except Exception:
            return ""
    st.subheader("Current Prices")
    st.dataframe(snap_df.style.format({"Current Price": "{:.2f}", "% Change": "{:.2f}%"}).applymap(color_change, subset=["% Change"]), use_container_width=True)
else:
    st.info("Select assets to view current prices.")

# -----------------------------
# Trend line chart
# -----------------------------
series_list = []
for t, df in series_by_asset.items():
    if not df.empty:
        # filter by date range
        mask = (df["Date"] >= start_date) & (df["Date"] <= end_date)
        tmp = df.loc[mask, ["Date", "Close"]].copy()
        tmp["Asset"] = t
        series_list.append(tmp)

if series_list:
    st.subheader("Trend (Closing Price)")
    chart_df = pd.concat(series_list, ignore_index=True)
    fig = px.line(chart_df, x="Date", y="Close", color="Asset")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No data available for the selected range.")

st.caption("Free Alpha Vantage tier allows up to ~25 requests/day; data is cached for 10 minutes to reduce calls.")