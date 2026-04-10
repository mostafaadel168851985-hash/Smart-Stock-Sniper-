import streamlit as st
import requests

# ================== CONFIG & MODERN STYLE ==================
st.set_page_config(page_title="🤖 Sniper AI v20.1", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 15px; height: 3.8em; font-weight: bold; border: 1px solid #30363d; }
    .metric-card { background: #161b22; padding: 20px; border-radius: 15px; border: 1px solid #30363d; text-align: center; }
    .entry-box { background: rgba(31, 111, 235, 0.1); border: 1px solid #58a6ff; padding: 15px; border-radius: 12px; text-align: center; }
    .chase-box { background: rgba(248, 81, 73, 0.15); border: 2px solid #f85149; padding: 15px; border-radius: 12px; text-align: center; }
    .avg-result { background: #1c2128; border-right: 5px solid #3fb950; padding: 15px; border-radius: 10px; margin-top: 10px; }
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
        
        is_chase = (p > r1 * 1.025) or (chg > 6 and rsi_val > 70)
        score = 0
        if not is_chase:
            if p > sma50: score += 30
            if ratio > 1.2: score += 20
            if 40 < rsi_val < 60: score += 20
        
        return {
            "name":name,"desc":desc,"p":p,"rsi":rsi_val,"chg":chg,"ratio":ratio,
            "t_score":max(min(score, 100), 0),"r1":r1,"r2":r2,"s1":s1,"s2":s2,"pp":pp,
            "is_chase": is_chase
        }
    except: return None

# ================== UI RENDERER ==================
def render(an):
    # تنبيه المطاردة
    if an['is_chase']:
        st.markdown(f"<div class='chase-box'>🚨 **تنبيه مطاردة:** السعر الحالي ({an['p']:.2f}) مرتفع جداً. انتظر تصحيح للمقومات.</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='entry-box'>✅ **نقطة دخول:** السعر الحالي {an['p']:.2f} مناسب للتمركز.</div>", unsafe_allow_html=True)

    st.write("")
    c_h1, c_h2 = st.columns([3, 1])
    c_h1.title(f"{an['name']} | {an['desc']}")
    c_h2.markdown(f"<div class='metric-card'>AI Score<br><b style='font-size:25px;'>{an['t_score']}%</b></div>", unsafe_allow_html=True)

    # مستويات الدعم والمقاومة التاريخية
    st.markdown("---")
    st.subheader("📊 المستويات الفنية (Historical Levels)")
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("دعم 2 (قوي)", f"{an['s2']:.2f}")
    sc2.metric("دعم 1", f"{an['s1']:.2f}")
    sc3.metric("مقاومة 1", f"{an['r1']:.2f}")
    sc4.metric("مقاومة 2", f"{an['r2']:.2f}")

    # التبويبات
    st.markdown("---")
    t1, t2, t3 = st.tabs(["🎯 خطة العمليات", "💰 ميزانية الـ 20 ألف", "🧮 حاسبة المتوسط الذكية"])
    
    with t1:
        st.success(f"🎯 الأهداف: هدف أول {an['r1']:.2f} | هدف ثانٍ {an['r2']:.2f}")
        st.error(f"🛑 الوقف: كسر مستوى {an['s1']:.2f}")
    
    with t2:
        st.write("تقسيم ميزانية 20,000 ج:")
        st.write(f"- 7000 ج عند سعر {an['p']:.2f}")
        st.write(f"- 7000 ج عند اختراق {an['r1']:.2f}")
        st.write(f"- 6000 ج سيولة طوارئ عند {an['s2']:.2f}")

    with t3:
        st.subheader("🛠️ حاسبة المتوسط المستهدف")
        cp1, cp2 = st.columns(2)
        old_p = cp1.number_input("سعرك القديم", value=float(an['p'] + 1.0), step=0.01, key=f"op_{an['name']}")
        old_q = cp2.number_input("كميتك الحالية", value=1000, step=10, key=f"oq_{an['name']}")
        
        target_avg = st.number_input("المتوسط الذي تريد الوصول إليه؟", value=float(an['p'] + 0.5), step=0.01, key=f"tg_{an['name']}")
        
        # --- منطق حساب المتوسط (The Fix) ---
        current_p = float(an['p'])
        
        if target_avg <= current_p:
            st.warning(f"⚠️ لا يمكن الوصول لمتوسط {target_avg} لأن السعر الحالي للسوق هو {current_p}. المتوسط يجب أن يكون دائماً أعلى من سعر الشراء الجديد.")
        elif target_avg >= old_p:
            st.info("سعر المتوسط المستهدف أعلى من سعرك الحالي بالفعل، لست بحاجة للتعديل.")
        else:
            # المعادلة: New_Qty = (Old_Qty * (Old_Price - Target)) / (Target - Current_Price)
            needed_q = (old_q * (old_p - target_avg)) / (target_avg - current_p)
            total_cost = needed_q * current_p
            
            st.markdown(f"""
            <div class='avg-result'>
            💡 <b>النتيجة:</b> لكي يصبح متوسطك <b>{target_avg:.2f}</b> ج:<br>
            ✅ يجب شراء: <b>{int(needed_q):,} سهم</b><br>
            💸 التكلفة المطلوبة: <b>{total_cost:,.0f} ج</b>
            </div>
            """, unsafe_allow_html=True)

# ================== PAGES ==================
if st.session_state.page == 'home':
    st.title("🏹 Sniper AI v20.1 Pro")
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
        else: st.error("لم يتم العثور على السهم.")

elif st.session_state.page in ['scanner', 'breakout', 'gold']:
    if st.button("🏠 الرئيسية"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        an = analyze_stock(r)
        if not an: continue
        show = (st.session_state.page == 'scanner' and an['t_score'] > 45) or \
               (st.session_state.page == 'breakout' and an['p'] > an['r1'] and not an['is_chase']) or \
               (st.session_state.page == 'gold' and an['ratio'] > 1.5)
        if show:
            with st.expander(f"📌 {an['name']} | Score: {an['t_score']}%"): render(an)
