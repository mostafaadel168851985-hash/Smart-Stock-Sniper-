import streamlit as st
import requests
import pandas as pd

# ================= CONFIG =================
st.set_page_config(page_title="EGX Sniper PRO MAX ULTRA", layout="wide")

# ================= STYLE =================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg,#020617,#020617,#0f172a);
    color:#ffffff;
}
h1,h2,h3,h4,p,span,div {color:white !important;}

.card {
    background:#020617;
    padding:18px;
    border-radius:18px;
    line-height:1.5;
    font-size:14px;
    box-shadow:0 0 15px rgba(0,0,0,0.6);
}
hr {border:1px solid #1e293b;margin:8px 0;}
</style>
""", unsafe_allow_html=True)

st.title("🏹 EGX Sniper PRO MAX ULTRA")

# ================= STOCKS =================
ALL_STOCKS = [
"TMGH","COMI","ETEL","SWDY","EFID","ATQA",
"ALCN","RMDA","ORAS","FWRY","AMOC","HELI"
]

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

def trend(p,h,l):
    mid = (h+l)/2
    if p > mid:
        return "📈 صاعد"
    elif p < mid:
        return "📉 هابط"
    else:
        return "➡️ عرضي"

# ================= SIGNAL =================
def get_signal(p,s1,r1,rsi_val):

    dist_s = abs(p-s1)/p*100
    dist_r = abs(p-r1)/p*100

    if dist_s < 1.5 and rsi_val < 40:
        return "🟢 BUY STRONG"

    if dist_r < 1.5 and rsi_val > 70:
        return "🔴 SELL STRONG"

    if dist_s < 2.5:
        return "🟡 BUY"

    if dist_r < 2.5:
        return "🟠 SELL"

    return "⚪ HOLD"

# ================= SCORE =================
def calc_score(rsi_val,trend_type):
    score = 50 + (50 - abs(50-rsi_val))

    if "صاعد" in trend_type:
        score += 10
    elif "هابط" in trend_type:
        score -= 10

    return round(max(0,min(100,score)),1)

# ================= AI =================
def ai_comment(signal,trend_type):
    if "BUY STRONG" in signal:
        return "فرصة قوية جداً للشراء من الدعم مع اتجاه مناسب."
    if "BUY" in signal:
        return "قريب من الدعم، يفضل انتظار تأكيد بسيط."
    if "SELL STRONG" in signal:
        return "تشبع شرائي قوي عند مقاومة، الأفضل البيع."
    if "SELL" in signal:
        return "اقتراب من مقاومة، يفضل تقليل المخاطرة."
    return "لا توجد فرصة واضحة حالياً."

# ================= CARD =================
def show_card(code,p,h,l,v):

    s1,s2,r1,r2 = pivots(p,h,l)
    rsi_val = rsi(p,h,l)
    trend_type = trend(p,h,l)
    liq = liquidity(v)

    signal = get_signal(p,s1,r1,rsi_val)
    score = calc_score(rsi_val,trend_type)
    comment = ai_comment(signal,trend_type)

    entry = round(s1+0.1,2)
    stop = round(s1-0.15,2)
    target = round(r1,2)

    rr = round((target-entry)/(entry-stop),2) if entry>stop else 0

    st.markdown(f"""
    <div class="card">

    <h3>{code}</h3>

    💰 {p:.2f} | RSI {rsi_val:.1f} | {trend_type}<br>
    🧱 {s2:.2f}/{s1:.2f} | 🚧 {r2:.2f}/{r1:.2f}<br>
    💧 {liq}

    <hr>

    📊 {signal} | ⭐ Score {score}

    <hr>

    🎯 Entry {entry} | Stop {stop} | Target {target}<br>
    ⚖️ R/R = {rr}

    <hr>

    🤖 {comment}

    </div>
    """, unsafe_allow_html=True)

    # TradingView Chart
    st.markdown(f"""
    <iframe src="https://s.tradingview.com/widgetembed/?symbol=EGX:{code}&interval=60&theme=dark"
    width="100%" height="400"></iframe>
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
        trend_type = trend(p,h,l)

        signal = get_signal(p,s1,r1,rsi_val)
        score = calc_score(rsi_val,trend_type)

        rows.append({
            "السهم":s,
            "السعر":round(p,2),
            "RSI":round(rsi_val,1),
            "Trend":trend_type,
            "الإشارة":signal,
            "Score":score
        })

    df = pd.DataFrame(rows)
    return df.sort_values(by="Score",ascending=False)

# ================= ALERT =================
def alerts(df):
    strong = df[df["الإشارة"].str.contains("STRONG")]
    if not strong.empty:
        st.success("🔥 فرص قوية الآن")
        st.dataframe(strong,use_container_width=True)

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
    if df.empty:
        st.warning("لا توجد بيانات")
    else:
        st.dataframe(df,use_container_width=True)

# Top فرص
with tab3:
    df = scanner()
    alerts(df)
