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
    st.markdown(f"""<div style="background:{color}; padding:10px; border-radius:10px; text-align:center; font-weight:bold; margin-top:10px; color:white; margin-bottom: 20px;">🎯 النمط الحالي: {icon} {mode}</div>""", unsafe_allow_html=True)

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
        entry_price = p # Simplified for context
        pp = (p + (h or p) + (l or p)) / 3
        s2 = pp - ((h or p) - (l or p))
        stop_loss = min(s2, entry_price * 0.97)
        target = (2 * pp) - (l or p)
        profit_ps = target - entry_price; loss_ps = entry_price - stop_loss
        if loss_ps <= 0: return None
        rr = round(profit_ps / loss_ps, 2)
        if rr >= 2 and t_short == "صاعد" and t_med == "صاعد": signal, sig_cls = "شراء قوي 🔥", "buy-strong"
        elif ratio > 2 and t_short == "صاعد": signal, sig_cls = "اختراق قوي 🚀", "buy-strong"
        elif ratio > 1.5 and rr >= 1.2: signal, sig_cls = "فرصة مضاربية ⚡", "buy-caution"
        elif rr >= 1.2: signal, sig_cls = "شراء حذر ⚠️", "buy-caution"
        else: signal, sig_cls = "انتظار ⏳", "wait"
        return {
            "name": name, "p": p, "rsi": rsi or 0, "chg": chg, "ratio": ratio,
            "signal": signal, "sig_cls": sig_cls, "t_short": t_short, "t_med": t_med, "t_long": t_long,
            "entry_price": entry_price, "stop_loss": stop_loss, "target": target, "rr": rr, 
            "risk_pct": (loss_ps/entry_price)*100, "target_pct": (profit_ps/entry_price)*100, "score": int((min(ratio, 2) * 20) + (rsi / 2 if rsi else 25))
        }
    except: return None

# ================== UI RENDERER ==================
def render_stock_ui(res):
    st.markdown(f"<div class='stock-header'>{res['name']} <span class='score-tag'>Score: {res['score']}</span></div>", unsafe_allow_html=True)
    tab_analysis, tab_management, tab_scenario = st.tabs(["📊 التحليل الفني", "📉 إدارة المخاطر", "🧠 الوضع الحالي"])

    with tab_analysis:
        st.markdown(f"<span class='signal-pill {res['sig_cls']}'>{res['signal']}</span>", unsafe_allow_html=True)
        st.metric("السعر الحالي", f"{res['p']:.2f}", f"{res['chg']:.1f}%")

    with tab_management:
        st.info("قسم إدارة السيولة والمخاطر المالي")

    with tab_scenario:
        st.markdown("### 🧠 تحليل وضعك الحالي")
        col1, col2 = st.columns(2)
        buy_price = col1.number_input("سعر الشراء", value=res['p'], key=f"buy_{res['name']}")
        qty = col2.number_input("عدد الأسهم", value=100, step=1, key=f"qty_{res['name']}")

        if qty > 0 and buy_price > 0:
            current_price = res['p']
            pnl = (current_price - buy_price) * qty
            
            # حساب نسبة الربح الفعلية
            pnl_pct = ((current_price - buy_price) / buy_price) * 100

            if pnl > 0: st.success(f"🟢 انت كسبان: {pnl:,.0f} ج (+{pnl_pct:.2f}%)")
            elif pnl < 0: st.error(f"🔴 انت خسران: {pnl:,.0f} ج ({pnl_pct:.2f}%)")
            else: st.info("⚖️ انت على التعادل")

            # ================= 🔔 SMART PROFIT ENGINE (ADVANCED UPDATE) =================
            st.markdown("---")
            st.markdown("### 🤖 توصيات ذكية حسب وضع الصفقة")

            # 🟢 حالة المكسب
            if pnl_pct > 0:
                # 🔒 تأمين قوي
                if pnl_pct >= 7:
                    sell_qty = int(qty * 0.5)
                    st.success(f"""
                    🔒 تأمين أرباح قوي:
                    - الربح وصل +{pnl_pct:.2f}%
                    - بيع 50% = {sell_qty} سهم
                    - سيب الباقي يكمل للهدف 🚀
                    """)
                # ⚖️ تأمين جزئي
                elif pnl_pct >= 3:
                    sell_qty = int(qty * 0.25)
                    st.info(f"""
                    ⚖️ تأمين جزئي:
                    - الربح متوسط +{pnl_pct:.2f}%
                    - بيع 25% = {sell_qty} سهم
                    - كمل بالباقي بحذر
                    """)
                # 👀 لسه بدري
                else:
                    st.warning(f"""
                    👀 لسه بدري على البيع:
                    - الربح الحالي +{pnl_pct:.2f}%
                    - خليك مستني تأكيد أو اختراق
                    """)

            # 🔴 حالة الخسارة
            elif pnl_pct < 0:
                trend_score = 0
                if res['t_short'] == "صاعد": trend_score += 1
                if res['t_med'] == "صاعد": trend_score += 1
                if res['ratio'] > 1.5: trend_score += 1
                
                distance_from_sl = (buy_price - res['stop_loss']) / buy_price * 100

                # 🟡 تبريد آمن
                if trend_score >= 2 and distance_from_sl > 6:
                    st.info(f"""
                    🟡 تبريد محسوب:
                    - الاتجاه مازال كويس
                    - في مسافة أمان عن وقف الخسارة ({distance_from_sl:.1f}%)
                    - ممكن تزود كمية بحذر
                    """)
                # 🔴 خطر
                else:
                    st.error(f"""
                    🔴 خطر عالي:
                    - الاتجاه ضعيف أو قريب من وقف الخسارة
                    - ❌ التبريد غير آمن
                    - الأفضل تقليل المركز أو الخروج
                    """)
            # ⚖️ تعادل
            else:
                st.info("⚖️ انت عند نقطة التعادل - استنى إشارة واضحة")

            # ================= 🔔 ALERTS =================
            st.markdown("---")
            st.markdown("### 🚨 تنبيهات فنية سريعة")
            alerts = []
            if res['ratio'] > 2: alerts.append("🚀 سيولة قوية جداً")
            if current_price <= res['stop_loss']: alerts.append("⛔ كسر وقف الخسارة")
            if alerts:
                for a in alerts: st.warning(a)

# ================== 🔥 NAVIGATION ==================
if st.session_state.page == 'home':
    st.title("🏹 Sniper Elite v15.8 Pro")
    render_mode_selector()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📡 تحليل سهم محدد"): st.session_state.page = 'analyze'; st.rerun()
        if st.button("🔭 كشاف السوق"): st.session_state.page = 'scanner'; st.rerun()
    with col2:
        if st.button("🚀 الاختراقات"): st.session_state.page = 'breakout'; st.rerun()

elif st.session_state.page == 'analyze':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    sym = st.text_input("رمز السهم (مثال: ATQA)").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data:
            res = analyze_stock(data[0])
            if res: render_stock_ui(res)
        else: st.error("الرمز غير صحيح")
