import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from tradingview_ta import TA_Handler, Interval

# =============================
# 🎨 UI ثابت (Dark Mode)
# =============================
st.set_page_config(layout="wide")

st.markdown("""
<style>

body {
    background-color: #0b1220;
    color: white;
}

.card {
    background: #111827;
    padding: 25px;
    border-radius: 20px;
    box-shadow: 0px 0px 20px rgba(0,0,0,0.4);
    margin-top: 20px;
}

.title {
    font-size: 28px;
    font-weight: bold;
    margin-bottom: 15px;
}

.line {
    border-top: 1px solid #2a2a2a;
    margin: 15px 0;
}

</style>
""", unsafe_allow_html=True)

# =============================
# 📊 TradingView
# =============================
def get_tv(symbol):
    try:
        handler = TA_Handler(
            symbol=symbol,
            screener="egypt",
            exchange="EGX",
            interval=Interval.INTERVAL_1_DAY
        )
        return handler.get_analysis()
    except:
        return None

# =============================
# 📊 Yahoo Backup (FIXED)
# =============================
def get_data(symbol):
    try:
        for suffix in [".CAIRO", ".EG", ""]:
            df = yf.download(symbol + suffix, period="6mo", interval="1d")
            if df is not None and not df.empty:
                df.dropna(inplace=True)
                return df
        return None
    except:
        return None

# =============================
# 📈 RSI
# =============================
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# =============================
# 🚀 APP
# =============================
st.title("🏹 EGX Sniper PRO MAX")

symbol = st.text_input("ادخل كود السهم", "TMGH")

# =============================
# 🔄 Data
# =============================
tv = get_tv(symbol)

if tv:
    st.success("✅ TradingView Live")
else:
    st.warning("⚠️ TradingView failed - using backup")

df = get_data(symbol)

if df is None or df.empty:
    st.error("❌ لا توجد بيانات")
    st.stop()

# =============================
# 📈 Indicators
# =============================
df["MA20"] = df["Close"].rolling(20).mean()
df["MA50"] = df["Close"].rolling(50).mean()
df["RSI"] = compute_rsi(df["Close"])

df.dropna(inplace=True)

if len(df) < 20:
    st.warning("⚠️ بيانات غير كافية")
    st.stop()

last = df.iloc[-1]

price = round(last["Close"],2)
rsi_val = round(last["RSI"],2)

# =============================
# 🧱 Support / Resistance
# =============================
support1 = round(df["Low"].rolling(20).min().iloc[-1],2)
support2 = round(df["Low"].rolling(50).min().iloc[-1],2)

res1 = round(df["High"].rolling(20).max().iloc[-1],2)
res2 = round(df["High"].rolling(50).max().iloc[-1],2)

# =============================
# 💧 Liquidity
# =============================
volume = df["Volume"].iloc[-1]
if volume > df["Volume"].mean():
    liquidity = "عالية 💧"
else:
    liquidity = "متوسطة ⚠️"

# =============================
# 🔔 Signals
# =============================
bounce = "لا توجد إشارة ارتداد"
confirm = "لا يوجد تأكيد"

if price <= support1 * 1.02:
    bounce = "قريب من دعم 🔥"

if last["MA20"] > last["MA50"]:
    confirm = "اتجاه صاعد ✅"

# =============================
# 🎯 Strategies
# =============================
entry_scalp = support1
stop_scalp = round(entry_scalp * 0.96,2)

entry_swing = price
stop_swing = round(price * 0.94,2)

entry_invest = round(last["MA50"],2)
stop_invest = round(entry_invest * 0.9,2)

# =============================
# 📊 Scores
# =============================
score_scalp = 50
score_swing = 65
score_invest = 55

if rsi_val < 40:
    score_scalp += 10

if last["MA20"] > last["MA50"]:
    score_swing += 10
    score_invest += 10

# =============================
# 📌 Recommendation
# =============================
recommend = "انتظار ⏳"

if price <= support1 * 1.02:
    recommend = "شراء قرب الدعم 🔥"

elif rsi_val > 80:
    recommend = "جني أرباح ⚠️"

# =============================
# 📦 UI CARD (OLD STYLE EXACT)
# =============================
st.markdown(f"""
<div class="card">

<div class="title">{symbol} -</div>

💰 السعر الحالي: {price}  
📊 RSI: {rsi_val}  

🧱 الدعم: {support2} / {support1}  
🚧 المقاومة: {res2} / {res1}  

💧 السيولة: {liquidity}  

<div class="line"></div>

↩️ {bounce}  
⚡ {confirm}  

<div class="line"></div>

🎯 المضارب: {score_scalp}/100  
⚡ مناسب لمضاربة سريعة قرب الدعم {support1} مع الالتزام بوقف الخسارة  
🎯 دخول: {entry_scalp} ، وقف خسارة: {stop_scalp}  

🔁 السوينيج: {score_swing}/100  
📊 السهم في حركة تصحيح داخل اتجاه عام، مراقبة الارتداد مطلوبة  
🎯 دخول: {entry_swing} ، وقف خسارة: {stop_swing}  

🏦 المستثمر: {score_invest}/100  
📈 الاتجاه طويل الأجل إيجابي طالما السعر أعلى المتوسط 50 يوم  
🎯 دخول: {entry_invest} ، وقف خسارة: {stop_invest}  

<div class="line"></div>

📌 التوصية: {recommend}

</div>
""", unsafe_allow_html=True)
