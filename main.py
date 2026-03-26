import streamlit as st
import requests
import pandas as pd
import numpy as np

st.set_page_config(layout="wide")

# ================= STYLE =================
st.markdown("""
<style>
.stApp {background-color:#0d1117;color:white;}
.card {
background:#161b22;
padding:18px;
border-radius:18px;
margin-bottom:15px;
box-shadow:0 0 10px rgba(0,0,0,0.4);
}
hr {border:0.5px solid #333;}
</style>
""", unsafe_allow_html=True)

# ================= SYMBOLS =================
SYMBOLS = [
"COMI","ETEL","TMGH","SWDY","EFIH","ORAS","AMOC","CLHO","OCIC",
"ATQA","RMDA","FWRY","ZMID","SVCE","ACAMD","BONY","MEPA","LUTS"
]

# ================= DATA =================
@st.cache_data(ttl=60)
def get_data(symbol):
    try:
        url = "https://scanner.tradingview.com/egypt/scan"
        payload = {
            "symbols": {"tickers": [f"EGX:{symbol}"], "query": {"types": []}},
            "columns": [
                "close","high","low","volume",
                "RSI","EMA200","MACD.macd","MACD.signal"
            ]
        }
        res = requests.post(url, json=payload).json()
        d = res["data"][0]["d"]

        return {
            "price": d[0],
            "high": d[1],
            "low": d[2],
            "volume": d[3],
            "rsi": d[4],
            "ema200": d[5],
            "macd": d[6],
            "signal": d[7]
        }
    except:
        return None

# ================= LOGIC =================
def pivots(p,h,l):
    piv = (p+h+l)/3
    s1 = (2*piv)-h
    s2 = piv-(h-l)
    r1 = (2*piv)-l
    r2 = piv+(h-l)
    return s1,s2,r1,r2

def liquidity(v):
    if v > 2_000_000: return "🔥 عالية"
    if v > 500_000: return "⚠ متوسطة"
    return "❌ ضعيفة"

def volume_spike(v):
    if v > 3_000_000:
        return "🚀 Volume Spike"
    return ""

def smart_score(p,s1,r1,rsi,ema):
    score = 50
    if rsi < 30: score += 25
    if abs(p-s1)/s1 < 0.02: score += 20
    if p > ema: score += 10
    return min(score,100)

def rating(score):
    if score >= 80: return "🔥 قوية"
    if score >= 60: return "⚠ متوسطة"
    return "❌ ضعيفة"

def ai_comment(p,s1,r1,rsi):
    if rsi < 30:
        return "🧠 ارتداد محتمل من الدعم → فرصة مضاربية"
    if p > r1:
        return "🧠 اختراق مقاومة → اتجاه صاعد"
    return "🧠 حركة عرضية"

def entry_zone(s1):
    return round(s1*1.01,2), round(s1*1.03,2)

def stop_loss(s1):
    return round(s1*0.97,2)

def confidence(score):
    return f"{score}%"

# ================= CARD =================
def show_card(sym,data):
    p,h,l,v,rsi,ema = data["price"],data["high"],data["low"],data["volume"],data["rsi"],data["ema200"]

    s1,s2,r1,r2 = pivots(p,h,l)

    score_trader = smart_score(p,s1,r1,rsi,ema)
    score_swing = min(100,60+(50-abs(50-rsi)))
    score_invest = 80 if p>ema else 50

    entry1,entry2 = entry_zone(s1)
    sl = stop_loss(s1)

    st.markdown(f"""
    <div class="card">
    <h2>{sym}</h2>

    💰 السعر: {p:.2f} | RSI: {rsi:.1f}<br><br>

    🧱 دعم 1: {s1:.2f}<br>
    🧱 دعم 2: {s2:.2f}<br><br>

    🚧 مقاومة 1: {r1:.2f}<br>
    🚧 مقاومة 2: {r2:.2f}<br><br>

    💧 السيولة: {liquidity(v)} {volume_spike(v)}<br>

    <hr>

    🎯 التقييم: {rating(score_trader)} ({score_trader}/100)<br>
    🧠 {ai_comment(p,s1,r1,rsi)}<br>

    🎯 منطقة دخول: {entry1} - {entry2}<br>
    ❌ وقف خسارة: {sl}<br>
    📊 Confidence: {confidence(score_trader)}

    <hr>

    🎯 المضارب: {score_trader}/100<br>
    🔁 السوينج: {int(score_swing)}/100<br>
    🏦 المستثمر: {score_invest}/100<br>

    <hr>

    📌 ملحوظة: أقرب دعم {s1:.2f} - دعم أقوى {s2:.2f}

    </div>
    """, unsafe_allow_html=True)

# ================= SCANNER =================
def scan():
    rows = []
    for s in SYMBOLS:
        d = get_data(s)
        if not d: continue

        p,h,l,v,rsi,ema = d["price"],d["high"],d["low"],d["volume"],d["rsi"],d["ema200"]
        s1,s2,r1,r2 = pivots(p,h,l)

        score = smart_score(p,s1,r1,rsi,ema)

        rows.append({
            "السهم": s,
            "السعر": round(p,2),
            "RSI": round(rsi,1),
            "دعم": round(s1,2),
            "مقاومة": round(r1,2),
            "التقييم": rating(score),
            "Score": score
        })

    df = pd.DataFrame(rows).sort_values("Score",ascending=False)
    return df

# ================= UI =================
st.title("🏹 EGX Sniper PRO")

tab1,tab2 = st.tabs(["📊 تحليل سهم","🔥 الفرص"])

with tab1:
    sym = st.text_input("ادخل السهم").upper()
    if sym:
        d = get_data(sym)
        if d:
            show_card(sym,d)
        else:
            st.error("السهم غير متاح")

with tab2:
    st.subheader("🔥 أفضل الفرص")
    df = scan()
    st.dataframe(df, use_container_width=True)
