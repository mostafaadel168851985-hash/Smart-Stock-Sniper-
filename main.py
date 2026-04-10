import streamlit as st
import requests

st.set_page_config(page_title="EGX Sniper v17.4 FINAL", layout="wide")

if 'page' not in st.session_state:
    st.session_state.page = 'home'

def go_to(p):
    st.session_state.page = p
    st.rerun()

# ================= DATA =================
@st.cache_data(ttl=300)
def fetch_egx_data(query_val=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    cols = ["name","close","RSI","volume","average_volume_10d_calc","high","low","change","description","SMA50","SMA200"]
    
    payload = {
        "filter":[{"left":"volume","operation":"greater","right":30000}],
        "columns":cols,
        "range":[0,100]
    }

    if not scan_all and query_val:
        payload["filter"].append({"left":"name","operation":"match","right":query_val.upper()})

    try:
        r = requests.post(url,json=payload,timeout=10).json()
        return r.get("data",[])
    except:
        return []

# ================= ANALYSIS =================
def analyze_stock(d_row):
    try:
        d = d_row['d']
        name,p,rsi,v,avg_v,h,l,chg,desc,sma50,sma200 = d

        pp = (h+l+p)/3
        r1,s1 = (2*pp)-l,(2*pp)-h
        r2,s2 = pp+(h-l),pp-(h-l)

        ratio = v/(avg_v or 1)
        rsi_val = rsi or 0

        # اتجاه
        t_short = "صاعد" if p > pp else "هابط"
        t_med = "صاعد" if sma50 and p > sma50 else "هابط"
        t_long = "صاعد" if sma200 and p > sma200 else "هابط"

        # سيولة
        vol_txt = "🔥 قوي" if ratio>1.5 else "⚪ متوسط" if ratio>0.8 else "🔴 ضعيف"

        # سكـور
        t_score = int(85 if 40<rsi_val<60 else 60 if rsi_val<70 else 35)
        if t_med=="هابط": t_score -= 15

        # إشارات محسنة
        is_gold = (ratio > 1.5 and 45 < rsi_val < 60 and t_med == "صاعد")

        is_break = (p >= h*0.995 and ratio > 1.2 and rsi_val > 50 and t_med == "صاعد")

        is_chase = ((p > r1*1.03 and rsi_val > 70) or (chg > 7 and ratio > 2))

        # Status
        if is_chase:
            status = "⚠️ مطاردة"
        elif is_break:
            status = "🚀 اختراق"
        elif is_gold:
            status = "💎 ذهب"
        elif rsi_val < 45:
            status = "🟢 تجميع"
        else:
            status = "🟡 انتظار"

        return {
            "name":name,"desc":desc,"p":p,"rsi":rsi_val,"chg":chg,"ratio":ratio,
            "t_score":t_score,"status":status,
            "r1":r1,"r2":r2,"s1":s1,"s2":s2,
            "t_short":t_short,"t_med":t_med,"t_long":t_long,
            "vol_txt":vol_txt,
            "is_gold":is_gold,"is_break":is_break,"is_chase":is_chase
        }
    except:
        return None

# ================= UI =================
def render(an):

    # تحذير المطاردة
    if an['is_chase']:
        st.error("⚠️ تحذير: السهم في منطقة مطاردة")

    st.markdown(f"## {an['name']} | {an['status']} | Score: {an['t_score']}")

    st.write(f"Trend: قصير({an['t_short']}) - متوسط({an['t_med']}) - طويل({an['t_long']})")

    st.write(f"السعر: {an['p']:.2f} | RSI: {an['rsi']:.1f} | السيولة: {an['vol_txt']}")

    st.divider()

    # الدعوم والمقاومات
    st.subheader("📊 الدعوم والمقاومات")
    c = st.columns(4)
    c[0].write(f"دعم2: {an['s2']:.2f}")
    c[1].write(f"دعم1: {an['s1']:.2f}")
    c[2].write(f"مقاومة1: {an['r1']:.2f}")
    c[3].write(f"مقاومة2: {an['r2']:.2f}")

    # المضارب والسوينج
    col1,col2 = st.columns(2)

    with col1:
        st.subheader("🎯 مضارب")
        st.write(f"دخول: {an['p']:.2f}")
        st.write(f"هدف: {an['r1']:.2f}")
        st.write(f"وقف: {an['s1']:.2f}")

    with col2:
        st.subheader("📈 سوينج")
        st.write(f"دخول: {an['p']:.2f}")
        st.write(f"هدف: {an['r2']:.2f}")
        st.write(f"دعم: {an['s2']:.2f}")

    # خطة السيولة
    st.subheader("💰 خطة السيولة (20,000)")
    st.write(f"7000 عند {an['p']:.2f}")
    st.write(f"7000 عند {an['r1']:.2f}")
    st.write(f"6000 عند {an['s2']:.2f}")

    # حاسبة المتوسط
    with st.expander("🧮 حاسبة المتوسط"):
        old_p = st.number_input("السعر القديم", value=float(an['p']))
        old_q = st.number_input("الكمية", value=1000)
        new_q = st.number_input("كمية جديدة", value=old_q)

        avg = ((old_p * old_q) + (an['p'] * new_q)) / (old_q + new_q)
        st.success(f"المتوسط الجديد: {avg:.2f}")

# ================= PAGES =================
if st.session_state.page == 'home':
    st.title("🏹 Sniper v17.4 FINAL")

    if st.button("📡 تحليل سهم"): go_to('analyze')
    if st.button("🔭 كشاف السوق"): go_to('scanner')
    if st.button("🚀 اختراق"): go_to('breakout')
    if st.button("💎 ذهب"): go_to('gold')

elif st.session_state.page == 'analyze':
    if st.button("⬅️"): go_to('home')

    q = st.text_input("ادخل الرمز").upper()
    if q:
        data = fetch_egx_data(query_val=q)
        if data:
            render(analyze_stock(data[0]))

elif st.session_state.page == 'scanner':
    if st.button("⬅️"): go_to('home')

    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r)) and an['t_score'] >= 50:
            with st.expander(f"{an['name']} | {an['status']}"):
                render(an)

elif st.session_state.page == 'breakout':
    if st.button("⬅️"): go_to('home')

    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r)) and an['is_break'] and not an['is_chase']:
            with st.expander(f"🚀 {an['name']}"):
                render(an)

elif st.session_state.page == 'gold':
    if st.button("⬅️"): go_to('home')

    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r)) and an['is_gold']:
            with st.expander(f"💎 {an['name']}"):
                render(an)
