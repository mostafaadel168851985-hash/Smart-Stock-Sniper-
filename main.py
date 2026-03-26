import streamlit as st
import pandas as pd
import numpy as np
from tradingview_ta import TA_Handler, Interval, Exchange

st.set_page_config(layout="wide")

# ================= STYLE =================
st.markdown("""
<style>
.stApp {background-color:#0d1117;color:white;}
h1,h2,h3,p,span,label {color:white !important;}

.card {
background:#161b22;
padding:20px;
border-radius:20px;
margin-bottom:20px;
box-shadow:0 0 15px rgba(0,0,0,0.6);
}
</style>
""", unsafe_allow_html=True)

# ================= SYMBOLS =================
SYMBOLS = [
"COMI","ETEL","TMGH","SWDY","EFIH","ORAS","AMOC","CLHO",
"ATQA","RMDA","FWRY","ZMID","SVCE","ACAMD","BONY","MEPA","LUTS"
]

# ================= DATA =================
def get_tv_data(symbol):
    try:
        handler = TA_Handler(
            symbol=symbol,
            exchange="EGX",
            screener="egypt",
            interval=Interval.INTERVAL_1_DAY
        )

        analysis = handler.get_analysis()

        return {
            "price": analysis.indicators.get("close",0),
            "rsi": analysis.indicators.get("RSI",50),
            "ema": analysis.indicators.get("EMA200",0),
            "high": analysis.indicators.get("high",0),
            "low": analysis.indicators.get("low",0),
            "volume": analysis.indicators.get("volume",0)
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
    elif v > 500_000: return "⚠ متوسطة"
    return "❌ ضعيفة"

# ================= AI SYSTEM =================
def ai_system(p,s1,s2,r1,r2,rsi,ema):

    # ================= TRADER =================
    trader_score = 50
    if rsi < 30: trader_score += 25
    if abs(p-s1)/s1 < 0.02: trader_score += 20
    if ema and p > ema: trader_score += 10

    trader_comment = "⚡ فرصة مضاربية جيدة قرب الدعم" if trader_score > 70 else "⚠ مخاطرة عالية"

    trader_entry = round(s1*1.01,2)
    trader_sl = round(s1*0.97,2)

    # ================= SWING =================
    swing_score = min(100, 60 + (50 - abs(50 - rsi)))

    if p > ema:
        swing_comment = "🔁 اتجاه متوسط إيجابي"
    else:
        swing_comment = "🔁 السهم في تصحيح"

    swing_entry = round((s1+r1)/2,2)
    swing_sl = round(swing_entry - 0.25,2)

    # ================= INVEST =================
    invest_score = 80 if p > ema else 55

    invest_comment = "🏦 اتجاه طويل الأجل صاعد" if p > ema else "🏦 اتجاه ضعيف"

    invest_entry = round((s1+s2)/2,2)
    invest_sl = round(s2 - 0.25,2)

    return {
        "trader": (trader_score, trader_comment, trader_entry, trader_sl),
        "swing": (swing_score, swing_comment, swing_entry, swing_sl),
        "invest": (invest_score, invest_comment, invest_entry, invest_sl)
    }

def rating(score):
    if score >= 80: return "🔥 قوية"
    elif score >= 60: return "⚠ متوسطة"
    return "❌ ضعيفة"

# ================= CARD =================
def show_card(sym,data):
    p,h,l,v,rsi,ema = data.values()

    s1,s2,r1,r2 = pivots(p,h,l)

    ai = ai_system(p,s1,s2,r1,r2,rsi,ema)

    trader, swing, invest = ai["trader"], ai["swing"], ai["invest"]

    st.markdown(f"""
    <div class="card">

    <h2>{sym}</h2>

    💰 السعر: {p:.2f} | RSI: {rsi:.1f}<br><br>

    🧱 دعم 1: {s1:.2f}<br>
    🧱 دعم 2: {s2:.2f}<br><br>

    🚧 مقاومة 1: {r1:.2f}<br>
    🚧 مقاومة 2: {r2:.2f}<br><br>

    💧 السيولة: {liquidity(v)}<br>

    <hr>

    🎯 التقييم: {rating(trader[0])} ({trader[0]}/100)<br><br>

    🎯 منطقة دخول: {trader[2]}<br>
    ❌ وقف خسارة: {trader[3]}<br>

    <hr>

    🎯 المضارب: {trader[0]}/100<br>
    {trader[1]}<br><br>

    🔁 السوينج: {int(swing[0])}/100<br>
    {swing[1]}<br><br>

    🏦 المستثمر: {invest[0]}/100<br>
    {invest[1]}<br>

    <hr>

    📌 ملحوظة: أقرب دعم {s1:.2f} - دعم أقوى {s2:.2f}

    </div>
    """, unsafe_allow_html=True)

# ================= SCANNER =================
def scan():
    rows = []

    for s in SYMBOLS:
        d = get_tv_data(s)
        if not d: continue

        p,h,l,rsi,ema = d.values()
        s1,_,r1,_ = pivots(p,h,l)

        score = 50
        if rsi < 30: score += 25
        if abs(p-s1)/s1 < 0.02: score += 20
        if ema and p > ema: score += 10

        rows.append({
            "السهم": s,
            "السعر": round(p,2),
            "RSI": round(rsi,1),
            "دعم": round(s1,2),
            "مقاومة": round(r1,2),
            "التقييم": rating(score),
            "Score": score
        })

    return pd.DataFrame(rows).sort_values("Score",ascending=False)

# ================= UI =================
st.title("🏹 EGX Sniper PRO")

tab1,tab2 = st.tabs(["📊 تحليل سهم","🔥 الفرص"])

with tab1:
    sym = st.text_input("ادخل كود السهم").upper()
    if sym:
        d = get_tv_data(sym)
        if d:
            show_card(sym,d)
        else:
            st.error("السهم غير متاح")

with tab2:
    df = scan()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("لا توجد فرص حالياً")
