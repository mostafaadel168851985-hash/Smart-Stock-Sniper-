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
    .avg-section { background: rgba(88, 166, 255, 0.05); border-left: 5px solid #58a6ff; padding: 25px; border-radius: 12px; margin: 20px 0; }
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
            if st.button("🛡️ محافظ"):
                st.session_state.mode = "🛡️ محافظ (محترف)"
        with col2:
            if st.button("⚖️ متوازن"):
                st.session_state.mode = "⚖️ متوازن"
        with col3:
            if st.button("🚀 هجومي"):
                st.session_state.mode = "🚀 هجومي"

    # Feedback واضح للمستخدم
    mode = st.session_state.mode
    
    if "محافظ" in mode:
        color = "#238636"
        icon = "🛡️"
    elif "هجومي" in mode:
        color = "#f85149"
        icon = "🚀"
    else:
        color = "#d29922"
        icon = "⚖️"

    st.markdown(f"""
    <div style="
        background:{color};
        padding:10px;
        border-radius:10px;
        text-align:center;
        font-weight:bold;
        margin-top:10px;
        color:white;
        margin-bottom: 20px;
    ">
        🎯 النمط الحالي: {icon} {mode}
    </div>
    """, unsafe_allow_html=True)

# ================== 🔥 HELPER FUNCTIONS ==================
def get_final_decision(res):
    rr = res["rr"]; trend = res["t_med"]; t_long = res["t_long"]; ratio = res["ratio"]
    if t_long == "هابط" and rr < 2: return "⚠️ اتجاه عام هابط", "#d29922"
    if rr < 1.2: return "🚫 صفقة سيئة جداً", "#6e7681"
    if rr >= 2.5 and trend == "صاعد" and ratio > 1.5: return "🚀 فرصة قوية جدًا", "#0f5132"
    elif rr >= 2 and trend == "صاعد": return "🟢 ادخل دلوقتي", "#238636"
    elif rr >= 1.5 and trend == "صاعد": return "🟡 راقب", "#d29922"
    else: return "🔴 ابعد", "#f85149"

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

def analyze_stock(d_row, is_scanner=False):
    try:
        d = d_row.get('d', [])
        name, p, rsi, v, avg_v, h, l, chg, desc, sma20, sma50, sma200 = d
        if p is None: return None
        ratio = v / (avg_v or 1)
        t_short = "صاعد" if (sma20 and p > sma20) else "هابط"
        t_med = "صاعد" if (sma50 and p > sma50) else "هابط"
        t_long = "صاعد" if (sma200 and p > sma200) else "هابط"

        pp = (p + (h or p) + (l or p)) / 3
        s1, r1 = (2 * pp) - (h or p), (2 * pp) - (l or p)
        s2 = pp - ((h or p) - (l or p))
        
        entry_min, entry_max = (s1, s1 * 1.01) if p <= r1 else (p * 0.99, p)
        entry_price = (entry_min + entry_max) / 2
        stop_loss = min(s2, entry_price * 0.97)
        target = r1 if p < r1 else r1 + ((r1 - s1) * 0.7)

        profit_ps = target - entry_price; loss_ps = entry_price - stop_loss
        if loss_ps <= 0: return None
        rr = round(profit_ps / loss_ps, 2)

        mode = st.session_state.mode
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
    decision, color = get_final_decision(res)
    st.markdown(f"<div style='background:{color};padding:15px;border-radius:10px;text-align:center;font-size:20px;font-weight:bold;margin-bottom:10px;color:white'>{decision}</div>", unsafe_allow_html=True)
    
    st.info(f"📊 المخاطرة لكل سهم: {res['entry_price'] - res['stop_loss']:.2f} ج")

    tab_analysis, tab_management = st.tabs(["📊 التحليل الفني", "📉 إدارة المخاطر والسيولة"])

    with tab_analysis:
        st.markdown(f"<span class='signal-pill {res['sig_cls']}'>{res['signal']}</span>", unsafe_allow_html=True)
        
        st.markdown(f"""
        💰 **R/R:** {res['rr']}  
        🎯 **Target:** +{res['target_pct']:.1f}%  
        ⚠️ **Risk:** -{res['risk_pct']:.1f}%
        """)
        
        t_short_c = "trend-up" if res['t_short'] == "صاعد" else "trend-down"
        t_med_c = "trend-up" if res['t_med'] == "صاعد" else "trend-down"
        t_long_c = "trend-up" if res['t_long'] == "صاعد" else "trend-down"
        st.markdown(f"<div><span class='trend-pill {t_short_c}'>قصير: {res['t_short']}</span><span class='trend-pill {t_med_c}'>متوسط: {res['t_med']}</span><span class='trend-pill {t_long_c}'>طويل: {res['t_long']}</span></div>", unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("السعر الحالي", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
        c2.metric("نشاط السيولة", f"{res['ratio']:.1f}x")
        c3.metric("RSI", f"{res['rsi']:.1f}")

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
        # --- 1. Position Sizing ---
        col_port, col_risk = st.columns(2)
        portfolio = col_port.number_input("إجمالي حجم المحفظة (ج):", value=100000, step=1000, key=f"port_{res['name']}")
        risk_per_trade = col_risk.slider("نسبة مخاطرة الصفقة (%)", 0.5, 5.0, 2.0, key=f"risk_{res['name']}")

        max_loss_allowed = portfolio * (risk_per_trade / 100)
        risk_per_share = res['entry_price'] - res['stop_loss']
        shares_to_buy = int(max_loss_allowed / risk_per_share) if risk_per_share > 0 else 0
        recommended_position_size = shares_to_buy * res['entry_price']

        st.markdown(f"""
        <div style='background: rgba(88, 166, 255, 0.1); border: 1px solid #58a6ff; padding: 15px; border-radius: 10px; margin-top: 10px;'>
            🧠 <b>إجمالي السيولة المسموح بها: {recommended_position_size:,.0f} ج</b> (أقصى خسارة: {max_loss_allowed:,.0f} ج)
        </div>
        """, unsafe_allow_html=True)

        # --- 2. Execution Strategy ---
        st.markdown("### 🎯 خطة الدخول المرحلية (Pyramiding)")
        
        if res['t_long'] == "هابط":
            st.warning("⚠️ الاتجاه العام هابط - الدخول المرحلي عالي الخطورة")
        
        if res['rr'] < 1.5:
            st.error("❌ لا ينصح بالدخول المرحلي في صفقة ضعيفة")
        else:
            if res['rr'] >= 2:
                entry1_pct, entry2_pct, entry3_pct = 0.7, 0.2, 0.1
                strategy_note = "🚀 صفقة قوية: دخول هجومي بالبداية"
            elif res['rr'] >= 1.5:
                entry1_pct, entry2_pct, entry3_pct = 0.5, 0.3, 0.2
                strategy_note = "⚖️ صفقة متوازنة: دخول مرحلي قياسي"
            else:
                entry1_pct, entry2_pct, entry3_pct = 0.3, 0.4, 0.3
                strategy_note = "🛡️ صفقة حذرة: دخول تدريجي بسيط"

            entry1_money = recommended_position_size * entry1_pct
            entry2_money = recommended_position_size * entry2_pct
            entry3_money = recommended_position_size * entry3_pct

            entry1_shares = int(entry1_money / res['entry_price'])
            entry2_shares = int(entry2_money / (res['entry_price'] * 0.97))
            entry3_shares = int(entry3_money / (res['entry_price'] * 1.02))

            st.caption(strategy_note)
            st.markdown(f"""
            <div class='plan-container'>
            🎯 <b>خطة الدخول المقترحة:</b><br><br>
            🟢 <b>دخول أول ({int(entry1_pct*100)}%):</b> {entry1_money:,.0f} ج ➜ {entry1_shares:,} سهم<br>
            🟡 <b>تعزيز ({int(entry2_pct*100)}%):</b> {entry2_money:,.0f} ج ➜ {entry2_shares:,} سهم<br>
            🔵 <b>تأكيد ({int(entry3_pct*100)}%):</b> {entry3_money:,.0f} ج ➜ {entry3_shares:,} سهم
            </div>
            """, unsafe_allow_html=True)

# ================== 🔥 NAVIGATION ==================
if st.session_state.page == 'home':
    st.title("🏹 Sniper Elite v15.8 Pro")
    render_mode_selector() # استخدام النسخة الجديدة هنا
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📡 تحليل سهم محدد"): st.session_state.page = 'analyze'; st.rerun()
        if st.button("🔭 كشاف السوق"): st.session_state.page = 'scanner'; st.rerun()
    with col2:
        if st.button("🚀 الاختراقات"): st.session_state.page = 'breakout'; st.rerun()
        if st.button("💎 قنص الذهب"): st.session_state.page = 'gold'; st.rerun()

elif st.session_state.page == 'analyze':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    render_mode_selector() # النسخة الجديدة
    sym = st.text_input("رمز السهم").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data:
            res = analyze_stock(data[0])
            if res: render_stock_ui(res)
        else: st.error("عفواً، الرمز غير متوفر.")

elif st.session_state.page == 'scanner':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    render_mode_selector() # النسخة الجديدة
    raw_data = fetch_egx_data(scan_all=True)
    results = [analyze_stock(r) for r in raw_data if analyze_stock(r)]
    results.sort(key=lambda x: (x['score'], x['rr']), reverse=True)
    for an in results[:15]:
        with st.expander(f"{an['name']} | RR: {an['rr']} | Score: {an['score']}"): render_stock_ui(an)
# ... باقي الكود (gold و breakout) يتبع نفس النمط
