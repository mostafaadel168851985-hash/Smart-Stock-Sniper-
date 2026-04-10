import streamlit as st
import requests

# ================== CONFIG & STYLE (V16.3 RETURN OF POWER) ==================
st.set_page_config(page_title="EGX Sniper Elite v16.3", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-weight: bold !important; }
    .stock-header { font-size: 20px !important; font-weight: bold; color: #58a6ff; }
    .price-callout { font-weight: bold; color: #3fb950; }
    .stoploss-callout { font-weight: bold; color: #f85149; }
    .trend-tag { padding: 3px 8px; border-radius: 6px; font-size: 12px; font-weight: bold; }
    .trend-up { background-color: #238636; color: white; }
    .trend-down { background-color: #da3633; color: white; }
    .plan-container { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-top: 10px; }
    .vol-label { font-size: 12px; font-weight: bold; margin-top: 5px; }
    .avg-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 10px; padding: 12px; margin-bottom: 8px; border-left: 5px solid #58a6ff; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'home'
def go_to(page_name):
    st.session_state.page = page_name
    st.rerun()

# ================== DATA ENGINE ==================
@st.cache_data(ttl=300)
def fetch_egx_data(query_val=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    cols = ["name", "close", "RSI", "volume", "average_volume_10d_calc", "high", "low", "change", "description", "SMA50", "SMA200"]
    if scan_all:
        payload = {"filter": [{"left": "volume", "operation": "greater", "right": 50000}], "columns": cols, "range": [0, 50]}
    else:
        payload = {"filter": [{"left": "name", "operation": "match", "right": query_val.upper() if query_val else ""}], "columns": cols}
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
        
        ratio = v / (avg_v or 1)
        rsi_val = rsi or 0
        
        # الزخم البصري
        if ratio > 1.6: vol_txt, vol_col, emoji = "🔥 زخم انفجاري", "#ffd700", "🔥"
        elif ratio > 0.8: vol_txt, vol_col, emoji = "⚪ تداول هادئ", "#8b949e", "⚪"
        else: vol_txt, vol_col, emoji = "🔴 سيولة غائبة", "#ff4b4b", "🔴"

        # المخاطرة والاتجاه
        rr = (r1 - p) / (p - s1 * 0.98) if (p - s1 * 0.98) != 0 else 0
        risk_status = "💎 ممتازة" if rr > 1.5 else "⚠️ مقبولة" if rr > 0.8 else "🛑 عالية"
        
        is_gold = (ratio > 1.6 and 50 < rsi_val < 65 and chg > 0.5)
        is_break = (p >= h * 0.992 and ratio > 1.2)

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "vol_txt": vol_txt, "vol_col": vol_col, "emoji": emoji,
            "t_e": s1, "t_t": r1, "t_s": s1 * 0.98, "s_e": p, "s_t": r2, "s_s": s2,
            "risk": risk_status, "is_gold": is_gold, "is_break": is_break,
            "t_short": "صاعد" if p > pp else "هابط",
            "t_med": "صاعد" if sma50 and p > sma50 else "هابط",
            "t_long": "صاعد" if sma200 and p > sma200 else "هابط"
        }
    except: return None

# ================== UI RENDERER ==================
def render_stock_ui(res):
    st.markdown(f"<div class='stock-header'>{res['name']} | {res['desc'][:30]}</div>", unsafe_allow_html=True)
    
    # الاتجاهات
    t_cols = st.columns(3)
    for col, lab, val in zip(t_cols, ["قصير", "متوسط", "طويل"], [res['t_short'], res['t_med'], res['t_long']]):
        cls = "trend-up" if val == "صاعد" else "trend-down"
        col.markdown(f"{lab}: <span class='trend-tag {cls}'>{val}</span>", unsafe_allow_html=True)

    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("RSI", f"{res['rsi']:.1f}")
    with c3:
        st.markdown(f"<div style='text-align:center;'><div style='font-size:16px; font-weight:bold;'>{res['ratio']:.1f}x</div><div class='vol-label' style='color:{res['vol_col']}'>{res['vol_txt']}</div></div>", unsafe_allow_html=True)

    st.info(f"درجة مخاطرة الصفقة: **{res['risk']}**")

    # خطة السيولة 30/40/30
    st.markdown("### 🛠️ خطة السيولة (ميزانية الـ 20 ألف)")
    p1, p2, p3 = 6000, 8000, 6000
    st.markdown(f"""
    <div class='plan-container'>
        <b>📈 صعود:</b> ادخل بـ {p1:,} ج عند {res['t_e']:.2f}.. زود بـ {p2:,} ج عند اختراق {res['t_t']:.2f}.. والتعزيز بـ {p3:,} ج فوق {res['s_t']:.2f}.<br><br>
        <b>📉 هبوط:</b> لو نزل لـ {res['s_s']:.2f} ادخل بـ {p2:,} ج للتعديل.. والـ {p3:,} ج الأخيرة عند العودة لـ {res['p']:.2f}.
    </div>
    """, unsafe_allow_html=True)

# ================== PAGES ==================
if st.session_state.page == 'home':
    st.title("🏹 Sniper Elite v16.3")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("📡 تحليل سهم"): go_to('analyze')
        if st.button("🔭 كشاف السوق"): go_to('scanner')
    with col_b:
        if st.button("🚀 رادار الاختراقات"): go_to('breakout')
        if st.button("💎 قنص الذهب"): go_to('gold')
    if st.button("🧮 مساعد المتوسطات"): go_to('average')

elif st.session_state.page == 'average':
    if st.button("🏠"): go_to('home')
    st.subheader("🧮 مساعد المتوسطات")
    c1, c2, c3 = st.columns(3)
    old_p, old_q = c1.number_input("السعر القديم", 0.0), c2.number_input("الكمية", 0)
    new_p = c3.number_input("السعر الحالي", 0.0)
    if old_p > 0 and old_q > 0 and new_p > 0:
        for label, q in [("بسيط (0.5x)", int(old_q*0.5)), ("متوسط (1:1)", old_q), ("جذري (2:1)", old_q*2)]:
            avg = ((old_p * old_q) + (new_p * q)) / (old_q + q)
            st.markdown(f"<div class='avg-card'><b>{label}</b>: شراء {q:,} سهم | المتوسط الجديد: <b style='color:#3fb950;'>{avg:.3f} ج</b></div>", unsafe_allow_html=True)
        st.divider()
        target = st.number_input("أدخل المتوسط المستهدف؟", value=old_p-0.1)
        if new_p < target < old_p:
            needed_q = (old_q * (old_p - target)) / (target - new_p)
            st.success(f"للوصول لمتوسط {target:.2f}: اشترِ {int(needed_q):,} سهم بمبلغ {needed_q*new_p:,.0f} ج")

elif st.session_state.page == 'analyze':
    if st.button("🏠"): go_to('home')
    query = st.text_input("ادخل الرمز")
    if query:
        data = fetch_egx_data(query_val=query)
        if data: render_stock_ui(analyze_stock(data[0]))

elif st.session_state.page == 'scanner':
    if st.button("🏠"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r)):
            with st.expander(f"{an['name']} | المخاطرة: {an['risk']}"): render_stock_ui(an)

elif st.session_state.page == 'breakout':
    if st.button("🏠"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r)) and an['is_break']:
            with st.expander(f"🚀 اختراق: {an['name']}"): render_stock_ui(an)

elif st.session_state.page == 'gold':
    if st.button("🏠"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r)) and an['is_gold']:
            with st.expander(f"💎 ذهب: {an['name']}"): render_stock_ui(an)
