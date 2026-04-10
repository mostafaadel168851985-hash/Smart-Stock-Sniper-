import streamlit as st
import requests

# ================== CONFIG & MODERN STYLE ==================
st.set_page_config(page_title="🤖 Sniper AI v20 Final", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 15px; height: 3.8em; font-weight: bold; border: 1px solid #30363d; transition: 0.3s; }
    .stButton>button:hover { background: #238636; border-color: #3fb950; }
    .metric-card { background: #161b22; padding: 20px; border-radius: 15px; border: 1px solid #30363d; text-align: center; }
    .entry-box { background: rgba(31, 111, 235, 0.1); border: 1px solid #58a6ff; padding: 15px; border-radius: 12px; text-align: center; }
    .chase-box { background: rgba(248, 81, 73, 0.15); border: 2px solid #f85149; padding: 15px; border-radius: 12px; text-align: center; animation: blinker 1.5s linear infinite; }
    @keyframes blinker { 50% { opacity: 0.6; } }
    .trend-pill { padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 14px; }
    .up-pill { background: #238636; color: white; }
    .down-pill { background: #da3633; color: white; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'home'
def go_to(p): st.session_state.page = p; st.rerun()

# ================== DATA ENGINE ==================
@st.cache_data(ttl=300)
def fetch_egx_data(query_val=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    cols = ["name","close","RSI","volume","average_volume_10d_calc","high","low","change","description","SMA50","SMA200"]
    payload = {"filter":[{"left":"volume","operation":"greater","right":30000}],"columns":cols,"range":[0,100]}
    if not scan_all and query_val:
        payload["filter"].append({"left":"name","operation":"match","right":query_val.upper()})
    try:
        r = requests.post(url,json=payload,timeout=10).json()
        return r.get("data", [])
    except: return []

# ================== AI CORE LOGIC ==================
def analyze_stock(d_row):
    try:
        d = d_row['d']
        name,p,rsi,v,avg_v,h,l,chg,desc,sma50,sma200 = d
        pp = (h+l+p)/3
        r1,s1,r2,s2 = (2*pp)-l,(2*pp)-h, pp+(h-l),pp-(h-l)
        ratio, rsi_val = v/(avg_v or 1), rsi or 0

        # سعر الدخول المقترح (بناء على قرب السعر من الدعم أو الارتكاز)
        entry_price = p if p <= r1 else s1
        
        # الاتجاهات
        t_short = "صاعد" if p > pp else "هابط"
        t_med = "صاعد" if sma50 and p > sma50 else "هابط"
        t_long = "صاعد" if sma200 and p > sma200 else "هابط"

        # AI Scoring & Chase Detection
        is_chase = (p > r1 * 1.025) or (chg > 6 and rsi_val > 70)
        score = 0
        if not is_chase:
            if t_med == "صاعد": score += 30
            if ratio > 1.2: score += 20
            if 40 < rsi_val < 60: score += 20
            if p > pp: score += 10
        
        return {
            "name":name,"desc":desc,"p":p,"rsi":rsi_val,"chg":chg,"ratio":ratio,
            "t_score":max(min(score, 100), 0),"r1":r1,"r2":r2,"s1":s1,"s2":s2,"pp":pp,
            "t_short":t_short,"t_med":t_med,"t_long":t_long,
            "entry_price": entry_price, "is_chase": is_chase
        }
    except: return None

# ================== UI RENDERER ==================
def render(an):
    # 1. تنبيه المطاردة الاحترافي
    if an['is_chase']:
        st.markdown(f"<div class='chase-box'>🚨 **تنبيه مطاردة خطرة:** السعر الحالي ({an['p']:.2f}) مرتفع جداً عن منطقة الدخول الآمنة. فكر في جني الأرباح أو الانتظار.</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='entry-box'>✅ **منطقة دخول آمنة:** السعر الحالي مناسب للمناورة. سعر الدخول المقترح: {an['entry_price']:.2f}</div>", unsafe_allow_html=True)

    st.write("")
    
    # رأس الصفحة
    c_h1, c_h2 = st.columns([3, 1])
    with c_h1:
        st.title(f"{an['name']} | {an['desc']}")
    with c_h2:
        color = "#3fb950" if an['t_score'] > 60 else "#d29922" if an['t_score'] > 40 else "#f85149"
        st.markdown(f"<div class='metric-card' style='border-color:{color}; padding:10px;'><small>AI Score</small><br><b style='color:{color}; font-size:25px;'>{an['t_score']}%</b></div>", unsafe_allow_html=True)

    # الاتجاهات بشكل Pills
    st.markdown("---")
    cols = st.columns(4)
    labels = ["قصير", "متوسط", "طويل"]
    vals = [an['t_short'], an['t_med'], an['t_long']]
    for col, l, v in zip(cols, labels, vals):
        cls = "up-pill" if v == "صاعد" else "down-pill"
        col.markdown(f"**{l}:** <span class='trend-pill {cls}'>{v}</span>", unsafe_allow_html=True)
    
    vol_icon = "🔥" if an['ratio'] > 1.5 else "🟢"
    cols[3].markdown(f"**السيولة:** {vol_icon} {an['ratio']:.1f}x")

    # مستويات الدعم والمقاومة
    st.markdown("---")
    st.subheader("📊 مستويات المناورة الفنية")
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("دعم 2 (تبريد)", f"{an['s2']:.2f}")
    sc2.metric("دعم 1 (دخول)", f"{an['s1']:.2f}")
    sc3.metric("مقاومة 1 (هدف)", f"{an['r1']:.2f}")
    sc4.metric("مقاومة 2 (انطلاق)", f"{an['r2']:.2f}")

    # التبويبات المتطورة
    st.markdown("---")
    t1, t2, t3 = st.tabs(["🎯 خطة العمليات", "💰 إدارة المحفظة", "🧮 حاسبة المتوسط الذكية"])
    
    with t1:
        st.info(f"🚩 **نقطة الدخول المثالية:** {an['entry_price']:.2f}")
        cc1, cc2 = st.columns(2)
        cc1.success(f"🎯 هدف أول: {an['r1']:.2f} | هدف ثانٍ: {an['r2']:.2f}")
        cc2.error(f"🛑 وقف الخسارة الصارم: {an['s1']:.2f}")
    
    with t2:
        st.write("💵 **تقسيم السيولة (ميزانية 20,000 ج):**")
        st.markdown(f"""
        1. **7000 ج:** شراء عند {an['p']:.2f} (المركز الأول).
        2. **7000 ج:** تعزيز عند تأكيد اختراق {an['r1']:.2f}.
        3. **6000 ج:** سيولة احتياطية للتبريد عند {an['s2']:.2f}.
        """)

    with t3:
        st.subheader("🛠️ حاسبة المتوسط الموجه (v12.7 + AI)")
        c_p, c_q = st.columns(2)
        old_p = c_p.number_input("سعرك القديم", value=float(an['p']), key=f"p_{an['name']}")
        old_q = c_q.number_input("كميتك الحالية", value=1000, key=f"q_{an['name']}")
        
        st.divider()
        st.markdown("#### 🎯 الوصول لمتوسط مستهدف (يدوي)")
        target_avg = st.number_input("ما هو السعر المتوسط الذي تطمح للوصول إليه؟", value=float(an['p'] + 0.1), step=0.01)
        
        if target_avg <= an['p'] and old_p > an['p']:
            st.warning("السعر المستهدف قريب جداً من السعر الحالي، الحساب قد يتطلب كميات ضخمة.")
        
        # معادلة حساب الكمية المطلوبة للوصول لمتوسط معين:
        # (old_p * old_q + p * new_q) / (old_q + new_q) = target_avg
        try:
            needed_q = (old_q * (old_p - target_avg)) / (target_avg - an['p'])
            if needed_q > 0:
                cost = needed_q * an['p']
                st.success(f"للوصول لمتوسط **{target_avg:.2f}**: تحتاج شراء **{int(needed_q):,} سهم** بتكلفة تقريبية **{cost:,.0f} ج**")
            else:
                st.info("سعر المتوسط المستهدف أعلى من سعرك الحالي بالفعل!")
        except ZeroDivisionError:
            st.write("ادخل سعر مستهدف مختلف عن السعر الحالي.")

# ================== PAGES ==================
if st.session_state.page == 'home':
    st.title("🏹 Sniper AI v20 Final")
    c1, c2 = st.columns(2)
    if c1.button("🏠 الرئيسية"): go_to('home')
    if c1.button("🔍 تحليل سهم"): go_to('analyze')
    if c2.button("🔭 كشاف السوق"): go_to('scanner')
    if c1.button("🚀 الاختراقات"): go_to('breakout')
    if c2.button("💎 قنص الذهب"): go_to('gold')

elif st.session_state.page == 'analyze':
    if st.button("🔙 عودة"): go_to('home')
    q = st.text_input("ادخل الرمز").upper()
    if q:
        data = fetch_egx_data(query_val=q)
        if data: render(analyze_stock(data[0]))

elif st.session_state.page in ['scanner', 'breakout', 'gold']:
    if st.button("🏠 الرئيسية"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        an = analyze_stock(r)
        if not an: continue
        show = (st.session_state.page == 'scanner' and an['t_score'] > 45) or \
               (st.session_state.page == 'breakout' and an['p'] > an['r1'] and not an['is_chase']) or \
               (st.session_state.page == 'gold' and an['ratio'] > 1.5 and an['rsi'] < 60)
        if show:
            with st.expander(f"📌 {an['name']} | AI: {an['t_score']}%"): render(an)
