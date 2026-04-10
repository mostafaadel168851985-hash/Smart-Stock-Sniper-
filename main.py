import streamlit as st
import requests

# ================== CONFIG & STYLE (V17.5 PRO) ==================
st.set_page_config(page_title="EGX Sniper v17.5 Pro", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; font-weight: bold !important; font-size: 16px !important; }
    .status-badge { padding: 4px 10px; border-radius: 8px; font-weight: bold; }
    .status-chase { background-color: #f85149; color: white; }
    .status-break { background-color: #238636; color: white; }
    .status-gold { background-color: #ffd700; color: black; }
    .status-buy { background-color: #1f6feb; color: white; }
    .status-wait { background-color: #8b949e; color: white; }
    
    /* Trends Styling */
    .trend-box { padding: 8px; border-radius: 8px; text-align: center; font-weight: bold; font-size: 13px; border: 1px solid #30363d; }
    .trend-up { background-color: #238636; color: white; }
    .trend-down { background-color: #da3633; color: white; }
    
    .target-box { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-bottom: 10px; }
    .price-callout { font-weight: bold; color: #3fb950; font-size: 18px; }
    .stoploss-callout { font-weight: bold; color: #f85149; font-size: 18px; }
    
    /* Avg Calculator Styling (v12.7 style) */
    .avg-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 10px; padding: 15px; margin-bottom: 10px; border-right: 5px solid #58a6ff; }
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

# ================== ANALYSIS ENGINE ==================
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

        # إشارات محسنة
        is_gold = (ratio > 1.5 and 45 < rsi_val < 60 and t_med == "صاعد")
        is_break = (p >= h*0.995 and ratio > 1.2 and rsi_val > 50 and t_med == "صاعد")
        is_chase = ((p > r1*1.03 and rsi_val > 70) or (chg > 7 and ratio > 2))

        # اختيار الحالة واللون
        if is_chase: status, s_cls = "⚠️ مطاردة", "status-chase"
        elif is_break: status, s_cls = "🚀 اختراق", "status-break"
        elif is_gold: status, s_cls = "💎 ذهب", "status-gold"
        elif rsi_val < 45: status, s_cls = "🟢 تجميع", "status-buy"
        else: status, s_cls = "🟡 انتظار", "status-wait"

        t_score = int(85 if 40<rsi_val<60 else 60 if rsi_val < 70 else 35)
        if t_med=="هابط": t_score -= 15

        return {
            "name":name,"desc":desc,"p":p,"rsi":rsi_val,"chg":chg,"ratio":ratio,
            "t_score":t_score,"status":status, "s_cls": s_cls,
            "r1":r1,"r2":r2,"s1":s1,"s2":s2,"pp":pp,
            "t_short":t_short,"t_med":t_med,"t_long":t_long,
            "vol_txt": "🔥 قوي" if ratio>1.5 else "⚪ متوسط",
            "is_gold":is_gold,"is_break":is_break,"is_chase":is_chase
        }
    except: return None

# ================== UI RENDERER ==================
def render(an):
    if an['is_chase']: st.error(f"🚨 تحذير مطاردة: السعر حالياً ({an['p']:.2f}) بعيد جداً عن نقطة الارتكاز ({an['pp']:.2f})")

    st.markdown(f"## {an['name']} | <span class='status-badge {an['s_cls']}'>{an['status']}</span> | Score: {an['t_score']}", unsafe_allow_html=True)
    st.caption(an['desc'])
    
    # 1. لوحة الاتجاهات الملونة (تعديلك)
    st.markdown("### 📊 لوحة الاتجاهات والسيولة")
    c_inf = st.columns(4)
    for col, lab, val in zip(c_inf[:3], ["قصير", "متوسط", "طويل"], [an['t_short'], an['t_med'], an['t_long']]):
        cls = "trend-up" if val == "صاعد" else "trend-down"
        col.markdown(f"<div class='trend-box {cls}'>{lab}: {val}</div>", unsafe_allow_html=True)
    
    with c_inf[3]:
        st.markdown(f"<div class='trend-box' style='background-color:#1c2128; color:#8b949e;'>السيولة: {an['vol_txt']} ({an['ratio']:.1f}x)</div>", unsafe_allow_html=True)

    st.divider()

    # الدعوم والمقاومات
    st.subheader("📊 مستويات الارتكاز (Pivot Points)")
    cols = st.columns(4)
    cols[0].metric("دعم 2", f"{an['s2']:.2f}")
    cols[1].metric("دعم 1", f"{an['s1']:.2f}")
    cols[2].metric("مقاومة 1", f"{an['r1']:.2f}")
    cols[3].metric("مقاومة 2", f"{an['r2']:.2f}")

    # التداول والسيولة
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🎯 خطة الأهداف الصارمة")
        st.markdown(f"<div class='target-box'>🎯 **مضارب:** دخول <span class='price-callout'>{an['p']:.2f}</span> | هدف <span class='price-callout'>{an['r1']:.2f}</span> | وقف <span class='stoploss-callout'>{an['s1']:.2f}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='target-box'>📈 **سوينج:** دخول <span class='price-callout'>{an['p']:.2f}</span> | هدف <span class='price-callout'>{an['r2']:.2f}</span> | دعم <span class='stoploss-callout'>{an['s2']:.2f}</span></div>", unsafe_allow_html=True)
    
    with c2:
        st.subheader("💰 إدارة الـ 20,000 ج")
        st.markdown(f"""
        <div class='target-box'>
        ✅ **دفعة 1:** 7000 ج عند {an['p']:.2f}<br>
        🚀 **دفعة 2:** 7000 ج عند اختراق {an['r1']:.2f}<br>
        🛑 **دفعة طوارئ:** 6000 ج عند {an['s2']:.2f}
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    # 2. حاسبة المتوسط "المساعدة" (v12.7 style - تعديلك)
    st.subheader("🧮 مساعد متوسط التكلفة (v12.7)")
    with st.expander("اضغط لفتح حاسبة التعديل المقترحة", expanded=True):
        c_calc1, c_calc2 = st.columns(2)
        old_p = c_calc1.number_input("سعر الشراء القديم", value=float(an['p']), key=f"p_{an['name']}")
        old_q = c_calc2.number_input("الكمية الحالية", value=1000, key=f"q_{an['name']}")
        
        st.markdown("---")
        # اقتراحات تلقائية للتعديل
        for label, q_mult in [("بسيط (0.5x)", 0.5), ("متوسط (1:1)", 1.0), ("جذري (2:1)", 2.0)]:
            new_q = int(old_q * q_mult)
            avg = ((old_p * old_q) + (an['p'] * new_q)) / (old_q + new_q)
            st.markdown(f"<div class='avg-card'>شراء {new_q:,} سهم ({label}) | المتوسط الجديد: <span class='price-callout'>{avg:.3f} ج</span></div>", unsafe_allow_html=True)

# ================== PAGES ==================
if st.session_state.page == 'home':
    st.title("🏹 Sniper Elite v17.5 Pro")
    c1, c2 = st.columns(2)
    if c1.button("📡 تحليل سهم"): go_to('analyze')
    if c2.button("🔭 كشاف السوق"): go_to('scanner')
    if c1.button("🚀 رادار الاختراق"): go_to('breakout')
    if c2.button("💎 قنص الذهب"): go_to('gold')

elif st.session_state.page == 'analyze':
    if st.button("⬅️"): go_to('home')
    q = st.text_input("ادخل الرمز").upper()
    if q:
        data = fetch_egx_data(query_val=q)
        if data: render(analyze_stock(data[0]))

elif st.session_state.page in ['scanner', 'breakout', 'gold']:
    if st.button("⬅️"): go_to('home')
    page = st.session_state.page
    for r in fetch_egx_data(scan_all=True):
        an = analyze_stock(r)
        if not an: continue
        show = False
        if page == 'scanner' and an['t_score'] >= 50: show = True
        if page == 'breakout' and an['is_break'] and not an['is_chase']: show = True
        if page == 'gold' and an['is_gold']: show = True
        
        if show:
            with st.expander(f"{an['name']} | {an['status']} | {an['p']} ج"):
                render(an)
