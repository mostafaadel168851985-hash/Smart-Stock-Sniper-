import streamlit as st
import requests

# ================== CONFIG & STYLE (V16.8 - THE ANALYST) ==================
st.set_page_config(page_title="EGX Sniper Elite v16.8", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; font-weight: bold !important; }
    .score-badge { background-color: #1c2128; border: 1px solid #58a6ff; padding: 2px 8px; border-radius: 8px; color: #58a6ff; font-weight: bold; }
    .status-buy { color: #3fb950; font-weight: bold; border: 1px solid #3fb950; padding: 2px 5px; border-radius: 4px; }
    .status-wait { color: #f85149; font-weight: bold; border: 1px solid #f85149; padding: 2px 5px; border-radius: 4px; }
    .target-box { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-bottom: 10px; }
    .support-val { color: #f85149; font-weight: bold; }
    .resistance-val { color: #3fb950; font-weight: bold; }
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
    # زيادة النطاق لـ 100 سهم لضمان ظهور نتائج في الفلاتر الصعبة
    payload = {"filter": [{"left": "volume", "operation": "greater", "right": 30000}], "columns": cols, "range": [0, 100]}
    if not scan_all and query_val:
        payload["filter"].append({"left": "name", "operation": "match", "right": query_val.upper()})
    
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except: return []

# ================== ANALYSIS LOGIC (V16.8 REBORN) ==================
def analyze_stock(d_row):
    try:
        d = d_row['d']
        name, p, rsi, v, avg_v, h, l, chg, desc, sma50, sma200 = d
        # حساب نقاط الارتكاز والدعوم والمقاومات
        pp = (h + l + p) / 3
        r1, s1 = (2 * pp) - l, (2 * pp) - h
        r2, s2 = pp + (h - l), pp - (h - l)
        
        ratio = v / (avg_v or 1)
        rsi_val = rsi or 0
        
        # تحديد التوصية
        if rsi_val < 40 and p > s1: status, cls = "🔴 شراء تدريجي", "status-buy"
        elif rsi_val > 70: status, cls = "⚠️ منطقة جني أرباح", "status-wait"
        elif p >= r1: status, cls = "🚀 اختراق قوي", "status-buy"
        else: status, cls = "⚪ انتظار المراجعة", "status-wait"

        # حساب السكور
        t_score = int(90 if rsi_val < 35 else 75 if rsi_val < 55 else 45)
        if p < pp: t_score -= 10

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "t_score": t_score, "status": status, "cls": cls,
            "pp": pp, "r1": r1, "r2": r2, "s1": s1, "s2": s2,
            "vol_txt": "🔥 زخم" if ratio > 1.5 else "⚪ هادئ",
            "is_gold": (ratio > 1.5 and 45 < rsi_val < 60),
            "is_break": (p >= h * 0.99 and ratio > 1.2),
            "is_chase": (p > pp and ratio > 1.3 and chg > 1) # تنبيه المطاردة
        }
    except: return None

# ================== UI RENDERER ==================
def render_stock_ui(res):
    st.markdown(f"### {res['name']} <span class='score-badge'>(T-Score: {res['t_score']})</span> <span class='{res['cls']}'>{res['status']}</span>", unsafe_allow_html=True)
    st.caption(res['desc'])
    
    # مستويات الدعم والمقاومة الجديدة
    cols = st.columns(4)
    cols[0].markdown(f"📉 دعم 2: <span class='support-val'>{res['s2']:.2f}</span>", unsafe_allow_html=True)
    cols[1].markdown(f"📉 دعم 1: <span class='support-val'>{res['s1']:.2f}</span>", unsafe_allow_html=True)
    cols[2].markdown(f"📈 مقاومة 1: <span class='resistance-val'>{res['r1']:.2f}</span>", unsafe_allow_html=True)
    cols[3].markdown(f"📈 مقاومة 2: <span class='resistance-val'>{res['r2']:.2f}</span>", unsafe_allow_html=True)
    
    st.divider()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    m2.metric("RSI", f"{res['rsi']:.1f}")
    m3.metric("الزخم", f"{res['ratio']:.1f}x", res['vol_txt'])

# ================== PAGES ==================
if st.session_state.page == 'home':
    st.title("🎯 Sniper Elite v16.8 Pro")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📡 تحليل سهم"): go_to('analyze')
        if st.button("🔭 كشاف السوق"): go_to('scanner')
    with c2:
        if st.button("🚀 رادار الاختراقات"): go_to('breakout')
        if st.button("💎 قنص الذهب"): go_to('gold')

elif st.session_state.page == 'scanner':
    if st.button("🏠 Home"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r)) and an['t_score'] >= 45:
            with st.expander(f"{an['name']} | {an['status']} | {an['p']} ج"): render_stock_ui(an)

elif st.session_state.page == 'breakout':
    if st.button("🏠 Home"): go_to('home')
    found = False
    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r)) and (an['is_break'] or an['is_chase']):
            found = True
            pref = "🔥 مطاردة" if an['is_chase'] else "🚀 اختراق"
            with st.expander(f"{pref}: {an['name']} | السعر: {an['p']}"): render_stock_ui(an)
    if not found: st.warning("لا توجد اختراقات حالية، تابع الكشاف.")

elif st.session_state.page == 'gold':
    if st.button("🏠 Home"): go_to('home')
    found = False
    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r)) and an['is_gold']:
            found = True
            with st.expander(f"💎 ذهب: {an['name']} | RSI: {an['rsi']:.1f}"): render_stock_ui(an)
    if not found: st.info("ابحث في الكشاف عن أسهم بسكور عالي حالياً.")
