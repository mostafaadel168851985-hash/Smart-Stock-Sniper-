import streamlit as st
import requests
import pandas as pd

# ================= CONFIG =================
st.set_page_config(page_title="EGX Sniper PRO", layout="wide")

# ================= STYLE =================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg,#020617,#0f172a);
    color:white;
}
.card {
    background:#0f172a;
    padding:20px;
    border-radius:18px;
    line-height:1.8;
    font-size:16px;
    box-shadow:0 0 20px rgba(0,0,0,0.5);
}
hr {border:1px solid #1e293b;}
</style>
""", unsafe_allow_html=True)

st.title("🏹 EGX Sniper PRO")

# ================= STOCKS =================
ALL_STOCKS = ["TMGH","COMI","ETEL","SWDY","EFID","ATQA","ALCN","RMDA","ORAS","FWRY","AMOC","HELI"]

# ================= DATA =================
@st.cache_data(ttl=300)
def get_data(symbol):
    try:
        url = "https://scanner.tradingview.com/egypt/scan"
        payload = {
            "symbols":{"tickers":[f"EGX:{symbol}"],"query":{"types":[]}},
            "columns":["close","high","low","volume"]
        }
        r = requests.post(url,json=payload)
        data = r.json()

        if "data" not in data or len(data["data"]) == 0:
            return None

        d = data["data"][0]["d"]
        return float(d[0]),float(d[1]),float(d[2]),float(d[3])
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

def rsi(p,h,l):
    if h==l: return 50
    return ((p-l)/(h-l))*100

def liquidity(v):
    if v>2_000_000: return "عالية"
    elif v>500_000: return "متوسطة"
    else: return "ضعيفة"

# ================= SIGNAL FIX =================
def get_signal(p,s1,r1,rsi_val):
    dist_s = abs(p-s1)/p*100
    dist_r = abs(p-r1)/p*100

    # BUY له أولوية عند الدعم
    if dist_s < 1.5 and rsi_val < 45:
        return "🟢 BUY"

    # SELL فقط عند المقاومة
    elif dist_r < 1.5 and rsi_val > 65:
        return "🔴 SELL"

    else:
        return "⚪ HOLD"

# ================= AI COMMENT =================
def ai_comment(signal,p,s1,r1):
    if signal=="🟢 BUY":
        return f"السهم قريب من دعم قوي ({round(s1,2)})، فرصة ارتداد جيدة."
    elif signal=="🔴 SELL":
        return f"السهم عند مقاومة ({round(r1,2)})، يفضل جني أرباح."
    else:
        return "السهم في منتصف الحركة، لا توجد فرصة واضحة حالياً."

# ================= CARD =================
def show_card(code,p,h,l,v):

    s1,s2,r1,r2 = pivots(p,h,l)
    rsi_val = rsi(p,h,l)
    liq = liquidity(v)
    signal = get_signal(p,s1,r1,rsi_val)

    # SCORES
    trader = 50
    swing = round(60 + (50-abs(50-rsi_val)),2)
    investor = 55

    comment = ai_comment(signal,p,s1,r1)

    st.markdown(f"""
    <div class="card">

    <h3>{code} -</h3>

    💰 السعر: {p:.2f}<br>
    📉 RSI: {rsi_val:.1f}<br>

    🧱 الدعم: {s2:.2f} / {s1:.2f}<br>
    🚧 المقاومة: {r2:.2f} / {r1:.2f}<br>
    💧 السيولة: {liq}<br>

    <hr>

    📊 الإشارة: {signal}

    <hr>

    🎯 المضارب: {trader}/100<br>
    دخول: {round(s1+0.1,2)} | وقف: {round(s1-0.15,2)}<br>

    🔁 السوينج: {swing}/100<br>
    دخول: {round((s1+r1)/2,2)} | وقف: {round((s1+r1)/2-0.25,2)}<br>

    🏦 المستثمر: {investor}/100<br>
    دخول: {round((s1+s2)/2,2)} | وقف: {round(s2-0.25,2)}<br>

    <hr>

    🤖 AI Comment:<br>
    {comment}

    <hr>

    📌 التوصية: {signal}

    </div>
    """, unsafe_allow_html=True)

# ================= SCANNER =================
def scanner():
    rows=[]

    for s in ALL_STOCKS:
        data = get_data(s)
        if not data: continue

        p,h,l,v = data
        s1,s2,r1,r2 = pivots(p,h,l)
        rsi_val = rsi(p,h,l)
        liq = liquidity(v)
        signal = get_signal(p,s1,r1,rsi_val)

        dist = abs(p-s1)/p*100

        if dist < 1:
            status="🔥 لاصق دعم"
        elif dist < 2:
            status="🟢 قريب دعم"
        else:
            status="⚪ بعيد"

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

with tab1:
    code = st.text_input("ادخل كود السهم").upper()
    if code:
        data = get_data(code)
        if data:
            show_card(code,*data)
        else:
            st.warning("السهم غير متاح")

with tab2:
    df = scanner()
    if df.empty:
        st.warning("لا توجد بيانات")
    else:
        st.dataframe(df,use_container_width=True)
