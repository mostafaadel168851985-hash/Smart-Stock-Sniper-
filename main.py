import streamlit as st
import requests
import yfinance as yf
import pandas as pd

# ================== CONFIG ==================
st.set_page_config(page_title="EGX Sniper PRO", layout="wide")

WATCHLIST = ["TMGH", "COMI", "ETEL", "SWDY", "EFID", "ATQA", "ALCN", "RMDA"]

COMPANIES = {
    "TMGH": "طلعت مصطفى",
    "COMI": "البنك التجاري الدولي",
    "ETEL": "المصرية للاتصالات",
    "SWDY": "السويدي إليكتريك",
    "EFID": "إيديتا",
    "ATQA": "عتاقة",
    "ALCN": "ألكون",
    "RMDA": "رمادا"
}

# ================== DATA ==================
@st.cache_data(ttl=300)
def get_tv_data(symbol):
    try:
        url = "https://scanner.tradingview.com/egypt/scan"
        payload = {
            "symbols": {"tickers": [f"EGX:{symbol.upper()}"], "query": {"types": []}},
            "columns": ["close", "high", "low", "volume"]
        }
        r = requests.post(url, json=payload, timeout=5).json()
        if not r.get("data"):
            return None, None, None, None
        d = r["data"][0]["d"]
        return float(d[0]), float(d[1]), float(d[2]), float(d[3])
    except:
        return None, None, None, None

@st.cache_data(ttl=600)
def get_yahoo(symbol):
    try:
        df = yf.download(f"{symbol}.CA", period="3mo", interval="1d")
        if df.empty:
            return None
        return df
    except:
        return None

# ================== INDICATORS ==================
def calculate_indicators(df):
    df['EMA20'] = df['Close'].ewm(span=20).mean()
    df['EMA50'] = df['Close'].ewm(span=50).mean()

    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    rs = gain.rolling(14).mean() / loss.rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + rs))

    return df

# ================== FALLBACK ==================
def pivots(p, h, l):
    piv = (p + h + l) / 3
    s1 = (2 * piv) - h
    s2 = piv - (h - l)
    r1 = (2 * piv) - l
    r2 = piv + (h - l)
    return s1, s2, r1, r2

def rsi_fake(p, h, l):
    if h == l:
        return 50
    return ((p - l) / (h - l)) * 100

# ================== REPORT ==================
def show_report(code):

    df = get_yahoo(code)

    # 🟢 Yahoo Mode
    if df is not None:
        df = calculate_indicators(df)
        last = df.iloc[-1]

        price = last['Close']
        rsi = last['RSI']
        ema20 = last['EMA20']
        ema50 = last['EMA50']

        trend = "صاعد" if ema20 > ema50 else "هابط"

        entry = ema20
        sl = ema50

        st.success("🧠 تحليل احترافي")

    # 🟡 Fallback Mode
    else:
        p,h,l,v = get_tv_data(code)

        if not p:
            st.error("❌ البيانات غير متاحة")
            return

        s1, s2, r1, r2 = pivots(p, h, l)
        price = p
        rsi = rsi_fake(p, h, l)
        ema20, ema50 = "-", "-"
        trend = "تقريبي"
        entry = s1
        sl = s2

        st.warning("⚡ تحليل سريع (Fallback)")

    st.markdown(f"""
    <div class="card">
    <h3>{code}</h3>
    💰 السعر: {price:.2f}<br>
    📉 RSI: {rsi:.1f}<br>
    📊 EMA20: {ema20}<br>
    📊 EMA50: {ema50}<br>
    📈 الاتجاه: {trend}<br>
    <hr>
    🎯 دخول: {entry:.2f}<br>
    🛑 وقف خسارة: {sl:.2f}<br>
    </div>
    """, unsafe_allow_html=True)

# ================== UI ==================
st.title("🏹 EGX Sniper PRO (Hybrid)")

code = st.text_input("ادخل كود السهم").upper().strip()

if code:
    show_report(code)
