import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime, timedelta

st.set_page_config(page_title="Livestock & Metals Dashboard", layout="wide")

# -----------------------------
# Config / mappings
# -----------------------------
ASSET_TYPES = ["Livestock", "Metal"]
LIVESTOCK_ASSETS = ["Cattle", "Sheep", "Poultry"]
METAL_ASSETS = ["Gold", "Silver", "Platinum"]

# Using Yahoo Finance tickers; some livestock categories are proxied:
# - Sheep → no direct symbol on Yahoo; using Feeder Cattle (GF=F) as proxy
# - Poultry → no direct symbol on Yahoo; using Lean Hogs (HE=F) as proxy
TICKER_MAP = {
    "Livestock": {
        "Cattle": "LE=F",      # Live Cattle Futures
        "Sheep": "GF=F",       # Feeder Cattle Futures (proxy)
        "Poultry": "HE=F",     # Lean Hogs Futures (proxy)
    },
    "Metal": {
        "Gold": "GC=F",         # Gold Futures
        "Silver": "SI=F",       # Silver Futures
        "Platinum": "PL=F",     # Platinum Futures
    }
}

TIME_RANGES = {
    "1D": 1,
    "1W": 7,
    "1M": 30,
    "3M": 90,
    "6M": 180,
    "1Y": 365,
}

# -----------------------------
# Helpers
# -----------------------------
@st.cache_data(ttl=600)
def fetch_history(ticker: str, start: datetime, end: datetime) -> pd.DataFrame:
    """Fetch historical OHLCV data for a ticker between start and end."""
    try:
        df = yf.download(ticker, start=start, end=end, progress=False)
        # Flatten MultiIndex columns (e.g., ('Close', 'LE=F')) to single level
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        df = df.rename(columns=str.title)  # Open, High, Low, Close, Adj Close, Volume
        df.index.name = "Date"
        df = df.reset_index()
        # Ensure required columns exist
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col not in df.columns:
                df[col] = np.nan
        return df
    except Exception:
        return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])  # empty


def compute_kpis(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "Highest Value": np.nan,
            "Lowest Value": np.nan,
            "Highest Closing Price": np.nan,
            "Lowest Closing Price": np.nan,
        }
    return {
        "Highest Value": float(df["High"].max(skipna=True)),
        "Lowest Value": float(df["Low"].min(skipna=True)),
        "Highest Closing Price": float(df["Close"].max(skipna=True)),
        "Lowest Closing Price": float(df["Close"].min(skipna=True)),
    }


def line_chart_close(series_map: dict):
    """Plot closing price over time for multiple assets.
    series_map: {asset_label: df}
    """
    if not series_map:
        st.info("Select at least one asset to view the closing price trend.")
        return
    plot_df_list = []
    for label, df in series_map.items():
        if df.empty:
            continue
        tmp = df[["Date", "Close"]].copy()
        tmp["Asset"] = label
        plot_df_list.append(tmp)
    if not plot_df_list:
        st.warning("No data available for the selected assets.")
        return
    plot_df = pd.concat(plot_df_list, ignore_index=True)
    fig = px.line(plot_df, x="Date", y="Close", color="Asset", title="Closing Price Trend")
    fig.update_layout(legend_title_text="Asset")
    st.plotly_chart(fig, use_container_width=True)


def candlestick_chart(df: pd.DataFrame, title: str):
    if df.empty:
        st.warning("No data available for the selected asset.")
        return
    fig = go.Figure(data=[go.Candlestick(
        x=df["Date"],
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name=title
    )])
    fig.update_layout(title=title, xaxis_title="Date", yaxis_title="Price")
    st.plotly_chart(fig, use_container_width=True)


# -----------------------------
# Sidebar filters (Right Panel)
# -----------------------------
with st.sidebar:
    st.header("Filters")
    asset_type = st.radio("Asset Type", ASSET_TYPES, index=0, horizontal=False)
    specific_assets = LIVESTOCK_ASSETS if asset_type == "Livestock" else METAL_ASSETS
    selected_assets = st.multiselect("Specific Asset(s)", specific_assets, default=[specific_assets[0]])
    # Move time range control out of the sidebar
    st.caption("Change time range using the controls above the charts.")

    # Navigation button
    st.write("\n")
    nav_col1, nav_col2 = st.columns([1, 1])
    with nav_col1:
        if st.button("View Crypto & Stock Prices"):
            try:
                st.switch_page("pages/Crypto_Stocks.py")
            except Exception:
                st.session_state["_navigate_hint"] = True
    with nav_col2:
        st.page_link("pages/Crypto_Stocks.py", label="Open Crypto/Stocks Page", icon="🔗")
    st.page_link("pages/Crypto_Prices.py", label="Open Crypto Prices Page", icon="💹")


# Hint for navigation if switch_page failed
if st.session_state.get("_navigate_hint"):
    st.info("If the button didn’t navigate, use the link above or select the Crypto/Stocks page from the sidebar.")

# -----------------------------
# Time range selector (applies to all graphs)
# -----------------------------
st.subheader("Time Range")
time_label = st.radio("Time Range", list(TIME_RANGES.keys()), index=5, horizontal=True)

# -----------------------------
# Data loading based on filters
# -----------------------------
end_date = datetime.now()
start_date = end_date - timedelta(days=TIME_RANGES[time_label])

asset_data = {}
for asset in selected_assets:
    ticker = TICKER_MAP[asset_type].get(asset)
    label = f"{asset_type} · {asset}"
    if asset_type == "Livestock" and asset in ("Sheep", "Poultry"):
        label += " (proxy)"
    df = fetch_history(ticker, start=start_date, end=end_date) if ticker else pd.DataFrame()
    # Volatility column (High - Low)
    if not df.empty:
        df["Volatility"] = df["High"] - df["Low"]
    asset_data[asset] = {"label": label, "df": df}

# -----------------------------
# Top Section – KPI Cards
# -----------------------------
st.title("Livestock & Precious Metals Dashboard")

primary_asset = selected_assets[0] if selected_assets else None
if primary_asset:
    df_primary = asset_data[primary_asset]["df"]
    kpis = compute_kpis(df_primary)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Highest Value", f"{kpis['Highest Value']:.2f}" if not np.isnan(kpis['Highest Value']) else "–")
    c2.metric("Lowest Value", f"{kpis['Lowest Value']:.2f}" if not np.isnan(kpis['Lowest Value']) else "–")
    c3.metric("Highest Closing Price", f"{kpis['Highest Closing Price']:.2f}" if not np.isnan(kpis['Highest Closing Price']) else "–")
    c4.metric("Lowest Closing Price", f"{kpis['Lowest Closing Price']:.2f}" if not np.isnan(kpis['Lowest Closing Price']) else "–")
else:
    st.info("Select at least one asset to view metrics.")

# -----------------------------
# Middle Section – Charts
# -----------------------------
st.subheader("Price Charts")

# 1) Line Chart – Closing Price Trend (multiple assets)
series_map = {v["label"]: v["df"] for k, v in asset_data.items() if not v["df"].empty}
line_chart_close(series_map)

# 2) High vs Low Comparison – Candlestick (primary asset)
if primary_asset:
    st.markdown("### High vs Low Comparison (Candlestick)")
    candlestick_chart(asset_data[primary_asset]["df"], title=asset_data[primary_asset]["label"])