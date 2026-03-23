import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="EGX Sniper", layout="wide")

st.title("🏹 EGX Sniper (Clean Version)")

# ================= STOCKS =================
STOCKS = ["TMGH","COMI","ETEL","SWDY","EFID","ATQA","ALCN","RMDA","ORAS","FWRY"]

# ================= DATA =================
def get_price(symbol):
    try:
        url = "https://scanner.tradingview.com/egypt/scan"

        headers = {"User-Agent": "Mozilla/5.0"}

        payload = {
            "symbols": {"tickers": [f"EGX:{symbol}"], "query": {"types": []}},
            "columns": ["close"]
        }

        r = requests.post(url, json=payload, headers=headers, timeout=10)

        if r.status_code != 200:
            return None

        data = r.json()

        if "data" not in data or len(data["data"]) == 0:
            return None

        return float(data["data"][0]["d"][0])

    except:
        return None

# ================= UI =================
st.subheader("📊 الأسعار الحالية")

rows = []

for s in STOCKS:
    price = get_price(s)

    if price:
        rows.append({
            "السهم": s,
            "السعر": price
        })

df = pd.DataFrame(rows)

if df.empty:
    st.warning("❌ مفيش بيانات")
else:
    st.dataframe(df, use_container_width=True)
