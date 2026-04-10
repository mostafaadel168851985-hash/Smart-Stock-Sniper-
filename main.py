import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="🤖 Sniper AI v21 Ultimate", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; font-weight: bold; height: 3.5em; }
    .metric-card { background: #161b22; padding: 15px; border-radius: 12px; border: 1px solid #30363d; text-align: center; }
    .signal-tag { padding: 5px 12px; border-radius: 20px; font-size: 14px; font-weight: bold; }
    .entry-box { background: rgba(35, 134, 54, 0.1); border: 1px solid #3fb950; padding: 10px; border-radius: 10px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'home'
def go_to(p): st.session_state.page = p; st.rerun()

# ================== DATA ENGINE ==================
@st.cache_data(ttl=300)
def fetch_egx_data(query_val=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    cols = ["name","close","RSI","volume","average_volume_10d_calc","high","low","change","description","SMA50","SMA200"]
    payload = {"filter":[{"left":"volume","operation":"greater","right":10000}],"columns":cols,"range":[0,150]}
    if not scan_all and query_val:
        payload["filter"].append({"left":"name","operation":"match","right":query_val.upper()})
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except: return []

# ================== ANALYSIS ENGINE (V21 SMART) ==================
def analyze_stock(d_row):
    try:
        d = d_row['d']
        name,p,rsi,v,avg_v,h,l,chg,desc,sma50,sma200 = d
        
        # Pivot Calculation
        pp = (h + l + p) / 3
        r1, s1 = (2 * pp) - l, (2 * pp) - h
        r2, s2 = pp + (h - l), pp - (h - l)
        ratio = v / (avg_v or 1)
        
        # Chase Logic
        is_chase = (p > r1 * 1.02) or (chg > 6 and rsi > 70)
        
        # Smart Scoring
        score = 0
        if p > (sma50 or 0): score += 20
        if ratio > 1.5: score += 25
        elif ratio > 1: score += 15
        if 40 <= rsi <= 62: score += 20  # توسيع النطاق قليلاً
        if p > r1: score += 15
        if is_chase: score -= 45 # تغليظ العقوبة
        
        score = max(min(score, 100), 0)
        
        # Signal Categorization
        if is_chase: signal = "🚨 مطاردة"
        elif p <= s1 * 1.01 and score >= 60: signal = "💎 صيد الثمين"
        elif p > r1 and ratio > 1.2: signal = "🚀 اختراق حقيقي"
        elif score >= 50: signal = "🟡 منطقة عمل"
        else: signal = "⚪ مراقبة"
        
        return {
            "name":name,"desc":desc,"p":p,"rsi":rsi,"chg":chg,"ratio":ratio,
            "r1":r1,"r2":r2,"s1":s1,"s2":s2,"pp":pp,"score":score,
            "signal":signal,"is_chase":is_chase,"is_gold": (rsi < 50 and ratio > 1.3)
        }
    except: return None

# ================== UI RENDERER ==================
def render(an):
    if an['is_chase']:
        st.error("🚨 تحذير: السعر متضخم جداً. مخاطرة الشراء هنا عالية.")
    
    # كروت الدخول الذكية
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='entry-box'>🎯 دخول دعم<br><b>{an['s1']:.2f}</b></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='entry-box' style='border-color:#58a6ff;'>🚀 دخول اختراق<br><b>{an['r1']:.2f}</b></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='entry-box' style='border-color:#adbac7;'>📊 السعر الحالي<br><b>{an['p']:.2f}</b></div>", unsafe_allow_html=True)
    
    st.divider()
    
    # الأهداف والحاسبة
    t1, t2, t3 = st.tabs(["🎯 الأهداف والسيولة", "🧮 حاسبة v12.7 (تعديل)", "📊 مؤشرات"])
    
    with t1:
        st.success(f"🎯 الأهداف: {an['r1']:.2f} ثم {an['r2']:.2f}")
        st.error(f"🛑 الوقف: {an['s2']:.2f}")
        budget = st.session_state.get('main_budget', 20000)
        st.info(f"توزيع ميزانية {budget:,}: {budget*0.4:,} شراء الآن | {budget*0.3:,} تعزيز | {budget*0.3:,} طوارئ")

    with t2:
        st.subheader("🛠️ مساعد تعديل المتوسط")
        col_p, col_q = st.columns(2)
        old_p = col_p.number_input("سعرك القديم", value=float(an['p']), key=f"op_{an['name']}")
        old_q = col_q.number_input("كميتك", value=1000, key=f"oq_{an['name']}")
        target = st.number_input("المتوسط المطلوب", value=float(an['p']+0.1), key=f"tg_{an['name']}")
        
        if target > an['p'] and target < old_p:
            nq = (old_q * (old_p - target)) / (target - an['p'])
            st.success(f"✅ اشترِ {int(nq):,} سهم بتكلفة {nq*an['p']:,.0f} ج")

    with t3:
        st.write(f"RSI: {an['rsi']:.1f} | السيولة: {an['ratio']:.2f}x")

# ================== PAGES ==================
st.sidebar.title("⚙️ المحفظة")
st.session_state.main_budget = st.sidebar.number_input("الميزانية (ج)", 20000, step=1000)

if st.session_state.page == 'home':
    st.title("🏹 Sniper AI v21 Ultimate")
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
    processed = [analyze_stock(r) for r in data if analyze_stock(r)]
    processed = sorted(processed, key=lambda x: x['score'], reverse=True)
    
    for an in processed:
        show = (st.session_state.page == 'scanner') or \
               (st.session_state.page == 'breakout' and "اختراق" in an['signal']) or \
               (st.session_state.page == 'gold' and an['is_gold'])
        if show:
            with st.expander(f"{an['name']} | {an['signal']} | Score: {an['score']}"):
                render(an)
