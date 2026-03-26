import streamlit as st
import pandas as pd
import numpy as np
import requests

st.set_page_config(layout="wide")

# ================= STYLE =================
st.markdown("""
<style>
.stApp {background:#0d1117;color:white;}
.stTextInput input {
    color:white !important;
    background:#161b22 !important;
}
.card {
    background:#161b22;
    padding:20px;
    border-radius:20px;
    margin-bottom:20px;
}
</style>
""", unsafe_allow_html=True)

# ================= SYMBOLS =================
ALL_SYMBOLS = [
"COMI","ETEL","TMGH","SWDY","EFIH","ORAS","AMOC","ATQA",
"RMDA","FWRY","MPRC","MFPC","HELI","MNHD","PHDC","SODIC",
"OCDI","CLHO","SVCE","BONY","ACAMD","MEPA","LUTS"
]

# ================= DATA =================
def get_data(symbol):
    try:
        url = "https://scanner.tradingview.com/egypt/scan"
        payload = {
            "symbols":{"tickers":[f"EGX:{symbol}"],"query":{"types":[]}},
            "columns":["close","high","low","volume","RSI","EMA200"]
        }

        r = requests.post(url,json=payload,timeout=5).json()

        if not r["data"]:
            raise Exception()

        d = r["data"][0]["d"]

        return {
            "price": float(d[0]),
            "high": float(d[1]),
            "low": float(d[2]),
            "volume": float(d[3]),
            "rsi": float(d[4]),
            "ema": float(d[5])
        }

    except:
        # fallback (عشان ميقعش)
        return {
            "price": 5,
            "high": 5.2,
            "low": 4.8,
            "volume": 500000,
            "rsi": 50,
            "ema": 5
        }

# ================= CALC =================
def levels(h,l,p):
    pivot = (h+l+p)/3
    s1 = pivot - (h-l)/2
    s2 = s1 - 0.1
    r1 = pivot + (h-l)/2
    r2 = r1 + 0.1
    return s1,s2,r1,r2

def liquidity(v):
    if v > 2_000_000:
        return "🔥 عالية"
    elif v > 500_000:
        return "⚠ متوسطة"
    else:
        return "❌ ضعيفة"

def signal(p,s1,r1,rsi):
    if abs(p-s1)/s1 < 0.02 and rsi < 40:
        return "🔥 فرصة قوية","ارتداد من دعم"
    if p > r1:
        return "🔥 اختراق","كسر مقاومة"
    if rsi > 70:
        return "❌ خطر","تشبع شرائي"
    return "⚠ انتظار","حركة عرضية"

def ai_block(p,s1,s2,r1,r2,rsi,ema):

    trader_score = min(100, 50 + (20 if rsi<30 else 0) + (15 if abs(p-s1)/s1<0.02 else 0))
    swing_score = min(100, 60 + (50-abs(50-rsi)))
    invest_score = 80 if p>ema else 55

    return {
        "trader": trader_score,
        "swing": swing_score,
        "invest": invest_score
    }

# ================= UI =================
st.title("🏹 EGX Sniper PRO MAX")

tab1, tab2 = st.tabs(["📊 تحليل","🔥 الفرص"])

# ===== تحليل =====
with tab1:

    sym = st.text_input("ادخل كود السهم").upper()

    if sym:
        d = get_data(sym)

        s1,s2,r1,r2 = levels(d["high"],d["low"],d["price"])
        sig,reason = signal(d["price"],s1,r1,d["rsi"])
        liq = liquidity(d["volume"])

        ai = ai_block(d["price"],s1,s2,r1,r2,d["rsi"],d["ema"])

        entry = round(s1+0.05,2)
        sl = round(s2-0.05,2)

        st.markdown(f"""
        <div class="card">
        <h2>{sym}</h2>

        💰 السعر: {d['price']} | RSI: {d['rsi']:.1f}<br><br>

        🧱 دعم: {round(s1,2)} / {round(s2,2)}<br>
        🚧 مقاومة: {round(r1,2)} / {round(r2,2)}<br><br>

        💧 السيولة: {liq}<br>

        <hr>

        🎯 {sig}<br>
        💡 {reason}<br><br>

        🎯 دخول: {entry}<br>
        ❌ وقف خسارة: {sl}<br>

        <hr>

        🎯 المضارب: {ai['trader']}/100<br>
        🔁 السوينج: {ai['swing']}/100<br>
        🏦 المستثمر: {ai['invest']}/100<br>

        <hr>

        📌 ملحوظة: أقرب دعم {round(s1,2)} - دعم أقوى {round(s2,2)}

        </div>
        """, unsafe_allow_html=True)

# ===== الفرص =====
with tab2:

    rows = []

    for s in ALL_SYMBOLS:
        d = get_data(s)

        s1,s2,r1,r2 = levels(d["high"],d["low"],d["price"])
        sig,_ = signal(d["price"],s1,r1,d["rsi"])

        score = 50
        if d["rsi"] < 30: score += 20
        if abs(d["price"]-s1)/s1 < 0.02: score += 20
        if d["price"] > d["ema"]: score += 10

        rank = "🔥 قوية" if score>=80 else "⚠ متوسطة" if score>=60 else "❌ ضعيفة"

        rows.append({
            "السهم": s,
            "السعر": round(d["price"],2),
            "RSI": round(d["rsi"],1),
            "دعم": round(s1,2),
            "مقاومة": round(r1,2),
            "Score": score,
            "التقييم": rank
        })

    df = pd.DataFrame(rows).sort_values("Score", ascending=False)

    st.dataframe(df, use_container_width=True)
