import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="EGX Sniper PRO", layout="wide")

# ================= STYLE =================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg,#020617,#020617,#0f172a);
    color:white;
}

input {
    background:#0f172a !important;
    color:white !important;
    border-radius:10px !important;
    border:1px solid #334155 !important;
}

button[data-baseweb="tab"] {
    background:#0f172a;
    border-radius:10px;
    color:white;
}
button[aria-selected="true"] {
    background:#1e293b !important;
    border-bottom:3px solid red;
}
</style>
""", unsafe_allow_html=True)

st.title("🏹 EGX Sniper PRO")

ALL_STOCKS = ["TMGH","COMI","ETEL","SWDY","EFID","ATQA","ALCN","RMDA","ORAS","FWRY"]

# ================= DATA =================
@st.cache_data(ttl=300)
def get_data(symbol):
    try:
        url = "https://scanner.tradingview.com/egypt/scan"
        payload = {
            "symbols":{"tickers":[f"EGX:{symbol}"],"query":{"types":[]}},
            "columns":["close","high","low","volume","RSI"]
        }
        r = requests.post(url,json=payload)
        d = r.json()["data"][0]["d"]
        return float(d[0]),float(d[1]),float(d[2]),float(d[3]),float(d[4])
    except:
        return None

# ================= CALC =================
def pivots(p,h,l):
    piv=(p+h+l)/3
    s1=(2*piv)-h
    s2=piv-(h-l)
    r1=(2*piv)-l
    r2=piv+(h-l)
    return s1,s2,r1,r2

def smart_score(p,s1,rsi,volume):
    score = 0
    if abs(p-s1)/p < 0.02: score += 40
    if rsi < 40: score += 30
    if volume > 2_000_000: score += 30
    return min(score,100)

# ================= الكارت القديم =================
def show_old_card(code,p,h,l,v,rsi):

    s1,s2,r1,r2 = pivots(p,h,l)

    st.markdown(f"""
    <div style="
        background:#020617;
        padding:20px;
        border-radius:15px;
        line-height:1.9;
        font-size:16px;
    ">

    <h2>{code} -</h2>

    💰 السعر الحالي: {p:.2f}<br>
    📉 RSI: {rsi:.1f}<br>

    🧱 الدعم: {s1:.2f} / {s2:.2f}<br>
    🚧 المقاومة: {r1:.2f} / {r2:.2f}<br>
    💧 السيولة: {"عالية" if v>2_000_000 else "متوسطة" if v>1_000_000 else "ضعيفة"}<br>

    <hr>

    🔄 لا توجد إشارة ارتداد<br>
    ⚡ لا يوجد تأكيد<br>

    <hr>

    🎯 المضارب: 50/100<br>
    دخول: {round(s1+0.1,2)} | وقف خسارة: {round(s1-0.15,2)}<br><br>

    🔁 السوينج: 65/100<br>
    دخول: {round((s1+r1)/2,2)} | وقف خسارة: {round((s1+r1)/2-0.25,2)}<br><br>

    🏦 المستثمر: 55/100<br>
    دخول: {round((s1+s2)/2,2)} | وقف خسارة: {round(s2-0.25,2)}<br>

    <hr>

    📌 التوصية: انتظار<br>

    📝 ملحوظة:<br>
    أقرب دعم {s1:.2f} - دعم أقوى {s2:.2f}

    </div>
    """, unsafe_allow_html=True)

    # الشارت (مفيش تغيير)
    st.components.v1.html(f"""
    <iframe src="https://www.tradingview.com/widgetembed/?symbol=EGX:{code}&interval=D&theme=dark"
    width="100%" height="350"></iframe>
    """, height=350)

# ================= UI =================
tab1,tab2 = st.tabs(["📊 تحليل سهم","🔥 فرص"])

# ================= تحليل =================
with tab1:
    code = st.text_input("ادخل كود السهم")

    if code:
        d = get_data(code.upper())
        if d:
            show_old_card(code.upper(),*d)

# ================= فرص =================
with tab2:

    rows=[]
    for s in ALL_STOCKS:
        d = get_data(s)
        if not d: continue

        p,h,l,v,rsi = d
        s1,_,_,_ = pivots(p,h,l)

        score = smart_score(p,s1,rsi,v)

        if score >= 60:
            rows.append({
                "السهم":s,
                "السعر":round(p,2),
                "RSI":round(rsi,1),
                "Score":score
            })

    if rows:
        st.dataframe(pd.DataFrame(rows),use_container_width=True)
    else:
        st.warning("لا توجد فرص حالياً")
