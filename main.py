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
    
    /* 🏛️ ستايل بلوك المستثمر الجديد */
    .investor-card { background-color: #161b22; border: 1px solid #d29922; border-radius: 12px; padding: 15px; margin-bottom: 15px; border-top: 4px solid #d29922; }
    .investor-title { color: #d29922; font-weight: bold; font-size: 18px; margin-bottom: 10px; display: block; border-bottom: 1px solid #30363d; padding-bottom: 5px; }
    .level-box { display: flex; justify-content: space-between; padding: 3px 0; border-bottom: 1px solid #21262d; }
    .sup-text { color: #3fb950; font-weight: bold; }
    .res-text { color: #f85149; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# ================== 🧠 HELPERS FOR RATINGS ==================
def get_rr_rating(rr):
    if rr < 1:
        return "❌ ضعيف", "RR سيء - مخاطرة أعلى من العائد"
    elif rr < 1.5:
        return "⚠️ متوسط", "مضاربة سريعة فقط"
    elif rr < 2:
        return "✅ جيد", "صفقة كويسة"
    else:
        return "🔥 ممتاز", "فرصة قوية جداً"

def get_volume_rating(ratio):
    if ratio < 1:
        return "❄️ ضعيفة", "مفيش سيولة كفاية"
    elif ratio < 1.5:
        return "🙂 عادية", "سيولة طبيعية"
    elif ratio < 2:
        return "⚡ نشطة", "في اهتمام بالسهم"
    else:
        return "🚀 قوية", "سيولة عالية واختراق محتمل"

# ✳️ [إضافة جديدة] "مخ" الـ RSI لتقييم الزخم
def get_rsi_signal(rsi):
    if rsi < 30:
        return "🟢 تشبع بيع (فرصة انعكاس)", "oversold"
    elif rsi < 50:
        return "🟡 ضعيف", "weak"
    elif rsi < 65:
        return "🟢 زخم صحي", "good"
    elif rsi < 75:
        return "⚠️ قرب تشبع شراء", "caution"
    else:
        return "🔴 تشبع شراء خطر", "overbought"

# 🔥 [تعديل ذكي] Function التصنيف باستخدام RSI
def classify_stock(res):
    rr = res['rr']
    ratio = res['ratio']
    t_short = res['t_short']
    t_med = res['t_med']
    rsi = res['rsi'] 

    mode = st.session_state.mode

    if "محافظ" in mode:
        rr_min = 1.7
    elif "هجومي" in mode:
        rr_min = 1.0
    else:
        rr_min = 1.3

    if rr >= 1.5 and t_short == "صاعد" and 50 < rsi < 70:
        return "gold"
    elif ratio > 2 and t_short == "صاعد" and rsi < 75:
        return "breakout"
    elif ratio > 1.5 and rr >= 1.2 and rsi < 80:
        return "scalp"
    elif rr >= rr_min and ratio > 1.2:
        return "watchlist"
    else:
        return "weak"

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
    
    current_range = [0, 300] if scan_all else [0, 150]
    
    payload = {"filter": [{"left": "volume", "operation": "greater", "right": 5000}], "columns": cols, "sort": {"sortBy": "change", "sortOrder": "desc"}, "range": current_range}
    if symbol:
        payload["filter"] = [{"left": "name", "operation": "match", "right": symbol.upper()}]
        payload["range"] = [0, 1]
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except Exception as e:
        print(f"API Error: {e}")
        return []

def analyze_stock(d_row):
    try:
        d = d_row.get('d', [])
        name, p, rsi, v, avg_v, h, l, chg, desc, sma20, sma50, sma200 = d
        if p is None: return None
        
        rsi_val = rsi if rsi is not None else 50
        ratio = v / avg_v if avg_v and avg_v > 0 else 1
        t_short = "صاعد" if (sma20 and p > sma20) else "هابط"
        t_med = "صاعد" if (sma50 and p > sma50) else "هابط"
        t_long = "صاعد" if (sma200 and p > sma200) else "هابط"

        entry_min = p * 0.98
        entry_max = p * 1.01
        entry_price = (entry_min + entry_max) / 2
        
        pp = (p + (h or p) + (l or p)) / 3
        s1, r1 = (2 * pp) - (h or p), (2 * pp) - (l or p)
        s2, r2 = pp - ((h or p) - (l or p)), pp + ((h or p) - (l or p))
        
        stop_loss = min(s2, entry_price * 0.97)
        target = max(r1, entry_price * 1.05)

        profit_ps = target - entry_price; loss_ps = entry_price - stop_loss
        if loss_ps <= 0: return None
        rr = round(profit_ps / loss_ps, 2)

        if rr >= 2 and t_short == "صاعد" and t_med == "صاعد" and rsi_val < 70:
            signal, sig_cls = "شراء قوي 🔥", "buy-strong"
        elif ratio > 2 and t_short == "صاعد" and rsi_val < 75:
            signal, sig_cls = "اختراق قوي 🚀", "buy-strong"
        elif ratio > 1.5 and rr >= 1.2 and rsi_val < 75:
            signal, sig_cls = "فرصة مضاربية ⚡", "buy-caution"
        elif rr >= 1.2 and rsi_val < 70:
            signal, sig_cls = "شراء حذر ⚠️", "buy-caution"
        else:
            signal, sig_cls = "انتظار ⏳", "wait"

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "signal": signal, "sig_cls": sig_cls, "t_short": t_short, "t_med": t_med, "t_long": t_long,
            "s1": s1, "s2": s2, "r1": r1, "r2": r2, "pp": pp,
            "entry_range": f"{entry_min:.2f} - {entry_max:.2f}", "entry_price": entry_price,
            "stop_loss": stop_loss, "target": target, "rr": rr, "risk_pct": (loss_ps/entry_price)*100, 
            "target_pct": (profit_ps/entry_price)*100, "score": int((min(ratio, 2) * 20) + (rsi_val / 2 if rsi_val else 25))
        }
    except Exception as e:
        print(f"Analysis Error for {d_row.get('s', 'Unknown')}: {e}")
        return None

# ================== UI RENDERER ==================
def render_stock_ui(res):
    st.markdown(f"<div class='stock-header'>{res['name']} - {res['desc']} <span class='score-tag'>Score: {res['score']}</span></div>", unsafe_allow_html=True)
    
    tab_analysis, tab_management, tab_scenario = st.tabs([
        "📊 التحليل الفني",
        "📉 إدارة المخاطر والسيولة",
        "🧠 الوضع الحالي"
    ])

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
        
        c1, c2, c3, c4 = st.columns(4) 
        c1.metric("السعر الحالي", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
        
        vol_label, vol_desc = get_volume_rating(res['ratio'])
        c2.metric("نشاط السيولة", f"{res['ratio']:.1f}x {vol_label}")
        
        rr_label, rr_desc = get_rr_rating(res['rr'])
        c3.metric("R/R Ratio", f"{res['rr']} {rr_label}")

        rsi_label, rsi_type = get_rsi_signal(res['rsi'])
        c4.metric("RSI", f"{res['rsi']:.1f}", rsi_label)
        
        with c2: st.caption(f"📊 {vol_desc}")
        with c3: st.caption(f"🧠 {rr_desc}")
        with c4: st.caption(f"📈 حالة الزخم: {rsi_label}")
        # تحذير عند المقاومة
    if res['p'] >= res['r1'] * 0.98: st.warning("⚠️ السعر قريب من مقاومة قوية")
      
    # 🏛️ [بلوك المستثمر الجديد]
        st.markdown(f"""
        <div class='investor-card'>
            <span class='investor-title'>🏛️ بيانات استرشادية (للمستثمر طويل الأجل)</span>
            <div class='level-box'><span>المقاومة التاريخية الثانية (R2):</span><span class='res-text'>{res['r2']:.2f}</span></div>
            <div class='level-box'><span>المقاومة التاريخية الأولى (R1):</span><span class='res-text'>{res['r1']:.2f}</span></div>
            <div style='text-align:center; color:#8b949e; font-size:11px; margin:5px 0;'>--- نقطة الارتكاز: {res['pp']:.2f} ---</div>
            <div class='level-box'><span>الدعم التاريخي القوي الأول (S1):</span><span class='sup-text'>{res['s1']:.2f}</span></div>
            <div class='level-box'><span>الدعم التاريخي القوي الثاني (S2):</span><span class='sup-text'>{res['s2']:.2f}</span></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class='entry-card-new'>
            🎯 <b>نطاق الدخول المقترح (مضاربة وسوينج فقط):</b> {res['entry_range']}<br>
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

        max_loss_allowed = portfolio * (risk_per_trade / 100)
        risk_per_share = res['entry_price'] - res['stop_loss']
        shares_to_buy_initial = int(max_loss_allowed / risk_per_share) if risk_per_share > 0 else 0
        
        max_position_size = portfolio * 0.25
        recommended_position_size = min(shares_to_buy_initial * res['entry_price'], max_position_size)
        
        shares_to_buy = max(1, int(recommended_position_size / res['entry_price'])) if res['entry_price'] > 0 else 0
        
        profit_val = (res['target'] - res['entry_price']) * shares_to_buy
        loss_val = (res['entry_price'] - res['stop_loss']) * shares_to_buy
        
        actual_risk_pct = (loss_val / portfolio) * 100

        st.markdown(f"""
        <div style='background: rgba(88, 166, 255, 0.1); border: 1px solid #58a6ff; padding: 15px; border-radius: 10px; margin-top: 10px;'>
            🧠 <b>إجمالي السيولة المقررة: { (shares_to_buy * res['entry_price']):,.0f} ج</b><br>
            ⚠️ <b>المخاطرة الفعلية: {actual_risk_pct:.2f}%</b>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class='plan-container' style='border-right: 5px solid #238636;'>
        📊 <b>تقييم مالي للصفقة ({shares_to_buy:,} سهم):</b><br>
        🟢 الربح المتوقع: {profit_val:,.0f} ج<br>
        🔴 الخسارة المحتملة: {loss_val:,.0f} ج<br>
        ⚖️ معدل RR المحقق: {res['rr']}
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("## 💰 إدارة الصفقة المباشرة (Deal Budget Mode)")

        deal_size = st.number_input("💰 حدد ميزانية الصفقة (ج)", value=10000, step=1000, key=f"deal_budget_{res['name']}")

        if deal_size > 0:
            if deal_size > portfolio * 0.3:
                st.warning("⚠️ الصفقة كبيرة مقارنة بالمحفظة")

            shares_deal = int(deal_size / res['entry_price']) if res['entry_price'] > 0 else 0
            actual_value = shares_deal * res['entry_price']

            profit_val_d = (res['target'] - res['entry_price']) * shares_deal
            loss_val_d = (res['entry_price'] - res['stop_loss']) * shares_deal

            st.markdown(f"""
            <div style='background: rgba(63, 185, 80, 0.1); border: 1px solid #3fb950; padding: 15px; border-radius: 10px; margin-top: 10px;'>
                💰 <b>قيمة الصفقة الفعلية: {actual_value:,.0f} ج</b><br>
                📦 <b>عدد الأسهم: {shares_deal:,}</b>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class='plan-container'>
            🟢 الربح المتوقع: {profit_val_d:,.0f} ج<br>
            🔴 الخسارة المحتملة: {loss_val_d:,.0f} ج<br>
            ⚖️ RR: {res['rr']}
            </div>
            """, unsafe_allow_html=True)

            range_size_d = res['entry_price'] - res['stop_loss']
            e1_p_d = res['entry_price']
            e2_p_d = max(res['entry_price'] - (range_size_d * 0.5), res['stop_loss'] * 1.02)
            e3_p_d = res['entry_price'] + (res['target'] - res['entry_price']) * 0.3

            if res['rr'] >= 2: weights_d = [0.7, 0.2, 0.1]
            elif res['rr'] >= 1.5: weights_d = [0.5, 0.3, 0.2]
            else: weights_d = [0.3, 0.4, 0.3]

            e1_m_d = deal_size * weights_d[0]
            e2_m_d = deal_size * weights_d[1]
            e3_m_d = deal_size * weights_d[2]

            e1_s_d = int(e1_m_d / e1_p_d)
            e2_s_d = int(e2_m_d / e2_p_d)
            e3_s_d = int(e3_m_d / e3_p_d)

            st.markdown("### 🏹 خطة التنفيذ المباشرة (حسب ميزانية الصفقة)")
            st.markdown(f"""
            <div class='plan-container'>
            🟢 <b>لو السعر ≈ {e1_p_d:.2f} ج ➜ اشتري (دخول أساسي)</b><br>
            📦 الكمية: {e1_s_d:,} سهم | 💰 القيمة: {e1_m_d:,.0f} ج<br><br>

            🟡 <b>لو السعر نزل لـ {e2_p_d:.2f} ج ➜ اشتري (تعزيز دعم)</b><br>
            📦 الكمية: {e2_s_d:,} سهم | 💰 القيمة: {e2_m_d:,.0f} ج<br><br>

            🔵 <b>لو السعر اخترق {e3_p_d:.2f} ج ➜ اشتري (تأكيد اختراق)</b><br>
            📦 الكمية: {e3_s_d:,} سهم | 💰 القيمة: {e3_m_d:,.0f} ج
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 🧮 تعديل متوسط السعر")
        c_avg1, c_avg2 = st.columns(2)
        add_price = c_avg1.number_input("سعر التعزيز الجديد", value=res['p'], key=f"ap_{res['name']}")
        add_qty_input = c_avg2.number_input("عدد الأسهم الجديدة", value=0, key=f"aq_{res['name']}")

        if add_qty_input > 0:
            new_total_qty = shares_to_buy + add_qty_input
            new_total_cost = (shares_to_buy * res['entry_price']) + (add_qty_input * add_price)
            new_avg = new_total_cost / new_total_qty
            st.info(f"📊 متوسط السعر بعد التعزيز: {new_avg:.2f}")

        range_size = res['entry_price'] - res['stop_loss']
        e1_p, e2_p = res['entry_price'], max(res['entry_price'] - (range_size * 0.5), res['stop_loss'] * 1.02)
        e3_p = res['entry_price'] + (res['target'] - res['entry_price']) * 0.3

        if res['rr'] >= 2: weights = [0.7, 0.2, 0.1]
        elif res['rr'] >= 1.5: weights = [0.5, 0.3, 0.2]
        else: weights = [0.3, 0.4, 0.3]

        current_total_val = shares_to_buy * res['entry_price']
        e1_m, e2_m, e3_m = current_total_val * weights[0], current_total_val * weights[1], current_total_val * weights[2]
        e1_s, e2_s, e3_s = int(e1_m / e1_p), int(e2_m / e2_p), int(e3_m / e3_p)

        st.markdown("### 🏹 خطة التنفيذ المباشرة (حسب إدارة المخاطر)")
        st.markdown(f"""
        <div class='plan-container'>
        🟢 <b>لو السعر ≈ {e1_p:.2f} ج ➜ اشتري (دخول أساسي)</b><br>
        📦 الكمية: {e1_s:,} سهم | 💰 القيمة: {e1_m:,.0f} ج<br><br>

        🟡 <b>لو السعر نزل لـ {e2_p:.2f} ج ➜ اشتري (تعزيز دعم)</b><br>
        📦 الكمية: {e2_s:,} سهم | 💰 القيمة: {e2_m:,.0f} ج<br><br>

        🔵 <b>لو السعر اخترق {e3_p:.2f} ج ➜ اشتري (تأكيد اختراق)</b><br>
        📦 الكمية: {e3_s:,} سهم | 💰 القيمة: {e3_m:,.0f} ج
        </div>
        """, unsafe_allow_html=True)

    with tab_scenario:
        st.markdown("### 🧠 تحليل وضعك الحالي")
        col1, col2 = st.columns(2)
        buy_price = col1.number_input("سعر الشراء", value=res['p'], key=f"buy_{res['name']}")
        qty = col2.number_input("عدد الأسهم", value=100, step=1, key=f"qty_{res['name']}")

        if qty > 0 and buy_price > 0:
            current_price = res['p']
            pnl = (current_price - buy_price) * qty
            pnl_pct = ((current_price - buy_price) / buy_price) * 100

            if pnl > 0:
                st.success(f"🟢 انت كسبان: {pnl:,.0f} ج (+{pnl_pct:.2f}%)")
                if pnl_pct >= 3:
                    be_price = buy_price
                    st.info(f"💡 حرك وقف الخسارة لنقطة الدخول: {be_price:.2f}")
            elif pnl < 0:
                st.error(f"🔴 انت خسران: {pnl:,.0f} ج ({pnl_pct:.2f}%)")
            else:
                st.info("⚖️ انت على التعادل")

            st.markdown("---")
            trend_score = 0
            if res['t_short'] == "صاعد": trend_score += 1
            if res['t_med'] == "صاعد": trend_score += 1
            if res['ratio'] > 1.5: trend_score += 1

            st.markdown("### 🟢 الاستمرار (Hold)")
            if trend_score >= 2:
                st.success(f"الاتجاه كويس ✅ خليك مستمر طالما السعر فوق {res['stop_loss']:.2f} | الهدف: {res['target']:.2f}")
            else:
                st.warning("الاتجاه ضعيف ⚠️ الأفضل تأمين جزء من الربح")

            st.markdown("### 🟡 التبريد (Averaging)")
            avg_zone = res['entry_price'] * 0.97
            if res['t_short'] == "صاعد" and res['ratio'] > 1.2 and current_price > res['stop_loss']:
                st.success(f"✅ تبريد آمن نسبيًا عند {avg_zone:.2f}")
            else:
                st.warning(f"⚠️ تبريد خطر عند {avg_zone:.2f} (الاتجاه ضعيف أو السعر قرب الوقف)")

            st.markdown("#### 🧮 احسب متوسطك بعد التبريد")
            add_qty_scenario = st.number_input("كمية التبريد المقترحة", value=0, key=f"add_qty_scen_{res['name']}")
            if add_qty_scenario > 0:
                new_avg = ((buy_price * qty) + (avg_zone * add_qty_scenario)) / (qty + add_qty_scenario)
                st.info(f"📊 متوسطك الجديد: {new_avg:.2f}")

            st.markdown("### 🔴 الخروج (Exit)")
            st.error(f"وقف الخسارة: {res['stop_loss']:.2f} | لو كسرها ➜ خروج فوري ❌")

            st.markdown("---")
            st.markdown("### 🤖 القرار الذكي")
            if pnl_pct >= 7: st.success("🔒 تأمين قوي → بيع 50%")
            elif pnl_pct >= 3: st.info("⚖️ تأمين جزئي → بيع 25%")
            elif pnl_pct <= -3:
                if trend_score >= 2: st.warning("🟡 تبريد بحذر")
                else: st.error("🔴 تقليل مركز / خروج")
            else: st.info("⚖️ استنى إشارة أوضح")

            st.markdown("### 🚨 تنبيهات")
            alerts = []
            if res['ratio'] > 2: alerts.append("🚀 سيولة قوية")
            if res['rr'] < 1: alerts.append("❌ RR ضعيف")
            if res['t_short'] == "هابط": alerts.append("🔻 اتجاه هابط")
            if res['rsi'] > 75: alerts.append("🔴 تشبع شراء خطر")
            if current_price <= res['stop_loss']: alerts.append("⛔ كسر وقف الخسارة")
            if alerts:
                for a in alerts: st.warning(a)
            else: st.success("✅ لا يوجد خطر حالي")

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
        if st.button("⚡ مضاربات سريعة"): st.session_state.page = 'scalp'; st.rerun()

elif st.session_state.page == 'avg':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    st.title("🧮 حاسبة متوسط السعر")
    col1, col2 = st.columns(2)
    p1 = col1.number_input("سعر الشراء الأول", value=0.0, format="%.2f")
    q1 = col2.number_input("عدد الأسهم", value=0, step=1)
    p2 = col1.number_input("سعر التعزيز", value=0.0, format="%.2f")
    q2 = col2.number_input("عدد الأسهم (تعزيز)", value=0, step=1)
    if (q1 + q2) > 0:
        avg = ((p1 * q1) + (p2 * q2)) / (q1 + q2)
        st.success(f"📊 متوسط السعر الجديد: {avg:.2f}")

elif st.session_state.page == 'gold':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    render_mode_selector()
    raw_data = fetch_egx_data(scan_all=True)
    found = False
    for r in raw_data:
        an = analyze_stock(r)
        if an and classify_stock(an) == "gold":
            with st.expander(f"✨ ذهبي: {an['name']} (RR: {an['rr']} | RSI: {an['rsi']:.1f})"): 
                render_stock_ui(an)
                found = True
    if not found: st.info("لا توجد فرص ذهبية حالياً.")

elif st.session_state.page == 'scanner':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    render_mode_selector()
    raw_data = fetch_egx_data(scan_all=True)
    results = []
    for r in raw_data:
        an = analyze_stock(r)
        if an and classify_stock(an) == "watchlist":
            results.append(an)
    results.sort(key=lambda x: (x['score'], x['rr']), reverse=True)
    for an in results[:15]:
        with st.expander(f"{an['name']} | {an['signal']}"): render_stock_ui(an)

elif st.session_state.page == 'breakout':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    render_mode_selector()
    raw_data = fetch_egx_data(scan_all=True)
    for r in raw_data:
        an = analyze_stock(r)
        if an and classify_stock(an) == "breakout":
            with st.expander(f"🚀 اختراق: {an['name']} (RSI: {an['rsi']:.1f})"): render_stock_ui(an)

elif st.session_state.page == 'scalp':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    render_mode_selector()
    raw_data = fetch_egx_data(scan_all=True)
    found = False
    for r in raw_data:
        an = analyze_stock(r)
        if an and classify_stock(an) == "scalp":
            with st.expander(f"⚡ مضاربة: {an['name']} (RSI: {an['rsi']:.1f})"):
                render_stock_ui(an)
                found = True
    if not found:
        st.info("لا توجد مضاربات سريعة حالياً.")

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
