import streamlit as st
import requests

# ================== CONFIG & STYLE (V17.2 - THE CHASE GUARDIAN) ==================
st.set_page_config(page_title="EGX Sniper v17.2", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; font-weight: bold; }
    .chase-warning { background-color: #701010; color: #ff7b72; padding: 15px; border-radius: 10px; border: 1px solid #ff7b72; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .chase-safe { background-color: #103010; color: #7ee787; padding: 15px; border-radius: 10px; border: 1px solid #7ee787; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .trend-tag { padding: 4px 10px; border-radius: 8px; font-size: 13px; font-weight: bold; }
    .trend-up { background-color: #238636; color: white; }
    .trend-down { background-color: #da3633; color: white; }
    .support-val { color: #ff7b72; font-weight: bold; }
    .resistance-val { color: #7ee787; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'home'
def go_to(p): st.session_state.page = p; st.rerun()

# ================== DATA ENGINE ==================
@st.cache_data(ttl=300)
def fetch_egx_data(query_val=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    cols = ["name", "close", "RSI", "volume", "average_volume_10d_calc", "high", "low", "change", "description", "SMA50", "SMA200"]
    payload = {"filter": [{"left": "volume", "operation": "greater", "right": 30000}], "columns": cols, "range": [0, 100]}
    if not scan_all and query_val:
        payload["filter"].append({"left": "name", "operation": "match", "right": query_val.upper()})
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except: return []

# ================== ANALYSIS LOGIC ==================
def analyze_stock(d_row):
    try:
        d = d_row['d']
        name, p, rsi, v, avg_v, h, l, chg, desc, sma50, sma200 = d
        pp = (h + l + p) / 3
        r1, s1, r2, s2 = (2*pp)-l, (2*pp)-h, pp+(h-l), pp-(h-l)
        ratio = v / (avg_v or 1)
        rsi_val = rsi or 0
        
        # الاتجاهات
        t_short = "صاعد" if p > pp else "هابط"
        t_med = "صاعد" if sma50 and p > sma50 else "هابط"
        t_long = "صاعد" if sma200 and p > sma200 else "هابط"
        
        # السيولة والسكور
        t_score = int(85 if 40 < rsi_val < 60 else 60 if rsi_val < 70 else 35)
        if t_med == "هابط": t_score -= 15

        # منطق تحذير المطاردة
        # لو السعر طار فوق المقاومة الأولى والزخم عالي جداً والـ RSI فوق 70
        is_chase = (p > r1 * 1.03 and rsi_val > 70) or (chg > 7 and ratio > 2)

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "t_score": t_score, "pp": pp, "r1": r1, "r2": r2, "s1": s1, "s2": s2,
            "t_short": t_short, "t_med": t_med, "t_long": t_long,
            "is_chase": is_chase, "vol_txt": "🔥 زخم" if ratio > 1.5 else "⚪ هادئ"
        }
    except: return None

# ================== UI COMPONENTS ==================
def render_analysis_ui(an):
    # 1. تحذير المطاردة (Chase Warning)
    if an['is_chase']:
        st.markdown(f"<div class='chase-warning'>⚠️ تحذير مطاردة: السهم طار منك! الانتظار أفضل لتجنب التعليقة.</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='chase-safe'>✅ منطقة آمنة: السهم في نطاق سعري يسمح بالدخول والمناورة.</div>", unsafe_allow_html=True)

    # 2. الهيدر والاتجاهات
    st.markdown(f"### {an['name']} | Score: {an['t_score']}")
    c_tr = st.columns(4)
    for col, lab, val in zip(c_tr[:3], ["قصير", "متوسط", "طويل"], [an['t_short'], an['t_med'], an['t_long']]):
        cls = "trend-up" if val == "صاعد" else "trend-down"
        col.markdown(f"{lab}: <span class='trend-tag {cls}'>{val}</span>", unsafe_allow_html=True)
    c_tr[3].markdown(f"**السيولة:** {an['vol_txt']} ({an['ratio']:.1f}x)")

    st.divider()

    # 3. الأهداف والدعوم
    st.subheader("🎯 أهداف المضارب والسوينج")
    col1, col2 = st.columns(2)
    with col1:
        st.info("🚀 أهداف سريعة")
        st.write(f"✅ هدف 1: {an['r1']:.2f} | ✅ هدف 2: {an['r2']:.2f}")
        st.write(f"🛑 وقف الخسارة: {an['s1']:.2f}")
    with col2:
        st.success("📉 مستويات الدعم (للتعديل)")
        st.markdown(f"• دعم أول: <span class='support-val'>{an['s1']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"• دعم ثانٍ: <span class='support-val'>{an['s2']:.2f}</span>", unsafe_allow_html=True)

    # 4. حاسبة المتوسط وخطة الـ 20 ألف
    with st.expander("🛠️ أدوات إدارة المحفظة (20,000 ج)"):
        st.markdown(f"**خطة الدخول:** 7000 ج عند {an['p']:.2f} | 7000 ج فوق {an['r1']:.2f} | 6000 ج سيولة طوارئ.")
        st.divider()
        st.subheader("🧮 حاسبة المتوسط")
        old_p = st.number_input("السعر القديم", value=float(an['p']))
        old_q = st.number_input("الكمية", value=1000)
        avg = ((old_p * old_q) + (an['p'] * old_q)) / (old_q * 2)
        st.code(f"المتوسط الجديد في حالة التعديل بنفس الكمية: {avg:.3f}")

# ================== PAGES ==================
if st.session_state.page == 'home':
    st.title("🏹 Sniper Elite v17.2")
    c1, c2 = st.columns(2)
    if c1.button("📡 تحليل السهم"): go_to('analyze')
    if c2.button("🔭 كشاف السوق"): go_to('scanner')

elif st.session_state.page == 'analyze':
    if st.button("⬅️"): go_to('home')
    q = st.text_input("ادخل الرمز").upper()
    if q:
        data = fetch_egx_data(query_val=q)
        if data: render_analysis_ui(analyze_stock(data[0]))

elif st.session_state.page == 'scanner':
    if st.button("⬅️"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r)) and an['t_score'] >= 50:
            with st.expander(f"{an['name']} | Score: {an['t_score']} | {an['vol_txt']}"):
                render_analysis_ui(an)
