import streamlit as st
import requests

# ================== CONFIG & STYLE (V16.2 REFINED) ==================
st.set_page_config(page_title="EGX Sniper Elite v16.2", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-weight: bold !important; }
    .price-callout { font-weight: bold; color: #3fb950; }
    .stoploss-callout { font-weight: bold; color: #f85149; }
    .warning-box { background-color: #2e2a0b; border-left: 6px solid #ffd700; padding: 12px; border-radius: 8px; color: #ffd700; font-weight: bold; margin: 10px 0; }
    .risk-tag { padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 14px; }
    .scenario-card { background-color: #0d1117; border: 1px solid #30363d; padding: 15px; border-radius: 12px; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'home'
def go_to(page_name):
    st.session_state.page = page_name
    st.rerun()

# ================== DATA ENGINE (FIXED SEARCH) ==================
@st.cache_data(ttl=300)
def fetch_egx_data(query_val=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    cols = ["name", "close", "RSI", "volume", "average_volume_10d_calc", "high", "low", "change", "description", "SMA50", "SMA200"]
    
    if scan_all:
        payload = {"filter": [{"left": "volume", "operation": "greater", "right": 50000}], "columns": cols, "range": [0, 50]}
    else:
        # إصلاح البحث ليدعم الرموز والأسماء معاً
        payload = {
            "filter": [{"left": "name", "operation": "match", "right": query_val.upper() if query_val else ""}],
            "columns": cols
        }
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except: return []

# ================== ANALYSIS LOGIC ==================
def analyze_stock(d_row):
    try:
        d = d_row['d']
        name, p, rsi, v, avg_v, h, l, chg, desc, sma50, sma200 = d
        pp = (p + h + l) / 3
        s1, r1, s2, r2 = (2*pp)-h, (2*pp)-l, pp-(h-l), pp+(h-l)
        
        # Risk Text Logic
        rr_val = (r1 - p) / (p - s1 * 0.98) if (p - s1 * 0.98) != 0 else 0
        if rr_val > 2: rr_txt, rr_col = "💎 مخاطرة ممتازة", "#3fb950"
        elif rr_val > 1: rr_txt, rr_col = "⚠️ مخاطرة متوسطة", "#ffd700"
        else: rr_txt, rr_col = "🛑 مخاطرة عالية جداً", "#f85149"
        
        # Pursuit Warning (تنبيه المطاردة)
        is_pursuit = p > (s1 * 1.02) # لو السعر أعلى من نقطة الدخول بـ 2%

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi or 0, "chg": chg, "ratio": v/(avg_v or 1),
            "t_e": s1, "t_t": r1, "t_s": s1 * 0.98, "s_e": p, "s_t": r2, "s_s": s2,
            "rr_txt": rr_txt, "rr_col": rr_col, "is_pursuit": is_pursuit,
            "t_short": "صاعد" if p > pp else "هابط",
            "t_med": "صاعد" if sma50 and p > sma50 else "هابط",
            "t_long": "صاعد" if sma200 and p > sma200 else "هابط"
        }
    except: return None

# ================== UI RENDERER ==================
def render_stock_ui(res):
    st.subheader(f"🏹 {res['name']} - {res['desc'][:30]}")
    
    # تحذير المطاردة
    if res['is_pursuit']:
        st.markdown(f"<div class='warning-box'>⚠️ تنبيه مطاردة: السعر حالياً بعيد عن منطقة الدخول المثالية ({res['t_e']:.2f}). انتظر تهدئة.</div>", unsafe_allow_html=True)
    
    st.markdown(f"درجة المخاطرة: <span class='risk-tag' style='color:{res['rr_col']}; border:1px solid {res['rr_col']};'>{res['rr_txt']}</span>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("الزخم", f"{res['ratio']:.1f}x")
    c3.metric("RSI", f"{res['rsi']:.1f}")

    st.divider()
    
    # أهداف وسيناريوهات
    st.markdown("### 🛠️ خطة التنفيذ والسيناريوهات")
    sc1, sc2 = st.columns(2)
    with sc1:
        st.markdown(f"""
        <div class='scenario-card'>
            <b>🎯 سيناريو المضارب السريع:</b><br>
            - منطقة الدخول: <span class='price-callout'>{res['t_e']:.2f}</span><br>
            - الهدف الأول: <span class='price-callout'>{res['t_t']:.2f}</span><br>
            - وقف الخسارة: <span class='stoploss-callout'>{res['t_s']:.2f}</span>
        </div>
        """, unsafe_allow_html=True)
    with sc2:
        st.markdown(f"""
        <div class='scenario-card'>
            <b>🔁 سيناريو السوينج (نفس طويل):</b><br>
            - الدخول الحالي: <span class='price-callout'>{res['p']:.2f}</span><br>
            - الهدف المستهدف: <span class='price-callout'>{res['s_t']:.2f}</span><br>
            - الدعم التاريخي: <span class='stoploss-callout'>{res['s_s']:.2f}</span>
        </div>
        """, unsafe_allow_html=True)

# ================== PAGES ==================
if st.session_state.page == 'home':
    st.title("🏹 Sniper Elite v16.2")
    if st.button("📡 تحليل سهم"): go_to('analyze')
    if st.button("🧮 مساعد المتوسطات"): go_to('average')
    if st.button("🔭 كشاف السوق"): go_to('scanner')

elif st.session_state.page == 'analyze':
    if st.button("🏠"): go_to('home')
    query = st.text_input("ادخل الرمز (مثل: ATQA) أو الكود الدولي")
    if query:
        data = fetch_egx_data(query_val=query)
        if data: render_stock_ui(analyze_stock(data[0]))
        else: st.error("لم يتم العثور على السهم. تأكد من الرمز.")

elif st.session_state.page == 'average':
    if st.button("🏠"): go_to('home')
    st.subheader("🧮 حاسبة المتوسط والمبلغ المطلوب")
    c1, c2, c3 = st.columns(3)
    old_p, old_q = c1.number_input("السعر القديم", 0.0), c2.number_input("الكمية", 0)
    new_p = c3.number_input("السعر الحالي", 0.0)
    
    if old_p > 0 and old_q > 0 and new_p > 0:
        st.divider()
        target = st.number_input("المتوسط المستهدف؟", value=old_p-0.1)
        if new_p < target < old_p:
            needed_q = (old_q * (old_p - target)) / (target - new_p)
            needed_money = needed_q * new_p
            st.success(f"✅ للوصول لمتوسط {target:.2f}:")
            st.markdown(f"- اشترِ: **{int(needed_q):,} سهم**")
            st.markdown(f"- المبلغ المطلوب: **{needed_money:,.0f} جنيه**")

elif st.session_state.page == 'scanner':
    if st.button("🏠"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        if an := analyze_stock(r):
            with st.expander(f"{an['name']} | {an['rr_txt']}"): render_stock_ui(an)
