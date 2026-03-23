import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="EGX Sniper PRO MAX", layout="wide")

# ================= STYLE =================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg,#020617,#020617,#0f172a);
    color:white;
}

/* CARD */
.card {
    background:#020617;
    padding:14px;
    border-radius:14px;
    line-height:1.5;
    font-size:14px;
    box-shadow:0 0 15px rgba(0,0,0,0.6);
}

/* INPUT */
input {
    background:#0f172a !important;
    color:white !important;
    border-radius:10px !important;
    border:1px solid #334155 !important;
}

/* TABS */
button[data-baseweb="tab"] {
    background:#0f172a;
    border-radius:10px;
    margin-right:6px;
    color:white;
}
button[aria-selected="true"] {
    background:#1e293b !important;
    border-bottom:3px solid red;
}

hr {
    border:1px solid #1e293b;
    margin:8px 0;
}
</style>
""", unsafe_allow_html=True)

st.title("🏹 EGX Sniper PRO MAX")

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

def liquidity(v):
    if v>3_000_000:
        return "سيولة عالية 🔥"
    elif v>1_000_000:
        return "سيولة متوسطة"
    return "سيولة ضعيفة"

# ================= SIGNAL =================
def signal(p,s1,r1,rsi):

    dist_s = abs(p-s1)/p*100
    dist_r = abs(p-r1)/p*100

    # تحسين الفرص (مش قليلة قوي)
    if dist_s < 2 and rsi < 55:
        return "🟢 BUY"

    if dist_r < 1.5 and rsi > 70:
        return "🔴 SELL"

    return "⚪ HOLD"

# ================= AI =================
def ai_comment(sig,rsi):
    if "BUY" in sig:
        return "السهم قريب من الدعم مع فرصة دخول جيدة."
    if "SELL" in sig:
        return "السهم عند مقاومة، يفضل جني أرباح."
    return "لا توجد فرصة واضحة حالياً."

# ================= CARD =================
def show_card(code,p,h,l,v,rsi):

    s1,s2,r1,r2 = pivots(p,h,l)

    sig = signal(p,s1,r1,rsi)

    entry = round(s1+0.1,2)
    stop = round(s1-0.15,2)
    target = round(r1,2)

    rr = round((target-entry)/(entry-stop),2) if entry!=stop else 0

    st.markdown(f"""
    <div class="card">

    <b style="font-size:22px;">{code}</b><br>

    💰 {p:.2f} | RSI {rsi:.1f}<br>

    🧱 {s1:.2f}/{s2:.2f} | 🚧 {r1:.2f}/{r2:.2f}<br>
    💧 {liquidity(v)}

    <hr>

    📢 {sig}<br>

    🎯 دخول {entry} | وقف {stop} | هدف {target}<br>
    ⚖️ R/R {rr}

    <hr>

    🤖 {ai_comment(sig,rsi)}

    </div>
    """, unsafe_allow_html=True)

    # chart
    st.components.v1.html(f"""
    <iframe src="https://www.tradingview.com/widgetembed/?symbol=EGX:{code}&interval=D&theme=dark"
    width="100%" height="350"></iframe>
    """, height=350)

# ================= UI =================
tab1,tab2,tab3 = st.tabs(["📊 تحليل","🚨 Scanner","🏆 فرص"])

# تحليل
with tab1:
    code = st.text_input("ادخل كود السهم")
    if code:
        d = get_data(code.upper())
        if d:
            show_card(code.upper(),*d)

# scanner
with tab2:
    rows=[]
    for s in ALL_STOCKS:
        d = get_data(s)
        if not d: continue
        p,h,l,v,rsi = d
        s1,s2,r1,r2 = pivots(p,h,l)
        sig = signal(p,s1,r1,rsi)

        rows.append({
            "السهم":s,
            "السعر":p,
            "RSI":rsi,
            "الإشارة":sig
        })

    st.dataframe(pd.DataFrame(rows),use_container_width=True)

# فرص
with tab3:
    rows=[]
    for s in ALL_STOCKS:
        d = get_data(s)
        if not d: continue
        p,h,l,v,rsi = d
        s1,s2,r1,r2 = pivots(p,h,l)

        sig = signal(p,s1,r1,rsi)

        if "BUY" in sig:
            score = round(100 - abs(50-rsi),1)

            rows.append({
                "السهم":s,
                "السعر":p,
                "RSI":rsi,
                "Score":score
            })

    df = pd.DataFrame(rows).sort_values(by="Score",ascending=False)

    st.dataframe(df,use_container_width=True)
