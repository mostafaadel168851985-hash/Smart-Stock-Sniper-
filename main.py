import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="EGX Sniper Ultimate v15.7", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; font-size: 16px !important; font-weight: bold !important; margin-bottom: 10px; }
    .stock-header { font-size: 24px !important; font-weight: bold; color: #58a6ff; border-bottom: 2px solid #30363d; margin-bottom: 15px; }
    .score-tag { float: left; background: #238636; color: white; padding: 2px 15px; border-radius: 10px; font-size: 18px; }
    .trend-container { display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap; }
    .trend-box { padding: 5px 12px; border-radius: 6px; font-size: 13px; font-weight: bold; border: 1px solid #30363d; }
    .up { color: #3fb950; border-color: #3fb950; background: rgba(63, 185, 80, 0.1); }
    .down { color: #f85149; border-color: #f85149; background: rgba(248, 81, 73, 0.1); }
    .side { color: #adbac7; border-color: #adbac7; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 10px; padding: 10px !important; }
    .plan-card { background: #0d1117; border: 1px solid #3fb950; border-radius: 15px; padding: 20px; margin: 15px 0; border-top: 5px solid #3fb950; }
    .target-box { border: 2px solid #58a6ff; border-radius: 12px; padding: 15px; text-align: center; background: #0d1117; font-size: 20px; font-weight: bold; }
    .avg-section { background: #161b22; border: 1px solid #30363d; border-radius: 15px; padding: 25px; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'home'

# ================== 🔥 DATA ENGINE ==================
@st.cache_data(ttl=300)
def fetch_egx_data(symbol=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    cols = ["name","close","RSI","volume","average_volume_10d_calc","high","low","change","description","SMA20","SMA50","SMA200"]
    payload = {"filter": [{"left": "name", "operation": "match", "right": symbol.upper()}] if symbol else [], "columns": cols, "range": [0, 150] if scan_all else [0, 1]}
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except: return []

def get_trend_label(price, sma):
    if not sma: return "غير محدد", "side"
    if price > sma: return "صاعد ↑", "up"
    return "هابط ↓", "down"

def analyze_stock(d_row):
    try:
        d = d_row.get('d', [])
        name, p, rsi, v, avg_v, h, l, chg, desc, sma20, sma50, sma200 = d
        p, h, l = p or 0, h or p, l or p
        ratio = v / (avg_v or 1)
        
        # تحليل الاتجاهات الثلاثة
        short_t, short_c = get_trend_label(p, sma20)
        mid_t, mid_c = get_trend_label(p, sma50)
        long_t, long_c = get_trend_label(p, sma200)

        # حساب الأهداف (Pivot Points)
        pp = (p + h + l) / 3
        s1, r1 = (2 * pp) - h, (2 * pp) - l
        s2 = pp - (h - l)
        stop_loss = min(s2, p * 0.97) if s2 < p else p * 0.95
        target = r1 if p < r1 else r1 + (r1 - s1)
        
        return {
            "name": name, "p": p, "rsi": rsi or 0, "chg": chg or 0, "ratio": ratio,
            "stop_loss": stop_loss, "target": target, 
            "score": int((min(ratio, 2) * 20) + (rsi / 2 if rsi else 25)),
            "trends": {
                "short": (short_t, short_c),
                "mid": (mid_t, mid_c),
                "long": (long_t, long_c)
            }
        }
    except: return None

# ================== UI RENDERER ==================
def render_analysis(res):
    st.markdown(f"<div class='stock-header'>{res['name']} <span class='score-tag'>Score: {res['score']}</span></div>", unsafe_allow_html=True)
    
    # عرض الاتجاهات
    t = res['trends']
    st.markdown(f"""
        <div class='trend-container'>
            <div class='trend-box {t['short'][1]}'>قصير (20): {t['short'][0]}</div>
            <div class='trend-box {t['mid'][1]}'>متوسط (50): {t['mid'][0]}</div>
            <div class='trend-box {t['long'][1]}'>طويل (200): {t['long'][0]}</div>
        </div>
        """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("السيولة", f"{res['ratio']:.1f}x")
    c3.metric("RSI", f"{res['rsi']:.1f}")

    st.markdown(f"<div class='target-box'>🏁 الهدف المتوقع: {res['target']:.2f}</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='plan-card'>", unsafe_allow_html=True)
    st.subheader("💰 إدارة الصفقة")
    budget = st.number_input(f"ميزانية {res['name']}:", value=10000, step=1000, key=f"bid_{res['name']}")
    if res['p'] > 0:
        shares = int(budget / res['p'])
        profit = (res['target'] - res['p']) * shares
        loss = (res['p'] - res['stop_loss']) * shares
        col_p, col_l = st.columns(2)
        col_p.markdown(f"<div style='color:#3fb950; font-size:18px;'><b>✅ ربح:</b> {profit:,.2f} ج</div>", unsafe_allow_html=True)
        col_l.markdown(f"<div style='color:#f85149; font-size:18px;'><b>🛑 وقف:</b> {res['stop_loss']:.2f} ({loss:,.2f} ج)</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ================== NAVIGATION ==================
if st.session_state.page == 'home':
    st.title("🏹 Sniper Pro v15.7")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📡 تحليل سهم"): st.session_state.page = 'analyze'; st.rerun()
        if st.button("🔭 كشاف السوق"): st.session_state.page = 'scanner'; st.rerun()
    with col2:
        if st.button("🚀 الاختراقات"): st.session_state.page = 'breakout'; st.rerun()
        if st.button("🧮 حاسبة المتوسطات"): st.session_state.page = 'average'; st.rerun()

elif st.session_state.page == 'analyze':
    if st.button("🏠"): st.session_state.page = 'home'; st.rerun()
    sym = st.text_input("رمز السهم").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data:
            res = analyze_stock(data[0])
            if res: render_analysis(res)
        else: st.error("السهم غير موجود")

elif st.session_state.page == 'scanner':
    if st.button("🏠"): st.session_state.page = 'home'; st.rerun()
    raw_data = fetch_egx_data(scan_all=True)
    for r in raw_data:
        res = analyze_stock(r)
        if res and res['score'] >= 60:
            with st.expander(f"⭐ {res['score']} | {res['name']} | قصير: {res['trends']['short'][0]}"):
                render_analysis(res)

elif st.session_state.page == 'breakout':
    if st.button("🏠"): st.session_state.page = 'home'; st.rerun()
    raw_data = fetch_egx_data(scan_all=True)
    for r in raw_data:
        res = analyze_stock(r)
        if res and res['rsi'] > 60 and res['ratio'] > 1.2:
            with st.expander(f"🚀 {res['name']} | سيولة: {res['ratio']:.1f}x"):
                render_analysis(res)

elif st.session_state.page == 'average':
    if st.button("🏠"): st.session_state.page = 'home'; st.rerun()
    st.markdown("## 🧮 حاسبة المتوسطات")
    with st.container():
        st.markdown("<div class='avg-section'>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        p_old = c1.number_input("السعر القديم", value=0.0)
        q_old = c1.number_input("الكمية الحالية", value=0)
        p_new = c2.number_input("السعر الجديد", value=0.0)
        q_new = c2.number_input("الكمية الجديدة", value=0)
        if q_old + q_new > 0:
            avg = ((p_old * q_old) + (p_new * q_new)) / (q_old + q_new)
            st.markdown(f"<div class='result-text'>📊 المتوسط الجديد: {avg:.3f}</div>", unsafe_allow_html=True)
        st.markdown("<hr>", unsafe_allow_html=True)
        target_avg = st.number_input("المتوسط المستهدف", value=0.0)
        if target_avg > 0 and p_new > 0 and q_old > 0 and target_avg != p_new:
            needed = (q_old * (p_old - target_avg)) / (target_avg - p_new)
            if needed > 0:
                st.info(f"✅ للوصول لمتوسط {target_avg:.2f}: اشترِ {int(needed):,} سهم على {p_new:.2f}")
        st.markdown("</div>", unsafe_allow_html=True)
