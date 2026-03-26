import streamlit as st
import pandas as pd
import numpy as np
from tradingview_ta import TA_Handler, Interval
import plotly.graph_objects as go

st.set_page_config(layout="wide")

# =========================
# ⚙️ الأسهم
# =========================
EGX_SYMBOLS = [
    "COMI","ETEL","TMGH","SWDY","EFIH","ORAS","AMOC",
    "RMDA","FWRY","MPRC","SIPC","MAAL","EKHO","JUFO"
]

# =========================
# 📊 TradingView Data
# =========================
def get_data(symbol):
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
            "symbol": symbol,
            "price": d.get("close", 0),
            "rsi": d.get("RSI", 50),
            "high": d.get("high", 0),
            "low": d.get("low", 0),
            "ema50": d.get("EMA50", 0),
            "ema200": d.get("EMA200", 0),
        }
    except:
        return None


# =========================
# 🧠 Trend Detection
# =========================
def trend(d):
    if d["price"] > d["ema50"] > d["ema200"]:
        return "UP"
    elif d["price"] < d["ema50"] < d["ema200"]:
        return "DOWN"
    else:
        return "SIDE"


# =========================
# 🔥 Breakout / Pullback
# =========================
def setup(d):
    p, r1, s1 = d["price"], d["high"], d["low"]

    if p > r1 * 0.995:
        return "BREAKOUT"
    elif abs(p - s1)/s1 < 0.02:
        return "PULLBACK"
    else:
        return "NONE"


# =========================
# 🎯 Smart Score
# =========================
def smart_score(d):
    score = 0

    if trend(d) == "UP":
        score += 30

    if setup(d) == "BREAKOUT":
        score += 30
    elif setup(d) == "PULLBACK":
        score += 20

    if d["rsi"] < 40:
        score += 20

    return min(score,100)


# =========================
# 🎯 Smart Entry
# =========================
def strategy(d, score):
    p, s1, r1 = d["price"], d["low"], d["high"]

    if score < 60:
        return None, None, None, None

    # breakout
    if setup(d) == "BREAKOUT":
        entry = r1
    else:
        entry = s1

    stop = round(entry * 0.97, 2)
    target = round(entry * 1.05, 2)

    rr = round((target-entry)/(entry-stop),2)

    return entry, stop, target, rr


# =========================
# 🤖 AI Recommendation
# =========================
def ai(d, score):
    t = trend(d)
    s = setup(d)

    if score >= 80:
        return f"🔥 اتجاه صاعد قوي + {s} — فرصة ممتازة"
    elif score >= 60:
        return f"✅ اتجاه {t} مع {s} — فرصة محتملة"
    else:
        return f"❌ لا يوجد اتجاه واضح — تجنب"


# =========================
# 📉 Candlestick Chart (Fake OHLC but realistic)
# =========================
def chart(price):
    data = []

    last = price

    for _ in range(50):
        open_p = last
        close = open_p + np.random.normal(0, price*0.01)
        high = max(open_p, close) + np.random.rand()*0.02*price
        low = min(open_p, close) - np.random.rand()*0.02*price

        data.append([open_p, high, low, close])
        last = close

    df = pd.DataFrame(data, columns=["Open","High","Low","Close"])

    fig = go.Figure(data=[go.Candlestick(
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"]
    )])

    fig.update_layout(height=400)
    return fig


# =========================
# 📊 Scan
# =========================
def scan():
    rows = []

    for s in EGX_SYMBOLS:
        d = get_data(s)
        if not d:
            continue

        score = smart_score(d)

        rows.append({
            "السهم": s,
            "السعر": round(d["price"],2),
            "RSI": round(d["rsi"],1),
            "Trend": trend(d),
            "Setup": setup(d),
            "Score": score
        })

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    return df.sort_values("Score", ascending=False)


# =========================
# UI
# =========================
st.title("🏹 EGX Sniper PRO MAX - Institutional Edition")

tab1, tab2 = st.tabs(["📊 تحليل سهم", "🔥 الفرص"])

# =========================
# تحليل سهم
# =========================
with tab1:
    symbol = st.text_input("ادخل السهم").upper()

    if symbol:
        d = get_data(symbol)

        if d:
            score = smart_score(d)

            st.subheader(symbol)

            st.write(f"💰 السعر: {d['price']}")
            st.write(f"📊 RSI: {round(d['rsi'],1)}")

            st.write(f"📈 Trend: {trend(d)}")
            st.write(f"🔥 Setup: {setup(d)}")

            st.write(f"🎯 Score: {score}")

            st.info(ai(d, score))

            entry, stop, target, rr = strategy(d, score)

            if entry:
                st.success(f"🎯 دخول: {entry}")
                st.write(f"❌ وقف خسارة: {stop}")
                st.write(f"🏁 هدف: {target}")
                st.write(f"📊 R/R: {rr}")
            else:
                st.warning("❌ لا يوجد دخول حالياً")

            st.plotly_chart(chart(d["price"]), use_container_width=True)

        else:
            st.warning("السهم غير متاح")


# =========================
# الفرص
# =========================
with tab2:
    df = scan()

    if df.empty:
        st.warning("لا توجد بيانات")
    else:
        df = df[df["Score"] >= 60]

        st.subheader("🔥 أفضل الفرص")
        st.dataframe(df.head(5))
