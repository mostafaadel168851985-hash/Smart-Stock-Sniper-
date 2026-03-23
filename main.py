import streamlit as st
import pandas as pd
from tradingview_ta import TA_Handler, Interval

st.set_page_config(layout="wide")

# ================= STYLE =================
st.markdown("""
<style>
body {
    direction: rtl;
}
.card {
    background: #0b1320;
    padding: 15px;
    border-radius: 15px;
    color: white;
    line-height: 1.6;
    margin-top: 10px;
}
.small-gap { margin-bottom: 6px; }
hr { margin: 10px 0px; }
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
            "price": analysis.indicators.get("close", 0),
            "high": analysis.indicators.get("high", 0),
            "low": analysis.indicators.get("low", 0),
            "volume": analysis.indicators.get("volume", 0),
            "rsi": analysis.indicators.get("RSI", 50)
        }
    except:
        return None

# ================= SCORING =================
def calculate_scores(d):

    price = d["price"]
    high = d["high"]
    low = d["low"]
    rsi = d["rsi"]

    # مضارب
    scalper = 50
    if rsi < 40: scalper += 25
    if rsi > 70: scalper -= 20
    if price <= low*1.02: scalper += 15

    # سوينج
    swing = 50
    if 40 < rsi < 60: swing += 20
    if price > (low + high)/2: swing += 15

    # مستثمر
    invest = 50
    if price > low: invest += 10
    if rsi < 60: invest += 10

    return scalper, swing, invest

# ================= SIGNAL =================
def get_trade_plan(d):

    price = d["price"]
    low = d["low"]
    high = d["high"]

    entry = round(low * 1.02,2)
    stop = round(low * 0.97,2)
    target = round(high * 0.98,2)

    rr = round((target-entry)/(entry-stop),2) if entry>stop else 0

    return entry, stop, target, rr

# ================= HEADER =================
st.title("🏹 EGX Sniper PRO")

tabs = st.tabs(["📊 تحليل سهم","🔥 فرص"])

# ================= TAB 1 =================
with tabs[0]:

    symbol = st.text_input("ادخل كود السهم", "MAAL")

    if symbol:

        d = get_data(symbol)

        if d is None:
            st.error("السهم غير متاح")
        else:
            entry, stop, target, rr = get_trade_plan(d)
            scalper, swing, invest = calculate_scores(d)

            st.markdown(f"""
            <div class="card">

            <h2>{symbol} -</h2>

            💰 السعر الحالي: {round(d['price'],2)}<br>
            📉 RSI: {round(d['rsi'],1)}<br>

            🧱 الدعم: {round(d['low'],2)} / {round(d['low']*1.1,2)}<br>
            🚧 المقاومة: {round(d['high']*0.9,2)} / {round(d['high'],2)}<br>
            💧 السيولة: {"عالية" if d['volume']>1000000 else "ضعيفة"}

            <hr>

            🔄 لا توجد إشارة ارتداد<br>
            ⚡ لا يوجد تأكيد

            <hr>

            🎯 المضارب: {scalper}/100<br>
            دخول: {entry} | وقف: {stop}

            <br>

            🔁 السوینج: {swing}/100<br>
            دخول: {round(entry*1.04,2)} | وقف: {round(stop*1.04,2)}

            <br>

            🏦 المستثمر: {invest}/100<br>
            دخول: {round(entry*0.9,2)} | وقف: {round(stop*0.9,2)}

            <hr>

            📌 التوصية: {"شراء" if scalper>65 else "انتظار"}

            </div>
            """, unsafe_allow_html=True)

# ================= TAB 2 =================
with tabs[1]:

    st.subheader("🔥 أفضل الفرص")

    symbols = ["ATQA","FWRY","SWDY","EFIH","ORAS"]

    rows = []

    for s in symbols:
        d = get_data(s)

        if d is None:
            continue

        scalper, swing, invest = calculate_scores(d)

        total_score = int((scalper + swing + invest)/3)

        # فلترة الفرص الحقيقية
        if total_score < 55:
            continue

        rows.append({
            "🔥": "🔥" if total_score>70 else "⭐",
            "السهم": s,
            "السعر": round(d['price'],2),
            "RSI": round(d['rsi'],1),
            "Score": total_score
        })

    if len(rows)==0:
        st.warning("لا توجد فرص حالياً")
    else:
        df = pd.DataFrame(rows).sort_values("Score", ascending=False)
        st.dataframe(df, use_container_width=True)
