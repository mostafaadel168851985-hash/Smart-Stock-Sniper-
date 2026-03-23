import streamlit as st
import requests
import pandas as pd

# ================= CONFIG =================
st.set_page_config(page_title="EGX Sniper PRO", layout="wide")

# ================= DARK MODE =================
st.markdown("""
<style>
html, body, [class*="css"] {
    background-color: #0e1117 !important;
    color: white !important;
}
.stApp {background-color:#0e1117;}
h1, h2, h3, h4, h5, h6, p, span, label {
    color:white !important;
}
</style>
""", unsafe_allow_html=True)

st.title("🏹 EGX Sniper PRO")

# ================= STOCKS =================
STOCKS = ["TMGH","COMI","ETEL","SWDY","EFID","ATQA","ALCN","RMDA","ORAS","FWRY"]

# ================= DATA =================
def get_data(symbol):
    try:
        url = "https://scanner.tradingview.com/egypt/scan"

        headers = {"User-Agent": "Mozilla/5.0"}

        payload = {
            "symbols": {"tickers":[f"EGX:{symbol}"],"query":{"types":[]}},
            "columns":["close","high","low","volume"]
        }

        r = requests.post(url, json=payload, headers=headers, timeout=10)

        if r.status_code != 200:
            return None,None,None,None

        data = r.json()

        if "data" not in data or len(data["data"]) == 0:
            return None,None,None,None

        d = data["data"][0]["d"]

        return float(d[0]), float(d[1]), float(d[2]), float(d[3])

    except:
        return None,None,None,None

# ================= CALC =================
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
    if v>2000000:
        return "💧 سيولة عالية"
    elif v>500000:
        return "💧 سيولة متوسطة"
    else:
        return "💧 سيولة ضعيفة"

# ================= CARD =================
def show_card(symbol,p,h,l,v):

    s1,s2,r1,r2 = pivots(p,h,l)
    rsi_val = rsi(p,h,l)
    liq = liquidity(v)

    dist = abs(p-s1)/p*100

    # دعم
    if dist < 1:
        support = "🔥 لاصق دعم"
    elif dist < 2:
        support = "🟢 قريب دعم"
    else:
        support = "⚪ بعيد"

    # تقييم
    trader = 50
    swing = round(60 + (50-abs(50-rsi_val)),2)
    investor = 55

    # توصية
    if dist < 1 and rsi_val < 40:
        recommendation = "🟢 فرصة شراء"
    elif rsi_val > 80:
        recommendation = "🔴 جني أرباح"
    else:
        recommendation = "⏳ انتظار"

    st.markdown(f"""
    <div style="
        background:#161b22;
        padding:20px;
        border-radius:15px;
        margin-bottom:15px;
        box-shadow:0 0 15px rgba(0,0,0,0.6);
    ">

    <h2>{symbol}</h2>

    💰 السعر: {p:.2f}<br>
    📉 RSI: {rsi_val:.1f}<br>

    🧱 الدعم: {s1:.2f} / {s2:.2f}<br>
    🚧 المقاومة: {r1:.2f} / {r2:.2f}<br>

    {liq}<br><br>

    📊 الحالة: {support}<br>

    <hr>

    🎯 المضارب: {trader}/100<br>
    دخول: {round(s1+0.1,2)} | وقف: {round(s1-0.15,2)}<br><br>

    🔁 السوينج: {swing}/100<br>
    دخول: {round((s1+r1)/2,2)}<br><br>

    🏦 المستثمر: {investor}/100<br>
    دخول: {round((s1+s2)/2,2)}<br>

    <hr>

    📌 التوصية: {recommendation}

    </div>
    """, unsafe_allow_html=True)

# ================= SCANNER =================
def scanner():
    rows = []

    for s in STOCKS:
        p,h,l,v = get_data(s)

        if p is None:
            continue

        s1,_,_,_ = pivots(p,h,l)
        dist = abs(p-s1)/p*100

        if dist < 1:
            signal="🔥 لاصق دعم"
        elif dist < 2:
            signal="🟢 قريب دعم"
        else:
            signal="⚪ بعيد"

        rows.append({
            "السهم":s,
            "السعر":round(p,2),
            "الحالة":signal
        })

    return pd.DataFrame(rows)

# ================= UI =================
tab1, tab2 = st.tabs(["📊 تحليل الأسهم","🚨 Scanner"])

# تحليل
with tab1:
    for s in STOCKS:
        p,h,l,v = get_data(s)

        if p:
            show_card(s,p,h,l,v)

# Scanner
with tab2:
    df = scanner()
    if df.empty:
        st.warning("لا توجد بيانات")
    else:
        st.dataframe(df, use_container_width=True)
