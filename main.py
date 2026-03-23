import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="EGX Sniper PRO MAX", layout="wide")

st.title("🏹 EGX Sniper PRO MAX")

ALL_STOCKS = ["TMGH","COMI","ETEL","SWDY","EFID","ATQA","ALCN","RMDA","ORAS","FWRY"]

# ================= DATA =================
@st.cache_data(ttl=300)
def get_data(symbol):
    try:
        url = "https://scanner.tradingview.com/egypt/scan"
        payload = {
            "symbols":{"tickers":[f"EGX:{symbol}"],"query":{"types":[]}},
            "columns":["close","high","low","volume","RSI","MACD.macd","MACD.signal"]
        }
        r = requests.post(url,json=payload)
        d = r.json()["data"][0]["d"]
        return float(d[0]),float(d[1]),float(d[2]),float(d[3]),float(d[4]),float(d[5]),float(d[6])
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

def smart_score(p,s1,rsi,macd,macd_signal,volume):
    score = 0

    if abs(p-s1)/p < 0.02:
        score += 30

    if rsi < 40:
        score += 25
    elif rsi < 55:
        score += 10

    if macd > macd_signal:
        score += 25

    if volume > 2_000_000:
        score += 20

    return min(score,100)

def ai_comment(score,rsi,p,s1):
    if score > 75:
        return "🔥 فرصة قوية جدًا (دعم + تأكيدات)"
    elif score > 60:
        return "⚡ فرصة جيدة تحتاج متابعة"
    elif rsi > 70:
        return "⚠️ السهم متشبع شراء"
    elif abs(p-s1)/p < 0.02:
        return "👀 السهم عند دعم"
    return "😐 لا توجد فرصة واضحة"

def position_size(capital,entry,stop):
    risk = capital * 0.02
    per_share = abs(entry-stop)
    if per_share == 0:
        return 0
    return int(risk / per_share)

# ================= OLD CARD =================
def show_card(code,p,h,l,v,rsi):

    s1,s2,r1,r2 = pivots(p,h,l)

    st.markdown(f"""
    <div style="background:#020617;padding:20px;border-radius:15px;line-height:1.8">

    <h2>{code} -</h2>

    💰 السعر الحالي: {p:.2f}<br>
    📉 RSI: {rsi:.1f}<br>

    🧱 الدعم: {s1:.2f} / {s2:.2f}<br>
    🚧 المقاومة: {r1:.2f} / {r2:.2f}<br>

    </div>
    """, unsafe_allow_html=True)

    st.components.v1.html(f"""
    <iframe src="https://www.tradingview.com/widgetembed/?symbol=EGX:{code}&interval=D&theme=dark"
    width="100%" height="350"></iframe>
    """, height=350)

    return s1,r1

# ================= UI =================
tab1,tab2 = st.tabs(["📊 تحليل احترافي","🔥 فرص جاهزة"])

# ================= TAB 1 =================
with tab1:
    capital = st.number_input("رأس المال",1000,1000000,50000)

    code = st.text_input("ادخل كود السهم")

    if code:
        d = get_data(code.upper())
        if d:
            p,h,l,v,rsi,macd,macd_signal = d

            s1,r1 = show_card(code.upper(),p,h,l,v,rsi)

            entry = round(s1+0.1,2)
            stop = round(s1-0.15,2)
            target = round(r1,2)

            rr = round((target-entry)/(entry-stop),2)
            size = position_size(capital,entry,stop)

            score = smart_score(p,s1,rsi,macd,macd_signal,v)

            st.markdown(f"""
            🎯 Entry: {entry}  
            ❌ Stop: {stop}  
            🎯 Target: {target}  
            ⚖️ R/R: {rr}  

            💰 حجم الصفقة: {size} سهم  

            ⭐ Score: {score}/100  

            🧠 {ai_comment(score,rsi,p,s1)}
            """)

# ================= TAB 2 =================
with tab2:

    rows=[]

    for s in ALL_STOCKS:
        d = get_data(s)
        if not d: continue

        p,h,l,v,rsi,macd,macd_signal = d
        s1,s2,r1,r2 = pivots(p,h,l)

        score = smart_score(p,s1,rsi,macd,macd_signal,v)

        if score > 60:
            rows.append({
                "السهم":s,
                "السعر":p,
                "RSI":rsi,
                "Score":score
            })

    if rows:
        df = pd.DataFrame(rows).sort_values("Score",ascending=False)
        st.dataframe(df,use_container_width=True)
    else:
        st.warning("لا توجد فرص حالياً")
