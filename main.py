import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="EGX Sniper Pro v15.8", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-size: 18px !important; font-weight: bold !important; margin-bottom: 10px; }
    .stock-header { font-size: 26px !important; font-weight: bold; color: #58a6ff; border-bottom: 2px solid #30363d; padding-bottom: 10px; }
    .score-tag { float: left; background: #238636; color: white; padding: 2px 15px; border-radius: 10px; font-size: 18px; margin-top: 5px; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 10px; padding: 10px !important; }
    .trend-pill { padding: 4px 12px; border-radius: 15px; font-size: 13px; font-weight: bold; margin: 2px; display: inline-block; border: 1px solid #30363d; }
    .trend-up { background-color: rgba(63, 185, 80, 0.15); color: #3fb950; border-color: #3fb950; }
    .trend-down { background-color: rgba(248, 81, 73, 0.15); color: #f85149; border-color: #f85149; }
    .signal-pill { padding: 8px 20px; border-radius: 20px; font-weight: bold; display: inline-block; margin: 10px 0; font-size: 16px; }
    .buy-strong { background: #238636; color: white; }
    .buy-caution { background: rgba(240, 139, 55, 0.2); color: #f08b37; border: 1px solid #f08b37; }
    .wait { background: #161b22; color: #8b949e; border: 1px solid #30363d; }
    .entry-card-new { background-color: #0d1117; border: 1px solid #3fb950; border-radius: 12px; padding: 15px; text-align: center; margin-bottom: 15px; border-top: 4px solid #3fb950; }
    .target-box { border: 2px solid #58a6ff; border-radius: 12px; padding: 15px; text-align: center; background: #0d1117; margin-top: 10px; font-size: 18px; }
    .plan-container { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-top: 15px; border-right: 5px solid #238636; }
    </style>
    """, unsafe_allow_html=True)

# ================== 🧠 HELPERS FOR RATINGS ==================
def get_rr_rating(rr):
    if rr < 1: return "❌ ضعيف", "RR سيء - مخاطرة أعلى من العائد"
    elif rr < 1.5: return "⚠️ متوسط", "مضاربة سريعة فقط"
    elif rr < 2: return "✅ جيد", "صفقة كويسة"
    else: return "🔥 ممتاز", "فرصة قوية جداً"

def get_volume_rating(ratio):
    if ratio < 1: return "❄️ ضعيفة", "مفيش سيولة كفاية"
    elif ratio < 1.5: return "🙂 عادية", "سيولة طبيعية"
    elif ratio < 2: return "⚡ نشطة", "في اهتمام بالسهم"
    else: return "🚀 قوية", "سيولة عالية واختراق محتمل"

# 🔥 1️⃣ وظيفة التصنيف الجديدة (Classification)
def classify_stock(res):
    rr = res['rr']
    ratio = res['ratio']
    t_short = res['t_short']
    t_med = res['t_med']
    mode = st.session_state.mode

    # 🎯 فلترة حسب نوع المتداول (المود)
    if "محافظ" in mode:
        rr_min = 1.7
    elif "هجومي" in mode:
        rr_min = 1.0
    else:
        rr_min = 1.3

    # 🥇 ذهبي (الأولوية القصوى)
    if rr >= 1.8 and t_short == "صاعد" and t_med == "صاعد":
        return "gold"
    # 🚀 اختراق
    elif ratio > 2 and t_short == "صاعد":
        return "breakout"
    # ⚡ مضاربة
    elif ratio > 1.5 and rr >= 1.2:
        return "scalp"
    # 👀 تحت المراقبة (الكشاف)
    elif rr >= rr_min and ratio > 1.2:
        return "watchlist"
    else:
        return "weak"

# ================== 🔥 SESSION STATE & MODES ==================
if "mode" not in st.session_state: st.session_state.mode = "⚖️ متوازن"
if 'page' not in st.session_state: st.session_state.page = 'home'

def render_mode_selector():
    with st.expander("🧠 اختر نوع التداول", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🛡️ محافظ"): st.session_state.mode = "🛡️ محافظ (محترف)"
        with col2:
            if st.button("⚖️ متوازن"): st.session_state.mode = "⚖️ متوازن"
        with col3:
            if st.button("🚀 هجومي"): st.session_state.mode = "🚀 هجومي"

    mode = st.session_state.mode
    color = "#238636" if "محافظ" in mode else "#f85149" if "هجومي" in mode else "#d29922"
    icon = "🛡️" if "محافظ" in mode else "🚀" if "هجومي" in mode else "⚖️"
    st.markdown(f"<div style='background:{color}; padding:10px; border-radius:10px; text-align:center; font-weight:bold; margin-top:10px; color:white; margin-bottom: 20px;'>🎯 النمط الحالي: {icon} {mode}</div>", unsafe_allow_html=True)

# ================== 🔥 DATA & ANALYSIS ENGINE ==================
@st.cache_data(ttl=300)
def fetch_egx_data(symbol=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    cols = ["name","close","RSI","volume","average_volume_10d_calc","high","low","change","description","SMA20","SMA50","SMA200"]
    payload = {"filter": [{"left": "volume", "operation": "greater", "right": 5000}], "columns": cols, "sort": {"sortBy": "change", "sortOrder": "desc"}, "range": [0, 150]}
    if symbol:
        payload["filter"] = [{"left": "name", "operation": "match", "right": symbol.upper()}]
        payload["range"] = [0, 1]
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except: return []

def analyze_stock(d_row):
    try:
        d = d_row.get('d', [])
        name, p, rsi, v, avg_v, h, l, chg, desc, sma20, sma50, sma200 = d
        if p is None: return None
        
        ratio = v / (avg_v or 1)
        t_short = "صاعد" if (sma20 and p > sma20) else "هابط"
        t_med = "صاعد" if (sma50 and p > sma50) else "هابط"
        t_long = "صاعد" if (sma200 and p > sma200) else "هابط"

        entry_min, entry_max = p * 0.98, p * 1.01
        entry_price = (entry_min + entry_max) / 2
        
        pp = (p + (h or p) + (l or p)) / 3
        s1, r1 = (2 * pp) - (h or p), (2 * pp) - (l or p)
        s2 = pp - ((h or p) - (l or p))
        
        stop_loss = min(s2, entry_price * 0.97)
        target = max(r1, entry_price * 1.05)

        profit_ps = target - entry_price; loss_ps = entry_price - stop_loss
        if loss_ps <= 0: return None
        rr = round(profit_ps / loss_ps, 2)

        # الإشارات الفنية (للعرض فقط)
        if rr >= 2 and t_short == "صاعد" and t_med == "صاعد": signal, sig_cls = "شراء قوي 🔥", "buy-strong"
        elif ratio > 2 and t_short == "صاعد": signal, sig_cls = "اختراق قوي 🚀", "buy-strong"
        elif ratio > 1.5 and rr >= 1.2: signal, sig_cls = "فرصة مضاربية ⚡", "buy-caution"
        elif rr >= 1.2: signal, sig_cls = "شراء حذر ⚠️", "buy-caution"
        else: signal, sig_cls = "انتظار ⏳", "wait"

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi or 0, "chg": chg, "ratio": ratio,
            "signal": signal, "sig_cls": sig_cls, "t_short": t_short, "t_med": t_med, "t_long": t_long,
            "entry_range": f"{entry_min:.2f} - {entry_max:.2f}", "entry_price": entry_price,
            "stop_loss": stop_loss, "target": target, "rr": rr, "risk_pct": (loss_ps/entry_price)*100, 
            "target_pct": (profit_ps/entry_price)*100, "score": int((min(ratio, 2) * 20) + (rsi / 2 if rsi else 25))
        }
    except: return None

# ================== UI RENDERER ==================
def render_stock_ui(res):
    st.markdown(f"<div class='stock-header'>{res['name']} <span class='score-tag'>Score: {res['score']}</span></div>", unsafe_allow_html=True)
    tab_analysis, tab_management, tab_scenario = st.tabs(["📊 التحليل الفني", "📉 إدارة المخاطر والسيولة", "🧠 الوضع الحالي"])

    with tab_analysis:
        t_short_c = "trend-up" if res['t_short'] == "صاعد" else "trend-down"
        t_med_c = "trend-up" if res['t_med'] == "صاعد" else "trend-down"
        t_long_c = "trend-up" if res['t_long'] == "صاعد" else "trend-down"
        st.markdown(f"<div><span class='trend-pill {t_short_c}'>قصير: {res['t_short']}</span><span class='trend-pill {t_med_c}'>متوسط: {res['t_med']}</span><span class='trend-pill {t_long_c}'>طويل: {res['t_long']}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<span class='signal-pill {res['sig_cls']}'>{res['signal']}</span>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("السعر الحالي", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
        vol_label, vol_desc = get_volume_rating(res['ratio'])
        c2.metric("نشاط السيولة", f"{res['ratio']:.1f}x {vol_label}")
        rr_label, rr_desc = get_rr_rating(res['rr'])
        c3.metric("R/R Ratio", f"{res['rr']} {rr_label}")

        st.markdown(f"<div class='entry-card-new'>🎯 نطاق الدخول: {res['entry_range']}<br>🛑 الوقف: {res['stop_loss']:.2f} <span style='color:#f85149'>(-{res['risk_pct']:.1f}%)</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='target-box'>🏁 المستهدف: {res['target']:.2f} <span style='color:#58a6ff'>(+{res['target_pct']:.1f}%)</span></div>", unsafe_allow_html=True)

    with tab_management:
        # احتفاظ بكامل منطق إدارة المحفظة القديم
        col_port, col_risk = st.columns(2)
        portfolio = col_port.number_input("إجمالي المحفظة (ج):", value=100000, key=f"port_{res['name']}")
        risk_per_trade = col_risk.slider("مخاطرة الصفقة (%)", 0.5, 5.0, 2.0, key=f"risk_{res['name']}")

        max_loss = portfolio * (risk_per_trade / 100)
        risk_per_share = res['entry_price'] - res['stop_loss']
        shares_to_buy = int(max_loss / risk_per_share) if risk_per_share > 0 else 0
        
        st.markdown(f"<div class='plan-container' style='border-right: 5px solid #238636;'>🟢 الربح المتوقع: {(res['target'] - res['entry_price']) * shares_to_buy:,.0f} ج<br>🔴 الخسارة المحتملة: {max_loss:,.0f} ج</div>", unsafe_allow_html=True)

        # Deal Budget Mode
        st.markdown("---")
        st.markdown("### 💰 Deal Budget Mode")
        deal_size = st.number_input("💰 ميزانية الصفقة", value=10000, key=f"db_{res['name']}")
        if deal_size > 0:
            shares_d = int(deal_size / res['entry_price'])
            e1_p, e2_p = res['entry_price'], max(res['entry_price']*0.98, res['stop_loss']*1.02)
            st.markdown(f"<div class='plan-container'>🟢 الدخول: {e1_p:.2f} (50%)<br>🟡 التعزيز: {e2_p:.2f} (30%)<br>🔵 الاختراق: {res['entry_price']*1.03:.2f} (20%)</div>", unsafe_allow_html=True)

    with tab_scenario:
        buy_price = st.number_input("سعر الشراء", value=res['p'], key=f"buy_{res['name']}")
        qty = st.number_input("عدد الأسهم", value=100, key=f"qty_{res['name']}")
        if qty > 0:
            pnl = (res['p'] - buy_price) * qty
            if pnl > 0: st.success(f"🟢 ربح: {pnl:,.0f} ج")
            else: st.error(f"🔴 خسارة: {pnl:,.0f} ج")

# ================== 🔥 NAVIGATION ==================
if st.session_state.page == 'home':
    st.title("🏹 Sniper Elite v15.8 Pro")
    render_mode_selector()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📡 تحليل سهم محدد"): st.session_state.page = 'analyze'; st.rerun()
        if st.button("🔭 كشاف السوق"): st.session_state.page = 'scanner'; st.rerun()
        if st.button("🧮 حاسبة المتوسط"): st.session_state.page = 'avg'; st.rerun()
    with col2:
        if st.button("🚀 الاختراقات"): st.session_state.page = 'breakout'; st.rerun()
        if st.button("💎 قنص الذهب"): st.session_state.page = 'gold'; st.rerun()
        # 🔥 5️⃣ زرار المضاربات الجديد
        if st.button("⚡ مضاربات سريعة"): st.session_state.page = 'scalp'; st.rerun()

elif st.session_state.page == 'avg':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    st.title("🧮 حاسبة المتوسط")
    p1 = st.number_input("سعر الشراء 1"); q1 = st.number_input("كمية 1", step=1)
    p2 = st.number_input("سعر الشراء 2"); q2 = st.number_input("كمية 2", step=1)
    if (q1+q2) > 0: st.success(f"المتوسط: {((p1*q1)+(p2*q2))/(q1+q2):.2f}")

elif st.session_state.page == 'scanner': # 2️⃣ تعديل الكشاف بالفلترة الذكية
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    render_mode_selector()
    raw_data = fetch_egx_data(scan_all=True)
    results = []
    for r in raw_data:
        an = analyze_stock(r)
        if an and classify_stock(an) == "watchlist":
            results.append(an)
    results.sort(key=lambda x: x['score'], reverse=True)
    for an in results[:15]:
        with st.expander(f"{an['name']} | {an['signal']}"): render_stock_ui(an)

elif st.session_state.page == 'gold': # 3️⃣ تعديل صفحة الذهب
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    render_mode_selector()
    raw_data = fetch_egx_data(scan_all=True)
    found = False
    for r in raw_data:
        an = analyze_stock(r)
        if an and classify_stock(an) == "gold":
            with st.expander(f"✨ ذهبي: {an['name']} (RR: {an['rr']})"): 
                render_stock_ui(an)
                found = True
    if not found: st.info("لا توجد فرص ذهبية حالياً.")

elif st.session_state.page == 'breakout': # 4️⃣ تعديل الاختراق
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    render_mode_selector()
    raw_data = fetch_egx_data(scan_all=True)
    for r in raw_data:
        an = analyze_stock(r)
        if an and classify_stock(an) == "breakout":
            with st.expander(f"🚀 اختراق: {an['name']}"): render_stock_ui(an)

# 🔥 5️⃣ صفحة المضاربات الجديدة
elif st.session_state.page == 'scalp':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    render_mode_selector()
    raw_data = fetch_egx_data(scan_all=True)
    found = False
    for r in raw_data:
        an = analyze_stock(r)
        if an and classify_stock(an) == "scalp":
            with st.expander(f"⚡ مضاربة: {an['name']}"):
                render_stock_ui(an)
                found = True
    if not found: st.info("لا توجد مضاربات سريعة حالياً.")

elif st.session_state.page == 'analyze':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    sym = st.text_input("رمز السهم").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data:
            res = analyze_stock(data[0])
            if res: render_stock_ui(res)
