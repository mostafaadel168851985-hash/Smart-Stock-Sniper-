import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="EGX Sniper PRO MAX AI", layout="wide")

# ================= STYLE =================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg,#020617,#020617,#0f172a);
    color:white;
}
.card {
    background:#020617;
    padding:16px;
    border-radius:16px;
    line-height:1.6;
    font-size:14px;
    box-shadow:0 0 20px rgba(0,0,0,0.6);
}
hr {border:1px solid #1e293b;margin:10px 0;}
</style>
""", unsafe_allow_html=True)

st.title("🏹 EGX Sniper PRO MAX AI")

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

def trend(p,h,l):
    return "صاعد 📈" if p > (h+l)/2 else "هابط 📉"

def candle_signal(p,h,l):
    body = abs(p - ((h+l)/2))
    if body < (h-l)*0.2:
        return "تجميع ⚖️"
    elif p > (h+l)/2:
        return "شمعة صاعدة 📈"
    else:
        return "شمعة هابطة 📉"

def volume(v):
    if v > 3_000_000:
        return "سيولة عالية 🔥"
    elif v > 1_000_000:
        return "سيولة متوسطة"
    return "سيولة ضعيفة"

# ================= SIGNAL =================
def signal_logic(p,s1,r1,rsi):

    dist_s = abs(p-s1)/p*100
    dist_r = abs(p-r1)/p*100

    if dist_s < 1.5 and rsi < 45:
        return "BUY STRONG"

    if dist_s < 2.5 and rsi < 55:
        return "BUY"

    if dist_r < 1.5 and rsi > 70:
        return "SELL"

    return "HOLD"

# ================= AI =================
def ai_comment(signal,rsi):

    if signal == "BUY STRONG":
        return "🔥 فرصة قوية جداً: السهم عند دعم + RSI ممتاز → دخول تدريجي"

    if signal == "BUY":
        return "🟡 فرصة جيدة: السهم قريب دعم → دخول بحذر"

    if signal == "SELL":
        return "🔴 السهم عند مقاومة قوية → يفضل جني أرباح"

    return "⚪ لا توجد فرصة واضحة حالياً"

# ================= POSITION SIZE =================
def position_size(balance, risk, entry, stop):
    risk_amount = balance * (risk/100)
    diff = abs(entry - stop)
    if diff == 0:
        return 0
    return int(risk_amount / diff)

# ================= CARD =================
def show_card(code,p,h,l,v,rsi):

    s1,s2,r1,r2 = pivots(p,h,l)

    signal = signal_logic(p,s1,r1,rsi)

    entry = round(s1+0.1,2)
    stop = round(s1-0.15,2)
    target = round(r1,2)

    rr = round((target-entry)/(entry-stop),2) if entry!=stop else 0

    size = position_size(100000,2,entry,stop)

    st.markdown(f"""
    <div class="card">

    <h2>{code}</h2>

    💰 {p:.2f} | RSI {rsi:.1f}<br>
    📈 {trend(p,h,l)} | {candle_signal(p,h,l)}<br>

    🧱 {s1:.2f}/{s2:.2f} | 🚧 {r1:.2f}/{r2:.2f}<br>
    💧 {volume(v)}

    <hr>

    📢 الإشارة: {signal}

    🎯 دخول: {entry} | وقف: {stop} | هدف: {target}<br>
    ⚖️ R/R: {rr}

    💰 حجم الصفقة: {size} سهم

    <hr>

    🤖 {ai_comment(signal,rsi)}

    </div>
    """, unsafe_allow_html=True)

    st.components.v1.html(f"""
    <iframe src="https://www.tradingview.com/widgetembed/?symbol=EGX:{code}&interval=D&theme=dark"
    width="100%" height="400"></iframe>
    """, height=400)

# ================= UI =================
tab1,tab2,tab3 = st.tabs(["📊 تحليل","🚨 Scanner","🏆 Top فرص"])

# تحليل
with tab1:
    code = st.text_input("ادخل كود السهم").upper()
    if code:
        d = get_data(code)
        if d:
            show_card(code,*d)

# Scanner
with tab2:
    rows=[]
    for s in ALL_STOCKS:
        d = get_data(s)
        if not d: continue
        p,h,l,v,rsi = d
        s1,s2,r1,r2 = pivots(p,h,l)
        sig = signal_logic(p,s1,r1,rsi)

        rows.append({
            "السهم":s,
            "السعر":round(p,2),
            "RSI":round(rsi,1),
            "الإشارة":sig
        })

    df = pd.DataFrame(rows)
    st.dataframe(df,use_container_width=True)

# Top فرص (BUY فقط)
with tab3:
    rows=[]
    for s in ALL_STOCKS:
        d = get_data(s)
        if not d: continue
        p,h,l,v,rsi = d
        s1,s2,r1,r2 = pivots(p,h,l)

        sig = signal_logic(p,s1,r1,rsi)

        if "BUY" in sig:
            score = round(100 - abs(50-rsi),1)

            rows.append({
                "السهم":s,
                "السعر":p,
                "RSI":rsi,
                "الإشارة":sig,
                "Score":score
            })

    df = pd.DataFrame(rows).sort_values(by="Score",ascending=False)
    st.dataframe(df,use_container_width=True)
