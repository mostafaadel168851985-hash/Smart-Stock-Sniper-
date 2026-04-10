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

# ================== 🔥 SESSION STATE & MODES ==================
if "mode" not in st.session_state:
    st.session_state.mode = "⚖️ متوازن"
if 'page' not in st.session_state: 
    st.session_state.page = 'home'

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

    st.markdown(f"""
    <div style="background:{color}; padding:10px; border-radius:10px; text-align:center; font-weight:bold; margin-top:10px; color:white; margin-bottom: 20px;">
        🎯 النمط الحالي: {icon} {mode}
    </div>
    """, unsafe_allow_html=True)

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

        entry_price = p
        entry_min = p * 0.98
        entry_max = p * 1.01
        
        pp = (p + (h or p) + (l or p)) / 3
        s1, r1 = (2 * pp) - (h or p), (2 * pp) - (l or p)
        s2 = pp - ((h or p) - (l or p))
        
        stop_loss = min(s2, entry_price * 0.97)
        target = r1 if p < r1 else r1 + ((r1 - s1) * 0.7)

        profit_ps = target - entry_price; loss_ps = entry_price - stop_loss
        if loss_ps <= 0: return None
        rr = round(profit_ps / loss_ps, 2)

        signal, sig_cls = ("شراء قوي 🔥", "buy-strong") if (t_short == "صاعد" and t_med == "صاعد" and rr >= 1.8) else \
                          ("شراء حذر ⚠️", "buy-caution") if (t_short == "صاعد" and rr >= 1.5) else ("انتظار ⏳", "wait")

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
    
    if res['rr'] >= 2: st.success("💎 صفقة قوية - فرصة ممتازة")
    elif res['rr'] >= 1.5: st.warning("⚖️ صفقة متوسطة")
    else: st.error("⚠️ صفقة ضعيفة - مخاطرة عالية")

    tab_analysis, tab_management = st.tabs(["📊 التحليل الفني", "📉 إدارة المخاطر والسيولة"])

    with tab_analysis:
        t_short_c = "trend-up" if res['t_short'] == "صاعد" else "trend-down"
        t_med_c = "trend-up" if res['t_med'] == "صاعد" else "trend-down"
        t_long_c = "trend-up" if res['t_long'] == "صاعد" else "trend-down"

        st.markdown(f"""
        <div style='margin-bottom: 15px;'>
            <span class='trend-pill {t_short_c}'>قصير: {res['t_short']}</span>
            <span class='trend-pill {t_med_c}'>متوسط: {res['t_med']}</span>
            <span class='trend-pill {t_long_c}'>طويل: {res['t_long']}</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"<span class='signal-pill {res['sig_cls']}'>{res['signal']}</span>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("السعر الحالي", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
        c2.metric("نشاط السيولة", f"{res['ratio']:.1f}x")
        c3.metric("R/R Ratio", f"{res['rr']}")

        st.markdown(f"""
        <div class='entry-card-new'>
            🎯 <b>نطاق الدخول المقترح:</b> {res['entry_range']}<br>
            🛑 <b>وقف الخسارة:</b> {res['stop_loss']:.2f} <span style='color:#f85149'>(⚠️ -{res['risk_pct']:.1f}%)</span>
        </div>
        <div class='target-box'>
            🏁 <b>المستهدف:</b> {res['target']:.2f} <span style='color:#58a6ff'>(🎯 +{res['target_pct']:.1f}%)</span>
        </div>
        """, unsafe_allow_html=True)

    with tab_management:
        col_port, col_risk = st.columns(2)
        portfolio = col_port.number_input("إجمالي حجم المحفظة (ج):", value=100000, step=1000, key=f"port_{res['name']}")
        risk_per_trade = col_risk.slider("نسبة مخاطرة الصفقة (%)", 0.5, 5.0, 2.0, key=f"risk_{res['name']}")

        # حسابات إدارة المخاطر
        max_loss_allowed = portfolio * (risk_per_trade / 100)
        risk_per_share = res['entry_price'] - res['stop_loss']
        shares_to_buy_initial = int(max_loss_allowed / risk_per_share) if risk_per_share > 0 else 0
        
        max_position_size = portfolio * 0.25
        recommended_position_size = min(shares_to_buy_initial * res['entry_price'], max_position_size)
        shares_to_buy = int(recommended_position_size / res['entry_price']) if res['entry_price'] > 0 else 0
        
        actual_loss = (res['entry_price'] - res['stop_loss']) * shares_to_buy
        actual_risk_pct = (actual_loss / portfolio) * 100

        st.markdown(f"""
        <div style='background: rgba(88, 166, 255, 0.1); border: 1px solid #58a6ff; padding: 15px; border-radius: 10px; margin-top: 10px;'>
            🧠 <b>إجمالي السيولة المقررة: {recommended_position_size:,.0f} ج</b><br>
            ⚠️ <b>المخاطرة الفعلية: {actual_risk_pct:.2f}%</b>
        </div>
        """, unsafe_allow_html=True)

        # 🧮 حاسبة المتوسط داخل التحليل (التعديل الجديد)
        st.markdown("---")
        st.markdown("### 🧮 تعديل متوسط السعر")
        c_avg1, c_avg2 = st.columns(2)
        add_price = c_avg1.number_input("سعر التعزيز الجديد", value=res['entry_price'], key=f"ap_{res['name']}")
        add_qty = c_avg2.number_input("عدد الأسهم الجديدة", value=0, key=f"aq_{res['name']}")

        if add_qty > 0:
            new_total_qty = shares_to_buy + add_qty
            new_total_cost = (shares_to_buy * res['entry_price']) + (add_qty * add_price)
            new_avg = new_total_cost / new_total_qty
            st.info(f"📊 متوسط السعر بعد التعزيز: {new_avg:.2f}")
        st.markdown("---")

        # خطة الدخول
        range_size = res['entry_price'] - res['stop_loss']
        entry1_price = res['entry_price']
        entry2_price = max(res['entry_price'] - (range_size * 0.5), res['stop_loss'] * 1.02)
        entry3_price = res['entry_price'] + (res['target'] - res['entry_price']) * 0.3

        if res['rr'] >= 2: weights = [0.7, 0.2, 0.1]
        elif res['rr'] >= 1.5: weights = [0.5, 0.3, 0.2]
        else: weights = [0.3, 0.4, 0.3]

        st.markdown(f"""
        <div class='plan-container'>
        🟢 <b>دخول أساسي:</b> {entry1_price:.2f} | {(recommended_position_size*weights[0]/entry1_price):,.0f} سهم<br>
        🟡 <b>تعزيز دعم:</b> {entry2_price:.2f} | {(recommended_position_size*weights[1]/entry2_price):,.0f} سهم<br>
        🔵 <b>تأكيد اختراق:</b> {entry3_price:.2f} | {(recommended_position_size*weights[2]/entry3_price):,.0f} سهم
        </div>
        """, unsafe_allow_html=True)

# ================== 🔥 NAVIGATION ==================
if st.session_state.page == 'home':
    st.title("🏹 Sniper Elite v15.8 Pro")
    render_mode_selector()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📡 تحليل سهم محدد"): st.session_state.page = 'analyze'; st.rerun()
        if st.button("🔭 كشاف السوق"): st.session_state.page = 'scanner'; st.rerun()
        if st.button("🧮 حاسبة المتوسط"): st.session_state.page = 'avg'; st.rerun() # الزرار الجديد
    with col2:
        if st.button("🚀 الاختراقات"): st.session_state.page = 'breakout'; st.rerun()
        if st.button("💎 قنص الذهب"): st.session_state.page = 'gold'; st.rerun()

elif st.session_state.page == 'avg': # الصفحة المستقلة الجديدة
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    st.title("🧮 حاسبة متوسط السعر")
    col1, col2 = st.columns(2)
    price1 = col1.number_input("سعر الشراء الأول", value=0.0, format="%.2f")
    qty1 = col2.number_input("عدد الأسهم", value=0, step=1)
    price2 = col1.number_input("سعر التعزيز", value=0.0, format="%.2f")
    qty2 = col2.number_input("عدد الأسهم (تعزيز)", value=0, step=1)
    
    total_qty = qty1 + qty2
    if total_qty > 0:
        total_cost = (price1 * qty1) + (price2 * qty2)
        avg_price = total_cost / total_qty
        st.success(f"📊 متوسط السعر الجديد: {avg_price:.2f}")
        st.info(f"💰 إجمالي التكلفة: {total_cost:,.2f} ج | إجمالي الأسهم: {total_qty:,}")

elif st.session_state.page == 'analyze':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    render_mode_selector()
    sym = st.text_input("رمز السهم").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data:
            res = analyze_stock(data[0])
            if res: render_stock_ui(res)
        else: st.error("الرمز غير متوفر.")

elif st.session_state.page == 'scanner':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    render_mode_selector()
    raw_data = fetch_egx_data(scan_all=True)
    results = [analyze_stock(r) for r in raw_data if analyze_stock(r)]
    results.sort(key=lambda x: (x['score'], x['rr']), reverse=True)
    for an in results[:15]:
        with st.expander(f"{an['name']} | RR: {an['rr']} | Score: {an['score']}"): render_stock_ui(an)

elif st.session_state.page == 'gold': # التعديل الذكي لقنص الذهب
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    render_mode_selector()
    raw_data = fetch_egx_data(scan_all=True)
    found = False
    for r in raw_data:
        an = analyze_stock(r)
        # خيار برو: RR عالي مع سيولة قوية أو سكور مرتفع
        if an and (an['rr'] >= 2 and an['ratio'] > 1.2 or an['score'] > 65):
            with st.expander(f"✨ ذهبي: {an['name']} (RR: {an['rr']})"): 
                render_stock_ui(an)
                found = True
    if not found: st.info("لا توجد فرص ذهبية حالياً تطابق المعايير الصارمة.")

elif st.session_state.page == 'breakout':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    render_mode_selector()
    raw_data = fetch_egx_data(scan_all=True)
    for r in raw_data:
        an = analyze_stock(r)
        if an and an['ratio'] > 2:
            with st.expander(f"🚀 اختراق: {an['name']}"): render_stock_ui(an)
