import streamlit as st
import requests

# ================== CONFIG & STYLE (V13.0 PRECISE & BOLD) ==================
st.set_page_config(page_title="EGX Sniper Elite v13.0", layout="wide")

st.markdown("""
    <style>
    /* تنسيق الأزرار */
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; font-size: 18px !important; font-weight: bold !important; margin-bottom: 10px; background-color: #1f4068; color: white; border: none; }
    .stButton>button:hover { background-color: #58a6ff; }
    
    /* تكبير العناوين والأسعار */
    .stock-header { font-size: 24px !important; font-weight: bold; color: #58a6ff; }
    .price-callout { font-size: 22px !important; font-weight: bold; color: #3fb950; } 
    .stoploss-callout { font-size: 20px !important; font-weight: bold; color: #f85149; } 
    
    /* ستايل متريكس والزخم */
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 8px; padding: 10px !important; }
    .vol-container { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; text-align: center; }
    .vol-icon { font-size: 35px; margin-bottom: 5px; } 
    .vol-number { font-size: 26px; font-weight: bold; color: white; }
    
    /* بطاقات الربح والخسارة الملونة (المطلوبة) */
    .pnl-container { display: flex; gap: 10px; margin-top: 15px; }
    .pnl-box { flex: 1; padding: 12px; border-radius: 10px; text-align: center; font-weight: bold; font-size: 16px; }
    .pnl-win { background-color: rgba(63, 185, 80, 0.15); color: #3fb950; border: 2px solid #3fb950; }
    .pnl-loss { background-color: rgba(248, 81, 73, 0.15); color: #f85149; border: 2px solid #f85149; }
    
    /* خطة السيولة والتعزيز */
    .plan-container { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-top: 15px; }
    .plan-step { margin-bottom: 12px; padding-right: 15px; border-right: 4px solid #58a6ff; line-height: 1.6; }
    .up-line { border-right-color: #3fb950; }
    .down-line { border-right-color: #f85149; }
    
    .target-box { background-color: #0d1117; border: 2px solid #58a6ff; border-radius: 12px; padding: 20px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'home'
def go_to(page_name):
    st.session_state.page = page_name
    st.rerun()

# ================== DATA ENGINE (FIXED SEARCH) ==================
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
        # البحث المتقدم بالاسم والرمز لضمان ظهور FERC
        payload = {
            "filter": [{"left": "name", "operation": "match", "right": symbol.upper()}],
            "columns": ["name", "close", "high", "low", "volume", "RSI", "average_volume_10d_calc", "change", "description"]
        }
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except: return []

# ================== ANALYSIS ENGINE ==================
def analyze_stock(d_row, is_scan=False):
    try:
        d = d_row['d']
        name, p, h, l, v, rsi, avg_v, chg, desc = d
        if p is None or h is None or l is None: return None
        
        pp = (p + h + l) / 3
        s1, r1 = (2 * pp) - h, (2 * pp) - l
        s2, r2 = pp - (h - l), pp + (h - l)
        
        ratio = v / (avg_v or 1)
        rsi_val = rsi if rsi else 0
        t_score = int(90 if rsi_val < 38 else 75 if rsi_val < 55 else 40)
        if p < pp: t_score -= 20
        
        is_breakout = (p >= h * 0.992 and ratio > 1.2)
        is_gold = (ratio > 1.6 and 50 < rsi_val < 65 and chg > 0.5)

        if ratio < 0.7: vol_txt, vol_col, vol_icon = "🔴 غائبة", "#ff4b4b", "💤"
        elif ratio < 1.3: vol_txt, vol_col, vol_icon = "⚪ هادئة", "#8b949e", "⚪"
        else: vol_txt, vol_col, vol_icon = "🔥 انفجاري", "#ffd700", "🔥"

        rec, col = ("🛑 تشبع شراء", "#ff4b4b") if rsi_val > 72 else ("💎 صفقة ذهبية", "#ffd700") if is_gold else ("🚀 شراء قوي", "#00ff00") if t_score >= 70 else ("⚖️ انتظار", "#58a6ff")

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "vol_txt": vol_txt, "vol_col": vol_col, "vol_icon": vol_icon,
            "t_e": s1, "t_t": r1, "t_s": s1 * 0.98, "t_score": t_score,
            "s_e": p, "s_t": r2, "s_s": s2, "s_score": int(80 if is_gold else 60),
            "rec": rec, "col": col, "is_gold": is_gold, "is_break": is_breakout
        }
    except: return None

# ================== UI RENDERER ==================
def render_stock_ui(res):
    if not res: return
    
    # رأس الصفحة والزخم
    st.markdown(f"<div style='display: flex; justify-content: space-between;'><span class='stock-header'>{res['name']} - {res['desc'][:20]}</span><span style='color:{res['col']}; font-weight:bold;'>{res['rec']}</span></div>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1, 1, 1.2])
    c1.metric("السعر الحالي", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("RSI", f"{res['rsi']:.1f}")
    with c3:
        st.markdown(f"<div class='vol-container'><div class='vol-icon'>{res['vol_icon']}</div><div class='vol-number'>{res['ratio']:.1f}x</div><div style='color:{res['vol_col']}; font-weight:bold;'>زخم {res['vol_txt']}</div></div>", unsafe_allow_html=True)
    
    st.divider()
    
    # ميزانية حساب الربح والخسارة
    budget = st.number_input("ميزانية السهم (ج):", value=20000, key=f"b_{res['name']}")
    
    col_t, col_s = st.columns(2)
    with col_t:
        st.markdown(f"**🎯 مضارب (Score: {res['t_score']})**")
        st.markdown(f"دخول: <span class='price-callout'>{res['t_e']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"هدف: <span class='price-callout'>{res['t_t']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"وقف: <span class='stoploss-callout'>{res['t_s']:.2f}</span>", unsafe_allow_html=True)
        
        t_profit = ((res['t_t'] - res['t_e']) / res['t_e']) * 100
        t_loss = ((res['t_s'] - res['t_e']) / res['t_e']) * 100
        st.markdown(f"<div class='pnl-container'><div class='pnl-box pnl-win'>💰 {t_profit:+.1f}%<br>(+{ (budget * t_profit/100):,.0f} ج)</div><div class='pnl-box pnl-loss'>⚠️ {t_loss:.1f}%<br>({ (budget * t_loss/100):,.0f} ج)</div></div>", unsafe_allow_html=True)

    with col_s:
        st.markdown(f"**🔁 سوينج (Score: {res['s_score']})**")
        st.markdown(f"دخول: <span class='price-callout'>{res['s_e']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"هدف: <span class='price-callout'>{res['s_t']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"وقف: <span class='stoploss-callout'>{res['s_s']:.2f}</span>", unsafe_allow_html=True)
        
        s_profit = ((res['s_t'] - res['s_e']) / res['s_e']) * 100
        s_loss = ((res['s_s'] - res['s_e']) / res['s_e']) * 100
        st.markdown(f"<div class='pnl-container'><div class='pnl-box pnl-win'>💰 {s_profit:+.1f}%<br>(+{ (budget * s_profit/100):,.0f} ج)</div><div class='pnl-box pnl-loss'>⚠️ {s_loss:.1f}%<br>({ (budget * s_loss/100):,.0f} ج)</div></div>", unsafe_allow_html=True)

    # خطة الدخول والسيولة
    st.markdown("---")
    st.subheader("🛠️ خطة السيولة وتمركزات التعزيز")
    p1, p2, p3 = budget * 0.3, budget * 0.4, budget * 0.3
    st.markdown(f"""
    <div class='plan-container'>
        <div class='plan-step up-line'>
            <b>📈 سيناريو الصعود (تجميع الأرباح):</b><br>
            • ادخل الآن بـ <span class='price-callout'>{p1:,.0f} ج</span> عند سعر {res['t_e']:.2f}.<br>
            • لو اخترق {res['t_t']:.2f} واستقر، زود بـ <span class='price-callout'>{p2:,.0f} ج</span>.<br>
            • <b>التعزيز النهائي:</b> ضخ الـ {p3:,.0f} ج الباقية عند تجاوز {res['s_t']:.2f}.
        </div>
        <div class='plan-step down-line'>
            <b>📉 سيناريو الهبوط (تعديل المتوسط):</b><br>
            • لو نزل السعر لـ <b style='color:#f85149;'>{res['s_s']:.2f}</b>، زود بـ <span class='price-callout'>{p2:,.0f} ج</span> لتحسين المتوسط.<br>
            • <b>تنبيه:</b> لو كسر السعر {res['s_s']*0.98:.2f} اخرج فوراً ولا تضخ باقي السيولة.
        </div>
    </div>
    """, unsafe_allow_html=True)

# ================== PAGES ==================
if st.session_state.page == 'home':
    st.title("🏹 EGX Sniper Elite v13.0")
    cols = st.columns(2)
    with cols[0]:
        if st.button("📡 تحليل سهم مباشر"): go_to('analyze')
        if st.button("🔭 كشاف السوق العام"): go_to('scanner')
        if st.button("💎 قنص الصفقات الذهبية"): go_to('gold')
    with cols[1]:
        if st.button("🚀 رادار الاختراقات"): go_to('breakout')
        if st.button("🧮 مساعد المتوسطات"): go_to('average')

elif st.session_state.page == 'analyze':
    if st.button("🏠 العودة"): go_to('home')
    sym = st.text_input("ادخل الرمز أو الاسم (مثلاً: ATQA أو FERC)").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data: render_stock_ui(analyze_stock(data[0]))
        else: st.warning("السهم غير موجود، تأكد من الرمز.")

elif st.session_state.page == 'scanner':
    if st.button("🏠"): go_to('home')
    if st.button("🔍 فحص سيولة السوق"):
        results = [an for r in fetch_egx_data(scan_all=True) if (an := analyze_stock(r, True)) and an['t_score'] >= 70]
        for an in sorted(results, key=lambda x: x['t_score'], reverse=True):
            with st.expander(f"⭐ {an['t_score']} | {an['name']}"): render_stock_ui(an)

elif st.session_state.page == 'average':
    if st.button("🏠"): go_to('home')
    st.subheader("🧮 حاسبة تعديل المتوسط المستهدف")
    c1, c2, c3 = st.columns(3)
    old_p, old_q = c1.number_input("السعر القديم", 0.0), c2.number_input("الكمية", 0)
    new_p = c3.number_input("السعر الحالي", 0.0)
    if old_p > 0 and new_p > 0:
        target = st.number_input("المتوسط اللي نفسك توصله؟", value=old_p*0.95)
        if new_p < target < old_p:
            needed = (old_q * (old_p - target)) / (target - new_p)
            st.markdown(f"<div class='target-box'><h3>خطة الوصول لمتوسط {target:.2f}</h3><p>✅ شراء: <b>{int(needed):,} سهم</b></p><p>✅ سيولة مطلوبة: <b>{(needed*new_p):,.2f} ج</b></p></div>", unsafe_allow_html=True)

elif st.session_state.page == 'breakout':
    if st.button("🏠"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r, True)) and an['is_break']:
            with st.container(): render_stock_ui(an)

elif st.session_state.page == 'gold':
    if st.button("🏠"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r, True)) and an['is_gold']:
            render_stock_ui(an)
