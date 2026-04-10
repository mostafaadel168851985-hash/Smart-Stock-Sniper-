import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="EGX Sniper Pro v15.7", layout="wide")

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
    .buy-strong { background: #238636; color: white; border: 1px solid #3fb950; }
    .buy-caution { background: rgba(240, 139, 55, 0.2); color: #f08b37; border: 1px solid #f08b37; }
    .wait { background: #161b22; color: #8b949e; border: 1px solid #30363d; }
    .entry-card-new { background-color: #0d1117; border: 1px solid #3fb950; border-radius: 12px; padding: 15px; text-align: center; margin-bottom: 15px; border-top: 4px solid #3fb950; }
    .target-box { border: 2px solid #58a6ff; border-radius: 12px; padding: 15px; text-align: center; background: #0d1117; margin-top: 10px; }
    .plan-container { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-top: 15px; }
    .rr-tag { font-size: 16px; font-weight: bold; color: #58a6ff; background: rgba(88, 166, 255, 0.1); padding: 5px 12px; border-radius: 8px; border: 1px solid rgba(88, 166, 255, 0.3); }
    .rr-label { font-size: 14px; font-weight: bold; margin-right: 5px; padding: 2px 8px; border-radius: 5px; }
    .rr-excellent { background: #238636; color: white; }
    .rr-good { background: #2ea043; color: white; }
    .rr-fair { background: #d29922; color: white; }
    .rr-bad { background: #f85149; color: white; }
    .avg-section { background: rgba(88, 166, 255, 0.05); border-left: 4px solid #58a6ff; padding: 15px; border-radius: 8px; margin: 10px 0; }
    .pnl-box { background: #0d1117; border: 1px solid #30363d; padding: 10px; border-radius: 8px; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# استدعاء الوضع المختار من الـ Sidebar ليكون متاحاً في كل الصفحات
with st.sidebar:
    st.header("🧠 إعدادات القناص")
    trading_mode = st.radio(
        "أسلوب التداول الحالي:",
        ["🛡️ محافظ (محترف)", "⚖️ متوازن", "🚀 هجومي"],
        help="🛡️ يركز على أعلى جودة فقط\n⚖️ توازن بين المخاطرة والفرص\n🚀 يبحث عن أي فرصة دخول إيجابية"
    )

if 'page' not in st.session_state: st.session_state.page = 'home'

# ================== 🔥 HELPER FUNCTIONS ==================
def get_rr_status(rr):
    if rr >= 3: return "فرصة ذهبية 🏆", "rr-excellent"
    elif rr >= 2: return "صفقة ممتازة ✅", "rr-good"
    elif rr >= 1.8: return "مقبول 👍", "rr-fair"
    else: return "خطر / عائد ضعيف ⚠️", "rr-bad"

def get_final_decision(res):
    rr = res["rr"]
    trend = res["t_med"]
    t_long = res["t_long"]
    ratio = res["ratio"]
    
    if t_long == "هابط" and rr < 2:
        return "⚠️ اتجاه عام هابط", "#d29922"
    if rr < 1.2: 
        return "🚫 صفقة سيئة جداً", "#6e7681"
    if rr >= 2.5 and trend == "صاعد" and ratio > 1.5: 
        return "🚀 فرصة قوية جدًا", "#0f5132"
    elif rr >= 2 and trend == "صاعد": 
        return "🟢 ادخل دلوقتي", "#238636"
    elif rr >= 1.5 and trend == "صاعد": 
        return "🟡 راقب", "#d29922"
    else: 
        return "🔴 ابعد", "#f85149"

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

# ================== 🔥 ANALYSIS ENGINE (MODIFIED FOR MODES) ==================
def analyze_stock(d_row, is_scanner=False):
    try:
        d = d_row.get('d', [])
        if not d or len(d) < 12: return None
        name, p, rsi, v, avg_v, h, l, chg, desc, sma20, sma50, sma200 = d
        if p is None: return None
        
        ratio = v / (avg_v or 1)
        t_short = "صاعد" if (sma20 and p > sma20) else "هابط"
        t_med = "صاعد" if (sma50 and p > sma50) else "هابط"
        t_long = "صاعد" if (sma200 and p > sma200) else "هابط"

        pp = (p + (h or p) + (l or p)) / 3
        s1, r1 = (2 * pp) - (h or p), (2 * pp) - (l or p)
        s2 = pp - ((h or p) - (l or p))
        
        if p < r1: entry_min, entry_max = s1, s1 * 1.01
        elif p <= r1 * 1.02: entry_min, entry_max = r1, r1 * 1.01
        else: entry_min, entry_max = p * 0.99, p
        
        entry_price = (entry_min + entry_max) / 2
        stop_loss = min(s2, entry_price * 0.97)
        range_size = r1 - s1
        target = r1 if p < r1 else r1 + (range_size * 0.7) 

        profit_per_share = target - entry_price
        loss_per_share = entry_price - stop_loss
        if loss_per_share <= 0: return None
        rr = round(profit_per_share / loss_per_share, 2)

        # --- 🧠 2. تطبيق شروط الـ Mode في الكشاف ---
        if is_scanner:
            if trading_mode == "🛡️ محافظ (محترف)":
                if rr < 1.8 or t_med != "صاعد": return None
            elif trading_mode == "⚖️ متوازن":
                if rr < 1.5 or t_med != "صاعد": return None
            elif trading_mode == "🚀 هجومي":
                if rr < 1.2: return None  # يسمح بدخول حتى لو الترند هابط لحظياً

        if t_short == "صاعد" and t_med == "صاعد" and rr >= 1.8: signal, sig_cls = "شراء قوي 🔥", "buy-strong"
        elif t_short == "صاعد" and rr >= 1.5: signal, sig_cls = "شراء حذر ⚠️", "buy-caution"
        else: signal, sig_cls = "انتظار ⏳", "wait"

        risk_pct = (entry_price - stop_loss) / entry_price * 100
        target_pct = (target - entry_price) / entry_price * 100
        rr_label, rr_class = get_rr_status(rr)
        
        score = 0
        if t_med == "صاعد": score += 25 
        if t_long == "صاعد": score += 15 
        if ratio > 1.2: score += 20
        if ratio > 2: score += 15 
        if 40 < (rsi or 0) < 65: score += 15
        if rr > 1.8: score += 10

        # --- 🧨 3. تحديد الـ Gold Stock حسب المود ---
        if trading_mode == "🛡️ محافظ (محترف)": g_rr, g_rat = 1.8, 1.5
        elif trading_mode == "⚖️ متوازن": g_rr, g_rat = 1.5, 1.3
        else: g_rr, g_rat = 1.3, 1.1
        
        is_gold = (ratio > g_rat and 45 < (rsi or 0) < 65 and t_med == "صاعد" and rr >= g_rr)

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi or 0, "chg": chg, "ratio": ratio,
            "score": score, "signal": signal, "sig_cls": sig_cls,
            "t_short": t_short, "t_med": t_med, "t_long": t_long,
            "is_gold": is_gold,
            "entry_range": f"{entry_min:.2f} - {entry_max:.2f}",
            "entry_price": entry_price, "stop_loss": stop_loss, "target": target,
            "rr": rr, "rr_label": rr_label, "rr_class": rr_class,
            "risk_pct": risk_pct, "target_pct": target_pct,
            "vol_icon": "🔥 انفجاري" if ratio > 2 else ("⚡ نشط" if ratio > 1.2 else "⚪ هادئ")
        }
    except: return None

# ================== UI RENDERER ==================
def render_stock_ui(res):
    st.markdown(f"<div class='stock-header'>{res['name']} | {res['desc'][:20]} <span class='score-tag'>Score: {res['score']}</span></div>", unsafe_allow_html=True)
    decision, color = get_final_decision(res)
    st.markdown(f"<div style='background:{color};padding:15px;border-radius:10px;text-align:center;font-size:20px;font-weight:bold;margin-bottom:10px;color:white'>{decision}</div>", unsafe_allow_html=True)

    st.markdown(f"<span class='signal-pill {res['sig_cls']}'>{res['signal']}</span> <span class='rr-tag'>RR: {res['rr']}</span> <span class='rr-label {res['rr_class']}'>{res['rr_label']}</span>", unsafe_allow_html=True)
    
    ts_c = "trend-up" if res['t_short'] == "صاعد" else "trend-down"
    tm_c = "trend-up" if res['t_med'] == "صاعد" else "trend-down"
    tl_c = "trend-up" if res['t_long'] == "صاعد" else "trend-down"
    st.markdown(f"<div><span class='trend-pill {ts_c}'>قصير: {res['t_short']}</span><span class='trend-pill {tm_c}'>متوسط: {res['t_med']}</span><span class='trend-pill {tl_c}'>طويل: {res['t_long']}</span></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("السعر الآن", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("السيولة", res['vol_icon'], f"{res['ratio']:.1f}x")
    c3.metric("قوة RSI", f"{res['rsi']:.1f}")

    st.markdown(f"""
    <div class='entry-card-new'>
        🎯 <b>نطاق الدخول:</b> {res['entry_range']}<br>
        🛑 <b>وقف الخسارة:</b> {res['stop_loss']:.2f} <span style='color:#f85149'>(⚠️ {res['risk_pct']:.1f}%)</span>
    </div>
    <div class='target-box'>
        🏁 <b>الهدف المتوقع:</b> {res['target']:.2f} <span style='color:#58a6ff'>(🎯 +{res['target_pct']:.1f}%)</span>
    </div>
    """, unsafe_allow_html=True)

    budget = st.number_input(f"الميزانية المخصصة للسهم:", value=10000, key=f"v_{res['name']}")

    st.markdown("<div class='avg-section'>", unsafe_allow_html=True)
    st.subheader("📉 إدارة المتوسط والتعديل")
    col_a, col_b = st.columns(2)
    old_p = col_a.number_input("متوسط سعر الشراء الحالي", value=0.0, key=f"ap_{res['name']}")
    old_q = col_b.number_input("الكمية الحالية", value=0, key=f"aq_{res['name']}")
    
    if old_p > 0 and old_q > 0:
        pnl = (old_q * res['p']) - (old_q * old_p)
        pnl_color = "#3fb950" if pnl >= 0 else "#f85149"
        st.markdown(f"<div class='pnl-box'>{"🟢 ربح" if pnl >= 0 else "🔴 خسارة"}: <b>{pnl:,.0f} ج</b></div>", unsafe_allow_html=True)

        if res['rr'] < 1.5:
            st.warning("⚠️ تحذير: الصفقة ضعيفة فنياً، التعديل قد لا يكون الخيار الأمثل.")

        entry_p = res['entry_price']
        scenarios = [("💰 25% من السيولة", budget * 0.25), ("💰 50% من السيولة", budget * 0.5), ("💰 100% من السيولة", budget)]
        
        best_scenario, best_avg = None, old_p
        for label, amount in scenarios:
            sh = int(amount / entry_p)
            if sh > 0:
                n_avg = ((old_p * old_q) + (entry_p * sh)) / (old_q + sh)
                st.write(f"{label} ➜ شراء **{sh}** سهم ➜ متوسط: **{n_avg:.2f}**")
                if n_avg < best_avg: best_avg = n_avg; best_scenario = label
        
        if best_scenario: st.success(f"🏆 الأفضل لتقليل المتوسط: {best_scenario}")

    st.markdown("</div>", unsafe_allow_html=True)

# ================== NAVIGATION ==================
if st.session_state.page == 'home':
    st.title("🏹 Sniper Elite v15.7 Pro")
    st.info(f"المود النشط حالياً: **{trading_mode}**")
    if st.button("📡 تحليل سهم"): st.session_state.page = 'analyze'; st.rerun()
    if st.button("🔭 كشاف السوق"): st.session_state.page = 'scanner'; st.rerun()
    if st.button("🚀 الاختراقات"): st.session_state.page = 'breakout'; st.rerun()
    if st.button("💎 قنص الذهب"): st.session_state.page = 'gold'; st.rerun()

elif st.session_state.page == 'analyze':
    if st.button("🏠"): st.session_state.page = 'home'; st.rerun()
    sym = st.text_input("رمز السهم").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data:
            res = analyze_stock(data[0], is_scanner=False)
            if res: render_stock_ui(res)
        else: st.error("سهم غير موجود")

elif st.session_state.page == 'scanner':
    if st.button("🏠"): st.session_state.page = 'home'; st.rerun()
    raw_data = fetch_egx_data(scan_all=True)
    results = [analyze_stock(r, is_scanner=True) for r in raw_data if analyze_stock(r, is_scanner=True)]
    results.sort(key=lambda x: (x['score'], x['rr']), reverse=True)
    for an in results[:15]:
        decision, _ = get_final_decision(an)
        with st.expander(f"{decision} | {an['name']} | RR: {an['rr']}"): render_stock_ui(an)

elif st.session_state.page == 'gold':
    if st.button("🏠"): st.session_state.page = 'home'; st.rerun()
    raw_data = fetch_egx_data(scan_all=True)
    for r in raw_data:
        an = analyze_stock(r, is_scanner=True)
        if an and an['is_gold']:
            decision, _ = get_final_decision(an)
            with st.expander(f"✨ {decision} | {an['name']}"): render_stock_ui(an)

elif st.session_state.page == 'breakout':
    if st.button("🏠"): st.session_state.page = 'home'; st.rerun()
    
    # --- 🧨 4. الاختراقات (Breakout) حسب المود ---
    if trading_mode == "🛡️ محافظ (محترف)": sc_min, rr_min = 75, 1.8
    elif trading_mode == "⚖️ متوازن": sc_min, rr_min = 65, 1.5
    else: sc_min, rr_min = 55, 1.3
    
    raw_data = fetch_egx_data(scan_all=True)
    for r in raw_data:
        an = analyze_stock(r, is_scanner=True)
        if an and an['score'] >= sc_min and an['rr'] >= rr_min:
            decision, _ = get_final_decision(an)
            with st.expander(f"🚀 {decision} | {an['name']}"): render_stock_ui(an)
