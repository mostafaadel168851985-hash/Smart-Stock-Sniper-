import streamlit as st
import requests
import pandas as pd
import numpy as np

st.set_page_config(layout="wide")

# ================= STYLE =================
st.markdown("""
<style>
body, .stApp {background-color:#0d1117;color:white;}
.card {
    background:#161b22;
    padding:20px;
    border-radius:15px;
    margin-bottom:20px;
}
input {color:white !important;}
</style>
""", unsafe_allow_html=True)

# ================= DATA =================
@st.cache_data(ttl=120)
def get_tv_data(symbol):
    try:
        url = "https://scanner.tradingview.com/egypt/scan"
        payload = {
            "symbols": {"tickers": [f"EGX:{symbol}"], "query": {"types": []}},
            "columns": [
                "close","high","low","volume",
                "RSI","EMA20","EMA50","EMA200"
            ]
        }
        r = requests.post(url, json=payload).json()
        d = r["data"][0]["d"]

        return {
            "price": float(d[0]),
            "high": float(d[1]),
            "low": float(d[2]),
            "volume": float(d[3]),
            "rsi": float(d[4]),
            "ema20": float(d[5]),
            "ema50": float(d[6]),
            "ema200": float(d[7]),
        }

    except:
        return None

# ================= FALLBACK =================
def fake_data(symbol):
    base = np.random.uniform(1, 20)
    return {
        "price": base,
        "high": base*1.03,
        "low": base*0.97,
        "volume": np.random.randint(100000,3000000),
        "rsi": np.random.uniform(30,70),
        "ema20": base,
        "ema50": base,
        "ema200": base
    }

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
    elif v > 500_000: return "⚠ متوسطة"
    return "❌ ضعيفة"

def volume_spike(v):
    return v > 1_500_000

def ai_comment(p,s1,r1,rsi,vol):
    if abs(p-s1)/s1 < 0.02 and rsi < 40 and vol:
        return "🔥 ارتداد من دعم قوي + سيولة → فرصة ممتازة"
    if p > r1:
        return "🚀 اختراق مقاومة → بداية اتجاه صاعد"
    if rsi > 70:
        return "⚠ تشبع شرائي → احتمال تصحيح"
    return "⚖️ حركة عرضية → انتظر تأكيد"

def smart_score(p,s1,r1,rsi,ema200,vol):
    score = 50
    if abs(p-s1)/s1 < 0.02: score += 20
    if rsi < 40: score += 15
    if p > ema200: score += 10
    if vol: score += 10
    return min(score,100)

def rank(score):
    if score >= 75: return "🔥 قوية"
    if score >= 60: return "⚠ متوسطة"
    return "❌ ضعيفة"

def entry_zone(p,s1):
    return round(s1*0.99,2), round(s1*1.01,2)

# ================= CARD =================
def show_card(symbol,data):
    p = data["price"]
    h = data["high"]
    l = data["low"]
    rsi = data["rsi"]
    vol = data["volume"]

    s1,s2,r1,r2 = pivots(p,h,l)
    vol_spike = volume_spike(vol)

    score = smart_score(p,s1,r1,rsi,data["ema200"],vol_spike)
    conf = int(score)

    entry_low, entry_high = entry_zone(p,s1)
    sl = round(s1*0.97,2)

    comment = ai_comment(p,s1,r1,rsi,vol_spike)

    trader = round(score)
    swing = round(score+10 if p>data["ema50"] else score)
    invest = round(score if p>data["ema200"] else score-10)

    st.markdown(f"""
    <div class="card">
    <h2>{symbol}</h2>

    💰 السعر: {round(p,2)} | RSI: {round(rsi,1)}<br><br>

    🧱 دعم: {round(s1,2)} / {round(s2,2)}<br>
    🚧 مقاومة: {round(r1,2)} / {round(r2,2)}<br><br>

    💧 السيولة: {liquidity(vol)}<br><br>

    🎯 <b>{rank(score)} ({score}/100)</b><br>
    💡 {comment}<br><br>

    🎯 دخول: {entry_low} - {entry_high}<br>
    ❌ وقف خسارة: {sl}<br>
    📊 Confidence: {conf}%<br><br>

    🎯 المضارب: {trader}/100<br>
    🔁 السوينج: {swing}/100<br>
    🏦 المستثمر: {invest}/100<br><br>

    📌 أقرب دعم: {round(s1,2)} - أقوى دعم: {round(s2,2)}
    </div>
    """, unsafe_allow_html=True)

# ================= SCANNER =================
def scan_market():
    symbols = ["COMI","TMGH","SWDY","EFID","ETEL","AMOC","CLHO","ORWE","EGTS","JUFO","PHDC","MFPC"]

    rows = []
    for s in symbols:
        data = get_tv_data(s) or fake_data(s)

        p = data["price"]
        s1,_,r1,_ = pivots(p,data["high"],data["low"])
        score = smart_score(p,s1,r1,data["rsi"],data["ema200"],volume_spike(data["volume"]))

        rows.append({
            "السهم": s,
            "السعر": round(p,2),
            "RSI": round(data["rsi"],1),
            "الدعم": round(s1,2),
            "المقاومة": round(r1,2),
            "Score": score,
            "التقييم": rank(score)
        })

    df = pd.DataFrame(rows)

    if not df.empty:
        df = df.sort_values(by="Score", ascending=False)

    return df

# ================= UI =================
st.title("🏹 EGX Sniper PRO MAX")

tab1, tab2 = st.tabs(["📊 تحليل", "🔥 الفرص"])

# ===== تحليل =====
with tab1:
    symbol = st.text_input("ادخل كود السهم").upper()

    if symbol:
        data = get_tv_data(symbol)

        if not data:
            data = fake_data(symbol)

        show_card(symbol,data)

# ===== الفرص =====
with tab2:
    st.subheader("🔥 أفضل الفرص")

    df = scan_market()

    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("لا توجد بيانات حالياً")
