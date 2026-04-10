import streamlit as st
import requests

# ================== CONFIG & STYLE (v13.3 GOLD RECOVERY) ==================
st.set_page_config(page_title="EGX Sniper Elite v13.3", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-size: 18px !important; font-weight: bold !important; margin-bottom: 10px; }
    .stock-header { font-size: 20px !important; font-weight: bold; color: #58a6ff; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 8px; padding: 5px !important; }
    .trend-pill { padding: 4px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; margin: 2px; display: inline-block; }
    .trend-up { background-color: rgba(63, 185, 80, 0.15); color: #3fb950; border: 1px solid #3fb950; }
    .trend-down { background-color: rgba(248, 81, 73, 0.15); color: #f85149; border: 1px solid #f85149; }
    .entry-card-new { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 15px; text-align: center; margin-bottom: 15px; border-top: 4px solid #3fb950; }
    .hist-box { background-color: #1c2128; border-radius: 8px; padding: 10px; border: 1px dashed #58a6ff; margin-bottom: 10px; font-size: 14px; }
    .vol-container { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 8px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'home'
def go_to(page_name):
    st.session_state.page = page_name
    st.rerun()

# ================== 🔥 DATA ENGINE ==================
@st.cache_data(ttl=300)
def fetch_egx_data(symbol=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    cols = [
        "name","close","RSI","volume","average_volume_10d_calc","high","low","change","description",
        "SMA20","SMA50","SMA200",
        "high_1M", "low_1M", "Price_52_Week_High", "Price_52_Week_Low", "Perf.W", "Perf.M"
    ]
    if scan_all:
        payload = {
            "filter": [{"left": "volume", "operation": "greater", "right": 10000}, {"left": "close", "operation": "greater", "right": 0.4}],
            "columns": cols, "sort": {"sortBy": "change", "sortOrder": "desc"}, "range": [0, 150]
        }
    else:
        payload = {"symbols": {"tickers": [f"EGX:{symbol.upper()}"]}, "columns": cols}
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except: return []

# ================== 🔥 ANALYSIS ENGINE ==================
def analyze_stock(d_row):
    try:
        d = d_row.get('d', [])
        if len(d) < 17: return None
        
        name, p, rsi, v, avg_v, h, l, chg, desc, sma20, sma50, sma200, h_1m, l_1m, h_52w, l_52w, perf_w, perf_m = d
        
        if p is None: return None
        if perf_w is not None and perf_w < -5: return None
        
        pp = (p + (h or p) + (l or p)) / 3
        s1, r1 = (2 * pp) - (h or p), (2 * pp) - (l or p)
        s2, r2 = pp - ((h or p) - (l or p)), pp + ((h or p) - (l or p))
        
        trend_short = "صاعد" if (sma20 and p > sma20) else "هابط"
        trend_med = "صاعد" if (sma50 and p > sma50) else "هابط"
        trend_long = "صاعد" if (sma200 and p > sma200) else "هابط"
        
        ratio = v / (avg_v or 1)
        rsi_val = rsi if rsi else 0
        
        # فلاتر القمة والذهب
        at_year_high = (h_52w and p >= h_52w * 0.97 and ratio > 1.2)
        at_month_high = (h_1m and p >= h_1m * 0.98 and ratio > 1.1)
        is_gold = (ratio > 1.5 and 45 < rsi_val < 65 and trend_med == "صاعد")

        near_support = p <= s1 * 1.02
        is_strong_break = (p > r1 and ratio > 1.3 and chg > 0.5)

        if near_support: entry_min, entry_max = s1 * 0.99, s1 * 1.01
        elif is_strong_break: entry_min, entry_max = r1, r1 * 1.01
        else: entry_min, entry_max = p * 0.99, p * 1.01

        entry_avg = (entry_min + entry_max) / 2
        risk = max(entry_avg - s2, 0.01)
        reward = max(r2 - entry_avg, 0.01)
        rr = round(reward / risk, 2)

        smart_score = 0
        if trend_short == "صاعد" and trend_med == "صاعد": smart_score += 10
        if trend_long == "صاعد": smart_score += 10
        if perf_m and perf_m > 10: smart_score += 10
        if ratio > 1.3: smart_score += 20
        if 40 <= rsi_val <= 65: smart_score += 15
        if at_year_high: smart_score += 20 
        if near_support: smart_score += 15
        
        smart_score = max(min(smart_score, 100), 0)

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "s1": s1, "s2": s2, "r1": r1, "r2": r2,
            "h_1m": h_1m, "l_1m": l_1m, "h_52w": h_52w, "l_52w": l_52w,
            "perf_w": perf_w, "perf_m": perf_m, "is_gold": is_gold,
            "t_short": trend_short, "t_med": trend_med, "t_long": trend_long,
            "s_score": smart_score, "rr": rr, "rr_rating": "🔥 ممتازة" if rr >= 2 else "👍 مقبولة" if rr >= 1.5 else "⚠️ ضعيفة",
            "entry_min": entry_min, "entry_max": entry_max, "entry_avg": entry_avg,
            "stop_loss": s2, "target1": r1, "target2": r2,
            "at_year_high": at_year_high, "at_month_high": at_month_high
        }
    except: return None

# ================== UI RENDERER ==================
def render_stock_ui(res, title=""):
    if not res: return
    if title: st.info(title)
    
    st.markdown(f"<div class='stock-header'>{res['name']} | {res['desc'][:20]} <span style='color:#ffd700; float:left;'>Score: {res['s_score']}</span></div>", unsafe_allow_html=True)
    
    ts_cls = "trend-up" if res['t_short'] == "صاعد" else "trend-down"
    tm_cls = "trend-up" if res['t_med'] == "صاعد" else "trend-down"
    tl_cls = "trend-up" if res['t_long'] == "صاعد" else "trend-down"
    st.markdown(f"<span class='trend-pill {ts_cls}'>قصير: {res['t_short']}</span><span class='trend-pill {tm_cls}'>متوسط: {res['t_med']}</span><span class='trend-pill {tl_cls}'>طويل: {res['t_long']}</span>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        l1m = res['l_1m'] if res['l_1m'] else 0
        h1m = res['h_1m'] if res['h_1m'] else 0
        h52 = res['h_52w'] if res['h_52w'] else 0
        st.markdown(f"<div class='hist-box'>📅 <b>شهر:</b> {l1m:.2f} - {h1m:.2f}<br>🏆 <b>سنة:</b> {h52:.2f}</div>", unsafe_allow_html=True)
    with c2:
        pw = res['perf_w'] if res['perf_w'] else 0
        pm = res['perf_m'] if res['perf_m'] else 0
        st.markdown(f"<div class='hist-box'>📊 <b>أسبوع:</b> {pw:.1f}%<br>📈 <b>شهر:</b> {pm:.1f}%</div>", unsafe_allow_html=True)

    m1, m2, m3 = st.columns(3)
    m1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    m2.metric("RSI", f"{res['rsi']:.1f}")
    with m3: st.markdown(f"<div class='vol-container'>الزخم: <b>{res['ratio']:.1f}x</b></div>", unsafe_allow_html=True)

    st.markdown(f"<div class='entry-card-new'>🎯 <b>الدخول:</b> {res['entry_min']:.2f} → {res['entry_max']:.2f}<br>🛑 <b>الوقف:</b> {res['stop_loss']:.2f}<br>⚖️ <b>النسبة:</b> 1:{res['rr']} ({res['rr_rating']})</div>", unsafe_allow_html=True)

# ================== NAVIGATION ==================
if st.session_state.page == 'home':
    st.title("🏹 EGX Sniper Elite v13.3")
    c1, c2 = st.columns(2)
    if c1.button("📡 تحليل سهم"): go_to('analyze')
    if c2.button("🔭 كشاف السوق"): go_to('scanner')
    if c1.button("🚀 الاختراقات"): go_to('breakout')
    if c2.button("💎 قنص الذهب"): go_to('gold')
    if st.button("🧮 مساعد المتوسطات"): go_to('average')

elif st.session_state.page == 'analyze':
    if st.button("🏠"): go_to('home')
    sym = st.text_input("رمز السهم").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data: 
            res = analyze_stock(data[0])
            if res: render_stock_ui(res)
            else: st.warning("السهم مستبعد حالياً")
        else: st.error("سهم غير موجود")

elif st.session_state.page == 'scanner':
    if st.button("🏠"): go_to('home')
    if st.button("🔍 فحص"):
        data = fetch_egx_data(scan_all=True)
        if data:
            results = [an for r in data if (an := analyze_stock(r)) and an['s_score'] >= 55]
            results.sort(key=lambda x: x['s_score'], reverse=True)
            for an in results:
                with st.expander(f"⭐ {an['s_score']} | {an['name']}"): render_stock_ui(an)

elif st.session_state.page == 'breakout':
    if st.button("🏠"): go_to('home')
    data = fetch_egx_data(scan_all=True)
    if data:
        for r in data:
            an = analyze_stock(r)
            if an and (an['at_year_high'] or an['at_month_high']):
                render_stock_ui(an, "🚀 اختراق قمة")

elif st.session_state.page == 'gold':
    if st.button("🏠"): go_to('home')
    data = fetch_egx_data(scan_all=True)
    found = False
    if data:
        for r in data:
            an = analyze_stock(r)
            if an and an['is_gold']:
                render_stock_ui(an, "💎 سهم ذهبي")
                found = True
    if not found: st.write("لا يوجد فرص ذهبية حالياً")

elif st.session_state.page == 'average':
    if st.button("🏠"): go_to('home')
    st.subheader("🧮 مساعد المتوسطات")
    c1, c2, c3 = st.columns(3)
    old_p, old_q = c1.number_input("سعر الشراء", 0.0), c2.number_input("الكمية", 0)
    new_p = c3.number_input("السعر الجديد", 0.0)
    if old_p > 0 and old_q > 0 and new_p > 0:
        for label, q in [("0.5x", int(old_q*0.5)), ("1:1", old_q), ("2:1", old_q*2)]:
            avg = ((old_p * old_q) + (q * new_p)) / (old_q + q)
            st.write(f"**{label}**: متوسط جديد {avg:.3f}")
