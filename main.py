import streamlit as st
import pandas as pd
import numpy as np
from tradingview_ta import TA_Handler, Interval
import plotly.graph_objects as go

st.set_page_config(layout="wide")

# =========================
# ⚙️ إعدادات
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
            "ema200": d.get("EMA200", 0),
        }
    except:
        return None


# =========================
# 🧠 Smart Score
# =========================
def smart_score(d):
    p, rsi, ema = d["price"], d["rsi"], d["ema200"]
    s1, r1 = d["low"], d["high"]

    score = 0

    if abs(p - s1)/s1 < 0.015:
        score += 25

    if rsi < 35:
        score += 25
    elif rsi < 45:
        score += 15
    elif rsi > 70:
        score -= 20

    if p > ema:
        score += 20
    else:
        score -= 10

    if p > r1 * 0.995:
        score += 25

    return max(min(score,100),0)


# =========================
# 📊 Recommendation AI
# =========================
def ai_recommendation(d, score):
    p, rsi = d["price"], d["rsi"]
    s1, r1 = d["low"], d["high"]

    if score >= 80:
        return "📈 السهم في اتجاه صاعد مع اقتراب من اختراق مقاومة — فرصة شراء قوية"
    elif score >= 65:
        return "✅ السهم جيد لكن يحتاج تأكيد — يفضل الدخول مع اختراق المقاومة"
    elif score >= 50:
        return "⚠ السهم في نطاق عرضي — يفضل الانتظار"
    else:
        return "❌ السهم ضعيف حالياً — تجنب الدخول"


# =========================
# 🎯 Strategy
# =========================
def strategy(d):
    entry = d["price"]
    stop = round(d["low"] * 0.98, 2)
    target = round(d["high"] * 1.02, 2)

    rr = round((target-entry)/(entry-stop),2) if (entry-stop)!=0 else 0

    return entry, stop, target, rr


# =========================
# 📉 Fake Chart (Simulation)
# =========================
def draw_chart(price):
    prices = np.random.normal(price, price*0.01, 50)

    fig = go.Figure()
    fig.add_trace(go.Scatter(y=prices, mode='lines'))
    fig.update_layout(height=300, margin=dict(l=10,r=10,t=10,b=10))

    return fig


# =========================
# 📊 Scan Market
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
            "دعم": round(d["low"],2),
            "مقاومة": round(d["high"],2),
            "Score": score
        })

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    return df.sort_values("Score", ascending=False)


# =========================
# UI
# =========================
st.title("🏹 EGX Sniper PRO MAX AI")

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

            st.write(f"🧱 دعم: {round(d['low'],2)}")
            st.write(f"🚧 مقاومة: {round(d['high'],2)}")

            st.write(f"🎯 Score: {score}")

            # AI Recommendation
            st.info(ai_recommendation(d, score))

            # Strategy
            entry, stop, target, rr = strategy(d)

            st.write(f"🎯 دخول: {entry}")
            st.write(f"❌ وقف خسارة: {stop}")
            st.write(f"🏁 هدف: {target}")
            st.write(f"📊 R/R: {rr}")

            # Chart
            st.plotly_chart(draw_chart(d["price"]), use_container_width=True)

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
        df = df[df["Score"] >= 65]

        st.subheader("🔥 أفضل الفرص")
        st.dataframe(df.head(5))
