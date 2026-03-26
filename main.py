import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go

st.set_page_config(layout="wide")

# ================= STYLE =================
st.markdown("""
<style>
.stApp {background:#0d1117;color:white;}
.card {
background:#161b22;
padding:20px;
border-radius:20px;
margin-bottom:20px;
}
</style>
""", unsafe_allow_html=True)

# ================= SYMBOLS =================
SYMBOLS = ["COMI","ETEL","TMGH","SWDY","EFIH","ORAS","AMOC","ATQA","RMDA","FWRY"]

# ================= REALTIME =================
def get_realtime(symbol):
    try:
        url = "https://scanner.tradingview.com/egypt/scan"
        payload = {
            "symbols":{"tickers":[f"EGX:{symbol}"],"query":{"types":[]}},
            "columns":["close","high","low","volume","RSI","EMA200"]
        }

        r = requests.post(url,json=payload).json()
        d = r["data"][0]["d"]

        return {
            "price": d[0],
            "high": d[1],
            "low": d[2],
            "volume": d[3],
            "rsi": d[4],
            "ema": d[5]
        }
    except:
        return None

# ================= HISTORICAL =================
def get_history(symbol):
    try:
        url = f"https://stooq.com/q/d/l/?s={symbol.lower()}.eg&i=d"
        df = pd.read_csv(url)

        df.columns = ["Date","Open","High","Low","Close","Volume"]
        df = df.dropna()

        return df.tail(120)
    except:
        return None

# ================= LEVELS =================
def smart_money(df):

    support = df["Low"].tail(20).min()
    resistance = df["High"].tail(20).max()

    liquidity_low = df["Low"].tail(50).min()
    liquidity_high = df["High"].tail(50).max()

    return support, resistance, liquidity_low, liquidity_high

# ================= RSI =================
def calc_rsi(df):
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    return (100 - (100/(1+rs))).iloc[-1]

# ================= SIGNAL ENGINE =================
def signal_engine(p, support, resistance, rsi, ema, volume):

    signal = "WAIT"
    reason = ""

    near_support = abs(p - support)/support < 0.02

    if near_support and rsi < 35 and volume > 1_000_000:
        signal = "BUY"
        reason = "ارتداد من دعم + RSI منخفض + سيولة"

    elif p > resistance and volume > 1_500_000:
        signal = "BUY"
        reason = "اختراق مقاومة + سيولة قوية"

    elif rsi > 70:
        signal = "SELL"
        reason = "تشبع شرائي"

    return signal, reason

# ================= AI =================
def ai_score(p,s,r,rsi,ema,volume):

    score = 50
    if rsi < 30: score += 20
    if abs(p-s)/s < 0.02: score += 25
    if p > ema: score += 10
    if volume > 1_000_000: score += 10

    return min(score,100)

# ================= CHART =================
def chart(df):

    fig = go.Figure(data=[go.Candlestick(
        x=df["Date"],
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"]
    )])

    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

# ================= BACKTEST =================
def backtest(df):

    wins = 0
    trades = 0

    for i in range(30,len(df)-5):

        window = df.iloc[i-30:i]
        p = df["Close"].iloc[i]

        support = window["Low"].min()
        rsi = calc_rsi(window)

        if p <= support*1.02 and rsi < 35:
            trades += 1
            future = df["Close"].iloc[i+5]

            if future > p:
                wins += 1

    if trades == 0:
        return 0,0

    return trades, round((wins/trades)*100,2)

# ================= UI =================
st.title("🏹 EGX Sniper PRO MAX")

tab1, tab2, tab3 = st.tabs(["📊 تحليل","🔥 الفرص","📈 Backtest"])

# ===== تحليل =====
with tab1:
    sym = st.text_input("ادخل السهم").upper()

    if sym:
        rt = get_realtime(sym)
        hist = get_history(sym)

        if rt and hist is not None:

            s,r,liq_low,liq_high = smart_money(hist)
            rsi = calc_rsi(hist)

            signal, reason = signal_engine(
                rt["price"], s, r, rsi, rt["ema"], rt["volume"]
            )

            score = ai_score(rt["price"],s,r,rsi,rt["ema"],rt["volume"])

            st.markdown(f"""
            <div class="card">
            <h2>{sym}</h2>

            💰 السعر: {rt["price"]}<br>
            📉 RSI: {rsi:.1f}<br>

            🧱 دعم: {round(s,2)}<br>
            🚧 مقاومة: {round(r,2)}<br>

            💧 Liquidity Zone: {round(liq_low,2)} - {round(liq_high,2)}

            <hr>

            🎯 Signal: {signal}<br>
            💡 {reason}<br>

            🎯 Score: {score}/100

            </div>
            """, unsafe_allow_html=True)

            chart(hist)

# ===== الفرص =====
with tab2:

    rows = []

    for s in SYMBOLS:
        rt = get_realtime(s)
        hist = get_history(s)

        if rt and hist is not None:
            sup,res,_,_ = smart_money(hist)
            rsi = calc_rsi(hist)

            signal,_ = signal_engine(rt["price"],sup,res,rsi,rt["ema"],rt["volume"])
            score = ai_score(rt["price"],sup,res,rsi,rt["ema"],rt["volume"])

            rows.append({
                "السهم": s,
                "السعر": rt["price"],
                "Signal": signal,
                "Score": score
            })

    df = pd.DataFrame(rows).sort_values("Score",ascending=False)
    st.dataframe(df)

# ===== Backtest =====
with tab3:

    sym_bt = st.text_input("Backtest سهم").upper()

    if sym_bt:
        hist = get_history(sym_bt)

        if hist is not None:
            trades, winrate = backtest(hist)

            st.metric("عدد الصفقات", trades)
            st.metric("نسبة النجاح %", winrate)

            chart(hist)
