import streamlit as st
import pandas as pd
from tradingview_ta import TA_Handler, Interval

st.set_page_config(layout="wide")

# ================= DARK MODE =================
st.markdown("""
<style>
html, body {
    background-color: #0b1320;
    color: white;
}

.card {
    background: #111827;
    padding: 12px;
    border-radius: 15px;
    margin-top: 10px;
    line-height: 1.5;
}

hr {
    margin: 8px 0;
}

.stTextInput input {
    background: #111827;
    color: white;
    border-radius: 10px;
}
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

        return analysis.indicators
    except:
        return None

# ================= CALCULATIONS =================
def analyze(d):

    price = d.get("close", 4.42)
    high = d.get("high", 4.79)
    low = d.get("low", 3.73)
    rsi = d.get("RSI", 50)

    support1 = round(low,2)
    support2 = round(low*0.97,2)

    resistance1 = round(high*0.95,2)
    resistance2 = round(high,2)

    entry = round(support1*1.02,2)
    stop = round(support2*0.98,2)
    target = round(resistance1,2)

    # Scores
    scalper = 50 + (20 if rsi<40 else -10 if rsi>70 else 10)
    swing = 50 + (20 if 40<rsi<60 else 0)
    invest = 50 + (10 if rsi<60 else 0)

    return {
        "price":price,"rsi":rsi,
        "s1":support1,"s2":support2,
        "r1":resistance1,"r2":resistance2,
        "entry":entry,"stop":stop,"target":target,
        "scalper":scalper,"swing":swing,"invest":invest
    }

# ================= AI COMMENT =================
def ai_comment(data):

    if data["rsi"] > 70:
        return "السهم متشبع شراء ⚠️ يفضل انتظار تصحيح"
    elif data["rsi"] < 40:
        return "السهم قريب من دعم 🔥 فرصة مضاربة"
    else:
        return "السهم في منطقة حيادية 👀 راقب الاختراق"

# ================= UI =================
st.title("🏹 EGX Sniper PRO")

tab1, tab2 = st.tabs(["📊 تحليل سهم","🔥 فرص"])

# ================= TAB 1 =================
with tab1:

    symbol = st.text_input("ادخل كود السهم", "MAAL")

    d = get_data(symbol)

    if d:
        data = analyze(d)

        st.markdown(f"""
        <div class="card">

        <h3>{symbol}</h3>

        💰 السعر: {data['price']} | RSI: {data['rsi']}

        <hr>

        🧱 دعم 1: {data['s1']}  
        🧱 دعم 2: {data['s2']}

        🚧 مقاومة 1: {data['r1']}  
        🚧 مقاومة 2: {data['r2']}

        <hr>

        🎯 دخول: {data['entry']}  
        ❌ وقف خسارة: {data['stop']}  
        🎯 هدف: {data['target']}

        <hr>

        ⚡ مضارب: {data['scalper']}/100  
        🔁 سوينج: {data['swing']}/100  
        🏦 مستثمر: {data['invest']}/100  

        <hr>

        🤖 {ai_comment(data)}

        </div>
        """, unsafe_allow_html=True)

# ================= TAB 2 =================
with tab2:

    st.subheader("🔥 أفضل الفرص")

    symbols = ["ATQA","FWRY","SWDY","EFIH","ORAS"]

    rows = []

    for s in symbols:
        d = get_data(s)

        if not d:
            continue

        data = analyze(d)

        score = int((data["scalper"]+data["swing"]+data["invest"])/3)

        if score < 60:
            continue

        rows.append({
            "🔥": "🔥",
            "السهم": s,
            "Entry": data["entry"],
            "Stop": data["stop"],
            "RSI": data["rsi"],
            "Score": score
        })

    if len(rows)==0:
        st.warning("لا توجد فرص حالياً")
    else:
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
