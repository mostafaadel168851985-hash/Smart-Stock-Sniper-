import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="🤖 Sniper AI v20.3 Pro", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; font-weight: bold; }
    .entry-card { padding: 15px; border-radius: 12px; margin-bottom: 10px; border: 1px solid #30363d; text-align: center; }
    .support-entry { background: rgba(35, 134, 54, 0.1); border-left: 5px solid #3fb950; }
    .break-entry { background: rgba(31, 111, 235, 0.1); border-left: 5px solid #58a6ff; }
    .current-p { background: rgba(173, 186, 199, 0.1); border-left: 5px solid #adbac7; }
    .budget-box { background: #161b22; padding: 20px; border-radius: 15px; border: 1px solid #58a6ff; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# إدارة الميزانية والصفحات
if 'budget' not in st.session_state: st.session_state.budget = 20000.0
if 'page' not in st.session_state: st.session_state.page = 'home'
def go_to(p): st.session_state.page = p; st.rerun()

# ================== DYNAMIC DATA ENGINE ==================
@st.cache_data(ttl=60) # تحديث كل دقيقة لضمان اللحظية
def fetch_egx_live():
    url = "https://scanner.tradingview.com/egypt/scan"
    # طلب بيانات اللحظة (السعر الحالي، أعلى، أدنى، حجم التداول اللحظي)
    cols = ["name","close","RSI","volume","average_volume_10d_calc","high","low","change","description","SMA50"]
    payload = {"filter":[{"left":"volume","operation":"greater","right":10000}],"columns":cols,"range":[0,150]}
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except: return []

def analyze_stock(d_row):
    try:
        d = d_row['d']
        name,p,rsi,v,avg_v,h,l,chg,desc,sma50 = d
        # حساب Pivot Points لحظية بناءً على شمعة اليوم الحالية لضمان عدم الاعتماد على التاريخي فقط
        pp = (h + l + p) / 3
        r1, s1 = (2 * pp) - l, (2 * pp) - h
        r2, s2 = pp + (h - l), pp - (h - l)
        
        ratio = v / (avg_v or 1)
        is_chase = (p > r1 * 1.02) or (chg > 6 and rsi > 70)
        
        return {
            "name":name,"desc":desc,"p":p,"rsi":rsi,"chg":chg,"ratio":ratio,
            "r1":r1,"r2":r2,"s1":s1,"s2":s2,"pp":pp,"is_chase":is_chase
        }
    except: return None

# ================== UI RENDERER ==================
def render(an):
    # 1. كروت الدخول الذكية (اقتراحك)
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='entry-card support-entry'>🎯 دخول آمن (دعم)<br><b style='font-size:20px;'>{an['s1']:.2f}</b></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='entry-card break-entry'>🚀 دخول اختراق<br><b style='font-size:20px;'>{an['r1']:.2f}</b></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='entry-card current-p'>📊 السعر الحالي<br><b style='font-size:20px;'>{an['p']:.2f}</b></div>", unsafe_allow_html=True)

    if an['is_chase']:
        st.error("🚨 تنبيه مطاردة: السعر تضخم لحظياً، انتظر التهدئة.")

    # 2. إدارة ميزانية الصفقة المتغيرة
    st.markdown("---")
    st.subheader(f"💰 إدارة سيولة الصفقة (ميزانية: {st.session_state.budget:,.0f} ج)")
    
    # توزيع الميزانية آلياً (35% دخول، 35% اختراق، 30% تبريد)
    d1, d2, d3 = st.session_state.budget * 0.35, st.session_state.budget * 0.35, st.session_state.budget * 0.30
    
    col_b1, col_b2, col_b3 = st.columns(3)
    col_b1.metric("دفعة 1 (الآن)", f"{d1:,.0f} ج", f"{int(d1/an['p'])} سهم")
    col_b2.metric("دفعة 2 (اختراق)", f"{d2:,.0f} ج", f"{int(d2/an['r1'])} سهم")
    col_b3.metric("طوارئ (تبريد)", f"{d3:,.0f} ج", f"{int(d3/an['s2'])} سهم")

    # 3. الحاسبة المتطورة
    with st.expander("🧮 حاسبة المتوسط المستهدف (v12.7)"):
        cp1, cp2 = st.columns(2)
        old_p = cp1.number_input("سعرك القديم", value=float(an['p']), key=f"op_{an['name']}")
        old_q = cp2.number_input("كميتك الحالية", value=1000, key=f"oq_{an['name']}")
        target = st.number_input("المتوسط المطلوب؟", value=float(an['p']+0.1), key=f"tg_{an['name']}")
        
        if target > an['p'] and target < old_p:
            nq = (old_q * (old_p - target)) / (target - an['p'])
            st.success(f"✅ تحتاج شراء {int(nq):,} سهم بتكلفة {nq*an['p']:,.0f} ج")

# ================== MAIN INTERFACE ==================
st.sidebar.title("⚙️ الإعدادات العامة")
st.session_state.budget = st.sidebar.number_input("ميزانية الصفقة الواحدة (EGP)", value=20000, step=1000)

if st.session_state.page == 'home':
    st.title("🏹 Sniper AI v20.3 Pro")
    st.markdown(f"<div class='budget-box'>💳 الميزانية المعتمدة حالياً: <b>{st.session_state.budget:,.0f} جنيه</b> للمركز الواحد.</div>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    if c1.button("🔍 تحليل سهم"): go_to('analyze')
    if c2.button("🔭 كشاف السوق"): go_to('scanner')
    if c1.button("🚀 الاختراقات"): go_to('breakout')
    if c2.button("💎 قنص الذهب"): go_to('gold')

elif st.session_state.page == 'analyze':
    if st.button("🏠 الرئيسية"): go_to('home')
    q = st.text_input("ادخل الرمز (مثل: ATQA)").upper()
    if q:
        data = fetch_egx_live()
        stock = next((x for x in data if x['s'] == f"EGX:{q}"), None)
        if stock: render(analyze_stock(stock))
        else: st.warning("السهم غير موجود أو لا يوجد تداول عليه الآن.")

elif st.session_state.page in ['scanner', 'breakout', 'gold']:
    if st.button("🏠 الرئيسية"): go_to('home')
    data = fetch_egx_live()
    for r in data:
        an = analyze_stock(r)
        if not an: continue
        # فلترة ذكية لكل صفحة بناءً على البيانات اللحظية
        show = (st.session_state.page == 'scanner' and an['ratio'] > 1) or \
               (st.session_state.page == 'breakout' and an['p'] >= an['r1']*0.98) or \
               (st.session_state.page == 'gold' and an['rsi'] < 50 and an['ratio'] > 1.2)
        if show:
            with st.expander(f"📌 {an['name']} | السعر: {an['p']:.2f} | سيولة: {an['ratio']:.1f}x"):
                render(an)
