import streamlit as st
import pandas as pd
import numpy as np
from tradingview_ta import TA_Handler, Interval

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
box-shadow:0 0 10px rgba(0,0,0,0.6);
}
</style>
""", unsafe_allow_html=True)

# ================= SYMBOLS =================
SYMBOLS = [
"COMI","ETEL","TMGH","SWDY","EFIH","ORAS","AMOC","CLHO",
"ATQA","RMDA","FWRY","ZMID","SVCE","ACAMD","BONY","MEPA","LUTS"
]

# ================= GET DATA =================
def get_data(symbol):
    try:
        handler = TA_Handler(
            symbol=symbol,
            exchange="EGX",
            screener="egypt",
            interval=Interval.INTERVAL_1_DAY
        )

        analysis = handler.get_analysis()

        return {
            "price": float(analysis.indicators.get("close", 0)),
            "high": float(analysis.indicators.get("high", 0)),
            "low": float(analysis.indicators.get("low", 0)),
            "rsi": float(analysis.indicators.get("RSI", 50)),
            "ema": float(analysis.indicators.get("EMA200", 0)),
            "volume": float(analysis.indicators.get("volume", 0))
        }

    except:
        return None

# ================= CALCULATIONS =================
def pivots(p, h, l):
    pivot = (p + h + l) / 3
    s1 = (2 * pivot) - h
    s2 = pivot - (h - l)
    r1 = (2 * pivot) - l
    r2 = pivot + (h - l)
    return round(s1,2), round(s2,2), round(r1,2), round(r2,2)

def liquidity(v):
    if v > 2_000_000:
        return "🔥 سيولة عالية"
    elif v > 500_000:
        return "⚠ سيولة متوسطة"
    else:
        return "❌ سيولة ضعيفة"

# ================= AI SYSTEM =================
def ai_analysis(p, s1, s2, r1, r2, rsi, ema):

    # ===== TRADER =====
    trader_score = 50
    if rsi < 30:
        trader_score += 25
    if abs(p - s1) / s1 < 0.02:
        trader_score += 20
    if ema and p > ema:
        trader_score += 10

    trader_comment = "⚡ فرصة ارتداد من الدعم" if trader_score >= 70 else "⚠ لا يوجد تأكيد قوي"

    trader_entry = round(s1 * 1.01, 2)
    trader_sl = round(s1 * 0.97, 2)

    # ===== SWING =====
    swing_score = int(min(100, 60 + (50 - abs(50 - rsi))))
    swing_comment = "🔁 اتجاه متوسط إيجابي" if p > ema else "🔁 حركة تصحيح"

    swing_entry = round((s1 + r1) / 2, 2)
    swing_sl = round(swing_entry - 0.25, 2)

    # ===== INVEST =====
    invest_score = 80 if p > ema else 55
    invest_comment = "🏦 اتجاه طويل الأجل صاعد" if p > ema else "🏦 اتجاه ضعيف"

    invest_entry = round((s1 + s2) / 2, 2)
    invest_sl = round(s2 - 0.25, 2)

    return {
        "trader": (trader_score, trader_comment, trader_entry, trader_sl),
        "swing": (swing_score, swing_comment, swing_entry, swing_sl),
        "invest": (invest_score, invest_comment, invest_entry, invest_sl)
    }

def rating(score):
    if score >= 80:
        return "🔥 قوية"
    elif score >= 60:
        return "⚠ متوسطة"
    else:
        return "❌ ضعيفة"

# ================= CARD =================
def show_card(symbol, data):

    p = data["price"]
    h = data["high"]
    l = data["low"]
    rsi = data["rsi"]
    ema = data["ema"]
    v = data["volume"]

    s1, s2, r1, r2 = pivots(p, h, l)

    ai = ai_analysis(p, s1, s2, r1, r2, rsi, ema)

    trader = ai["trader"]
    swing = ai["swing"]
    invest = ai["invest"]

    st.markdown(f"""
    <div class="card">

    <h2>{symbol}</h2>

    💰 السعر: {p:.2f} | RSI: {rsi:.1f}<br><br>

    🧱 دعم 1: {s1}<br>
    🧱 دعم 2: {s2}<br><br>

    🚧 مقاومة 1: {r1}<br>
    🚧 مقاومة 2: {r2}<br><br>

    💧 {liquidity(v)}<br>

    <hr>

    🎯 التقييم: {rating(trader[0])} ({trader[0]}/100)<br><br>

    🎯 دخول: {trader[2]}<br>
    ❌ وقف خسارة: {trader[3]}<br>

    <hr>

    🎯 المضارب: {trader[0]}/100<br>
    {trader[1]}<br><br>

    🔁 السوينج: {swing[0]}/100<br>
    {swing[1]}<br><br>

    🏦 المستثمر: {invest[0]}/100<br>
    {invest[1]}<br>

    <hr>

    📌 ملحوظة: أقرب دعم {s1} - دعم أقوى {s2}

    </div>
    """, unsafe_allow_html=True)

# ================= SCANNER =================
def scan_market():
    rows = []

    for sym in SYMBOLS:
        d = get_data(sym)
        if not d:
            continue

        p = d["price"]
        h = d["high"]
        l = d["low"]
        rsi = d["rsi"]
        ema = d["ema"]

        s1, _, r1, _ = pivots(p, h, l)

        score = 50
        if rsi < 30:
            score += 25
        if abs(p - s1) / s1 < 0.02:
            score += 20
        if ema and p > ema:
            score += 10

        rows.append({
            "السهم": sym,
            "السعر": round(p,2),
            "RSI": round(rsi,1),
            "دعم": s1,
            "مقاومة": r1,
            "Score": score,
            "التقييم": rating(score)
        })

    df = pd.DataFrame(rows)

    if not df.empty:
        df = df.sort_values("Score", ascending=False)

    return df

# ================= UI =================
st.title("🏹 EGX Sniper PRO")

tab1, tab2 = st.tabs(["📊 تحليل سهم", "🔥 الفرص"])

# ===== TAB 1 =====
with tab1:
    symbol = st.text_input("ادخل كود السهم").upper().strip()

    if symbol:
        data = get_data(symbol)

        if data:
            show_card(symbol, data)
        else:
            st.error("السهم غير متاح أو البيانات غير متوفرة")

# ===== TAB 2 =====
with tab2:
    st.subheader("🔥 أفضل الفرص")

    df = scan_market()

    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("لا توجد فرص حالياً")
