import streamlit as st
import pandas as pd
from tradingview_ta import TA_Handler, Interval

st.set_page_config(layout="wide")

# ================= DARK MODE =================
st.markdown("""
<style>
html, body, .stApp {
    background-color: #0b1320 !important;
    color: white !important;
}
.card {
    background: #111827;
    padding: 14px;
    border-radius: 18px;
    margin-top: 10px;
    line-height: 1.6;
}
hr {margin:8px 0;}
</style>
""", unsafe_allow_html=True)

# ================= GET DATA =================
def get_data(symbol):
    try:
        handler = TA_Handler(
            symbol=symbol,
            screener="egypt",
            exchange="EGX",
            interval=Interval.INTERVAL_1_DAY
        )
        analysis = handler.get_analysis()

        return {
            "price": analysis.indicators["close"],
            "rsi": analysis.indicators["RSI"],
            "high": analysis.indicators["high"],
            "low": analysis.indicators["low"]
        }
    except:
        return None

# ================= LOGIC =================
def analyze(d):

    s1 = round(d["low"],2)
    s2 = round(d["low"] * 0.97,2)

    r1 = round(d["high"] * 0.97,2)
    r2 = round(d["high"],2)

    entry = round(s1 * 1.02,2)
    stop = round(s2 * 0.98,2)

    scalper = int(100 - abs(50 - d["rsi"]))
    swing = int(100 - abs(55 - d["rsi"]))
    invest = int(100 - abs(60 - d["rsi"]))

    return {
        "s1":s1,"s2":s2,
        "r1":r1,"r2":r2,
        "entry":entry,"stop":stop,
        "scalper":scalper,
        "swing":swing,
        "invest":invest
    }

# ================= AI COMMENT =================
def ai_comment(rsi):
    if rsi > 70:
        return "⚠️ السهم في تشبع شراء - احتمال تصحيح"
    elif rsi < 40:
        return "🔥 قريب من دعم قوي - فرصة محتملة"
    else:
        return "👀 السهم في منطقة حيادية"

# ================= UI =================
st.title("🏹 EGX Sniper PRO")

tab1, tab2 = st.tabs(["📊 تحليل سهم","🔥 فرص"])

# ================= تحليل =================
with tab1:

    symbol = st.text_input("ادخل كود السهم", "MAAL")

    data = get_data(symbol)

    if not data:
        st.error("السهم غير متاح")
    else:
        a = analyze(data)

        st.markdown(f"""
        <div class="card">

        <h3>{symbol}</h3>

        💰 السعر الحالي: {round(data['price'],2)}  
        📉 RSI: {round(data['rsi'],1)}

        <hr>

        🧱 الدعم: {a['s1']} / {a['s2']}  
        🚧 المقاومة: {a['r1']} / {a['r2']}  

        💧 السيولة: عالية

        <hr>

        🔄 لا توجد إشارة ارتداد  
        ⚡ لا يوجد تأكيد

        <hr>

        🎯 المضارب: {a['scalper']}/100  
        دخول: {a['entry']} | وقف خسارة: {a['stop']}

        🔁 السوينج: {a['swing']}/100  
        دخول: {round(a['entry']*1.04,2)} | وقف: {round(a['stop']*1.04,2)}

        🏦 المستثمر: {a['invest']}/100  
        دخول: {round(a['entry']*0.95,2)} | وقف: {round(a['stop']*0.95,2)}

        <hr>

        📌 التوصية: {ai_comment(data['rsi'])}

        </div>
        """, unsafe_allow_html=True)

# ================= فرص =================
with tab2:

    st.subheader("🔥 أفضل الفرص")

    symbols = ["ATQA","FWRY","SWDY","EFIH","ORAS","HRHO","TMGH"]

    rows = []

    for s in symbols:
        d = get_data(s)
        if not d:
            continue

        a = analyze(d)

        score = int((a["scalper"]+a["swing"]+a["invest"])/3)

        # شرط الفرصة الحقيقية
        if d["rsi"] < 60 and score > 60:

            rows.append({
                "🔥": "⭐",
                "السهم": s,
                "السعر": round(d["price"],2),
                "Entry": a["entry"],
                "Stop": a["stop"],
                "RSI": round(d["rsi"],1),
                "Score": score
            })

    if len(rows)==0:
        st.warning("لا توجد فرص حالياً")
    else:
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
