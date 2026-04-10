import streamlit as st
import requests

# ================== CONFIG & STYLE (V17.4 FINAL PRO) ==================
st.set_page_config(page_title="EGX Sniper v17.4 FINAL", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; font-weight: bold; }
    .status-badge { padding: 4px 10px; border-radius: 8px; font-weight: bold; }
    .status-chase { background-color: #f85149; color: white; }
    .status-break { background-color: #238636; color: white; }
    .status-gold { background-color: #ffd700; color: black; }
    .status-buy { background-color: #1f6feb; color: white; }
    .status-wait { background-color: #8b949e; color: white; }
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

        # إشارات محسنة (من تعديلك الذكي)
        is_gold = (ratio > 1.5 and 45 < rsi_val < 60 and t_med == "صاعد")
        is_break = (p >= h*0.995 and ratio > 1.2 and rsi_val > 50 and t_med == "صاعد")
        is_chase = ((p > r1*1.03 and rsi_val > 70) or (chg > 7 and ratio > 2))

        # اختيار الحالة واللون
        if is_chase: status, s_cls = "⚠️ مطاردة", "status-chase"
        elif is_break: status, s_cls = "🚀 اختراق", "status-break"
        elif is_gold: status, s_cls = "💎 ذهب", "status-gold"
        elif rsi_val < 45: status, s_cls = "🟢 تجميع", "status-buy"
        else: status, s_cls = "🟡 انتظار", "status-wait"

        t_score = int(85 if 40<rsi_val<60 else 60 if rsi_val<70 else 35)
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
    
    # تفاصيل سريعة
    c_inf = st.columns(3)
    c_inf[0].write(f"**الاتجاه:** {an['t_short']} | {an['t_med']} | {an['t_long']}")
    c_inf[1].write(f"**RSI:** {an['rsi']:.1f}")
    c_inf[2].write(f"**السيولة:** {an['vol_txt']} ({an['ratio']:.1f}x)")

    st.divider()

    # الدعوم والمقاومات
    st.subheader("📊 مستويات الارتكاز (Pivot Points)")
    cols = st.columns(4)
    cols[0].metric("دعم 2", f"{an['s2']:.2f}")
    cols[1].metric("دعم 1", f"{an['s1']:.2f}")
    cols[2].metric("مقاومة 1", f"{an['r1']:.2f}")
    cols[3].metric("مقاومة 2", f"{an['r2']:.2f}")

    # التداول والسيولة
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🎯 خطة الصفقات")
        st.info(f"**مضارب:** دخول {an['p']:.2f} | هدف {an['r1']:.2f} | وقف {an['s1']:.2f}")
        st.success(f"**سوينج:** دخول {an['p']:.2f} | هدف {an['r2']:.2f} | دعم {an['s2']:.2f}")
    
    with c2:
        st.subheader("💰 إدارة الـ 20,000 ج")
        st.write(f"✅ **دفعة 1:** 7000 ج عند {an['p']:.2f}")
        st.write(f"🚀 **دفعة 2:** 7000 ج عند اختراق {an['r1']:.2f}")
        st.write(f"🛑 **دفعة طوارئ:** 6000 ج عند {an['s2']:.2f}")

    with st.expander("🧮 حاسبة المتوسط"):
        old_p = st.number_input("السعر القديم", value=float(an['p']), key=f"p_{an['name']}")
        old_q = st.number_input("الكمية القديمة", value=1000, key=f"q_{an['name']}")
        avg = ((old_p * old_q) + (an['p'] * old_q)) / (old_q * 2)
        st.warning(f"متوسطك الجديد في حال الشراء بنفس الكمية: {avg:.3f}")

# ================== PAGES ==================
if st.session_state.page == 'home':
    st.title("🏹 Sniper v17.4 FINAL PRO")
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
