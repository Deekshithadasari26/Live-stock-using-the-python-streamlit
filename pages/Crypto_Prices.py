import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime

st.set_page_config(page_title="Crypto Prices (CoinMarketCap-style)", layout="wide")

# -----------------------------
# Config
# -----------------------------
MAJORS = [
    {"id": "bitcoin", "symbol": "BTC", "name": "Bitcoin"},
    {"id": "ethereum", "symbol": "ETH", "name": "Ethereum"},
    {"id": "binancecoin", "symbol": "BNB", "name": "BNB"},
    {"id": "solana", "symbol": "SOL", "name": "Solana"},
    {"id": "ripple", "symbol": "XRP", "name": "XRP"},
]

GECKO_BASE = "https://api.coingecko.com/api/v3"

# -----------------------------
# Data helpers (cached)
# -----------------------------
@st.cache_data(ttl=300)
def get_markets_for_cards(ids: list[str]) -> pd.DataFrame:
    params = {
        "vs_currency": "usd",
        "ids": ",".join(ids),
        "sparkline": "true",
        "price_change_percentage": "24h",
    }
    r = requests.get(f"{GECKO_BASE}/coins/markets", params=params, timeout=20)
    df = pd.DataFrame(r.json())
    # Normalize sparkline to list of numbers
    if "sparkline_in_7d" in df.columns:
        df["sparkline"] = df["sparkline_in_7d"].apply(lambda x: x.get("price", []) if isinstance(x, dict) else [])
    else:
        df["sparkline"] = [[] for _ in range(len(df))]
    return df[["id", "symbol", "name", "current_price", "price_change_percentage_24h", "sparkline"]]

@st.cache_data(ttl=300)
def get_market_chart(coin_id: str, days: int) -> pd.DataFrame:
    params = {"vs_currency": "usd", "days": days}
    r = requests.get(f"{GECKO_BASE}/coins/{coin_id}/market_chart", params=params, timeout=20)
    js = r.json()
    prices = js.get("prices", [])
    market_caps = js.get("market_caps", [])
    df_p = pd.DataFrame(prices, columns=["ts", "price"]) if prices else pd.DataFrame(columns=["ts", "price"])
    df_m = pd.DataFrame(market_caps, columns=["ts", "market_cap"]) if market_caps else pd.DataFrame(columns=["ts", "market_cap"])
    df = pd.merge(df_p, df_m, on="ts", how="left")
    if not df.empty:
        df["Date"] = pd.to_datetime(df["ts"], unit="ms")
    return df

@st.cache_data(ttl=300)
def get_global_data() -> dict:
    r = requests.get(f"{GECKO_BASE}/global", timeout=20)
    js = r.json().get("data", {})
    btc_dom = js.get("market_cap_percentage", {}).get("btc")
    return {"btc_dom": btc_dom}

@st.cache_data(ttl=300)
def get_fear_greed() -> dict:
    # Alternative.me F&G index
    try:
        r = requests.get("https://api.alternative.me/fng/", params={"limit": 1}, timeout=20)
        data = r.json().get("data", [])
        if data:
            val = float(data[0].get("value", "nan"))
            cls = data[0].get("value_classification", "")
            return {"value": val, "classification": cls}
    except Exception:
        pass
    return {"value": np.nan, "classification": ""}

@st.cache_data(ttl=300)
def get_market_tickers(coin_id: str) -> pd.DataFrame:
    # Exchange tickers for selected coin
    r = requests.get(f"{GECKO_BASE}/coins/{coin_id}/tickers", timeout=20)
    js = r.json()
    tickers = js.get("tickers", [])
    rows = []
    for t in tickers:
        market = t.get("market", {})
        rows.append({
            "Exchange": market.get("name"),
            "Pair": f"{t.get('base')}/{t.get('target')}",
            "Price": t.get("last"),
            "Volume_24h": t.get("volume"),
            "Liquidity": t.get("trust_score"),  # green/yellow/red
            "Trade URL": t.get("trade_url"),
        })
    df = pd.DataFrame(rows)
    if not df.empty and "Volume_24h" in df.columns:
        total_vol = df["Volume_24h"].sum()
        df["Volume %"] = (df["Volume_24h"] / total_vol * 100.0).round(2) if total_vol else 0.0
    return df

# -----------------------------
# State
# -----------------------------
if "active_crypto_id" not in st.session_state:
    st.session_state.active_crypto_id = MAJORS[0]["id"]
    st.session_state.active_crypto_name = MAJORS[0]["name"]

# -----------------------------
# Top – market cards
# -----------------------------
st.title("Crypto Prices")
ids = [m["id"] for m in MAJORS]
card_df = get_markets_for_cards(ids)

st.subheader("Top Coins")
cols = st.columns(len(MAJORS))
for i, m in enumerate(MAJORS):
    coin = card_df.loc[card_df["id"] == m["id"]]
    with cols[i]:
        st.button(f"{m['name']} ({m['symbol']})", key=f"btn_{m['id']}",
                  on_click=lambda cid=m['id'], cname=m['name']: (st.session_state.__setitem__('active_crypto_id', cid), st.session_state.__setitem__('active_crypto_name', cname)))
        if not coin.empty:
            price = coin["current_price"].values[0]
            pct = coin["price_change_percentage_24h"].values[0]
            color = "green" if (pd.notna(pct) and pct >= 0) else "red"
            st.markdown(f"**${price:,.2f}**  |  <span style='color:{color}'>{pct:.2f}%</span>", unsafe_allow_html=True)
            spark = coin["sparkline"].values[0]
            if isinstance(spark, list) and len(spark) > 3:
                s_df = pd.DataFrame({"x": range(len(spark)), "y": spark})
                s_fig = px.line(s_df, x="x", y="y")
                s_fig.update_layout(showlegend=False, height=120, margin=dict(l=10, r=10, t=10, b=0))
                s_fig.update_traces(line=dict(color=color))
                st.plotly_chart(s_fig, use_container_width=True)
        else:
            st.write("–")

active_id = st.session_state.active_crypto_id
active_name = st.session_state.active_crypto_name

# -----------------------------
# Middle – price/market cap chart with time filter
# -----------------------------
st.subheader(f"{active_name} Price / Market Cap")
trange = st.radio("Time Range", ["1D", "7D", "1M", "3M", "1Y"], index=1, horizontal=True)
DAYS_MAP = {"1D": 1, "7D": 7, "1M": 30, "3M": 90, "1Y": 365}
series = get_market_chart(active_id, DAYS_MAP[trange])

metric_choice = st.radio("Metric", ["Price", "Market Cap"], index=0, horizontal=True)
if not series.empty:
    up = series.iloc[-1]["price"] - series.iloc[0]["price"] if "price" in series.columns else 0
    color = "green" if up >= 0 else "red"
    y_col = "price" if metric_choice == "Price" else "market_cap"
    title = f"{active_name} {metric_choice} Chart"
    # Ensure clean data types and drop missing values
    series = series.copy()
    if "Date" in series.columns:
        series["Date"] = pd.to_datetime(series["Date"], errors="coerce")
    series[y_col] = pd.to_numeric(series.get(y_col), errors="coerce")
    series = series.dropna(subset=["Date", y_col])
    if series.empty:
        st.info("No chart data available after cleaning.")
    else:
        fig = px.line(series, x="Date", y=y_col, title=title)
        fig.update_traces(line=dict(color=color, width=2))
        fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No chart data available.")

# -----------------------------
# Optional sentiment widgets
# -----------------------------
st.subheader("Market Sentiment")
fg = get_fear_greed()
global_data = get_global_data()

c1, c2, c3 = st.columns(3)
with c1:
    val = fg.get("value")
    cls = fg.get("classification")
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=val if pd.notna(val) else 0,
        title={'text': f"Fear & Greed\n{cls}"},
        gauge={'axis': {'range': [0, 100]}, 'bar': {'color': 'orange'}}
    ))
    fig.update_layout(height=220, margin=dict(l=10, r=10, t=30, b=0))
    st.plotly_chart(fig, use_container_width=True)
with c2:
    btc_dom = global_data.get("btc_dom")
    st.metric("Bitcoin Dominance", f"{btc_dom:.2f}%" if btc_dom else "–")
with c3:
    # Approximate Altcoin Season Index as 100 - BTC dominance
    if global_data.get("btc_dom"):
        alt_season = 100 - global_data["btc_dom"]
        st.metric("Altcoin Season Index (approx)", f"{alt_season:.2f}")
    else:
        st.metric("Altcoin Season Index", "–")

# -----------------------------
# Bottom – markets table
# -----------------------------
st.subheader(f"{active_name} Markets")
mt = get_market_tickers(active_id)
if not mt.empty:
    # Pretty liquidity
    def map_liq(x):
        if x == "green":
            return 3
        if x == "yellow":
            return 2
        if x == "red":
            return 1
        return np.nan
    mt["Liquidity score"] = mt["Liquidity"].apply(map_liq)
    display_cols = ["Exchange", "Pair", "Price", "Volume_24h", "Liquidity score", "Volume %"]
    st.dataframe(mt[display_cols].rename(columns={"Volume_24h": "Volume (24h)"}).style.format({
        "Price": "${:,.4f}", "Volume (24h)": "{:,.0f}", "Volume %": "{:.2f}%"
    }), use_container_width=True)
else:
    st.info("No market tickers available.")