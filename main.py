import streamlit as st
import pandas as pd
import numpy as np
import time
from tradingview_ta import TA_Handler, Interval

st.set_page_config(layout="wide")

# ---------- DARK UI (زي الأول بالظبط) ----------
st.markdown("""
<style>
body {
    background-color: #0b0f1a;
    color: white;
}
.stApp {
    background-color: #0b0f1a;
}
.card {
    background: linear-gradient(145deg, #111827, #0b0f1a);
    padding: 20px;
    border-radius: 20px;
    box-shadow: 0 0 20px rgba(0,0,0,0.5);
    margin-top: 20px;
}
input {
    background-color: #1f2937 !important;
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

# ---------- FUNCTIONS ----------
def get_tv_data(symbol):
    for i in range(3):  # retry 3 مرات
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
                "high": d["high"],
                "low": d["low"],
            }

        except:
            time.sleep(1)

    return None


def analyze(symbol):
    data = get_tv_data(symbol)

    if data is None:
        return None

    price = data["price"]
    rsi = data["rsi"]

    support = data["low"]
    resistance = data["high"]

    score = 0

    if 40 < rsi < 60:
        score += 30
    if price > support:
        score += 30
    if price < resistance:
        score += 20
    if rsi < 70:
        score += 20

    return {
        "symbol": symbol,
        "price": round(price,2),
        "rsi": round(rsi,1),
        "support": round(support,2),
        "resistance": round(resistance,2),
        "score": score
    }


# ---------- UI ----------
st.title("🏹 EGX Sniper PRO MAX")

tab1, tab2 = st.tabs(["📊 تحليل سهم", "🔥 الفرص"])

# ---------- ANALYSIS ----------
with tab1:
    symbol = st.text_input("ادخل كود السهم", "TMGH")

    if symbol:
        result = analyze(symbol.upper())

        if result:

            rec = "🔥 دخول" if result["score"] >= 70 else "⚠️ انتظار" if result["score"] >= 50 else "❌ تجنب"

            st.markdown(f"""
            <div class="card">

            <h2>{result['symbol']}</h2>

            💰 السعر: {result['price']} | RSI: {result['rsi']}

            🧱 دعم: {result['support']}  
            🚧 مقاومة: {result['resistance']}  

            💧 السيولة: {"عالية" if result['score']>70 else "متوسطة"}

            ----------------------

            🎯 التقييم: {result['score']}/100  
            💡 {"ارتداد من دعم قوي" if result['score']>70 else "حركة عرضية"}

            ----------------------

            🎯 دخول: {round(result['price']*1.01,2)}  
            ❌ وقف خسارة: {round(result['support']*0.99,2)}

            ----------------------

            📌 التوصية: {rec}

            </div>
            """, unsafe_allow_html=True)

        else:
            st.error("❌ السهم غير متاح أو TradingView واقع حالياً")


# ---------- OPPORTUNITIES ----------
with tab2:

    symbols = ["COMI","ETEL","TMGH","SWDY","EFIH","ORAS","AMOC","RMDA","FWRY","MPRC"]

    rows = []

    for s in symbols:
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
        st.error("❌ لا توجد فرص حالياً")
