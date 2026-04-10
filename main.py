import streamlit as st
import requests

# ================== CONFIG & STYLE (V16.6 THE PROTECTOR) ==================
st.set_page_config(page_title="EGX Sniper Elite v16.6", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; font-weight: bold !important; font-size: 16px !important; }
    .score-badge { background-color: #1c2128; border: 1px solid #58a6ff; padding: 2px 8px; border-radius: 8px; color: #58a6ff; font-weight: bold; }
    .target-box { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-bottom: 10px; }
    .price-callout { font-weight: bold; color: #3fb950; font-size: 18px; }
    .stoploss-callout { font-weight: bold; color: #f85149; font-size: 18px; }
    .trend-tag { padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: bold; }
    .trend-up { background-color: #238636; color: white; }
    .trend-down { background-color: #da3633; color: white; }
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

# ================== ANALYSIS LOGIC (v12.7 REBORN) ==================
def analyze_stock(d_row):
    try:
        d = d_row['d']
        name, p, rsi, v, avg_v, h, l, chg, desc, sma50, sma200 = d
        pp = (p + h + l) / 3
        s1, r1, s2, r2 = (2*pp)-h, (2*pp)-l, pp-(h-l), pp+(h-l)
        ratio = v / (avg_v or 1)
        rsi_val = rsi or 0
        
        # حساب السكورات (المعادلة الكلاسيكية)
        t_score = int(90 if rsi_val < 35 else 75 if rsi_val < 50 else 45)
        if p <= pp: t_score -= 15
        
        s_score = int(85 if ratio > 1.5 and 45 < rsi_val < 65 else 60)
        
        vol_info = ("🔥 زخم انفجاري", "#ffd700") if ratio > 1.6 else ("⚪ تداول هادئ", "#8b949e") if ratio > 0.8 else ("🔴 سيولة غائبة", "#ff4b4b")

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "t_score": t_score, "s_score": s_score,
            "vol_txt": vol_info[0], "vol_col": vol_info[1],
            "t_e": s1, "t_t": r1, "t_s": s1 * 0.98,
            "s_e": p, "s_t": r2, "s_s": s2,
            "t_short": "صاعد" if p > pp else "هابط",
            "t_med": "صاعد" if sma50 and p > sma50 else "هابط",
            "t_long": "صاعد" if sma200 and p > sma200 else "هابط",
            "is_gold": (ratio > 1.6 and 50 < rsi_val < 65),
            "is_break": (p >= h * 0.992 and ratio > 1.2)
        }
    except: return None

# ================== UI RENDERER ==================
def render_stock_ui(res):
    st.markdown(f"### {res['name']} <span class='score-badge'>(T-Score: {res['t_score']})</span>", unsafe_allow_html=True)
    st.caption(res['desc'])
    
    t_cols = st.columns(3)
    for col, lab, val in zip(t_cols, ["قصير", "متوسط", "طويل"], [res['t_short'], res['t_med'], res['t_long']]):
        cls = "trend-up" if val == "صاعد" else "trend-down"
        col.markdown(f"{lab}: <span class='trend-tag {cls}'>{val}</span>", unsafe_allow_html=True)

    st.divider()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("السعر الحالي", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    m2.metric("RSI", f"{res['rsi']:.1f}")
    with m3:
        st.markdown(f"<div style='text-align:center;'><b>{res['ratio']:.1f}x</b><br><span style='color:{res['vol_col']}; font-size:12px;'>{res['vol_txt']}</span></div>", unsafe_allow_html=True)

    c_t, c_s = st.columns(2)
    with c_t:
        st.markdown(f"#### 🎯 مضارب (Score: {res['t_score']})")
        st.markdown(f"<div class='target-box'>• دخول: <span class='price-callout'>{res['t_e']:.2f}</span><br>• هدف: <span class='price-callout'>{res['t_t']:.2f}</span><br>• وقف: <span class='stoploss-callout'>{res['t_s']:.2f}</span></div>", unsafe_allow_html=True)
    with c_s:
        st.markdown(f"#### 🔁 سوينج (Score: {res['s_score']})")
        st.markdown(f"<div class='target-box'>• دخول: <span class='price-callout'>{res['s_e']:.2f}</span><br>• هدف مستهدف: <span class='price-callout'>{res['s_t']:.2f}</span><br>• دعم تاريخي: <span class='stoploss-callout'>{res['s_s']:.2f}</span></div>", unsafe_allow_html=True)

    with st.expander("🛠️ خطة السيولة (ميزانية الـ 20 ألف)"):
        st.markdown(f"""
        - **صعود:** ادخل بـ 6000 ج عند {res['t_e']:.2f}.. زود بـ 8000 ج عند اختراق {res['t_t']:.2f}.. والتعزيز بـ 6000 ج فوق {res['s_t']:.2f}.
        - **هبوط:** لو نزل لـ {res['s_s']:.2f} ادخل بـ 8000 ج للتعديل.. والـ 6000 ج الأخيرة عند العودة لـ {res['p']:.2f}.
        """)

# ================== PAGES ==================
if st.session_state.page == 'home':
    st.title("🏹 Sniper Elite v16.6 Pro")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📡 تحليل سهم"): go_to('analyze')
        if st.button("🔭 كشاف السوق (Score > 50)"): go_to('scanner')
    with c2:
        if st.button("🚀 رادار الاختراقات"): go_to('breakout')
        if st.button("💎 قنص الذهب"): go_to('gold')
    if st.button("🧮 مساعد المتوسطات"): go_to('average')

elif st.session_state.page == 'analyze':
    if st.button("🏠 Home"): go_to('home')
    q = st.text_input("ادخل الرمز (مثل: ATQA)")
    if q:
        data = fetch_egx_data(query_val=q)
        if data: render_stock_ui(analyze_stock(data[0]))

elif st.session_state.page == 'scanner':
    if st.button("🏠 Home"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r)) and an['t_score'] >= 50: # فلتر السكور الحاسم
            with st.expander(f"{an['name']} | Score: {an['t_score']} | {an['vol_txt']}"): render_stock_ui(an)

elif st.session_state.page == 'breakout':
    if st.button("🏠 Home"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r)) and an['is_break'] and an['t_score'] >= 50: # حماية السكور
            with st.expander(f"🚀 {an['name']} | Score: {an['t_score']}"): render_stock_ui(an)

elif st.session_state.page == 'gold':
    if st.button("🏠 Home"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r)) and an['is_gold'] and an['t_score'] >= 50: # حماية السكور
            with st.expander(f"💎 {an['name']} | Score: {an['s_score']}"): render_stock_ui(an)

elif st.session_state.page == 'average':
    if st.button("🏠 Home"): go_to('home')
    st.subheader("🧮 مساعد المتوسطات")
    c1, c2, c3 = st.columns(3)
    o_p, o_q = c1.number_input("السعر القديم", 0.0), c2.number_input("الكمية", 0)
    n_p = c3.number_input("السعر الحالي", 0.0)
    if o_p > 0 and o_q > 0 and n_p > 0:
        for lab, q in [("بسيط (0.5x)", int(o_q*0.5)), ("متوسط (1:1)", o_q), ("جذري (2:1)", o_q*2)]:
            avg = ((o_p * o_q) + (n_p * q)) / (o_q + q)
            st.markdown(f"<div style='background:#1c2128; padding:10px; margin:5px; border-left:4px solid #58a6ff;'><b>{lab}</b>: اشترِ {q:,} سهم | متوسطك: {avg:.3f} ج</div>", unsafe_allow_html=True)
