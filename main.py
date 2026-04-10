import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="EGX Sniper Elite v14.0", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-size: 18px !important; font-weight: bold !important; margin-bottom: 10px; }
    .stock-header { font-size: 22px !important; font-weight: bold; color: #58a6ff; border-bottom: 2px solid #30363d; padding-bottom: 5px; }
    .score-tag { float: left; background: #238636; color: white; padding: 2px 12px; border-radius: 10px; font-size: 16px; margin-top: 5px; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 8px; padding: 5px !important; }
    .trend-pill { padding: 4px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; margin: 2px; display: inline-block; }
    .trend-up { background-color: rgba(63, 185, 80, 0.15); color: #3fb950; border: 1px solid #3fb950; }
    .trend-down { background-color: rgba(248, 81, 73, 0.15); color: #f85149; border: 1px solid #f85149; }
    .signal-pill { padding: 5px 15px; border-radius: 20px; font-weight: bold; display: inline-block; margin: 10px 0; }
    .buy { background: rgba(63, 185, 80, 0.2); color: #3fb950; border: 1px solid #3fb950; }
    .wait { background: rgba(240, 139, 55, 0.2); color: #f08b37; border: 1px solid #f08b37; }
    .sell { background: rgba(248, 81, 73, 0.2); color: #f85149; border: 1px solid #f85149; }
    .entry-card-new { background-color: #0d1117; border: 1px solid #3fb950; border-radius: 12px; padding: 15px; text-align: center; margin-bottom: 15px; border-top: 4px solid #3fb950; }
    .target-box { border: 2px solid #58a6ff; border-radius: 12px; padding: 15px; text-align: center; background: #0d1117; margin-top: 10px; }
    .plan-container { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-top: 15px; }
    .profit-text { color: #3fb950; font-weight: bold; }
    .loss-text { color: #f85149; font-weight: bold; }
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
        
        t_short = "صاعد" if (sma20 and p > sma20) else "هابط"
        t_med = "صاعد" if (sma50 and p > sma50) else "هابط"
        t_long = "صاعد" if (sma200 and p > sma200) else "هابط"
        
        rsi_val = rsi or 0
        if rsi_val > 70: signal, sig_cls = "تشبع شراء ⚠️", "sell"
        elif rsi_val < 35: signal, sig_cls = "مبالغ في بيعه 📡", "buy"
        elif t_short == "صاعد": signal, sig_cls = "شراء ✅", "buy"
        else: signal, sig_cls = "انتظار ⏳", "wait"

        ratio = v / (avg_v or 1)
        vol_icon = "🔥 انفجاري" if ratio > 1.5 else "⚪ هادئ"
        
        score = 0
        if t_med == "صاعد": score += 30
        if ratio > 1.2: score += 30
        if 40 < rsi_val < 65: score += 20
        if chg > 0: score += 20

        pp = (p + (h or p) + (l or p)) / 3
        s1, r1 = (2 * pp) - (h or p), (2 * pp) - (l or p)
        s2 = pp - ((h or p) - (l or p))
        
        entry_min, entry_max = s1 * 0.99, s1 * 1.01
        if p > r1: entry_min, entry_max = r1, r1 * 1.01 

        is_gold = (ratio > 1.5 and 45 < rsi_val < 65 and t_med == "صاعد")
        early_break = (p >= r1 * 0.97 and ratio > 1.1)
        strong_break = (p > r1 and ratio > 1.3)

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "s1": s1, "s2": s2, "r1": r1, "score": score,
            "vol_icon": vol_icon, "signal": signal, "sig_cls": sig_cls,
            "t_short": t_short, "t_med": t_med, "t_long": t_long,
            "is_gold": is_gold, "early_break": early_break, "strong_break": strong_break,
            "entry_range": f"{entry_min:.2f} - {entry_max:.2f}",
            "stop_loss": s2, "target1": r1
        }
    except: return None

# ================== UI RENDERER ==================
def render_stock_ui(res, title=""):
    if not res: return
    if title: st.info(title)
    
    st.markdown(f"<div class='stock-header'>{res['name']} | {res['desc'][:25]} <span class='score-tag'>Score: {res['score']}</span></div>", unsafe_allow_html=True)
    st.markdown(f"<span class='signal-pill {res['sig_cls']}'>{res['signal']}</span>", unsafe_allow_html=True)
    
    ts_cls = "trend-up" if res['t_short'] == "صاعد" else "trend-down"
    tm_cls = "trend-up" if res['t_med'] == "صاعد" else "trend-down"
    tl_cls = "trend-up" if res['t_long'] == "صاعد" else "trend-down"
    st.markdown(f"<div><span class='trend-pill {ts_cls}'>قصير: {res['t_short']}</span><span class='trend-pill {tm_cls}'>متوسط: {res['t_med']}</span><span class='trend-pill {tl_cls}'>طويل: {res['t_long']}</span></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("RSI", f"{res['rsi']:.1f}")
    with c3: st.markdown(f"<div class='vol-container'>الزخم: <b>{res['ratio']:.1f}x</b><br>{res['vol_icon']}</div>", unsafe_allow_html=True)

    st.markdown(f"""
    <div class='entry-card-new'>🎯 <b>نطاق الدخول:</b> {res['entry_range']}<br>🛑 <b>وقف الخسارة:</b> {res['stop_loss']:.2f}</div>
    <div class='target-box'>🏁 <b>الهدف:</b> {res['target1']:.2f}</div>
    """, unsafe_allow_html=True)

    # خطة السيولة والربح والخسارة
    st.subheader("🛠️ إدارة المخاطر والسيولة")
    budget = st.number_input(f"الميزانية (جنيه) للسهم {res['name']}:", value=10000, key=f"bud_{res['name']}")
    
    # حسابات الربح والخسارة بالجنيه
    num_shares = budget / res['p']
    potential_profit_val = (res['target1'] - res['p']) * num_shares
    potential_loss_val = (res['p'] - res['stop_loss']) * num_shares
    profit_pct = ((res['target1'] / res['p']) - 1) * 100
    loss_pct = (1 - (res['stop_loss'] / res['p'])) * 100

    st.markdown(f"""
        <div class='plan-container'>
            💰 <b>الكمية المتاحة:</b> {int(num_shares):,} سهم<br><br>
            <span class='profit-text'>📈 الربح المتوقع عند الهدف:</span> {potential_profit_val:,.2f} ج ({profit_pct:.1f}%)<br>
            <span class='loss-text'>📉 الخسارة المتوقعة عند الوقف:</span> {potential_loss_val:,.2f} ج ({loss_pct:.1f}%)<br><hr>
            ✅ <b>دخول أول (50%):</b> {budget*0.5:,.0f} ج | تشتري {int((budget*0.5)/res['p']):,} سهم<br>
            🛡️ <b>احتياطي تدعيم (50%):</b> {budget*0.5:,.0f} ج
        </div>
    """, unsafe_allow_html=True)

# ================== NAVIGATION ==================
if st.session_state.page == 'home':
    st.title("🏹 Sniper Elite v14.0")
    c1, c2 = st.columns(2)
    if c1.button("📡 تحليل سهم"): go_to('analyze')
    if c2.button("🔭 كشاف السوق"): go_to('scanner')
    if c1.button("🚀 الاختراقات"): go_to('breakout')
    if c2.button("💎 قنص الذهب"): go_to('gold')
    if st.button("🧮 مساعد المتوسطات والخطة"): go_to('average')

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
        if an and an['score'] >= 50:
            with st.expander(f"⭐ {an['score']} | {an['name']} | {an['signal']}"): render_stock_ui(an)

elif st.session_state.page == 'gold':
    if st.button("🏠"): go_to('home')
    data = fetch_egx_data(scan_all=True)
    st.subheader("💎 قائمة قنص الذهب (سيولة + اتجاه)")
    for r in data:
        an = analyze_stock(r)
        if an and an['is_gold']:
            with st.expander(f"✨ {an['name']} | السعر: {an['p']}"): render_stock_ui(an)

elif st.session_state.page == 'breakout':
    if st.button("🏠"): go_to('home')
    data = fetch_egx_data(scan_all=True)
    st.subheader("🚀 قائمة الاختراقات المبكرة والقوية")
    for r in data:
        an = analyze_stock(r)
        if an:
            if an['strong_break']:
                with st.expander(f"🔥 اختراق قوي | {an['name']}"): render_stock_ui(an)
            elif an['early_break']:
                with st.expander(f"🟡 اختراق مبكر | {an['name']}"): render_stock_ui(an)

elif st.session_state.page == 'average':
    if st.button("🏠"): go_to('home')
    st.header("🧮 حاسبة المتوسط المستهدف")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🛠️ الوصول للمتوسط المطلوب")
        curr_p = st.number_input("سعر السهم القديم", value=0.0)
        curr_q = st.number_input("الكمية الحالية", value=0)
        market_p = st.number_input("سعر السوق الحالي", value=0.0)
        target_avg = st.number_input("المتوسط المستهدف", value=0.0)
        if curr_p > 0 and market_p < target_avg < curr_p:
            req_q = (curr_q * (curr_p - target_avg)) / (target_avg - market_p)
            st.success(f"للوصول لمتوسط {target_avg:.2f}: اشتر {int(req_q):,} سهم بتكلفة {req_q * market_p:,.0f} ج")
    with col2:
        st.subheader("📊 توزيع مبلغ جديد")
        cash = st.number_input("المبلغ المتاح للتعديل (ج)", value=5000)
        if cash > 0 and market_p > 0:
            st.info(f"بهذا المبلغ تشتري {int(cash/market_p):,} سهم إضافي.")
