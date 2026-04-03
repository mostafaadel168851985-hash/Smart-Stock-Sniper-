import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="EGX Sniper Elite v9.2", layout="wide")

st.markdown("""
    <style>
    button[data-baseweb="tab"] { padding-left: 2px !important; padding-right: 2px !important; margin-right: 2px !important; font-size: 11px !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 2px !important; }
    .stock-header { font-size: 18px !important; font-weight: bold; color: #58a6ff; }
    .price-callout { font-size: 18px !important; font-weight: bold; color: #3fb950; }
    .stoploss-callout { font-size: 16px !important; font-weight: bold; color: #f85149; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 8px; }
    div[data-testid="stExpander"] { border: 1px solid #30363d; background-color: #0d1117; }
    .warning-box { background-color: #2e2a0b; border: 1px solid #ffd700; color: #ffd700; padding: 12px; border-radius: 8px; margin: 10px 0; font-weight: bold; border-left: 5px solid #ffd700; }
    .breakout-card { border: 2px solid #00ffcc !important; background-color: #0a1a1a !important; border-radius: 12px; padding: 10px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# ================== DATA ENGINE ==================
@st.cache_data(ttl=300)
def fetch_egx_data(symbol=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    if scan_all:
        payload = {
            "filter": [{"left": "volume", "operation": "greater", "right": 50000}, {"left": "close", "operation": "greater", "right": 0.4}],
            "columns": ["name", "close", "RSI", "volume", "average_volume_10d_calc", "high", "low", "change", "description"],
            "sort": {"sortBy": "change", "sortOrder": "desc"}, "range": [0, 100]
        }
    else:
        payload = {
            "symbols": {"tickers": [f"EGX:{symbol.upper()}"], "query": {"types": []}},
            "columns": ["close", "high", "low", "volume", "RSI", "average_volume_10d_calc", "change", "description"]
        }
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except: return []

# ================== ANALYSIS LOGIC ==================
def analyze_stock(d_row, is_scan=False):
    try:
        d = d_row['d']
        if is_scan: name, p, rsi, v, avg_v, h, l, chg, desc = d
        else: p, h, l, v, rsi, avg_v, chg, desc = d; name = ""
        
        if p is None or h is None or l is None: return None
        
        pp = (p + h + l) / 3
        s1, r1 = (2 * pp) - h, (2 * pp) - l
        
        ratio = v / (avg_v or 1)
        rsi_val = rsi if rsi is not None else 0
        
        # الفرصة الذهبية (معادلتك الأصلية)
        is_gold = (ratio > 1.6 and 48 < rsi_val < 66 and chg > 0.5 and p > ((h + l) / 2))
        
        # الاختراق المؤكد (إضافة v9.2)
        # السعر قفل فوق r1 + سيولة أعلى من المتوسط بـ 20% + RSI فوق 50
        is_breakout = (p > r1 * 0.998 and ratio > 1.2 and rsi_val > 50)

        t_score = int(90 if rsi_val < 38 else 75 if rsi_val < 55 else 40)
        
        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "t_e": s1, "t_t": r1, "t_s": s1 * 0.98, "t_score": t_score, "is_gold": is_gold, "is_break": is_breakout
        }
    except: return None

# ================== UI COMPONENTS ==================
def render_stock_ui(res, is_break=False):
    if not res: return
    
    if is_break:
        st.markdown(f"<div class='breakout-card'>🚀 <b>اختراق حقيقي: {res['name']}</b></div>", unsafe_allow_html=True)

    st.markdown(f"""
        <div style='display: flex; justify-content: space-between; align-items: center;'>
            <span class='stock-header'>{res['name']} {res['desc'][:15]}</span>
        </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("RSI", f"{res['rsi']:.1f}")
    c3.metric("الزخم", f"{res['ratio']:.1f}x")
    
    daily_entry_top = res['t_e'] * 1.008
    safety_limit = daily_entry_top * 1.01 
    
    if res['p'] > safety_limit:
        st.markdown(f"<div class='warning-box'>⚠️ تنبيه: السعر ({res['p']:.2f}) بعيد عن نطاق الدخول الآمن ({daily_entry_top:.2f})</div>", unsafe_allow_html=True)
    
    st.divider()
    st.markdown(f"🎯 نطاق دخول: <span class='price-callout'>{res['t_e']:.2f} - {daily_entry_top:.2f}</span>", unsafe_allow_html=True)
    st.markdown(f"🎯 هدف أول: <span class='price-callout'>{res['t_t']:.2f}</span>", unsafe_allow_html=True)
    st.markdown(f"🛑 وقف خسارة: <span class='stoploss-callout'>{res['t_s']:.2f}</span>", unsafe_allow_html=True)

# ================== MAIN APP STRUCTURE ==================
st.title("🏹 EGX Sniper Elite v9.2")

tab1, tab2, tab3, tab4 = st.tabs(["📡 تحليل سهم", "🔭 للمراقبة", "🧮 حساب المتوسط", "💎 قنص الذهب"])

with tab1:
    sym = st.text_input("ادخل كود السهم").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data:
            an = analyze_stock(data[0])
            if an: render_stock_ui(an)

with tab2:
    col_l, col_r = st.columns(2)
    with col_l:
        scan_btn = st.button("🔍 فحص سريع")
    with col_r:
        break_btn = st.button("🚀 كشف الاختراقات")

    if scan_btn:
        all_d = fetch_egx_data(scan_all=True)
        for r in all_d:
            an = analyze_stock(r, is_scan=True)
            if an and (an['rsi'] > 45 and an['ratio'] > 1):
                with st.expander(f"📊 {an['name']} | {an['p']}"): render_stock_ui(an)
                
    if break_btn:
        all_d = fetch_egx_data(scan_all=True)
        found = False
        for r in all_d:
            an = analyze_stock(r, is_scan=True)
            if an and an['is_break']:
                found = True
                render_stock_ui(an, is_break=True)
        if not found: st.warning("لا توجد اختراقات مؤكدة حالياً.")

with tab3:
    st.subheader("🧮 حاسبة متوسط التكلفة")
    c1, c2, c3 = st.columns(3)
    op, oq, np = c1.number_input("سعرك", 0.0), c2.number_input("كميتك", 0), c3.number_input("جديد", 0.0)
    if op > 0 and oq > 0 and np > 0:
        target = st.number_input("المستهدف؟", value=op-0.01)
        needed = (oq * (op - target)) / (target - np)
        st.success(f"اشتري {int(needed):,} سهم")

with tab4:
    if st.button("صيد الذهب الآن 🏹"):
        all_d = fetch_egx_data(scan_all=True)
        for r in all_d:
            an = analyze_stock(r, is_scan=True)
            if an and an['is_gold']:
                st.markdown("<div class='warning-box'>💎 فرصة ذهبية</div>", unsafe_allow_html=True)
                render_stock_ui(an)
