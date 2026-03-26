import streamlit as st
import requests

st.set_page_config(page_title="EGX Sniper PRO", layout="wide")

WATCHLIST = ["TMGH","COMI","ETEL","SWDY","EFID","ATQA","ALCN","RMDA"]

COMPANIES = {
    "TMGH":"طلعت مصطفى","COMI":"البنك التجاري الدولي","ETEL":"المصرية للاتصالات",
    "SWDY":"السويدي إليكتريك","EFID":"إيديتا","ATQA":"عتاقة","ALCN":"ألكون","RMDA":"رمادا"
}

st.markdown("""
<style>
body,.stApp{background:#0d1117;color:white;}
.card{background:#161b22;padding:20px;border-radius:15px;margin-bottom:20px;}
</style>
""", unsafe_allow_html=True)

# ================= DATA =================
@st.cache_data(ttl=120)
def get_data(symbol):
    try:
        url="https://scanner.tradingview.com/egypt/scan"
        payload={
            "symbols":{"tickers":[f"EGX:{symbol}"],"query":{"types":[]}},
            "columns":["close","high","low","volume"]
        }
        r=requests.post(url,json=payload,timeout=10).json()
        d=r["data"][0]["d"]
        return float(d[0]),float(d[1]),float(d[2]),float(d[3])
    except:
        return None,None,None,None

# ================= LOGIC =================
def pivots(p,h,l):
    piv=(p+h+l)/3
    s1=(2*piv)-h
    s2=piv-(h-l)
    r1=(2*piv)-l
    r2=piv+(h-l)
    return s1,s2,r1,r2

def rsi(p,h,l):
    if h==l:return 50
    return ((p-l)/(h-l))*100

def smart_score(p,s1,r1,rsi):
    score=50

    if rsi<30: score+=20
    elif rsi<40: score+=10
    elif rsi>70: score-=15

    if abs(p-s1)/s1<0.02: score+=20
    if p>r1: score+=15

    return max(min(score,100),0)

def rank(score):
    if score>=80: return "🔥 قوية"
    elif score>=60: return "⚠ متوسطة"
    else: return "❌ ضعيفة"

def ai_comment(p,s1,r1,rsi):
    if abs(p-s1)/s1<0.02 and rsi<40:
        return "🔥 ارتداد من دعم قوي"
    if p>r1:
        return "🚀 اختراق مقاومة"
    if rsi>70:
        return "⚠ تشبع شرائي"
    return "⚖ حركة عرضية"

# ================= REPORT =================
def show_report(code,p,h,l,v):
    s1,s2,r1,r2=pivots(p,h,l)
    r=rsi(p,h,l)

    score=smart_score(p,s1,r1,r)
    comment=ai_comment(p,s1,r1,r)

    entry=round(s1+0.05,2)
    sl=round(s1-0.15,2)

    st.markdown(f"""
    <div class="card">
    <h3>{code} - {COMPANIES.get(code,'')}</h3>

    💰 السعر: {p:.2f} | RSI: {r:.1f}<br>
    🧱 دعم: {s1:.2f} / {s2:.2f}<br>
    🚧 مقاومة: {r1:.2f} / {r2:.2f}<br>

    <hr>

    🎯 Score: {score}/100 ({rank(score)})<br>
    💡 {comment}<br>

    🎯 دخول: {entry}<br>
    ❌ وقف خسارة: {sl}<br>

    <hr>

    📊 Confidence: {score}%<br>

    </div>
    """, unsafe_allow_html=True)

# ================= SCANNER =================
def scanner():
    rows=[]
    for s in WATCHLIST:
        p,h,l,v=get_data(s)
        if not p:continue

        s1,_,r1,_=pivots(p,h,l)
        r=rsi(p,h,l)

        score=smart_score(p,s1,r1,r)

        rows.append({
            "السهم":s,
            "السعر":round(p,2),
            "RSI":round(r,1),
            "Score":score,
            "التقييم":rank(score)
        })
    return rows

# ================= UI =================
st.title("🏹 EGX Sniper PRO")

tab1,tab2,tab3=st.tabs(["📡 التحليل","🛠️ يدوي","🚨 الفرص"])

with tab1:
    code=st.text_input("ادخل كود السهم").upper().strip()
    if code:
        p,h,l,v=get_data(code)
        if p:
            show_report(code,p,h,l,v)
        else:
            st.error("لا توجد بيانات")

with tab2:
    p=st.number_input("السعر",format="%.2f")
    h=st.number_input("أعلى",format="%.2f")
    l=st.number_input("أقل",format="%.2f")
    v=st.number_input("السيولة")

    if p>0:
        show_report("MANUAL",p,h,l,v)

with tab3:
    data=scanner()
    if data:
        for d in data:
            st.info(d)
    else:
        st.success("لا توجد فرص حالياً")
