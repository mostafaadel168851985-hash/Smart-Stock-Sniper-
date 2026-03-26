import streamlit as st
import requests
import pandas as pd
import numpy as np

st.set_page_config(page_title="EGX Sniper PRO", layout="wide")

# ================== STYLE ==================
st.markdown("""
<style>
body, .stApp {background:#0d1117;color:white;}
.card {
    background:#161b22;
    padding:18px;
    border-radius:18px;
    margin-top:15px;
    line-height:1.8;
}
hr {border:0.5px solid #2c313a;}
</style>
""", unsafe_allow_html=True)

# ================== DATA ==================
@st.cache_data(ttl=300)
def get_data(symbol):
    try:
        url = "https://scanner.tradingview.com/egypt/scan"
        payload = {
            "symbols":{"tickers":[f"EGX:{symbol}"],"query":{"types":[]}},
            "columns":["close","high","low","volume"]
        }

        r = requests.post(url, json=payload).json()
        d = r["data"][0]["d"]

        p,h,l,v = float(d[0]),float(d[1]),float(d[2]),float(d[3])

        # RSI + Indicators من TradingView
        try:
            from tradingview_ta import TA_Handler, Interval

            handler = TA_Handler(
                symbol=symbol,
                screener="egypt",
                exchange="EGX",
                interval=Interval.INTERVAL_1_DAY
            )

            analysis = handler.get_analysis()

            rsi = analysis.indicators.get("RSI",50)
            ema20 = analysis.indicators.get("EMA20",p)
            ema50 = analysis.indicators.get("EMA50",p)

        except:
            rsi, ema20, ema50 = 50, p, p

        return p,h,l,v,rsi,ema20,ema50

    except:
        return None,None,None,None,50,0,0

# ================== INDICATORS ==================
def pivots(p,h,l):
    piv=(p+h+l)/3
    s1=(2*piv)-h
    s2=piv-(h-l)
    r1=(2*piv)-l
    r2=piv+(h-l)
    return s1,s2,r1,r2

# ================== SIGNAL ENGINE ==================
def analyze(p,s1,s2,r1,r2,rsi,volume,ema20,ema50):

    near_support = abs(p - s1)/s1 < 0.03
    breakout = p > r1
    strong_volume = volume > 1_000_000
    uptrend = p > ema20 > ema50

    # ===== SCORE =====
    score = 50
    if rsi < 30: score += 20
    if near_support: score += 15
    if strong_volume: score += 10
    if breakout: score += 10
    if uptrend: score += 10

    score = min(100, score)

    # ===== RANK =====
    if score >= 75:
        rank = "🔥 قوية"
    elif score >= 60:
        rank = "⚠ متوسطة"
    else:
        rank = "❌ ضعيفة"

    # ===== ENTRY =====
    if breakout:
        entry = r1
        sl = r1 - 0.2
        comment = "📈 اختراق مقاومة → فرصة قوية لاستكمال الصعود"
    elif near_support:
        entry = s1 + 0.05
        sl = s1 - 0.1
        comment = "🟢 ارتداد من الدعم → فرصة مضاربة جيدة"
    else:
        entry = (s1 + r1)/2
        sl = entry - 0.3
        comment = "⚠ لا توجد فرصة واضحة حالياً"

    return score, rank, entry, sl, comment

# ================== CARD ==================
def show_card(code,p,h,l,v,rsi,ema20,ema50):

    s1,s2,r1,r2 = pivots(p,h,l)
    score, rank, entry, sl, comment = analyze(p,s1,s2,r1,r2,rsi,v,ema20,ema50)

    st.markdown(f"""
    <div class="card">

    <h3>{code}</h3>

    💰 السعر: {p:.2f}<br>
    📉 RSI: {rsi:.1f}<br>

    🧱 الدعم: {s1:.2f} / {s2:.2f}<br>
    🚧 المقاومة: {r1:.2f} / {r2:.2f}<br>

    <hr>

    🎯 التقييم: {rank} ({score}/100)<br>
    💡 {comment}<br>

    <hr>

    🎯 دخول: {entry:.2f}<br>
    ❌ وقف خسارة: {sl:.2f}<br>

    <hr>

    📝 ملحوظة للمحبوس: أقرب دعم {s1:.2f} - الدعم الأقوى {s2:.2f}

    </div>
    """, unsafe_allow_html=True)

# ================== MARKET SCAN ==================
def scan_market():

    url = "https://scanner.tradingview.com/egypt/scan"

    payload = {
        "symbols":{"query":{"types":[]},"tickers":[]},
        "columns":["name","close","high","low","volume"]
    }

    r = requests.post(url, json=payload).json()

    rows = []

    for stock in r["data"]:

        name = stock["d"][0]
        p = stock["d"][1]
        h = stock["d"][2]
        l = stock["d"][3]
        v = stock["d"][4]

        s1,s2,r1,r2 = pivots(p,h,l)

        rsi = ((p-l)/(h-l))*100 if h!=l else 50

        score, rank, entry, sl, _ = analyze(p,s1,s2,r1,r2,rsi,v,p,p)

        rows.append({
            "السهم": name,
            "السعر": round(p,2),
            "RSI": round(rsi,1),
            "دعم": round(s1,2),
            "مقاومة": round(r1,2),
            "التقييم": rank,
            "دخول": round(entry,2),
            "وقف": round(sl,2),
            "Score": score
        })

    df = pd.DataFrame(rows)
    df = df.sort_values(by="Score", ascending=False)

    return df.head(20)

# ================== UI ==================
st.title("🏹 EGX Sniper PRO")

tab1, tab2 = st.tabs(["📊 تحليل سهم","🔥 أفضل الفرص"])

# ===== تحليل =====
with tab1:
    code = st.text_input("ادخل كود السهم").upper()

    if code:
        p,h,l,v,rsi,ema20,ema50 = get_data(code)

        if p:
            show_card(code,p,h,l,v,rsi,ema20,ema50)
        else:
            st.error("السهم غير متاح")

# ===== فرص =====
with tab2:
    st.subheader("🔥 Top Opportunities")

    df = scan_market()

    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("لا توجد فرص حالياً")
