import streamlit as st
import pandas as pd
import numpy as np
import requests
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

    # ===== TRY tradingview-ta =====
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
        pass

    # ===== FALLBACK TradingView Scanner =====
    try:
        url = "https://scanner.tradingview.com/egypt/scan"

        payload = {
            "symbols": {"tickers": [f"EGX:{symbol}"], "query": {"types": []}},
            "columns": ["close","high","low","volume","RSI","EMA200"]
        }

        r = requests.post(url, json=payload).json()
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

# ================= AI =================
def ai_analysis(p, s1, s2, r1, r2, rsi, ema):

    trader_score = 50
    if rsi < 30:
        trader_score += 25
    if abs(p - s1) / s1 < 0.02:
        trader_score += 20
    if ema and p > ema:
        trader_score += 10

    trader_comment = "🔥 ارتداد من دعم قوي" if trader_score >= 75 else "⚠ فرصة ضعيفة"

    trader_entry = round(s1 * 1.01, 2)
    trader_sl = round(s1 * 0.97, 2)

    swing_score = int(min(100, 60 + (50 - abs(50 - rsi))))
    swing_comment = "🔁 اتجاه صاعد" if p > ema else "🔁 تصحيح"

    invest_score = 80 if p > ema else 50
    invest_comment = "🏦 استثمار إيجابي" if p > ema else "🏦 ضعيف"

    return trader_score, trader_comment, trader_entry, trader_sl, swing_score, swing_comment, invest_score, invest_comment

def rating(score):
    if score >= 80:
        return "🔥 قوية"
    elif score >= 60:
        return "⚠ متوسطة"
    else:
        return "❌ ضعيفة"

# ================= CARD =================
def show_card(symbol, d):

    p = d["price"]
    h = d["high"]
    l = d["low"]
    rsi = d["rsi"]
    ema = d["ema"]
    v = d["volume"]

    s1, s2, r1, r2 = pivots(p, h, l)

    trader_score, trader_comment, entry, sl, swing_score, swing_comment, invest_score, invest_comment = ai_analysis(p,s1,s2,r1,r2,rsi,ema)

    st.markdown(f"""
    <div class="card">

    <h2>{symbol}</h2>

    💰 السعر: {p:.2f} | RSI: {rsi:.1f}<br><br>

    🧱 دعم: {s1} / {s2}<br>
    🚧 مقاومة: {r1} / {r2}<br><br>

    💧 {liquidity(v)}<br>

    <hr>

    🎯 التقييم: {rating(trader_score)} ({trader_score}/100)<br>
    💡 {trader_comment}<br><br>

    🎯 دخول: {entry}<br>
    ❌ وقف خسارة: {sl}<br>

    <hr>

    🎯 المضارب: {trader_score}/100<br>
    🔁 السوينج: {swing_score}/100<br>
    🏦 المستثمر: {invest_score}/100<br>

    <hr>

    📌 أقرب دعم {s1} - دعم أقوى {s2}

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

        s1, _, r1, _ = pivots(p,h,l)

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

with tab1:
    symbol = st.text_input("ادخل كود السهم").upper().strip()

    if symbol:
        d = get_data(symbol)

        if d:
            show_card(symbol, d)
        else:
            st.error("السهم غير متاح أو البيانات غير متوفرة")

with tab2:
    st.subheader("🔥 أفضل الفرص")

    df = scan_market()

    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("لا توجد فرص حالياً")
