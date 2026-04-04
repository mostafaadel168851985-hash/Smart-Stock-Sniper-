import streamlit as st
import requests

# ================== CONFIG & STYLE (V12.2 PERFECTED) ==================
st.set_page_config(page_title="EGX Sniper Elite v12.2", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-size: 18px !important; font-weight: bold !important; margin-bottom: 10px; }
    .stock-header { font-size: 18px !important; font-weight: bold; color: #58a6ff; }
    .price-callout { font-size: 16px !important; font-weight: bold; color: #3fb950; }
    .stoploss-callout { font-size: 14px !important; font-weight: bold; color: #f85149; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 8px; padding: 5px !important; }
    
    /* رجوع ألوان المتوسط القديمة */
    .avg-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-bottom: 12px; border-left: 5px solid #58a6ff; }
    .target-box { background-color: #0d1117; border: 2px solid #58a6ff; border-radius: 12px; padding: 20px; margin-top: 15px; text-align: center; }
    .target-res { color: #3fb950; font-weight: bold; font-size: 20px; }
    
    .warning-box { background-color: #2e2a0b; border: 1px solid #ffd700; color: #ffd700; padding: 12px; border-radius: 10px; margin-top: 10px; font-weight: bold; border-left: 6px solid #ffd700; }
    .vol-container { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 8px; text-align: center; }
    
    /* ستايل الخطة الشاملة */
    .plan-section { background: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-top: 10px; }
    .up-scen { border-right: 4px solid #3fb950; padding-right: 10px; margin-bottom: 10px; }
    .down-scen { border-right: 4px solid #f85149; padding-right: 10px; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'home'
def go_to(page_name):
    st.session_state.page = page_name
    st.rerun()

# ================== DATA ENGINE ==================
@st.cache_data(ttl=300)
def fetch_egx_data(symbol=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    if scan_all:
        payload = {
            "filter": [{"left": "volume", "operation": "greater", "right": 50000}, {"left": "close", "operation": "greater", "right": 0.4}],
            "columns": ["name", "close", "RSI", "volume", "average_volume_10d_calc", "high", "low", "change", "description"],
            "sort": {"sortBy": "change", "sortOrder": "desc"}, "range": [0, 100]
        }
    else:
        payload = {
            "symbols": {"tickers": [f"EGX:{symbol.upper()}"], "query": {"types": []}},
            "columns": ["close", "high", "low", "volume", "RSI", "average_volume_10d_calc", "change", "description"]
        }
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except: return []

# ================== ANALYSIS ENGINE ==================
def analyze_stock(d_row, is_scan=False):
    try:
        d = d_row['d']
        if is_scan: name, p, rsi, v, avg_v, h, l, chg, desc = d
        else: p, h, l, v, rsi, avg_v, chg, desc = d; name = ""
        
        if p is None or h is None or l is None: return None
        pp = (p + h + l) / 3
        s1, r1 = (2 * pp) - h, (2 * pp) - l
        s2, r2 = pp - (h - l), pp + (h - l)
        
        ratio = v / (avg_v or 1)
        rsi_val = rsi if rsi else 0
        trend_ok = p > pp
        volume_ok = ratio > 1

        t_score = int(90 if rsi_val < 38 else 75 if rsi_val < 55 else 40)
        if not trend_ok: t_score -= 20
        if not volume_ok: t_score -= 15
        t_score = max(t_score, 0)

        s_score = int(85 if (ratio > 1.1 and 40 < rsi_val < 65) else 50)
        is_breakout = (p >= h * 0.992 and ratio > 1.2 and rsi_val > 52)
        is_gold = (ratio > 1.6 and 50 < rsi_val < 65 and chg > 0.5 and trend_ok)

        if ratio < 0.7: vol_txt, vol_col = "🔴 سيولة غائبة", "#ff4b4b"
        elif ratio < 1.3: vol_txt, vol_col = "⚪ تداول هادئ", "#8b949e"
        else: vol_txt, vol_col = "🔥 زخم انفجاري", "#ffd700"

        if rsi_val > 72: rec, col = "🛑 تشبع شراء", "#ff4b4b"
        elif is_gold: rec, col = "💎 صفقة ذهبية", "#ffd700"
        elif t_score >= 75: rec, col = "🚀 شراء قوي", "#00ff00"
        else: rec, col = "⚖️ انتظار", "#58a6ff"

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "vol_txt": vol_txt, "vol_col": vol_col,
            "t_e": s1, "t_t": r1, "t_s": s1 * 0.98, "t_score": t_score,
            "s_e": p, "s_t": r2, "s_s": s2, "s_score": s_score,
            "rec": rec, "col": col, "is_gold": is_gold, "is_break": is_breakout, "s2": s2
        }
    except: return None

# ================== UI RENDERER ==================
def render_stock_ui(res, title=""):
    if not res: return
    if title: st.markdown(f"<div class='breakout-card' style='border:2px solid #00ffcc; background:#0a1a1a; padding:10px; border-radius:12px; margin-bottom:10px;'>{title}</div>", unsafe_allow_html=True)
    
    st.markdown(f"""
        <div style='display: flex; justify-content: space-between; align-items: center;'>
            <span class='stock-header'>{res['name']} {res['desc'][:20]}</span>
            <span style='color:{res['col']}; font-weight:bold; border:1px solid {res['col']}; padding:2px 8px; border-radius:6px;'>{res['rec']}</span>
        </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("RSI", f"{res['rsi']:.1f}")
    with c3:
        st.markdown(f"<div class='vol-container'><div style='color:#8b949e;font-size:10px;'>الزخم</div><div style='font-size:16px;font-weight:bold;'>{res['ratio']:.1f}x</div><div style='color:{res['vol_col']};font-size:10px;'>{res['vol_txt']}</div></div>", unsafe_allow_html=True)
    
    daily_top = res['t_e'] * 1.008
    if res['p'] > daily_top * 1.015:
        st.markdown(f"<div class='warning-box'>⚠️ مطاردة خطر! السعر بعيد عن منطقة الدخول ({daily_top:.2f})</div>", unsafe_allow_html=True)
    
    st.divider()
    col_t, col_s = st.columns(2)
    with col_t:
        st.markdown(f"**🎯 مضارب (Score: {res['t_score']})**")
        st.markdown(f"دخول: <span class='price-callout'>{res['t_e']:.2f} - {daily_top:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"هدف: <span class='price-callout'>{res['t_t']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"وقف: <span class='stoploss-callout'>{res['t_s']:.2f}</span>", unsafe_allow_html=True)
    with col_s:
        st.markdown(f"**🔁 سوينج (Score: {res['s_score']})**")
        st.markdown(f"دخول: <span class='price-callout'>{res['s_e']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"هدف: <span class='price-callout'>{res['s_t']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"وقف: <span class='stoploss-callout'>{res['s_s']:.2f}</span>", unsafe_allow_html=True)

    # --- الخطة الشاملة (صعود وهبوط) ---
    st.markdown("---")
    st.subheader("🛠️ استراتيجية السيولة الذكية")
    budget = st.number_input("ميزانية السهم (جنيه):", value=20000, key=f"plan_{res['name']}")
    p1, p2, p3 = budget * 0.3, budget * 0.4, budget * 0.3
    
    st.markdown(f"""
    <div class='plan-section'>
        <div class='up-scen'>
            <b>📈 في حالة الصعود:</b><br>
            - اشتري بـ <span class='price-callout'>{p1:,.0f} ج</span> الآن (جس نبض).<br>
            - زود بـ <span class='price-callout'>{p2:,.0f} ج</span> لو السهم اخترق واستقر فوق {res['t_t']:.2f}.
        </div>
        <div class='down-scen'>
            <b>📉 في حالة الهبوط (تعديل):</b><br>
            - لو السهم نزل لـ <span class='price-callout'>{res['s2']:.2f}</span> (دعم قوي)، زود بـ <span class='price-callout'>{p2:,.0f} ج</span> لتحسين المتوسط.<br>
            - <span class='stoploss-callout'>تنبيه:</span> لو كسر السهم {res['t_s']:.2f}، اخرج فوراً ولا تضخ باقي الميزانية ({p3:,.0f} ج).
        </div>
    </div>
    """, unsafe_allow_html=True)

# ================== NAVIGATION ==================
if st.session_state.page == 'home':
    st.title("🏹 EGX Sniper Elite v12.2")
    if st.button("📡 تحليل سهم"): go_to('analyze')
    if st.button("🔭 كشاف السوق"): go_to('scanner')
    if st.button("🚀 رادار الاختراقات"): go_to('breakout')
    if st.button("🧮 مساعد المتوسطات"): go_to('average')
    if st.button("💎 قنص الذهب"): go_to('gold')

elif st.session_state.page == 'analyze':
    if st.button("🏠"): go_to('home')
    sym = st.text_input("ادخل رمز السهم (مثلاً: ATQA)").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data: render_stock_ui(analyze_stock(data[0]))

elif st.session_state.page == 'scanner':
    if st.button("🏠"): go_to('home')
    if st.button("🔍 فحص السوق"):
        results = [an for r in fetch_egx_data(scan_all=True) if (an := analyze_stock(r, True)) and an['t_score'] >= 70]
        results.sort(key=lambda x: x['t_score'], reverse=True)
        for an in results:
            with st.expander(f"⭐ {an['t_score']} | {an['name']}"): render_stock_ui(an)

elif st.session_state.page == 'breakout':
    if st.button("🏠"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r, True)) and an['is_break']:
            render_stock_ui(an, f"🚀 اختراق: {an['name']}")

elif st.session_state.page == 'gold':
    if st.button("🏠"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r, True)) and an['is_gold']:
            render_stock_ui(an, "💎 فرصة ذهبية")

elif st.session_state.page == 'average':
    if st.button("🏠"): go_to('home')
    st.subheader("🧮 مساعد متوسط التكلفة")
    c1, c2, c3 = st.columns(3)
    old_p = c1.number_input("السعر القديم", value=0.0, format="%.2f")
    old_q = c2.number_input("الكمية القديمة", value=0)
    new_p = c3.number_input("السعر الجديد (التعديل)", value=0.0, format="%.2f")
    
    if old_p > 0 and old_q > 0 and new_p > 0:
        total_old = old_p * old_q
        for label, q in [("بسيط (0.5x)", int(old_q*0.5)), ("متوسط (1:1)", old_q), ("جذري (2:1)", old_q*2)]:
            avg = (total_old + (q * new_p)) / (old_q + q)
            st.markdown(f"<div class='avg-card'><b>{label}</b>: شراء {q:,} سهم.<br>المتوسط الجديد: <span class='price-callout'>{avg:.3f} ج</span></div>", unsafe_allow_html=True)
        
        st.divider()
        target = st.number_input("المتوسط المستهدف؟", value=old_p-0.01, format="%.2f")
        if new_p < target < old_p:
            needed_q = (old_q * (old_p - target)) / (target - new_p)
            needed_money = needed_q * new_p
            st.markdown(f"""
                <div class='target-box'>
                    <h3>الوصول لمتوسط {target:.2f}</h3>
                    شراء عدد: <span class='target-res'>{int(needed_q):,} سهم</span><br>
                    بمبلغ إجمالي: <span class='target-res'>{needed_money:,.2f} جنيه</span>
                </div>
            """, unsafe_allow_html=True)
