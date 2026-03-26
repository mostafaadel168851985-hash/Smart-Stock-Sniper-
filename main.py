import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from tradingview_ta import TA_Handler, Interval
import plotly.graph_objects as go

# =============================
# 🎨 UI ثابت (Dark Mode)
# =============================
st.set_page_config(layout="wide")

st.markdown("""
<style>
body {background-color: #0b1220; color: white;}
.card {
    background-color: #111827;
    padding: 20px;
    border-radius: 15px;
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
        df = yf.download(symbol + ".CA", period="6mo", interval="1d")
        df.dropna(inplace=True)
        return df
    except:
        return None

# =============================
# 📈 Indicators (FIXED)
# =============================
def indicators(df):
    if len(df) < 50:
        return None

    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    df["RSI"] = rsi(df["Close"])
    return df.dropna()

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# =============================
# 🎯 Strategy PRO++
# =============================
def strategy(df):
    last = df.iloc[-1]

    # Trend
    if last["MA20"] > last["MA50"]:
        trend = "صاعد 📈"
    else:
        trend = "ضعيف ⚠️"

    # Breakout
    resistance = df["High"].rolling(20).max().iloc[-1]
    support = df["Low"].rolling(20).min().iloc[-1]

    breakout = last["Close"] > resistance * 0.99
    pullback = last["Close"] <= support * 1.02

    # Entry logic
    if breakout:
        entry = resistance
        signal = "BUY 🔥"
    elif pullback:
        entry = support
        signal = "BUY (Pullback)"
    else:
        entry = last["Close"]
        signal = "WAIT ⏳"

    stop = entry * 0.96
    target = entry * 1.06

    return trend, signal, entry, stop, target, support, resistance

# =============================
# 📊 Chart (Candlestick)
# =============================
def chart(df):
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
# 🤖 AI Recommendation
# =============================
def ai(signal, trend, rsi):
    if signal == "BUY 🔥" and rsi < 70:
        return "🚀 فرصة قوية - اختراق واضح"
    elif "Pullback" in signal:
        return "📉 شراء من دعم - مخاطرة أقل"
    elif rsi > 80:
        return "⚠️ تشبع شرائي - خطر"
    else:
        return "⏳ انتظار أفضل"

# =============================
# 🚀 UI
# =============================
st.title("🏹 EGX Sniper PRO++")

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

df = indicators(df)

if df is None:
    st.warning("⚠️ بيانات غير كافية")
    st.stop()

trend, signal, entry, stop, target, support, resistance = strategy(df)

last = df.iloc[-1]
rsi_val = round(last["RSI"], 2)

recommendation = ai(signal, trend, rsi_val)

# =============================
# 📦 CARD (نفس الشكل)
# =============================
st.markdown(f"""
<div class="card">

<h2>{symbol}</h2>

💰 السعر الحالي: {round(last['Close'],2)}  
📊 RSI: {rsi_val}  

🧱 الدعم: {round(support,2)}  
🚧 المقاومة: {round(resistance,2)}  

<hr>

🎯 دخول: {round(entry,2)}  
❌ وقف خسارة: {round(stop,2)}  
🏁 هدف: {round(target,2)}  

📈 الاتجاه: {trend}  
🔥 الإشارة: {signal}  

<hr>

🤖 التوصية: {recommendation}

</div>
""", unsafe_allow_html=True)

# =============================
# 📉 Chart
# =============================
chart(df)

# =============================
# 🔥 Scanner (زي الصورة)
# =============================
st.subheader("🔥 الفرص")

watchlist = ["COMI","ETEL","TMGH","SWDY","EFIH","ORAS"]

results = []

for s in watchlist:
    d = get_data(s)
    d = indicators(d) if d is not None else None

    if d is None:
        continue

    _, sig, _, _, _, sup, res = strategy(d)

    results.append({
        "السهم": s,
        "الدعم": round(sup,2),
        "المقاومة": round(res,2),
        "الإشارة": sig
    })

if results:
    st.dataframe(pd.DataFrame(results))
else:
    st.warning("لا توجد فرص")
