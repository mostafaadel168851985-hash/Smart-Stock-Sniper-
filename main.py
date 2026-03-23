import streamlit as st
import requests
import pandas as pd
import numpy as np

# ================== CONFIG ==================
st.set_page_config(page_title="EGX Sniper PRO", layout="wide")

WATCHLIST = ["TMGH", "COMI", "ETEL", "SWDY", "EFIH", "ATQA", "ORAS"]

# ================== STYLE (دارك مود ثابت) ==================
st.markdown("""
<style>
body, .stApp {
    background-color: #0d1117;
    color: #ffffff;
}
h1,h2,h3,h4,p,label,span {
    color: #ffffff !important;
}
.card {
    background: #161b22;
    padding: 16px;
    border-radius: 16px;
    margin-bottom: 15px;
    line-height: 1.6;
}
hr {
    border: 0.5px solid #2c313a;
    margin: 10px 0;
}
</style>
""", unsafe_allow_html=True)

# ================== DATA ==================
@st.cache_data(ttl=300)
def get_data(symbol):
    try:
        url = "https://scanner.tradingview.com/egypt/scan"
        payload = {
            "symbols": {"tickers": [f"EGX:{symbol}"], "query": {"types": []}},
            "columns": ["close", "high", "low", "volume"]
        }

        r = requests.post(url, json=payload).json()
        d = r["data"][0]["d"]

        p, h, l, v = float(d[0]), float(d[1]), float(d[2]), float(d[3])

        try:
            from tradingview_ta import TA_Handler, Interval

            handler = TA_Handler(
                symbol=symbol,
                screener="egypt",
                exchange="EGX",
                interval=Interval.INTERVAL_1_DAY
            )

            analysis = handler.get_analysis()
            rsi = analysis.indicators.get("RSI", 50)

        except:
            rsi = 50

        hist = pd.Series([p]*100)

        return p, h, l, v, hist, rsi

    except:
        return None, None, None, None, pd.Series([]), 50

# ================== INDICATORS ==================
def pivots(p, h, l):
    piv = (p + h + l) / 3
    s1 = (2 * piv) - h
    s2 = piv - (h - l)
    r1 = (2 * piv) - l
    r2 = piv + (h - l)
    return s1, s2, r1, r2

def liquidity(v):
    if v > 2_000_000:
        return "سيولة عالية"
    elif v > 500_000:
        return "سيولة متوسطة"
    return "سيولة ضعيفة"

# ================== AI ==================
def ai_calc(p, s1, s2, r1, r2, rsi):
    trader_score = min(100, 50 + (20 if rsi < 35 else 0))
    swing_score = min(100, 60 + (50 - abs(50 - rsi)))
    invest_score = 70 if p > s1 else 50

    trader_entry = round(s1 + 0.05, 2)
    trader_sl = round(s1 - 0.1, 2)

    swing_entry = round((s1 + r1)/2, 2)
    swing_sl = round(swing_entry - 0.2, 2)

    invest_entry = round((s1 + s2)/2, 2)
    invest_sl = round(s2 - 0.2, 2)

    return {
        "trader": (trader_score, trader_entry, trader_sl),
        "swing": (swing_score, swing_entry, swing_sl),
        "invest": (invest_score, invest_entry, invest_sl)
    }

# ================== CARD ==================
def show_card(code, p, h, l, v, rsi):
    s1, s2, r1, r2 = pivots(p,h,l)
    liq = liquidity(v)
    ai = ai_calc(p, s1, s2, r1, r2, rsi)

    st.markdown(f"""
    <div class="card">
    <h3>{code}</h3>

    💰 السعر: {p:.2f} | RSI: {rsi:.1f}<br><br>

    🧱 دعم 1: {s1:.2f}<br>
    🧱 دعم 2: {s2:.2f}<br>

    🚧 مقاومة 1: {r1:.2f}<br>
    🚧 مقاومة 2: {r2:.2f}<br>

    💧 {liq}
    <hr>

    🎯 المضارب: {ai['trader'][0]}/100<br>
    دخول: {ai['trader'][1]} | وقف خسارة: {ai['trader'][2]}<br><br>

    🔁 السوينج: {ai['swing'][0]}/100<br>
    دخول: {ai['swing'][1]} | وقف خسارة: {ai['swing'][2]}<br><br>

    🏦 المستثمر: {ai['invest'][0]}/100<br>
    دخول: {ai['invest'][1]} | وقف خسارة: {ai['invest'][2]}<br>

    </div>
    """, unsafe_allow_html=True)

# ================== OPPORTUNITIES ==================
def get_opportunities():
    results = []

    for s in WATCHLIST:
        p,h,l,v,_,rsi = get_data(s)
        if not p:
            continue

        s1, s2, r1, r2 = pivots(p,h,l)

        if rsi < 35 or p < s1:
            results.append({
                "السهم": s,
                "السعر": round(p,2),
                "RSI": round(rsi,1),
                "دخول": round(s1+0.05,2),
                "وقف خسارة": round(s1-0.1,2),
                "Score": int(70 + (35-rsi))
            })

    return pd.DataFrame(results)

# ================== UI ==================
st.title("🏹 EGX Sniper PRO")

tab1, tab2 = st.tabs(["📊 تحليل سهم", "🔥 فرص"])

# ===== تحليل =====
with tab1:
    code = st.text_input("ادخل كود السهم").upper()

    if code:
        p,h,l,v,_,rsi = get_data(code)

        if p:
            show_card(code,p,h,l,v,rsi)
        else:
            st.error("السهم غير متاح")

# ===== فرص =====
with tab2:
    st.subheader("🔥 أفضل الفرص")

    df = get_opportunities()

    if not df.empty:
        st.dataframe(df)
    else:
        st.warning("لا توجد فرص حالياً")
