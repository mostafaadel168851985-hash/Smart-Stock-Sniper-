import streamlit as st
import pandas as pd
from tradingview_ta import TA_Handler, Interval

st.set_page_config(layout="wide")

# ========= STYLE (تقليل المسافات فقط) =========
st.markdown("""
<style>
.block-container {
    padding-top: 1rem;
    padding-bottom: 1rem;
}
hr {
    margin: 6px 0 !important;
}
.card {
    background:#020617;
    padding:12px 14px;
    border-radius:12px;
    line-height:1.4;
    font-size:14px;
}
</style>
""", unsafe_allow_html=True)

st.title("🏹 EGX Sniper PRO")

tabs = st.tabs(["📊 تحليل سهم","🔥 فرص"])

# ========= DATA =========
def get_data(symbol):
    handler = TA_Handler(
        symbol=symbol,
        screener="egypt",
        exchange="EGX",
        interval=Interval.INTERVAL_1_DAY
    )
    analysis = handler.get_analysis()

    return {
        "price": analysis.indicators.get("close", 0),
        "high": analysis.indicators.get("high", 0),
        "low": analysis.indicators.get("low", 0),
        "volume": analysis.indicators.get("volume", 0),
        "rsi": analysis.indicators.get("RSI", 0)
    }

# ========= CALC =========
def pivots(p,h,l):
    pivot = (h+l+p)/3
    s1 = 2*pivot - h
    s2 = pivot - (h-l)
    r1 = 2*pivot - l
    r2 = pivot + (h-l)
    return s1,s2,r1,r2

# ========= CARD (نفس القديم بالظبط + compact) =========
def show_card(code,p,h,l,v,rsi):

    s1,s2,r1,r2 = pivots(p,h,l)

    st.markdown(f"""
    <div class="card">

    <h3 style="margin-bottom:6px;">{code} -</h3>

    💰 السعر الحالي: {p:.2f}<br>
    📉 RSI: {rsi:.1f}

    <div style="margin-top:4px;">
    🧱 الدعم: {s1:.2f} / {s2:.2f} &nbsp;&nbsp;
    🚧 المقاومة: {r1:.2f} / {r2:.2f}
    </div>

    <div style="margin-top:3px;">
    💧 السيولة: {"عالية" if v>2_000_000 else "متوسطة" if v>1_000_000 else "ضعيفة"}
    </div>

    <hr>

    🔄 لا توجد إشارة ارتداد<br>
    ⚡ لا يوجد تأكيد

    <hr>

    🎯 المضارب: 50/100<br>
    دخول: {round(s1+0.1,2)} | وقف خسارة: {round(s1-0.15,2)}

    <div style="margin-top:3px;">
    🔁 السوينج: 65/100<br>
    دخول: {round((s1+r1)/2,2)} | وقف خسارة: {round((s1+r1)/2-0.25,2)}
    </div>

    <div style="margin-top:3px;">
    🏦 المستثمر: 55/100<br>
    دخول: {round((s1+s2)/2,2)} | وقف خسارة: {round(s2-0.25,2)}
    </div>

    <hr>

    📌 التوصية: انتظار

    </div>
    """, unsafe_allow_html=True)

# ========= TAB 1 =========
with tabs[0]:

    symbol = st.text_input("ادخل كود السهم", "MAAL")

    if symbol:
        try:
            data = get_data(symbol)

            show_card(
                symbol,
                data['price'],
                data['high'],
                data['low'],
                data['volume'],
                data['rsi']
            )

            st.markdown("### 📊 الشارت")

            st.components.v1.html(f"""
            <iframe src="https://s.tradingview.com/widgetembed/?symbol=EGX:{symbol}&interval=D"
            width="100%" height="400"></iframe>
            """, height=400)

        except:
            st.error("السهم غير متاح")

# ========= TAB 2 =========
with tabs[1]:

    st.subheader("🔥 فرص جاهزة")

    symbols = ["ATQA","FWRY","SWDY"]

    rows = []

    for s in symbols:
        try:
            d = get_data(s)
            p = d['price']
            rsi = d['rsi']

            score = 50

            if rsi < 40:
                score += 20
            elif rsi > 70:
                score -= 10

            rows.append({
                "🔥": "🔥" if score >= 70 else "⭐" if score >= 55 else "👀",
                "السهم": s,
                "السعر": round(p,2),
                "RSI": round(rsi,1),
                "Score": score
            })

        except:
            pass

    df = pd.DataFrame(rows).sort_values("Score", ascending=False)

    st.dataframe(df, use_container_width=True)
