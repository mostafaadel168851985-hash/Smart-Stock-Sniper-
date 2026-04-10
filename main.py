import streamlit as st
import requests

# ================== CONFIG & STYLE (V17.1 - FULL VISION) ==================
st.set_page_config(page_title="EGX Sniper v17.1", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; font-weight: bold; }
    .trend-tag { padding: 4px 10px; border-radius: 8px; font-size: 13px; font-weight: bold; margin-right: 5px; }
    .trend-up { background-color: #238636; color: white; }
    .trend-down { background-color: #da3633; color: white; }
    .vol-box { background: #161b22; padding: 10px; border-radius: 10px; text-align: center; border: 1px solid #30363d; }
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
        
        # السيولة
        if ratio > 1.6: vol_txt, vol_col, emoji = "🔥 زخم انفجاري", "#ffd700", "🔥"
        elif ratio > 0.8: vol_txt, vol_col, emoji = "⚪ تداول هادئ", "#8b949e", "⚪"
        else: vol_txt, vol_col, emoji = "🔴 سيولة غائبة", "#ff4b4b", "🔴"

        # سكور وتوصية
        t_score = int(85 if 40 < rsi_val < 60 else 60 if rsi_val < 70 else 35)
        if t_med == "هابط": t_score -= 15
        
        status = "🟢 شراء/تجميع" if rsi_val < 45 else "🚀 اختراق" if p > r1 else "🟡 مراقبة السلوك"

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "t_score": t_score, "status": status, "vol_txt": vol_txt, "vol_col": vol_col, "emoji": emoji,
            "s1": s1, "s2": s2, "r1": r1, "r2": r2, "pp": pp,
            "t_short": t_short, "t_med": t_med, "t_long": t_long,
            "is_gold": (ratio > 1.5 and 45 < rsi_val < 62),
            "is_break": (p >= h * 0.99 and ratio > 1.2)
        }
    except: return None

# ================== UI COMPONENTS ==================
def render_analysis_ui(an):
    # 1. الاتجاهات والسيولة في الرأس
    st.markdown(f"### {an['name']} | {an['status']} (Score: {an['t_score']})")
    
    c_tr = st.columns(4)
    for col, lab, val in zip(c_tr[:3], ["قصير", "متوسط", "طويل"], [an['t_short'], an['t_med'], an['t_long']]):
        cls = "trend-up" if val == "صاعد" else "trend-down"
        col.markdown(f"{lab}: <span class='trend-tag {cls}'>{val}</span>", unsafe_allow_html=True)
    
    with c_tr[3]:
        st.markdown(f"<div class='vol-box' style='color:{an['vol_col']}'>{an['emoji']} {an['ratio']:.1f}x السيولة</div>", unsafe_allow_html=True)

    st.divider()

    # 2. الدعوم والمقاومات
    cols = st.columns(4)
    cols[0].markdown(f"📉 دعم 2: <span class='support-val'>{an['s2']:.2f}</span>", unsafe_allow_html=True)
    cols[1].markdown(f"📉 دعم 1: <span class='support-val'>{an['s1']:.2f}</span>", unsafe_allow_html=True)
    cols[2].markdown(f"📈 مقاومة 1: <span class='resistance-val'>{an['r1']:.2f}</span>", unsafe_allow_html=True)
    cols[3].markdown(f"📈 مقاومة 2: <span class='resistance-val'>{an['r2']:.2f}</span>", unsafe_allow_html=True)

    # 3. الأهداف وخطة السيولة
    st.subheader("🎯 خطة الأهداف وإدارة الـ 20 ألف ج")
    col_a, col_b = st.columns(2)
    with col_a:
        st.info("🎯 مضارب سريع")
        st.write(f"✅ هدف 1: {an['r1']:.2f} | ✅ هدف 2: {an['r2']:.2f}")
        st.write(f"🛑 وقف خسارة: {an['s1']:.2f}")
    with col_b:
        st.success("💰 توزيع الميزانية")
        st.write(f"• شراء بـ 7000 ج عند {an['p']:.2f}")
        st.write(f"• تعزيز بـ 7000 ج عند اختراق {an['r1']:.2f}")
        st.write(f"• سيولة طوارئ بـ 6000 ج عند {an['s2']:.2f}")

    # 4. حاسبة المتوسط
    with st.expander("🧮 حاسبة تعديل المتوسط السريع"):
        c1, c2 = st.columns(2)
        old_p = c1.number_input("السعر القديم", value=float(an['p']))
        old_q = c2.number_input("الكمية الحالية", value=1000)
        new_q = st.number_input("كمية الشراء الجديدة للتعديل", value=old_q)
        avg = ((old_p * old_q) + (an['p'] * new_q)) / (old_q + new_q)
        st.warning(f"المتوسط الجديد سيكون: {avg:.3f} ج")

# ================== PAGES ==================
if st.session_state.page == 'home':
    st.title("🏹 Sniper Elite v17.1")
    c1, c2 = st.columns(2)
    if c1.button("📡 تحليل السهم"): go_to('analyze')
    if c2.button("🔭 كشاف السوق"): go_to('scanner')
    if c1.button("🚀 الاختراقات"): go_to('breakout')
    if c2.button("💎 قنص الذهب"): go_to('gold')

elif st.session_state.page == 'analyze':
    if st.button("⬅️"): go_to('home')
    q = st.text_input("ادخل الرمز").upper()
    if q:
        data = fetch_egx_data(query_val=q)
        if data: render_analysis_ui(analyze_stock(data[0]))
        else: st.error("لا توجد بيانات لهذا السهم.")

elif st.session_state.page == 'scanner':
    if st.button("⬅️"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r)) and an['t_score'] >= 50:
            with st.expander(f"{an['name']} | {an['status']} | {an['emoji']} {an['ratio']:.1f}x"):
                render_analysis_ui(an)
