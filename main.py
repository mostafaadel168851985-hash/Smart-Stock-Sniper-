import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="🤖 Sniper AI v19.1 Pro", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; font-weight: bold; height: 3em; }
    .trend-box { padding: 10px; border-radius: 10px; text-align: center; font-weight: bold; font-size: 14px; border: 1px solid #30363d; }
    .avg-card { background-color: #1c2128; border-right: 5px solid #58a6ff; padding: 12px; border-radius: 8px; margin-bottom: 8px; }
    .status-tag { padding: 5px 12px; border-radius: 20px; font-weight: bold; font-size: 16px; }
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

# ================== AI ANALYSIS ENGINE ==================
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

        # نظام الـ Score (AI Logic)
        score = 0
        if t_short == "صاعد": score += 10
        if t_med == "صاعد": score += 20
        if t_long == "صاعد": score += 10
        if ratio > 1.5: score += 20
        elif ratio > 1.0: score += 10
        if 45 < rsi_val < 60: score += 15
        elif rsi_val < 70: score += 8
        
        # إشارات خاصة
        is_gold = (ratio > 1.5 and 45 < rsi_val < 60 and t_med == "صاعد")
        is_break = (p > r1 and ratio > 1.2 and t_med == "صاعد")
        is_chase = ((p > r1*1.02 and rsi_val > 70) or (chg > 7 and ratio > 2))
        
        if is_break: score += 15
        if is_gold: score += 10
        if is_chase: score -= 40 # خصم المطاردة

        confidence = max(min(score, 100), 0)
        rr = (r1 - p) / (p - s1) if (p - s1) != 0 else 0

        return {
            "name":name,"desc":desc,"p":p,"rsi":rsi_val,"chg":chg,"ratio":ratio,
            "t_score":confidence,"r1":r1,"r2":r2,"s1":s1,"s2":s2,"pp":pp,
            "t_short":t_short,"t_med":t_med,"t_long":t_long,
            "is_gold":is_gold,"is_break":is_break,"is_chase":is_chase,"rr":rr
        }
    except: return None

# ================== UI RENDERER ==================
def render(an):
    # 1. تنبيه المطاردة (بشكل أوضح)
    if an['is_chase']:
        st.error("🚨 تحذير مطاردة: السعر تضخم جداً! انتظر التصحيح قرب مستويات الدعم.")
    
    # 2. الهيدر ونسبة الثقة
    c_head1, c_head2 = st.columns([2, 1])
    with c_head1:
        st.markdown(f"## {an['name']} | {an['desc']}")
    with c_head2:
        conf_color = "#3fb950" if an['t_score'] > 70 else "#d29922" if an['t_score'] > 50 else "#f85149"
        st.markdown(f"<div style='text-align:center; border:2px solid {conf_color}; border-radius:15px; padding:5px;'>AI Confidence<br><span style='font-size:24px; color:{conf_color}; font-weight:bold;'>{an['t_score']}%</span></div>", unsafe_allow_html=True)

    # 3. لوحة الاتجاهات الملونة (إضافة مفقودة)
    st.markdown("### 📊 حالة الاتجاه والسيولة")
    c_tr = st.columns(4)
    for col, lab, val in zip(c_tr[:3], ["قصير", "متوسط", "طويل"], [an['t_short'], an['t_med'], an['t_long']]):
        color = "#238636" if val == "صاعد" else "#da3633"
        col.markdown(f"<div class='trend-box' style='background:{color}; color:white;'>{lab}: {val}</div>", unsafe_allow_html=True)
    c_tr[3].markdown(f"<div class='trend-box'>زخم السيولة: {an['ratio']:.1f}x</div>", unsafe_allow_html=True)

    st.divider()

    # 4. الأهداف وإدارة الـ 20 ألف ج
    col_aim, col_money = st.columns(2)
    with col_aim:
        st.subheader("🎯 أهداف التداول")
        st.info(f"**المضارب:** هدف {an['r1']:.2f} | وقف {an['s1']:.2f} (R/R: {an['rr']:.2f})")
        st.success(f"**السوينج:** هدف كبير {an['r2']:.2f} | دعم رئيسي {an['s2']:.2f}")
    
    with col_money:
        st.subheader("💰 خطة السيولة (ميزانية 20,000 ج)")
        st.write(f"🔹 **7000 ج** عند سعر الشراء الحالي {an['p']:.2f}")
        st.write(f"🚀 **7000 ج** في حالة اختراق {an['r1']:.2f}")
        st.write(f"🛑 **6000 ج** سيولة طوارئ عند دعم {an['s2']:.2f}")

    st.divider()

    # 5. حاسبة المتوسط المساعدة (v12.7 Style - إضافة مفقودة)
    st.subheader("🧮 مساعد تعديل التكلفة (v12.7 Pro)")
    with st.expander("اضغط لحساب سيناريوهات التعديل المقترحة", expanded=True):
        c_c1, c_c2 = st.columns(2)
        old_p = c_c1.number_input("سعر شراءك القديم", value=float(an['p']), key=f"op_{an['name']}")
        old_q = c_c2.number_input("كميتك الحالية (سهم)", value=1000, key=f"oq_{an['name']}")
        
        st.markdown("---")
        for label, mult in [("تعديل بسيط (0.5x)", 0.5), ("تعديل متوازن (1:1)", 1.0), ("تعديل هجومي (2x)", 2.0)]:
            nq = int(old_q * mult)
            avg = ((old_p * old_q) + (an['p'] * nq)) / (old_q + nq)
            st.markdown(f"<div class='avg-card'>شراء {nq:,} سهم ({label}) ⬅️ المتوسط الجديد سيكون: <span style='color:#3fb950; font-weight:bold;'>{avg:.3f} ج</span></div>", unsafe_allow_html=True)

# ================== PAGES ==================
if st.session_state.page == 'home':
    st.title("🤖 Sniper AI v19.1 Pro")
    st.info("نظام تداول ذكي يجمع بين التحليل الفني الكلاسيكي ومنطق النقاط (Score System).")
    c1, c2 = st.columns(2)
    if c1.button("📡 تحليل سهم محدد"): go_to('analyze')
    if c2.button("🔥 أفضل فرص السوق (AI)"): go_to('top')

elif st.session_state.page == 'analyze':
    if st.button("⬅️ عودة"): go_to('home')
    q = st.text_input("ادخل رمز السهم (مثال: ATQA)").upper()
    if q:
        data = fetch_egx_data(query_val=q)
        if data: render(analyze_stock(data[0]))
        else: st.warning("السهم غير موجود أو لا توجد سيولة كافية.")

elif st.session_state.page == 'top':
    if st.button("⬅️ عودة"): go_to('home')
    stocks = []
    with st.spinner("جاري تحليل أقوى 100 سهم في البورصة..."):
        for r in fetch_egx_data(scan_all=True):
            an = analyze_stock(r)
            if an and not an['is_chase'] and an['t_score'] > 50:
                stocks.append(an)
    
    top = sorted(stocks, key=lambda x: x['t_score'], reverse=True)[:10]
    if top:
        for an in top:
            with st.expander(f"🔥 {an['name']} | Confidence: {an['t_score']}% | Price: {an['p']} ج"):
                render(an)
    else: st.info("لا توجد فرص قوية حالياً تحقق شروط الـ AI.")
