import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="🤖 Sniper AI v19.7 Final", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; font-weight: bold; height: 3.5em; border: 1px solid #30363d; }
    .trend-box { padding: 10px; border-radius: 10px; text-align: center; font-weight: bold; border: 1px solid #30363d; }
    .up { background-color: rgba(35, 134, 54, 0.2); color: #3fb950; border-color: #238636; }
    .down { background-color: rgba(248, 81, 73, 0.2); color: #f85149; border-color: #da3633; }
    .avg-card { background: #161b22; padding: 12px; border-radius: 10px; border-right: 5px solid #58a6ff; margin-bottom: 8px; }
    .pivot-val { font-size: 18px; font-weight: bold; color: #adbac7; }
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

        # الاتجاهات
        t_short = "صاعد" if p > pp else "هابط"
        t_med = "صاعد" if sma50 and p > sma50 else "هابط"
        t_long = "صاعد" if sma200 and p > sma200 else "هابط"

        # نظام الـ Score
        score = 0
        if t_short == "صاعد": score += 10
        if t_med == "صاعد": score += 20
        if t_long == "صاعد": score += 10
        if ratio > 1.3: score += 20
        if 45 < rsi_val < 62: score += 20
        
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
    if an['is_chase']: st.error("🚫 **تحذير مطاردة:** السهم تضخم جداً، المخاطرة عالية هنا.")
    
    # الهيدر ونظام الثقة
    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown(f"## {an['name']} | <small>{an['desc']}</small>", unsafe_allow_html=True)
    with c2:
        color = "#3fb950" if an['t_score'] > 70 else "#d29922" if an['t_score'] > 40 else "#f85149"
        st.markdown(f"<div style='border:2px solid {color}; border-radius:15px; text-align:center; padding:5px;'><small>AI Confidence</small><br><b style='color:{color}; font-size:20px;'>{an['t_score']}%</b></div>", unsafe_allow_html=True)

    # الاتجاهات والسيولة
    st.markdown("---")
    cols = st.columns(4)
    for col, lab, val in zip(cols[:3], ["قصير", "متوسط", "طويل"], [an['t_short'], an['t_med'], an['t_long']]):
        cls = "up" if val == "صاعد" else "down"
        col.markdown(f"<div class='trend-box {cls}'>{lab}: {val}</div>", unsafe_allow_html=True)
    
    vol_icon = "🔥" if an['ratio'] > 1.5 else "🟢" if an['ratio'] > 0.8 else "⚪"
    cols[3].markdown(f"<div class='trend-box'>سيولة: {vol_icon} {an['ratio']:.1f}x</div>", unsafe_allow_html=True)

    # الدعوم والمقاومات التاريخية (S1, S2, R1, R2)
    st.markdown("---")
    st.subheader("📊 مستويات الدعم والمقاومة التاريخية")
    p_cols = st.columns(4)
    p_cols[0].metric("دعم 2 (قوي)", f"{an['s2']:.2f}")
    p_cols[1].metric("دعم 1", f"{an['s1']:.2f}")
    p_cols[2].metric("مقاومة 1", f"{an['r1']:.2f}")
    p_cols[3].metric("مقاومة 2 (هدف)", f"{an['r2']:.2f}")

    # التبويبات للأدوات المساعدة
    st.markdown("---")
    t1, t2, t3 = st.tabs(["🎯 خطة الصفقات", "💰 ميزانية الـ 20 ألف", "🧮 مساعد التعديل v12.7"])
    
    with t1:
        cc1, cc2 = st.columns(2)
        cc1.info(f"**مضارب سريـع:** هدف {an['r1']:.2f} | وقف {an['s1']:.2f}")
        cc2.success(f"**مستثمر سوينج:** هدف {an['r2']:.2f} | دعم {an['s2']:.2f}")
    
    with t2:
        st.write(f"💵 تقسيم السيولة المقترح للسهم:")
        st.markdown(f"""
        - 🟢 **7000 ج:** شراء الآن (سعر {an['p']:.2f})
        - 🚀 **7000 ج:** اختراق المقاومة {an['r1']:.2f}
        - 🛑 **6000 ج:** تبريد عند الدعم {an['s2']:.2f}
        """)

    with t3:
        st.subheader("🛠️ مساعد v12.7 لتقليل متوسط التكلفة")
        c_p, c_q = st.columns(2)
        old_p = c_p.number_input("سعرك القديم", value=float(an['p']), key=f"p_{an['name']}")
        old_q = c_q.number_input("كميتك الحالية", value=1000, key=f"q_{an['name']}")
        
        st.write("---")
        for lbl, mult in [("تعديل حذر (0.5x)", 0.5), ("تعديل متوازن (1:1)", 1.0), ("تعديل هجومي (2x)", 2.0)]:
            nq = int(old_q * mult)
            avg = ((old_p * old_q) + (an['p'] * nq)) / (old_q + nq)
            st.markdown(f"<div class='avg-card'>شراء {nq:,} سهم ({lbl}) ⬅️ المتوسط الجديد: <b style='color:#3fb950'>{avg:.3f} ج</b></div>", unsafe_allow_html=True)

# ================== PAGES ==================
if st.session_state.page == 'home':
    st.title("🏹 Sniper AI v19.7 Final")
    with st.expander("💡 ما هو الـ AI Confidence؟"):
        st.write("هو تقييم رقمي يجمع بين (قوة الترند + حجم السيولة + مؤشر RSI + المسافة عن المقاومة). كلما زاد عن 70% زادت احتمالية نجاح الصفقة.")
    
    c1, c2 = st.columns(2)
    if c1.button("🔍 تحليل سهم"): go_to('analyze')
    if c2.button("🔭 كشاف السوق"): go_to('scanner')
    if c1.button("🚀 الاختراقات"): go_to('breakout')
    if c2.button("💎 قنص الذهب"): go_to('gold')

elif st.session_state.page == 'analyze':
    if st.button("🏠 الرئيسية"): go_to('home')
    q = st.text_input("ادخل الرمز").upper()
    if q:
        data = fetch_egx_data(query_val=q)
        if data: render(analyze_stock(data[0]))

elif st.session_state.page in ['scanner', 'breakout', 'gold']:
    if st.button("🏠 الرئيسية"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        an = analyze_stock(r)
        if not an: continue
        show = (st.session_state.page == 'scanner' and an['t_score'] > 50) or \
               (st.session_state.page == 'breakout' and an['is_break'] and not an['is_chase']) or \
               (st.session_state.page == 'gold' and an['is_gold'])
        if show:
            with st.expander(f"📌 {an['name']} | AI: {an['t_score']}%"): render(an)
