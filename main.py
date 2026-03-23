import streamlit as st
import requests
import pandas as pd

# ================= CONFIG =================
st.set_page_config(page_title="EGX Sniper PRO", layout="wide")

# ================= DARK STYLE =================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg,#020617,#0f172a);
    color: white;
}
.card {
    background: linear-gradient(145deg,#0f172a,#020617);
    padding: 25px;
    border-radius: 20px;
    box-shadow: 0 0 25px rgba(0,0,0,0.6);
    line-height: 2;
    font-size: 17px;
}
hr {
    border: 1px solid #1e293b;
}
</style>
""", unsafe_allow_html=True)

st.title("🏹 EGX Sniper PRO")

# ================= STOCKS =================
WATCHLIST = ["TMGH","COMI","ETEL","SWDY","EFID","ATQA","ALCN","RMDA"]
ALL_STOCKS = WATCHLIST + ["ORAS","FWRY","AMOC","HELI","EKHO","PHDC"]

# ================= DATA FROM TRADINGVIEW =================
@st.cache_data(ttl=300)
def get_data(symbol):
    try:
        url = "https://scanner.tradingview.com/egypt/scan"
        payload = {
            "symbols": {"tickers": [f"EGX:{symbol}"], "query": {"types": []}},
            "columns": ["close","high","low","volume"]
        }

        r = requests.post(url, json=payload)
        data = r.json()

        if "data" not in data or len(data["data"]) == 0:
            return None

        d = data["data"][0]["d"]

        return float(d[0]), float(d[1]), float(d[2]), float(d[3])

    except:
        return None

# ================= CALCULATIONS =================
def pivots(p,h,l):
    piv=(p+h+l)/3
    s1=(2*piv)-h
    s2=piv-(h-l)
    r1=(2*piv)-l
    r2=piv+(h-l)
    return s1,s2,r1,r2

def rsi(p,h,l):
    if h==l:
        return 50
    return ((p-l)/(h-l))*100

def liquidity(v):
    if v > 2_000_000:
        return "عالية"
    elif v > 500_000:
        return "متوسطة"
    else:
        return "ضعيفة"

# ================= SIGNAL =================
def get_signal(p,s1,r1,rsi_val,v):
    dist_s = abs(p-s1)/p*100
    dist_r = abs(p-r1)/p*100

    if dist_s < 1.5 and rsi_val < 40 and v > 1_000_000:
        return "🟢 BUY"
    elif dist_r < 1.5 and rsi_val > 70:
        return "🔴 SELL"
    else:
        return "⚪ HOLD"

# ================= AI COMMENT =================
def ai_comment(p,s1,r1,rsi_val,signal):

    if signal == "🟢 BUY":
        return "السهم قريب من منطقة دعم قوية مع سيولة جيدة، فرصة مناسبة للمضاربة أو بداية ارتداد محتمل."
    
    elif signal == "🔴 SELL":
        return "السهم بالقرب من مقاومة قوية مع تشبع شرائي، يفضل جني أرباح أو الحذر من التصحيح."

    else:
        if p < (s1 + (r1-s1)/2):
            return "السهم في النصف السفلي من الحركة، يحتاج تأكيد ارتداد قبل الدخول."
        else:
            return "السهم في منتصف الاتجاه، لا توجد فرصة واضحة حالياً، يفضل الانتظار."

# ================= CARD =================
def show_card(code,p,h,l,v):

    s1,s2,r1,r2 = pivots(p,h,l)
    rsi_val = rsi(p,h,l)
    liq = liquidity(v)
    signal = get_signal(p,s1,r1,rsi_val,v)
    comment = ai_comment(p,s1,r1,rsi_val,signal)

    st.markdown(f"""
    <div class="card">

    <h2>{code} -</h2>

    💰 السعر الحالي: {p:.2f}<br>
    📉 RSI: {rsi_val:.1f}<br>

    🧱 الدعم: {s2:.2f} / {s1:.2f}<br>
    🚧 المقاومة: {r2:.2f} / {r1:.2f}<br>

    💧 السيولة: {liq}<br>

    <hr>

    📊 الإشارة: {signal}

    <hr>

    🎯 المضارب: 50/100<br>
    دخول: {round(s1+0.1,2)} | وقف خسارة: {round(s1-0.15,2)}<br><br>

    🔁 السوينج: {round(60 + (50-abs(50-rsi_val)),2)}/100<br>
    دخول: {round((s1+r1)/2,2)} | وقف: {round((s1+r1)/2-0.25,2)}<br><br>

    🏦 المستثمر: 55/100<br>
    دخول: {round((s1+s2)/2,2)} | وقف: {round(s2-0.25,2)}

    <hr>

    🤖 <b>AI Comment:</b><br>
    {comment}

    <hr>

    📌 التوصية: {signal}

    </div>
    """, unsafe_allow_html=True)

# ================= SCANNER =================
def scanner():

    rows = []

    for s in ALL_STOCKS:
        data = get_data(s)

        if not data:
            continue

        p,h,l,v = data

        s1,s2,r1,r2 = pivots(p,h,l)
        rsi_val = rsi(p,h,l)
        liq = liquidity(v)
        signal = get_signal(p,s1,r1,rsi_val,v)

        dist = abs(p-s1)/p*100

        if dist < 1:
            status = "🔥 لاصق دعم"
        elif dist < 2:
            status = "🟢 قريب دعم"
        else:
            status = "⚪ بعيد"

        rows.append({
            "السهم":s,
            "السعر":round(p,2),
            "RSI":round(rsi_val,1),
            "الدعم":round(s1,2),
            "المقاومة":round(r1,2),
            "السيولة":liq,
            "الحالة":status,
            "الإشارة":signal
        })

    return pd.DataFrame(rows)

# ================= UI =================
tab1,tab2 = st.tabs(["📊 تحليل سهم","🚨 Scanner"])

# تحليل
with tab1:
    code = st.text_input("ادخل كود السهم").upper()

    if code:
        data = get_data(code)

        if data:
            p,h,l,v = data
            show_card(code,p,h,l,v)
        else:
            st.warning("السهم غير متاح")

# Scanner
with tab2:
    df = scanner()

    if df.empty:
        st.warning("لا توجد بيانات")
    else:
        st.dataframe(df, use_container_width=True)
