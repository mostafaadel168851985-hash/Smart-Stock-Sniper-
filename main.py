import streamlit as st
import requests

# ================== CONFIG & STYLE (v13.1 PRO FILTER) ==================
st.set_page_config(page_title="EGX Sniper Elite v13.1", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-size: 18px !important; font-weight: bold !important; margin-bottom: 10px; }
    .stock-header { font-size: 20px !important; font-weight: bold; color: #58a6ff; }
    .price-callout { font-size: 16px !important; font-weight: bold; color: #3fb950; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 8px; padding: 5px !important; }
    .trend-pill { padding: 4px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; margin: 2px; display: inline-block; }
    .trend-up { background-color: rgba(63, 185, 80, 0.15); color: #3fb950; border: 1px solid #3fb950; }
    .trend-down { background-color: rgba(248, 81, 73, 0.15); color: #f85149; border: 1px solid #f85149; }
    .entry-card-new { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 15px; text-align: center; margin-bottom: 15px; border-top: 4px solid #3fb950; }
    .hist-box { background-color: #1c2128; border-radius: 8px; padding: 10px; border: 1px dashed #58a6ff; margin-bottom: 10px; font-size: 14px; }
    .vol-container { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 8px; text-align: center; }
    .breakout-card { border: 2px solid #00ffcc !important; background-color: #0a1a1a !important; border-radius: 12px; padding: 10px; margin-bottom: 10px; }
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
        d = d_row['d']
        name, p, rsi, v, avg_v, h, l, chg, desc, sma20, sma50, sma200, h_1m, l_1m, h_52w, l_52w, perf_w, perf_m = d
        
        if p is None: return None

        # ✳️ 4. منع الأسهم الضعيفة (Skip)
        if perf_w and perf_w < -5: return None
        
        # حساب الدعوم اللحظية
        pp = (p + h + l) / 3
        s1, r1 = (2 * pp) - h, (2 * pp) - l
        s2, r2 = pp - (h - l), pp + (h - l)
        
        # الاتجاهات
        trend_short = "صاعد" if sma20 and p > sma20 else "هابط"
        trend_med = "صاعد" if sma50 and p > sma50 else "هابط"
        trend_long = "صاعد" if sma200 and p > sma200 else "هابط"
        
        ratio = v / (avg_v or 1)
        rsi_val = rsi if rsi else 0
        
        # ✳️ 1. فلتر القمة السنوية الجديد
        at_year_high = (p >= h_52w * 0.97 and ratio > 1.2) if h_52w else False
        at_month_high = (p >= h_1m * 0.99) if h_1m else False
        
        # نظام الدخول
        near_support = p <= s1 * 1.02
        is_strong_break = (p > r1 and ratio > 1.3 and chg > 0.5 and trend_med == "صاعد")
        is_chase = (p > r1 * 1.02)

        if near_support: entry_min, entry_max = s1 * 0.99, s1 * 1.01
        elif is_strong_break: entry_min, entry_max = r1, r1 * 1.01
        else: entry_min, entry_max = p * 0.99, p * 1.01

        entry_avg = (entry_min + entry_max) / 2
        risk, reward = (entry_avg - s2), (r2 - entry_avg)
        rr = round(reward / risk, 2) if risk > 0 else 0

        # ================== 🧠 SMART SCORE (تعديلاتك) ==================
        smart_score = 0
        # ✳️ 3. فلتر الاتجاه الثلاثي
        if trend_short == "صاعد" and trend_med == "صاعد": smart_score += 10
        if trend_long == "صاعد": smart_score += 10
        
        # ✳️ 2. قوة الأداء
        if perf_m and perf_m > 10: smart_score += 10
        
        if ratio > 1.3: smart_score += 20
        if 40 <= rsi_val <= 65: smart_score += 15
        if at_year_high: smart_score += 20 
        if near_support: smart_score += 15
        if is_chase: smart_score -= 40
        
        smart_score = max(min(smart_score, 100), 0)

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "s1": s1, "s2": s2, "r1": r1, "r2": r2,
            "h_1m": h_1m, "l_1m": l_1m, "h_52w": h_52w, "l_52w": l_52w,
            "perf_w": perf_w, "perf_m": perf_m,
            "t_short": trend_short, "t_med": trend_med, "t_long": trend_long,
            "s_score": smart_score, "rr": rr, "rr_rating": "🔥 ممتازة" if rr >= 2 else "👍 مقبولة" if rr >= 1.5 else "⚠️ ضعيفة",
            "entry_min": entry_min, "entry_max": entry_max, "entry_avg": entry_avg,
            "stop_loss": s2, "target1": r1, "target2": r2,
            "at_year_high": at_year_high, "at_month_high": at_month_high,
            "is_strong_break": is_strong_break, "is_chase": is_chase
        }
    except: return None

# ================== UI RENDERER ==================
def render_stock_ui(res, title=""):
    if not res: return
    if title: st.markdown(f"<div class='breakout-card'>{title}</div>", unsafe_allow_html=True)
    
    st.markdown(f"<div class='stock-header'>{res['name']} | {res['desc'][:20]} <span style='color:#ffd700; float:left;'>Score: {res['s_score']}</span></div>", unsafe_allow_html=True)
    
    ts_cls = "trend-up" if res['t_short'] == "صاعد" else "trend-down"
    tm_cls = "trend-up" if res['t_med'] == "صاعد" else "trend-down"
    tl_cls = "trend-up" if res['t_long'] == "صاعد" else "trend-down"
    st.markdown(f"<span class='trend-pill {ts_cls}'>قصير: {res['t_short']}</span><span class='trend-pill {tm_cls}'>متوسط: {res['t_med']}</span><span class='trend-pill {tl_cls}'>طويل: {res['t_long']}</span>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        <div class='hist-box'>
        📅 <b>نطاق شهر:</b> {res['l_1m']:.2f} — {res['h_1m']:.2f}<br>
        🏆 <b>قمة سنة:</b> {res['h_52w']:.2f} 
        {"<span style='color:#00ffcc;'> (قوة اختراق!)</span>" if res['at_year_high'] else ""}
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class='hist-box'>
        📊 <b>أداء أسبوع:</b> {res['perf_w']:.1f}%<br>
        📈 <b>أداء شهر:</b> {res['perf_m']:.1f}%
        </div>
        """, unsafe_allow_html=True)

    m1, m2, m3 = st.columns(3)
    m1.metric("السعر الحالي", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    m2.metric("RSI", f"{res['rsi']:.1f}")
    with m3: st.markdown(f"<div class='vol-container'>الزخم: <b>{res['ratio']:.1f}x</b></div>", unsafe_allow_html=True)

    st.markdown(f"""
    <div class='entry-card-new'>
    🎯 <b>منطقة الدخول الذكية:</b> {res['entry_min']:.2f} → {res['entry_max']:.2f}<br>
    🛑 <b>وقف الخسارة (S2):</b> <span style='color:#f85149;'>{res['stop_loss']:.2f}</span><br>
    ⚖️ <b>النسبة RR:</b> 1 : {res['rr']} ({res['rr_rating']})
    </div>
    """, unsafe_allow_html=True)

# ================== NAVIGATION ==================
if st.session_state.page == 'home':
    st.title("🏹 EGX Sniper Elite v13.1")
    c1, c2 = st.columns(2)
    if c1.button("📡 تحليل سهم محدد"): go_to('analyze')
    if c2.button("🔭 كشاف السوق الكامل"): go_to('scanner')
    if c1.button("🚀 اختراقات تاريخية"): go_to('breakout')
    if st.button("🧮 مساعد المتوسطات"): go_to('average')

elif st.session_state.page == 'analyze':
    if st.button("🏠"): go_to('home')
    sym = st.text_input("رمز السهم").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data: 
            res = analyze_stock(data[0])
            if res: render_stock_ui(res)
            else: st.warning("السهم مستبعد حالياً بسبب ضعف الأداء (Perf.W < -5%)")
        else: st.error("سهم غير موجود")

elif st.session_state.page == 'scanner':
    if st.button("🏠"): go_to('home')
    if st.button("🔍 فحص الفرص"):
        data = fetch_egx_data(scan_all=True)
        results = [an for r in data if (an := analyze_stock(r)) and an['s_score'] >= 55]
        results.sort(key=lambda x: x['s_score'], reverse=True)
        for an in results:
            with st.expander(f"⭐ {an['s_score']} | {an['name']} | RR: {an['rr']}"): render_stock_ui(an)

elif st.session_state.page == 'breakout':
    if st.button("🏠"): go_to('home')
    data = fetch_egx_data(scan_all=True)
    found = False
    for r in data:
        an = analyze_stock(r)
        if an and (an['at_year_high'] or an['at_month_high']):
            tag = "🚀 اختراق قمة سنة (بزخم)" if an['at_year_high'] else "🔥 اختراق قمة شهر"
            render_stock_ui(an, tag)
            found = True
    if not found: st.write("لا توجد اختراقات تاريخية حالياً")

elif st.session_state.page == 'average':
    if st.button("🏠"): go_to('home')
    st.subheader("🧮 مساعد متوسط التكلفة")
    c1, c2, c3 = st.columns(3)
    old_p, old_q = c1.number_input("سعر الشراء القديم", 0.0), c2.number_input("كمية الأسهم", 0)
    new_p = c3.number_input("سعر الشراء الجديد", 0.0)
    if old_p > 0 and old_q > 0 and new_p > 0:
        total_old = old_p * old_q
        for label, q in [("تعديل بسيط (0.5x)", int(old_q*0.5)), ("تعديل متوازن (1:1)", old_q), ("تعديل قوي (2:1)", old_q*2)]:
            cost, avg = q * new_p, (total_old + (q * new_p)) / (old_q + q)
            st.markdown(f"**{label}**: متوسط جديد {avg:.3f} ج")
