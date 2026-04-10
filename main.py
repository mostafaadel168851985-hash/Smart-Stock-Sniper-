import streamlit as st
import requests

# ================== CONFIG & STYLE (V16.1 PRO ULTIMATE) ==================
st.set_page_config(page_title="EGX Sniper Elite v16.1 PRO", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-size: 18px !important; font-weight: bold !important; margin-bottom: 10px; }
    .stock-header { font-size: 20px !important; font-weight: bold; color: #58a6ff; }
    .price-callout { font-size: 16px !important; font-weight: bold; color: #3fb950; }
    .stoploss-callout { font-size: 14px !important; font-weight: bold; color: #f85149; }
    .trend-tag { padding: 3px 10px; border-radius: 6px; font-size: 12px; font-weight: bold; }
    .trend-up { background-color: #238636; color: white; border: 1px solid #3fb950; }
    .trend-down { background-color: #da3633; color: white; border: 1px solid #f85149; }
    .avg-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-bottom: 12px; border-left: 5px solid #58a6ff; }
    .risk-box { background-color: #0d1117; border: 1px solid #30363d; border-radius: 10px; padding: 10px; text-align: center; margin-top: 10px; }
    .hist-level { background-color: #161b22; border-right: 4px solid #58a6ff; padding: 10px; margin: 5px 0; border-radius: 4px; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'home'
def go_to(page_name):
    st.session_state.page = page_name
    st.rerun()

# ================== DATA ENGINE (SMART SEARCH) ==================
@st.cache_data(ttl=300)
def fetch_egx_data(query_val=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    columns = ["name", "close", "RSI", "volume", "average_volume_10d_calc", "high", "low", "change", "description", "SMA50", "SMA200"]
    
    if scan_all:
        payload = {
            "filter": [{"left": "volume", "operation": "greater", "right": 50000}, {"left": "close", "operation": "greater", "right": 0.4}],
            "columns": columns, "sort": {"sortBy": "change", "sortOrder": "desc"}, "range": [0, 100]
        }
    else:
        # البحث الذكي: يحاول المطابقة مع الاسم أو الوصف أو الكود الدولي
        payload = {
            "filter": [{"left": "any_of", "operation": "match", "right": query_val.upper() if query_val else ""}],
            "columns": columns
        }
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except: return []

# ================== ANALYSIS ENGINE (v16.1 PRO Logic) ==================
def analyze_stock(d_row):
    try:
        d = d_row['d']
        name, p, rsi, v, avg_v, h, l, chg, desc, sma50, sma200 = d
        if p is None or h is None or l is None: return None
        
        # 1. Pivot Points (v11.8 Logic)
        pp = (p + h + l) / 3
        s1, r1, s2, r2 = (2*pp)-h, (2*pp)-l, pp-(h-l), pp+(h-l)
        
        # 2. Historical & Risk Analysis
        ratio = v / (avg_v or 1)
        rsi_val = rsi or 0
        rr_ratio = (r1 - p) / (p - s1 * 0.98) if (p - s1 * 0.98) != 0 else 0
        
        # 3. Trend Logic
        t_short = "صاعد" if p > pp else "هابط"
        t_med = "صاعد" if sma50 and p > sma50 else "هابط"
        t_long = "صاعد" if sma200 and p > sma200 else "هابط"
        
        # 4. Scoring & Signals
        t_score = int(90 if rsi_val < 38 else 75 if rsi_val < 55 else 40)
        if p <= pp: t_score -= 20
        
        is_gold = (ratio > 1.6 and 50 < rsi_val < 65 and chg > 0.5)
        is_break = (p >= h * 0.992 and ratio > 1.2)
        
        rec, col = ("🛑 تشبع", "#ff4b4b") if rsi_val > 72 else ("💎 ذهب", "#ffd700") if is_gold else ("🚀 شراء", "#00ff00") if t_score >= 70 else ("⚖️ انتظار", "#58a6ff")

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "t_e": s1, "t_t": r1, "t_s": s1 * 0.98, "t_score": t_score,
            "s_e": p, "s_t": r2, "s_s": s2, "rr": rr_ratio,
            "t_short": t_short, "t_med": t_med, "t_long": t_long,
            "rec": rec, "col": col, "is_gold": is_gold, "is_break": is_break
        }
    except: return None

# ================== UI RENDERER ==================
def render_stock_ui(res):
    if not res: return
    
    # Header & Trends
    st.markdown(f"<div class='stock-header'>{res['name']} | {res['desc'][:25]} <span style='color:{res['col']}; float:left;'>{res['rec']}</span></div>", unsafe_allow_html=True)
    
    tr_cols = st.columns(3)
    for col, lab, val in zip(tr_cols, ["قصير", "متوسط", "طويل"], [res['t_short'], res['t_med'], res['t_long']]):
        cls = "trend-up" if val == "صاعد" else "trend-down"
        col.markdown(f"{lab}: <span class='trend-tag {cls}'>{val}</span>", unsafe_allow_html=True)

    st.divider()
    
    # Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    m2.metric("RSI", f"{res['rsi']:.1f}")
    m3.metric("الزخم", f"{res['ratio']:.1f}x")

    # Risk/Reward Info
    rr_col = "#3fb950" if res['rr'] > 2 else "#ffd700" if res['rr'] > 1 else "#f85149"
    st.markdown(f"<div class='risk-box'>معدل الربح للمخاطرة (R/R Ratio): <b style='color:{rr_col};'>{res['rr']:.2f}</b></div>", unsafe_allow_html=True)

    st.divider()
    
    # Daily Goals
    c_t, c_s = st.columns(2)
    with c_t:
        st.markdown("**🎯 مضارب اليومي**")
        st.markdown(f"دخول: <span class='price-callout'>{res['t_e']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"هدف: <span class='price-callout'>{res['t_t']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"وقف: <span class='stoploss-callout'>{res['t_s']:.2f}</span>", unsafe_allow_html=True)
    with c_s:
        st.markdown("**🔁 سوينج / تاريخي**")
        st.markdown(f"دخول: <span class='price-callout'>{res['s_e']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"هدف: <span class='price-callout'>{res['s_t']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"دعم تاريخي: <span class='stoploss-callout'>{res['s_s']:.2f}</span>", unsafe_allow_html=True)

# ================== PAGES ==================
if st.session_state.page == 'home':
    st.title("🏹 EGX Sniper Elite v16.1 PRO")
    c_m1, c_m2 = st.columns(2)
    with c_m1:
        if st.button("📡 تحليل سهم"): go_to('analyze')
        if st.button("🔭 كشاف السوق"): go_to('scanner')
    with c_m2:
        if st.button("🚀 رادار الاختراقات"): go_to('breakout')
        if st.button("🧮 مساعد المتوسطات"): go_to('average')
    if st.button("💎 قنص الذهب"): go_to('gold')

elif st.session_state.page == 'analyze':
    if st.button("🏠"): go_to('home')
    query = st.text_input("ادخل الرمز، الكود الدولي، أو اسم الشركة").strip()
    if query:
        data = fetch_egx_data(query_val=query)
        if data:
            for d in data[:3]: # عرض أول 3 نتائج مطابقة
                render_stock_ui(analyze_stock(d))
        else: st.error("لم يتم العثور على نتائج. جرب الكود الدولي EGS...")

elif st.session_state.page == 'average':
    if st.button("🏠"): go_to('home')
    st.subheader("🧮 مساعد متوسط التكلفة والمستهدف")
    c1, c2, c3 = st.columns(3)
    old_p, old_q = c1.number_input("السعر القديم", 0.0), c2.number_input("الكمية القديمة", 0)
    new_p = c3.number_input("السعر الحالي", 0.0)
    if old_p > 0 and old_q > 0 and new_p > 0:
        for label, q in [("بسيط (0.5x)", int(old_q*0.5)), ("متوسط (1:1)", old_q), ("جذري (2:1)", old_q*2)]:
            avg = ((old_p * old_q) + (new_p * q)) / (old_q + q)
            st.markdown(f"<div class='avg-card'><b>{label}</b>: شراء {q:,} سهم<br>المتوسط: <span class='price-callout'>{avg:.3f} ج</span></div>", unsafe_allow_html=True)
        st.divider()
        target = st.number_input("المتوسط المستهدف؟", value=old_p-0.01)
        if new_p < target < old_p:
            needed_q = (old_q * (old_p - target)) / (target - new_p)
            st.success(f"للوصول لمتوسط {target:.2f}: اشترِ {int(needed_q):,} سهم")

elif st.session_state.page == 'scanner':
    if st.button("🏠"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r)) and an['t_score'] >= 70:
            with st.expander(f"⭐ {an['t_score']} | {an['name']}"): render_stock_ui(an)

elif st.session_state.page == 'breakout':
    if st.button("🏠"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r)) and an['is_break']:
            with st.expander(f"🚀 {an['name']}"): render_stock_ui(an)

elif st.session_state.page == 'gold':
    if st.button("🏠"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r)) and an['is_gold']:
            with st.expander(f"💎 {an['name']}"): render_stock_ui(an)
