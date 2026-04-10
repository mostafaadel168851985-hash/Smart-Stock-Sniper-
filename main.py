import streamlit as st
import requests

# ================== CONFIG ==================
st.set_page_config(page_title="EGX Sniper v17.3 PRO", layout="wide")

if 'page' not in st.session_state:
    st.session_state.page = 'home'

def go_to(p):
    st.session_state.page = p
    st.rerun()

# ================== DATA ==================
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

# ================== ANALYSIS ==================
def analyze_stock(d_row):
    try:
        d = d_row['d']
        name,p,rsi,v,avg_v,h,l,chg,desc,sma50,sma200 = d
        
        pp = (h+l+p)/3
        r1,s1 = (2*pp)-l,(2*pp)-h
        r2,s2 = pp+(h-l),pp-(h-l)

        ratio = v/(avg_v or 1)
        rsi_val = rsi or 0

        # الاتجاه
        t_short = "صاعد" if p > pp else "هابط"
        t_med = "صاعد" if sma50 and p > sma50 else "هابط"
        t_long = "صاعد" if sma200 and p > sma200 else "هابط"

        # السيولة
        vol_txt = "🔥 قوي" if ratio>1.5 else "⚪ متوسط" if ratio>0.8 else "🔴 ضعيف"

        # سكـور
        t_score = int(85 if 40<rsi_val<60 else 60 if rsi_val<70 else 35)
        if t_med=="هابط": t_score -= 15

        # ================== إشارات ==================

        # GOLD (فرص نظيفة)
        is_gold = (
            ratio > 1.5 and
            45 < rsi_val < 60 and
            t_med == "صاعد"
        )

        # BREAKOUT (حقيقي مش وهمي)
        is_break = (
            p >= h*0.995 and
            ratio > 1.2 and
            rsi_val > 50 and
            t_med == "صاعد"
        )

        # مطاردة
        is_chase = (
            (p > r1*1.03 and rsi_val > 70) or
            (chg > 7 and ratio > 2)
        )

        # Status
        if is_chase:
            status = "⚠️ مطاردة - تجنب"
        elif is_break:
            status = "🚀 اختراق"
        elif is_gold:
            status = "💎 فرصة ذهبية"
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

# ================== UI ==================
def render(an):

    # تحذير
    if an['is_chase']:
        st.error("⚠️ السهم في منطقة مطاردة - الأفضل الانتظار")

    st.markdown(f"### {an['name']} | {an['status']} | Score: {an['t_score']}")

    # الاتجاه
    st.write(f"قصير: {an['t_short']} | متوسط: {an['t_med']} | طويل: {an['t_long']}")

    # بيانات
    st.write(f"السعر: {an['p']:.2f} | RSI: {an['rsi']:.1f} | سيولة: {an['vol_txt']}")

    st.divider()

    # أهداف
    col1,col2 = st.columns(2)

    with col1:
        st.subheader("🎯 مضارب")
        st.write(f"هدف1: {an['r1']:.2f}")
        st.write(f"هدف2: {an['r2']:.2f}")
        st.write(f"وقف: {an['s1']:.2f}")

    with col2:
        st.subheader("💰 خطة 20,000")
        st.write(f"7000 عند {an['p']:.2f}")
        st.write(f"7000 عند اختراق {an['r1']:.2f}")
        st.write(f"6000 عند {an['s2']:.2f}")

# ================== PAGES ==================
if st.session_state.page == 'home':
    st.title("🏹 Sniper v17.3 PRO")

    if st.button("📡 تحليل سهم"): go_to('analyze')
    if st.button("🔭 كشاف السوق"): go_to('scanner')
    if st.button("🚀 الاختراقات"): go_to('breakout')
    if st.button("💎 الفرص الذهب"): go_to('gold')

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
