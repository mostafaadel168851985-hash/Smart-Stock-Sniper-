import streamlit as st
import pandas as pd
import random

st.set_page_config(layout="wide")

# ================= FORCE DARK MODE =================
st.markdown("""
<style>
html, body, .stApp {
    background-color: #0b1320 !important;
    color: white !important;
}

.card {
    background: #111827;
    padding: 12px;
    border-radius: 15px;
    margin-top: 10px;
    line-height: 1.5;
    color: white;
}

hr {
    margin: 8px 0;
}

.stTextInput input {
    background: #111827 !important;
    color: white !important;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

# ================= FAKE DATA (عشان نضمن يشتغل 100%) =================
def get_data(symbol):
    return {
        "price": round(random.uniform(3,10),2),
        "rsi": round(random.uniform(30,70),1),
        "low": round(random.uniform(3,4),2),
        "high": round(random.uniform(4,6),2)
    }

# ================= LOGIC =================
def analyze(d):
    s1 = d["low"]
    s2 = round(s1 * 0.97,2)

    r1 = round(d["high"] * 0.95,2)
    r2 = d["high"]

    entry = round(s1 * 1.02,2)
    stop = round(s2 * 0.98,2)
    target = r1

    scalper = random.randint(50,80)
    swing = random.randint(50,80)
    invest = random.randint(50,80)

    return {
        "price":d["price"], "rsi":d["rsi"],
        "s1":s1,"s2":s2,
        "r1":r1,"r2":r2,
        "entry":entry,"stop":stop,"target":target,
        "scalper":scalper,"swing":swing,"invest":invest
    }

def ai_comment(rsi):
    if rsi > 70:
        return "تشبع شراء ⚠️"
    elif rsi < 40:
        return "قريب من دعم 🔥"
    else:
        return "منطقة حيادية 👀"

# ================= UI =================
st.title("🏹 EGX Sniper PRO")

tab1, tab2 = st.tabs(["📊 تحليل سهم","🔥 فرص"])

# ================= تحليل =================
with tab1:

    symbol = st.text_input("ادخل كود السهم", "MAAL")

    d = get_data(symbol)
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

    🤖 {ai_comment(data['rsi'])}

    </div>
    """, unsafe_allow_html=True)

# ================= فرص =================
with tab2:

    st.subheader("🔥 أفضل الفرص")

    symbols = ["ATQA","FWRY","SWDY","EFIH","ORAS"]

    rows = []

    for s in symbols:
        d = get_data(s)
        data = analyze(d)

        score = int((data["scalper"]+data["swing"]+data["invest"])/3)

        if score < 60:
            continue

        rows.append({
            "🔥": "⭐",
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
