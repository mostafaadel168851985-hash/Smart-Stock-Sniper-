import streamlit as st
import requests

# ================== CONFIG & MODERN STYLE ==================
st.set_page_config(page_title="🤖 Sniper AI v19.5", layout="wide")

st.markdown("""
    <style>
    /* أزرار مودرن */
    .stButton>button { 
        width: 100%; border-radius: 15px; height: 4em; 
        font-weight: bold !important; border: 1px solid #30363d;
        transition: all 0.3s ease;
    }
    .stButton>button:hover { background-color: #238636; border-color: #3fb950; }
    
    /* كروت الاتجاه */
    .trend-card { padding: 12px; border-radius: 12px; text-align: center; font-weight: bold; border: 1px solid #30363d; }
    .up { background-color: rgba(35, 134, 54, 0.2); color: #3fb950; border-color: #238636; }
    .down { background-color: rgba(248, 81, 73, 0.2); color: #f85149; border-color: #da3633; }
    
    /* كروت السيولة والحاسبة */
    .metric-box { background: #161b22; padding: 15px; border-radius: 15px; border-right: 5px solid #58a6ff; margin-bottom: 10px; }
    .confidence-ring { text-align: center; border: 3px solid #3fb950; border-radius: 50%; width: 80px; height: 80px; line-height: 80px; margin: auto; font-size: 20px; font-weight: bold; }
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
        return r.get("data",[])
    except: return []

# ================== AI CORE LOGIC ==================
def analyze_stock(d_row):
    try:
        d = d_row['d']
        name,p,rsi,v,avg_v,h,l,chg,desc,sma50,sma200 = d
        pp = (h+l+p)/3
        r1,s1,r2,s2 = (2*pp)-l,(2*pp)-h, pp+(h-l),pp-(h-l)
        ratio, rsi_val = v/(avg_v or 1), rsi or 0

        # الاتجاهات
        t_short = "صاعد" if p > pp else "هابط"
        t_med = "صاعد" if sma50 and p > sma50 else "هابط"
        t_long = "صاعد" if sma200 and p > sma200 else "هابط"

        # AI Scoring System
        score = 0
        if t_short == "صاعد": score += 10
        if t_med == "صاعد": score += 20
        if t_long == "صاعد": score += 10
        if ratio > 1.5: score += 20
        elif ratio > 0.8: score += 10
        if 45 < rsi_val < 60: score += 20
        
        is_gold = (ratio > 1.5 and 45 < rsi_val < 60 and t_med == "صاعد")
        is_break = (p > r1 and ratio > 1.1 and t_med == "صاعد")
        is_chase = ((p > r1*1.02 and rsi_val > 70) or (chg > 7 and ratio > 2))
        
        if is_break: score += 10
        if is_gold: score += 10
        if is_chase: score -= 40

        return {
            "name":name,"desc":desc,"p":p,"rsi":rsi_val,"chg":chg,"ratio":ratio,
            "t_score":max(min(score, 100), 0),"r1":r1,"r2":r2,"s1":s1,"s2":s2,"pp":pp,
            "t_short":t_short,"t_med":t_med,"t_long":t_long,
            "is_gold":is_gold,"is_break":is_break,"is_chase":is_chase
        }
    except: return None

# ================== UI RENDERER ==================
def render(an):
    if an['is_chase']: st.error("🚫 **تحذير مطاردة:** السهم متضخم سعرياً، انتظر التهدئة.")
    
    # رأس الصفحة
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        st.markdown(f"## {an['name']} | <small>{an['desc']}</small>", unsafe_allow_html=True)
    with c2:
        vol_icon = "🔥" if an['ratio'] > 1.5 else "🟢" if an['ratio'] > 0.8 else "⚪"
        st.markdown(f"**السيولة:** {vol_icon} {an['ratio']:.1f}x")
    with c3:
        color = "#3fb950" if an['t_score'] > 70 else "#d29922" if an['t_score'] > 40 else "#f85149"
        st.markdown(f"<div style='color:{color}; font-weight:bold; font-size:22px; text-align:right;'>AI Score: {an['t_score']}%</div>", unsafe_allow_html=True)

    # الاتجاهات الملونة
    st.markdown("---")
    cols = st.columns(3)
    for col, lab, val in zip(cols, ["المدى القصير", "المدى المتوسط", "المدى الطويل"], [an['t_short'], an['t_med'], an['t_long']]):
        cls = "up" if val == "صاعد" else "down"
        col.markdown(f"<div class='trend-card {cls}'>{lab}<br>{val}</div>", unsafe_allow_html=True)

    # الأهداف وخطة الـ 20 ألف
    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["🎯 خطة التداول", "💰 إدارة السيولة", "🧮 حاسبة المتوسط"])
    
    with tab1:
        cc1, cc2 = st.columns(2)
        cc1.info(f"**المضارب:** دخول {an['p']:.2f} | هدف {an['r1']:.2f} | وقف {an['s1']:.2f}")
        cc2.success(f"**السوينج:** دخول {an['p']:.2f} | هدف {an['r2']:.2f} | دعم {an['s2']:.2f}")
    
    with tab2:
        st.write("📊 تقسيم محفظة الـ 20,000 ج لهذا السهم:")
        st.markdown(f"""
        - 🟢 **7000 ج:** شراء الآن عند {an['p']:.2f}
        - 🚀 **7000 ج:** تعزيز عند اختراق {an['r1']:.2f}
        - 🛑 **6000 ج:** سيولة طوارئ عند الدعم التاريخي {an['s2']:.2f}
        """)

    with tab3:
        st.write("🛠️ **مساعد v12.7 للتعديل:**")
        old_p = st.number_input("سعر الشراء القديم", value=float(an['p']), key=f"p_{an['name']}")
        old_q = st.number_input("الكمية الحالية", value=1000, key=f"q_{an['name']}")
        for lbl, m in [("تعديل 1:1", 1.0), ("تعديل 2:1", 2.0)]:
            nq = int(old_q * m)
            avg = ((old_p * old_q) + (an['p'] * nq)) / (old_q + nq)
            st.markdown(f"<div class='metric-box'>شراء {nq:,} سهم ⬅️ المتوسط الجديد: {avg:.3f} ج</div>", unsafe_allow_html=True)

# ================== PAGES ==================
if st.session_state.page == 'home':
    st.title("🤖 Sniper AI v19.5")
    c1, c2 = st.columns(2)
    if c1.button("🔍 تحليل سهم محدد"): go_to('analyze')
    if c2.button("📡 كشاف السوق العام"): go_to('scanner')
    if c1.button("🚀 صفقات الاختراق"): go_to('breakout')
    if c2.button("💎 فرص الذهب"): go_to('gold')

elif st.session_state.page == 'analyze':
    if st.button("🏠 عودة للرئيسية"): go_to('home')
    q = st.text_input("ادخل الرمز").upper()
    if q:
        data = fetch_egx_data(query_val=q)
        if data: render(analyze_stock(data[0]))

elif st.session_state.page in ['scanner', 'breakout', 'gold']:
    if st.button("🏠 عودة للرئيسية"): go_to('home')
    page = st.session_state.page
    for r in fetch_egx_data(scan_all=True):
        an = analyze_stock(r)
        if not an: continue
        show = False
        if page == 'scanner' and an['t_score'] > 50: show = True
        if page == 'breakout' and an['is_break'] and not an['is_chase']: show = True
        if page == 'gold' and an['is_gold']: show = True
        
        if show:
            with st.expander(f"📌 {an['name']} | AI: {an['t_score']}%"): render(an)
