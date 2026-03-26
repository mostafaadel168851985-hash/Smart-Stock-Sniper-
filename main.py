import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from tradingview_ta import TA_Handler, Interval
import plotly.graph_objects as go

# =============================
# 🎨 UI Config (Dark Mode ثابت)
# =============================
st.set_page_config(layout="wide")

st.markdown("""
<style>
body {background-color: #0b1220; color: white;}
.stTextInput input {
    background-color: #1c2536;
    color: white;
}
.card {
    background-color: #111827;
    padding: 20px;
    border-radius: 15px;
    box-shadow: 0px 0px 10px rgba(0,0,0,0.5);
}
</style>
""", unsafe_allow_html=True)

# =============================
# 📊 TradingView Data
# =============================
def get_tv_data(symbol):
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
# 📊 Backup Yahoo
# =============================
def get_yahoo(symbol):
    try:
        df = yf.download(symbol + ".CA", period="3mo", interval="1d")
        return df
    except:
        return None

# =============================
# 📈 Indicators
# =============================
def calc_indicators(df):
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    df["RSI"] = compute_rsi(df["Close"])
    return df

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# =============================
# 🎯 Smart Strategy
# =============================
def strategy(df):
    last = df.iloc[-1]
    
    if last["Close"] > last["MA20"] > last["MA50"]:
        trend = "صاعد"
    else:
        trend = "ضعيف"

    entry = last["Close"] * 0.99
    stop = last["Close"] * 0.96
    target = last["Close"] * 1.05

    return trend, entry, stop, target

# =============================
# 📊 Chart (Candlestick)
# =============================
def plot_chart(df):
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close']
    ))

    fig.add_trace(go.Scatter(x=df.index, y=df["MA20"], name="MA20"))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA50"], name="MA50"))

    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

# =============================
# 🚀 UI
# =============================
st.title("🏹 EGX Sniper PRO MAX")

symbol = st.text_input("ادخل كود السهم", "TMGH")

# =============================
# 🔄 Data Fetch Logic
# =============================
tv = get_tv_data(symbol)

if tv:
    price = tv.indicators.get("close", 0)
    rsi = tv.indicators.get("RSI", 0)
else:
    st.warning("⚠️ TradingView failed - using backup")

df = get_yahoo(symbol)

if df is None or df.empty:
    st.error("❌ لا توجد بيانات")
    st.stop()

df = calc_indicators(df)

trend, entry, stop, target = strategy(df)

# =============================
# 📦 Card UI
# =============================
st.markdown(f"""
<div class="card">
<h2>{symbol}</h2>

💰 السعر: {round(df['Close'].iloc[-1],2)}  
📊 RSI: {round(df['RSI'].iloc[-1],2)}  

🧱 الدعم: {round(df['Low'].min(),2)}  
🚧 المقاومة: {round(df['High'].max(),2)}  

💧 السيولة: متوسطة  

<hr>

🎯 دخول: {round(entry,2)}  
❌ وقف خسارة: {round(stop,2)}  
🏁 هدف: {round(target,2)}  

📈 الاتجاه: {trend}
</div>
""", unsafe_allow_html=True)

# =============================
# 📉 Chart
# =============================
plot_chart(df)
