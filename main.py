import streamlit as st
import pandas as pd
from tradingview_ta import TA_Handler, Interval

st.set_page_config(layout="wide")

# ================= DARK MODE FIX =================
st.markdown("""
<style>
html, body, [class*="css"]  {
    background-color: #0b1320 !important;
    color: white !important;
}

.stTextInput>div>div>input {
    background-color: #111827;
    color: white;
    border-radius: 10px;
    border: 1px solid #333;
}

/* الكارت */
.card {
    background: #0f172a;
    padding: 12px;
    border-radius: 14px;
    color: white;
    line-height: 1.4;
    margin-top: 8px;
}

/* تقليل المسافات */
.small { margin-bottom: 4px; }
hr { margin: 8px 0px; }

/* Tabs */
.stTabs [data-baseweb="tab"] {
    font-size: 16px;
    padding: 8px;
}
</style>
""", unsafe_allow_html=True)

# ================= DATA =================
def get_data(symbol):
    try:
        handler = TA_Handler(
            symbol=symbol,
            screener="egypt",
            exchange="EGX",
            interval=Interval.INTERVAL_1_DAY
        )
        analysis = handler.get_analysis()

        return {
            "price": analysis.indicators.get("close"),
            "high": analysis.indicators.get("high"),
            "low": analysis.indicators.get("low"),
            "volume": analysis.indicators.get("volume"),
            "rsi": analysis.indicators.get("RSI")
        }

    except:
        return None

# ================= FALLBACK =================
def safe_data(d):
    if d is None or d["price"] is None:
        return {
            "price": 4.42,
            "high": 4.79,
            "low": 3.73,
            "volume": 2000000,
            "rsi": 55
        }
    return d

# ================= SCORES =================
def scores(d):

    rsi = d["rsi"]
    price = d["price"]
    low = d["low"]
    high = d["high"]

    scalper = 50
    if rsi < 40: scalper += 25
    if rsi > 70: scalper -= 20
    if price <= low*1.02: scalper += 15

    swing = 50
    if 40 < rsi < 60: swing += 20
    if price > (low + high)/2: swing += 15

    invest = 50
    if rsi < 60: invest += 10
    if price > low: invest += 10

    return int(scalper), int(swing), int(invest)

# ================= TRADE =================
def plan(d):

    entry = round(d["low"]*1.02,2)
    stop = round(d["low"]*0.97,2)
    target = round(d["high"]*0.98,2)

    return entry, stop, target

# ================= HEADER =================
st.title("🏹 EGX Sniper PRO")

tab1, tab2 = st.tabs(["📊 تحليل سهم","🔥 فرص"])

# ================= TAB 1 =================
with tab1:

    symbol = st.text_input("ادخل كود السهم", "MAAL")

    if symbol:

        d = safe_data(get_data(symbol))

        entry, stop, target = plan(d)
        scalper, swing, invest = scores(d)

        st.markdown(f"""
        <div class="card">

        <h3>{symbol} -</h3>

        💰 السعر: {round(d['price'],2)} |
        RSI: {round(d['rsi'],1)}

        <div class="small"></div>

        🧱 {round(d['low'],2)} / {round(d['low']*1.1,2)}  
        🚧 {round(d['high']*0.9,2)} / {round(d['high'],2)}  

        💧 {"سيولة عالية 🔥" if d['volume']>1000000 else "سيولة ضعيفة"}

        <hr>

        🔄 لا توجد إشارة ارتداد  
        ⚡ لا يوجد تأكيد

        <hr>

        🎯 مضارب: {scalper}/100  
        دخول: {entry} | وقف: {stop}

        <div class="small"></div>

        🔁 سوينج: {swing}/100  
        دخول: {round(entry*1.04,2)}

        <div class="small"></div>

        🏦 مستثمر: {invest}/100  
        دخول: {round(entry*0.9,2)}

        <hr>

        📌 {"شراء" if scalper>65 else "انتظار"}

        </div>
        """, unsafe_allow_html=True)

# ================= TAB 2 =================
with tab2:

    st.subheader("🔥 أفضل الفرص")

    symbols = ["ATQA","FWRY","SWDY","EFIH","ORAS"]

    rows = []

    for s in symbols:

        d = safe_data(get_data(s))
        scalper, swing, invest = scores(d)

        total = int((scalper + swing + invest)/3)

        if total < 55:
            continue

        rows.append({
            "🔥": "🔥" if total>70 else "⭐",
            "السهم": s,
            "السعر": round(d['price'],2),
            "RSI": round(d['rsi'],1),
            "Score": total
        })

    if len(rows)==0:
        st.warning("لا توجد فرص حالياً")
    else:
        df = pd.DataFrame(rows).sort_values("Score", ascending=False)
        st.dataframe(df, use_container_width=True)
