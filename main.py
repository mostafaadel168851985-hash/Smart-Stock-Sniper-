import streamlit as st
import requests

# ================== CONFIG & STYLE (The UI You Loved) ==================
st.set_page_config(page_title="EGX Sniper Ultimate v13.7", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-size: 18px !important; font-weight: bold !important; margin-bottom: 10px; }
    .stock-header { font-size: 20px !important; font-weight: bold; color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 5px; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 8px; padding: 5px !important; }
    .trend-pill { padding: 4px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; margin: 2px; display: inline-block; }
    .trend-up { background-color: rgba(63, 185, 80, 0.15); color: #3fb950; border: 1px solid #3fb950; }
    .trend-down { background-color: rgba(248, 81, 73, 0.15); color: #f85149; border: 1px solid #f85149; }
    .entry-card-new { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 15px; text-align: center; margin-bottom: 15px; border-top: 4px solid #3fb950; }
    .avg-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-bottom: 12px; border-left: 5px solid #58a6ff; }
    .vol-container { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 8px; text-align: center; }
    .target-box { border: 2px solid #58a6ff; border-radius: 12px; padding: 15px; text-align: center; background: #0d1117; margin-top: 10px; }
    .plan-container { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-top: 15px; }
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
    cols = ["name","close","RSI","volume","average_volume_10d_calc","high","low","change","description","SMA20","SMA50","SMA200"]
    if scan_all:
        payload = {"filter": [{"left": "volume", "operation": "greater", "right": 5000}], "columns": cols, "sort": {"sortBy": "change", "sortOrder": "desc"}, "range": [0, 150]}
    else:
        payload = {"filter": [{"left": "name", "operation": "match", "right": symbol.upper()}], "columns": cols, "range": [0, 1]}
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except: return []

# ================== 🔥 ANALYSIS ENGINE ==================
def analyze_stock(d_row):
    try:
        d = d_row.get('d', [])
        if len(d) < 12: return None
        name, p, rsi, v, avg_v, h, l, chg, desc, sma20, sma50, sma200 = d
        if p is None: return None
        
        # الاتجاهات
        t_short = "صاعد" if (sma20 and p > sma20) else "هابط"
        t_med = "صاعد" if (sma50 and p > sma50) else "هابط"
        t_long = "صاعد" if (sma200 and p > sma200) else "هابط"
        
        # الدعم والمقاومة
        pp = (p + (h or p) + (l or p)) / 3
        s1, r1 = (2 * pp) - (h or p), (2 * pp) - (l or p)
        s2, r2 = pp - ((h or p) - (l or p)), pp + ((h or p) - (l or p))
        
        ratio = v / (avg_v or 1)
        rsi_val = rsi or 0
        
        # فلاتر الذهب والاختراق
        is_gold = (ratio > 1.5 and 45 < rsi_val < 65 and t_med == "صاعد")
        early_break = (p >= r1 * 0.97 and ratio > 1.1)
        strong_break = (p > r1 and ratio > 1.3)

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "s1": s1, "s2": s2, "r1": r1, "r2": r2,
            "t_short": t_short, "t_med": t_med, "t_long": t_long,
            "is_gold": is_gold, "early_break": early_break, "strong_break": strong_break,
            "stop_loss": s2, "target1": r1, "target2": r2
        }
    except: return None

# ================== UI RENDERER ==================
def render_stock_ui(res, title=""):
    if not res: return
    if title: st.info(title)
    
    st.markdown(f"<div class='stock-header'>{res['name']} | {res['desc'][:25]}</div>", unsafe_allow_html=True)
    
    ts_cls = "trend-up" if res['t_short'] == "صاعد" else "trend-down"
    tm_cls = "trend-up" if res['t_med'] == "صاعد" else "trend-down"
    tl_cls = "trend-up" if res['t_long'] == "صاعد" else "trend-down"
    st.markdown(f"<span class='trend-pill {ts_cls}'>قصير: {res['t_short']}</span><span class='trend-pill {tm_cls}'>متوسط: {res['t_med']}</span><span class='trend-pill {tl_cls}'>طويل: {res['t_long']}</span>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("RSI", f"{res['rsi']:.1f}")
    with c3: st.markdown(f"<div class='vol-container'>الزخم: <b>{res['ratio']:.1f}x</b></div>", unsafe_allow_html=True)

    st.markdown(f"""
    <div class='entry-card-new'>🎯 <b>نقطة الدخول الحالية:</b> {res['p']:.2f}<br>🛑 <b>وقف الخسارة:</b> {res['stop_loss']:.2f}</div>
    <div class='target-box'>🏁 <b>الأهداف المستهدفة:</b> {res['target1']:.2f} — {res['target2']:.2f}</div>
    """, unsafe_allow_html=True)

    # خطة السيولة الذكية لكل سهم
    st.subheader("🛠️ خطة السيولة")
    budget = st.number_input(f"الميزانية للسهم {res['name']}:", value=10000, key=res['name'])
    st.markdown(f"""
        <div class='plan-container'>
            ✅ <b>دخول أول (40%):</b> {budget*0.4:,.0f} ج عند {res['p']:.2f}<br>
            💎 <b>تدعيم عند الاختراق (30%):</b> {budget*0.3:,.0f} ج عند {res['target1']:.2f}<br>
            🛡️ <b>احتياطي للطوارئ (30%):</b> {budget*0.3:,.0f} ج
        </div>
    """, unsafe_allow_html=True)

# ================== NAVIGATION ==================
if st.session_state.page == 'home':
    st.title("🏹 EGX Sniper Ultimate v13.7")
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
        if data: render_stock_ui(analyze_stock(data[0]))
        else: st.error("لم يتم العثور على السهم")

elif st.session_state.page == 'scanner':
    if st.button("🏠"): go_to('home')
    data = fetch_egx_data(scan_all=True)
    for r in data:
        an = analyze_stock(r)
        if an and an['p'] > 0.5:
            with st.expander(f"{an['name']} | السعر: {an['p']}"): render_stock_ui(an)

elif st.session_state.page == 'gold':
    if st.button("🏠"): go_to('home')
    data = fetch_egx_data(scan_all=True)
    for r in data:
        an = analyze_stock(r)
        if an and an['is_gold']: render_stock_ui(an, "💎 فرصة ذهبية")

elif st.session_state.page == 'breakout':
    if st.button("🏠"): go_to('home')
    data = fetch_egx_data(scan_all=True)
    for r in data:
        an = analyze_stock(r)
        if an:
            if an['strong_break']: render_stock_ui(an, "🚀 اختراق قوي")
            elif an['early_break']: render_stock_ui(an, "🟡 اختراق مبكر")

elif st.session_state.page == 'average':
    if st.button("🏠"): go_to('home')
    st.subheader("🧮 مساعد متوسط التكلفة الذكي")
    c1, c2, c3 = st.columns(3)
    old_p = c1.number_input("سعر الشراء القديم", 0.0)
    old_q = c2.number_input("كمية الأسهم", 0)
    new_p = c3.number_input("سعر الشراء الجديد", 0.0)
    if old_p > 0 and old_q > 0 and new_p > 0:
        for label, q in [("تعديل بسيط (0.5x)", int(old_q*0.5)), ("تعديل متوازن (1:1)", old_q), ("تعديل قوي (2:1)", old_q*2)]:
            avg = ((old_p * old_q) + (q * new_p)) / (old_q + q)
            st.markdown(f"<div class='avg-card'><b>{label}</b>: شراء {q:,} سهم<br>المتوسط الجديد: {avg:.3f} ج</div>", unsafe_allow_html=True)
