import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import yfinance as yf
from tradingview_ta import TA_Handler, Interval

# ------------------ SETTINGS ------------------
st.set_page_config(layout="wide")

# Dark Mode
st.markdown("""
<style>
body {background-color:#0e1117;color:white;}
.stApp {background-color:#0e1117;}
.card {
    background-color:#111827;
    padding:20px;
    border-radius:15px;
    margin-top:20px;
}
</style>
""", unsafe_allow_html=True)

# ------------------ SYMBOLS ------------------
EGX_SYMBOLS = [
    "COMI","ETEL","TMGH","SWDY","EFIH",
    "ORAS","AMOC","RMDA","FWRY","MPRC",
    "MAAL"
]

# ------------------ DATA ------------------
def get_tv_data(symbol):
    try:
        handler = TA_Handler(
            symbol=symbol,
            screener="egypt",
            exchange="EGX",
            interval=Interval.INTERVAL_1_DAY
        )
        analysis = handler.get_analysis()
        d = analysis.indicators

        return {
            "price": d["close"],
            "rsi": d["RSI"],
            "ema50": d.get("EMA50", d["close"]),
            "ema200": d.get("EMA200", d["close"]),
        }

    except:
        return None


def get_yf_data(symbol):
    try:
        df = yf.download(symbol + ".CA", period="3mo", interval="1d")
        return df
    except:
        return None


# ------------------ STRATEGY ------------------
def analyze(symbol):
    tv = get_tv_data(symbol)
    yf_data = get_yf_data(symbol)

    if tv is None or yf_data is None or len(yf_data) == 0:
        return None

    price = tv["price"]
    rsi = tv["rsi"]

    support = yf_data["Low"].rolling(20).min().iloc[-1]
    resistance = yf_data["High"].rolling(20).max().iloc[-1]

    score = 0

    if 40 < rsi < 60:
        score += 30
    if price > tv["ema50"]:
        score += 30
    if price > tv["ema200"]:
        score += 20
    if price > support:
        score += 20

    return {
        "symbol": symbol,
        "price": round(price,2),
        "rsi": round(rsi,1),
        "support": round(support,2),
        "resistance": round(resistance,2),
        "score": score,
        "data": yf_data
    }


# ------------------ UI ------------------
st.title("🏹 EGX Sniper PRO MAX")

tab1, tab2 = st.tabs(["📊 تحليل سهم", "🔥 الفرص"])

# ------------------ ANALYSIS ------------------
with tab1:
    symbol = st.selectbox("ادخل السهم", EGX_SYMBOLS)

    result = analyze(symbol)

    if result:
        st.markdown(f"""
        <div class="card">
        <h2>{result['symbol']}</h2>

        💰 السعر الحالي: {result['price']}  
        📊 RSI: {result['rsi']}  

        🧱 الدعم: {result['support']}  
        🚧 المقاومة: {result['resistance']}  

        💧 السيولة: {"عالية" if result['score']>70 else "متوسطة"}  

        ----------------------

        🎯 المضارب: {result['score']}/100  
        ⚡ مناسب مضاربة سريعة  

        🔁 السوينج: {min(100, result['score']+10)}/100  

        🏦 المستثمر: {min(100, result['score']+20)}/100  

        ----------------------

        📌 التوصية: {"🔥 دخول" if result['score']>70 else "⚠️ انتظار"}
        </div>
        """, unsafe_allow_html=True)

        # ----------- CHART -----------
        df = result["data"]

        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close']
        )])

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("❌ لا توجد بيانات")

# ------------------ OPPORTUNITIES ------------------
with tab2:
    rows = []

    for s in EGX_SYMBOLS:
        r = analyze(s)
        if r:
            rows.append(r)

    if rows:
        df = pd.DataFrame(rows)
        df = df.sort_values("score", ascending=False)

        df["التقييم"] = df["score"].apply(
            lambda x: "🔥 قوية" if x>=70 else "⚠️ متوسطة" if x>=50 else "❌ ضعيفة"
        )

        st.dataframe(df[[
            "symbol","price","rsi","support","resistance","score","التقييم"
        ]], use_container_width=True)

    else:
        st.warning("❌ لا توجد فرص")
