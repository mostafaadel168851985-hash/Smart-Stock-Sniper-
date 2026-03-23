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
.card {
    background:#020617;
    padding:20px;
    border-radius:18px;
    line-height:1.9;
    font-size:15px;
    box-shadow:0 0 25px rgba(0,0,0,0.6);
}
hr {
    border:1px solid #334155;
    margin:12px 0;
}
</style>
""", unsafe_allow_html=True)

st.title("🏹 EGX Sniper PRO")

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
        return "سيولة عالية"
    elif v>1_000_000:
        return "سيولة متوسطة"
    return "سيولة ضعيفة"

# ================= SIGNAL =================
def signal(p,s1,r1,rsi):

    dist_s = abs(p-s1)/p*100
    dist_r = abs(p-r1)/p*100

    if dist_s < 1.5 and rsi < 45:
        return "🟢 توجد إشارة ارتداد"

    if dist_r < 1.5 and rsi > 70:
        return "🔴 جني أرباح"

    return "↪️ لا توجد إشارة ارتداد"

def confirm(rsi):
    if rsi < 40:
        return "🟢 يوجد تأكيد"
    return "⚪ لا يوجد تأكيد"

# ================= AI =================
def ai_comment(sig,rsi):
    if "ارتداد" in sig:
        return "السهم قريب من الدعم وقد يظهر ارتداد، يمكن المتابعة."
    if "جني" in sig:
        return "السهم عند مقاومة قوية، يفضل الحذر أو جني أرباح."
    return "السهم في منتصف الاتجاه، لا توجد فرصة واضحة حالياً."

# ================= CARD =================
def show_card(code,p,h,l,v,rsi):

    s1,s2,r1,r2 = pivots(p,h,l)

    sig = signal(p,s1,r1,rsi)
    conf = confirm(rsi)

    entry = round(s1+0.1,2)
    stop = round(s1-0.15,2)
    target = round(r1,2)

    swing_entry = round((s1+r1)/2,2)
    invest_entry = round((s1+s2)/2,2)

    trader_score = 50
    swing_score = round(60 + (50-abs(50-rsi)),2)
    investor_score = 55

    st.markdown(f"""
    <div class="card">

    <h2>{code} -</h2>

    💰 السعر الحالي: {p:.2f}<br>
    📉 RSI: {rsi:.1f}<br>

    🧱 الدعم: {s1:.2f} / {s2:.2f}<br>
    🚧 المقاومة: {r1:.2f} / {r2:.2f}<br>
    💧 السيولة: {liquidity(v)}

    <hr>

    🔄 {sig}<br>
    ⚡ {conf}

    <hr>

    🎯 المضارب: {trader_score}/100<br>
    ⚡ مناسب لمضاربة سريعة قرب الدعم {s1:.2f}<br>
    دخول: {entry} ، وقف خسارة: {stop}<br><br>

    🔁 السوينج: {swing_score}/100<br>
    🔁 السهم في حركة تصحيح داخل اتجاه عام<br>
    دخول: {swing_entry} ، وقف خسارة: {round(swing_entry-0.25,2)}<br><br>

    🏦 المستثمر: {investor_score}/100<br>
    🏦 الاتجاه طويل الأجل إيجابي طالما السعر أعلى المتوسط<br>
    دخول: {invest_entry} ، وقف خسارة: {round(s2-0.25,2)}

    <hr>

    📌 التوصية: انتظار

    📝 ملحوظة للمحبوس:<br>
    أقرب دعم {s1:.2f} ، دعم أقوى {s2:.2f}

    <hr>

    🤖 AI:<br>
    {ai_comment(sig,rsi)}

    </div>
    """, unsafe_allow_html=True)

    # ===== CHART =====
    st.components.v1.html(f"""
    <iframe src="https://www.tradingview.com/widgetembed/?symbol=EGX:{code}&interval=D&theme=dark"
    width="100%" height="400"></iframe>
    """, height=400)

# ================= UI =================
code = st.text_input("ادخل كود السهم").upper()

if code:
    d = get_data(code)
    if d:
        show_card(code,*d)
    else:
        st.warning("السهم غير متاح")
