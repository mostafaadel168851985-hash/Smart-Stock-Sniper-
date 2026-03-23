import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="EGX Sniper ULTIMATE", layout="wide")

# ================= STYLE =================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg,#020617,#020617,#0f172a);
    color:white;
}
.card {
    background:#020617;
    padding:14px;
    border-radius:16px;
    line-height:1.5;
    font-size:14px;
    box-shadow:0 0 20px rgba(0,0,0,0.6);
}
hr {border:1px solid #1e293b;}
</style>
""", unsafe_allow_html=True)

st.title("🏹 EGX Sniper ULTIMATE")

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

        price = float(d[0])
        high = float(d[1])
        low = float(d[2])
        volume = float(d[3])
        rsi = float(d[4])

        return price,high,low,volume,rsi
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

def volume_score(v):
    if v>3_000_000: return 90
    elif v>1_500_000: return 75
    elif v>500_000: return 60
    else: return 40

def volume_spike(v):
    return "🚀 Volume Spike" if v>2_500_000 else ""

def ema_trend(p,h,l):
    mid=(h+l)/2
    return "📈 Bullish" if p>mid else "📉 Bearish"

def breakout(p,r1,s1):
    if p > r1:
        return "🚀 Breakout Up"
    if p < s1:
        return "⚠️ Breakout Down"
    return ""

# ================= MACD (تقريب) =================
def macd_signal(rsi):
    if rsi > 60:
        return "📈 MACD Bullish"
    elif rsi < 40:
        return "📉 MACD Bearish"
    return "⚖️ Neutral"

# ================= SIGNAL =================
def signal_logic(p,s1,r1,rsi,vol):

    dist_s = abs(p-s1)/p*100
    dist_r = abs(p-r1)/p*100

    if dist_s < 1.5 and rsi < 40 and vol > 60:
        return "🟢 BUY STRONG"

    if dist_s < 2.5 and rsi < 50:
        return "🟡 BUY"

    if dist_r < 1.5 and rsi > 70:
        return "🔴 TAKE PROFIT"

    return "⚪ HOLD"

# ================= AI =================
def ai_decision(signal,rsi,trend):

    if "BUY STRONG" in signal:
        return "💎 Accumulate بقوة"

    if "BUY" in signal:
        return "📊 شراء تدريجي"

    if "TAKE PROFIT" in signal:
        return "💰 بيع جزئي"

    if rsi > 75:
        return "⚠️ السهم متشبع شراء"

    return "⏳ انتظار"

# ================= CARD =================
def show_card(code,p,h,l,v,rsi):

    s1,s2,r1,r2 = pivots(p,h,l)
    vol = volume_score(v)

    sig = signal_logic(p,s1,r1,rsi,vol)

    entry = round(s1+0.1,2)
    stop = round(s1-0.15,2)
    target = round(r1,2)

    rr = round((target-entry)/(entry-stop),2) if entry!=stop else 0

    trend = ema_trend(p,h,l)
    macd = macd_signal(rsi)
    vol_sp = volume_spike(v)
    brk = breakout(p,r1,s1)

    decision = ai_decision(sig,rsi,trend)

    # ALERT
    if "BUY STRONG" in sig:
        st.success("🚀 فرصة قوية الآن")
    elif "BUY" in sig:
        st.info("📊 فرصة محتملة")

    st.markdown(f"""
    <div class="card">

    <h2>{code}</h2>

    💰 {p:.2f} | RSI {rsi:.1f}<br>
    {trend} | {macd}<br>
    🧱 {s1:.2f}/{s2:.2f} | 🚧 {r1:.2f}/{r2:.2f}<br>
    💧 Vol | {vol_sp} {brk}

    <hr>

    📢 {sig}

    🎯 Entry {entry} | Stop {stop} | Target {target}<br>
    ⚖️ R/R = {rr}

    <hr>

    🤖 {decision}

    </div>
    """, unsafe_allow_html=True)

    # ===== CHART =====
    st.components.v1.html(f"""
    <iframe src="https://www.tradingview.com/widgetembed/?symbol=EGX:{code}&interval=D&theme=dark"
    width="100%" height="400"></iframe>
    """, height=400)

# ================= SCANNER =================
def scanner():

    rows=[]

    for s in ALL_STOCKS:
        data = get_data(s)
        if not data: continue

        p,h,l,v,rsi = data
        s1,s2,r1,r2 = pivots(p,h,l)

        vol = volume_score(v)
        sig = signal_logic(p,s1,r1,rsi,vol)

        score = round((100 - abs(50-rsi)) + vol/2,1)

        rows.append({
            "السهم":s,
            "السعر":round(p,2),
            "RSI":round(rsi,1),
            "Score":score,
            "الإشارة":sig
        })

    return pd.DataFrame(rows)

# ================= TOP =================
def top(df):
    return df[df["الإشارة"].str.contains("BUY")].sort_values(by="Score",ascending=False)

# ================= UI =================
tab1,tab2,tab3 = st.tabs(["📊 تحليل سهم","🚨 Scanner","🏆 Top فرص"])

# تحليل
with tab1:
    code = st.text_input("ادخل كود السهم").upper()
    if code:
        data = get_data(code)
        if data:
            show_card(code,*data)
        else:
            st.warning("السهم غير متاح")

# Scanner
with tab2:
    df = scanner()
    st.dataframe(df,use_container_width=True)

# Top فرص
with tab3:
    df = scanner()
    t = top(df)

    if t.empty:
        st.warning("لا توجد فرص حالياً")
    else:
        st.success("🔥 أفضل فرص شراء")
        st.dataframe(t,use_container_width=True)
