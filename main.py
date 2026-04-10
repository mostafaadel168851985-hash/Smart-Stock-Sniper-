import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="🤖 Sniper AI v20.4 Pro", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; font-weight: bold; }
    .entry-card { padding: 15px; border-radius: 12px; margin-bottom: 10px; border: 1px solid #30363d; text-align: center; }
    .support-entry { background: rgba(35, 134, 54, 0.1); border-left: 5px solid #3fb950; }
    .break-entry { background: rgba(31, 111, 235, 0.1); border-left: 5px solid #58a6ff; }
    .current-p { background: rgba(173, 186, 199, 0.1); border-left: 5px solid #adbac7; }
    .chase-alert { background: rgba(248, 81, 73, 0.15); border: 2px solid #f85149; padding: 10px; border-radius: 10px; text-align: center; color: #f85149; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'home'
def go_to(p): st.session_state.page = p; st.rerun()

# ================== DATA ENGINE (OFF-MARKET READY) ==================
@st.cache_data(ttl=300)
def fetch_egx_data(query_val=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    # حذفنا فلتر "volume > 0" عشان الأسهم تظهر حتى والسوق مقفل بناءً على آخر إغلاق
    cols = ["name","close","RSI","volume","average_volume_10d_calc","high","low","change","description","SMA50"]
    payload = {"filter":[], "columns":cols, "range":[0,150]} # سحب أكبر عدد من الأسهم
    
    if not scan_all and query_val:
        payload["filter"].append({"left":"name","operation":"match","right":query_val.upper()})
    
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except: return []

def analyze_stock(d_row):
    try:
        d = d_row['d']
        name,p,rsi,v,avg_v,h,l,chg,desc,sma50 = d
        # Pivot Points بناءً على آخر بيانات مسجلة (سواء لحظية أو إغلاق سابق)
        pp = (h + l + p) / 3
        r1, s1 = (2 * pp) - l, (2 * pp) - h
        r2, s2 = pp + (h - l), pp - (h - l)
        ratio = v / (avg_v or 1)
        is_chase = (p > r1 * 1.025) or (chg > 7 and rsi > 70)
        
        return {
            "name":name,"desc":desc,"p":p,"rsi":rsi,"chg":chg,"ratio":ratio,
            "r1":r1,"r2":r2,"s1":s1,"s2":s2,"pp":pp, "is_chase":is_chase
        }
    except: return None

# ================== UI RENDERER ==================
def render(an):
    if an['is_chase']:
        st.markdown(f"<div class='chase-alert'>🚨 تنبيه مطاردة: السعر بعيد عن الدعم</div>", unsafe_allow_html=True)
    
    # كروت الدخول المقترحة
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='entry-card support-entry'>🎯 دخول آمن (دعم)<br><b style='font-size:18px;'>{an['s1']:.2f}</b></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='entry-card break-entry'>🚀 دخول اختراق<br><b style='font-size:18px;'>{an['r1']:.2f}</b></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='entry-card current-p'>📊 آخر سعر<br><b style='font-size:18px;'>{an['p']:.2f}</b></div>", unsafe_allow_html=True)

    st.markdown("---")
    t1, t2, t3 = st.tabs(["💰 إدارة السيولة", "🎯 الأهداف", "🧮 حاسبة المتوسط"])
    
    with t1:
        budget = st.session_state.get('main_budget', 20000)
        st.write(f"توزيع ميزانية **{budget:,.0f} ج** على السهم:")
        b1, b2, b3 = budget*0.35, budget*0.35, budget*0.30
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("دفعة 1 (دخول)", f"{b1:,.0f} ج", f"{int(b1/an['p'])} سهم")
        col_m2.metric("دفعة 2 (تعزيز)", f"{b2:,.0f} ج", f"{int(b2/an['r1'])} سهم")
        col_m3.metric("تبريد (طوارئ)", f"{b3:,.0f} ج", f"{int(b3/an['s2'])} سهم")

    with t2:
        st.success(f"الهدف الأول: {an['r1']:.2f} | الهدف الثاني: {an['r2']:.2f}")
        st.error(f"وقف الخسارة: كسر {an['s1']:.2f}")

    with t3:
        st.write("🛠️ الوصول لمتوسط مستهدف:")
        c_p, c_q = st.columns(2)
        old_p = c_p.number_input("سعر شراءك", value=float(an['p']+0.5), key=f"p_{an['name']}")
        old_q = c_q.number_input("كميتك", value=1000, key=f"q_{an['name']}")
        tg = st.number_input("المتوسط المطلوب", value=float(an['p']+0.2), key=f"t_{an['name']}")
        if tg > an['p'] and tg < old_p:
            nq = (old_q * (old_p - tg)) / (tg - an['p'])
            st.success(f"تحتاج شراء {int(nq):,} سهم بتكلفة {nq*an['p']:,.0f} ج")

# ================== MAIN ==================
st.sidebar.title("⚙️ الإعدادات")
st.session_state.main_budget = st.sidebar.number_input("الميزانية لكل سهم (ج)", 20000, step=1000)

if st.session_state.page == 'home':
    st.title("🏹 Sniper AI v20.4")
    st.info("البرنامج يعمل الآن بنظام 'خارج أوقات العمل' - يعرض بيانات آخر إغلاق.")
    c1, c2 = st.columns(2)
    if c1.button("🔍 تحليل سهم"): go_to('analyze')
    if c2.button("🔭 كشاف السوق"): go_to('scanner')
    if c1.button("🚀 الاختراقات"): go_to('breakout')
    if c2.button("💎 قنص الذهب"): go_to('gold')

elif st.session_state.page == 'analyze':
    if st.button("🏠"): go_to('home')
    q = st.text_input("رمز السهم").upper()
    if q:
        data = fetch_egx_data(query_val=q)
        if data: render(analyze_stock(data[0]))

elif st.session_state.page in ['scanner', 'breakout', 'gold']:
    if st.button("🏠"): go_to('home')
    data = fetch_egx_data(scan_all=True)
    for r in data:
        an = analyze_stock(r)
        if not an: continue
        show = (st.session_state.page == 'scanner' and an['ratio'] > 0.5) or \
               (st.session_state.page == 'breakout' and an['p'] >= an['r1']*0.97) or \
               (st.session_state.page == 'gold' and an['rsi'] < 55)
        if show:
            with st.expander(f"📌 {an['name']} | السعر: {an['p']:.2f}"): render(an)
