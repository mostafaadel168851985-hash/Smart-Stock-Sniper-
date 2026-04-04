import streamlit as st
import requests

# ================== CONFIG & STYLE (V12.9 PERFECTED) ==================
st.set_page_config(page_title="EGX Sniper Elite v12.9", layout="wide")

st.markdown("""
    <style>
    /* تحسين الأزرار الأساسية */
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; font-size: 18px !important; font-weight: bold !important; margin-bottom: 10px; background-color: #1f4068; color: white; border: none; }
    .stButton>button:hover { background-color: #58a6ff; }
    
    /* تكبير العناوين والأرقام الأساسية */
    .stock-header { font-size: 24px !important; font-weight: bold; color: #58a6ff; }
    .price-callout { font-size: 20px !important; font-weight: bold; color: #3fb950; } /* تكبير خط الدخول والهدف */
    .stoploss-callout { font-size: 20px !important; font-weight: bold; color: #f85149; } /* تكبير خط الوقف */
    
    /* ستايل متريكس المحسن */
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 8px; padding: 10px !important; }
    
    /* ستايل الزخم الانفجاري (تكبير وتمييز) */
    .vol-container { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 15px; text-align: center; }
    .vol-icon { font-size: 30px; margin-bottom: 5px; } /* الرمز أكبر */
    .vol-number { font-size: 24px; font-weight: bold; color: white; } /* الرقم أكبر */
    .vol-status { background-color: rgba(255, 215, 0, 0.1); color: #ffd700; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 14px; }
    
    /* ستايل بطاقات الربح والخسارة المحسن */
    .pnl-container { display: flex; gap: 10px; margin-top: 10px; }
    .pnl-box { flex: 1; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; font-size: 15px; }
    .pnl-win { background-color: rgba(63, 185, 80, 0.1); color: #3fb950; border: 1px solid #3fb950; }
    .pnl-loss { background-color: rgba(248, 81, 73, 0.1); color: #f85149; border: 1px solid #f85149; }
    
    /* بطاقات مساعد المتوسطات */
    .avg-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-bottom: 12px; border-left: 5px solid #58a6ff; }
    .target-box { background-color: #0d1117; border: 2px solid #58a6ff; border-radius: 12px; padding: 20px; margin-top: 15px; text-align: center; }
    .plan-container { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-top: 15px; }
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
        # المحاولة الأولى: البحث بالكود المباشر (ATQA, ALCN..)
        payload = {
            "symbols": {"tickers": [f"EGX:{symbol.upper()}"], "query": {"types": []}},
            "columns": ["name", "close", "high", "low", "volume", "RSI", "average_volume_10d_calc", "change", "description"]
        }
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        data = r.get("data", [])
        
        # المحاولة الثانية (البحث المرن): لو السهم زي FERC و NAPR مش متسجل بالكود العادي
        if not data and not scan_all and symbol:
            search_payload = {
                "filter": [{"left": "name", "operation": "match", "right": symbol.upper()}],
                "columns": ["name", "close", "high", "low", "volume", "RSI", "average_volume_10d_calc", "change", "description"]
            }
            r_alt = requests.post(url, json=search_payload, timeout=10).json()
            return r_alt.get("data", [])
        return data
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
        trend_ok = p > pp
        volume_ok = ratio > 1

        t_score = int(90 if rsi_val < 38 else 75 if rsi_val < 55 else 40)
        if not trend_ok: t_score -= 20
        if not volume_ok: t_score -= 15
        t_score = max(t_score, 0)

        s_score = int(85 if (ratio > 1.1 and 40 < rsi_val < 65) else 50)
        is_breakout = (p >= h * 0.992 and ratio > 1.2 and rsi_val > 52)
        is_gold = (ratio > 1.6 and 50 < rsi_val < 65 and chg > 0.5 and trend_ok)

        # تحسين وصف الزخم
        if ratio < 0.7: vol_txt, vol_col, vol_icon = "🔴 غائبة", "#ff4b4b", "💤"
        elif ratio < 1.3: vol_txt, vol_col, vol_icon = "⚪ هادئة", "#8b949e", "⚪"
        else: vol_txt, vol_col, vol_icon = "🔥 انفجاري", "#ffd700", "🔥"

        if rsi_val > 72: rec, col = "🛑 تشبع شراء", "#ff4b4b"
        elif is_gold: rec, col = "💎 صفقة ذهبية", "#ffd700"
        elif t_score >= 75: rec, col = "🚀 شراء قوي", "#00ff00"
        else: rec, col = "⚖️ انتظار", "#58a6ff"

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "vol_txt": vol_txt, "vol_col": vol_col, "vol_icon": vol_icon,
            "t_e": s1, "t_t": r1, "t_s": s1 * 0.98, "t_score": t_score,
            "s_e": p, "s_t": r2, "s_s": s2, "s_score": s_score,
            "rec": rec, "col": col, "is_gold": is_gold, "is_break": is_breakout
        }
    except: return None

# ================== UI RENDERER ==================
def render_stock_ui(res, title=""):
    if not res: return
    
    st.markdown(f"<div style='display: flex; justify-content: space-between; align-items: center;'><span class='stock-header'>{res['name']} {res['desc'][:20]}</span><span style='color:{res['col']}; font-weight:bold; border:1px solid {res['col']}; padding:2px 8px; border-radius:6px;'>{res['rec']}</span></div>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("RSI", f"{res['rsi']:.1f}")
    with c3:
        # زخم مكبر ومميز
        st.markdown(f"""
        <div class='vol-container'>
            <div class='vol-icon'>{res['vol_icon']}</div>
            <div class='vol-number'>{res['ratio']:.1f}x</div>
            <div class='vol-status'>{res['vol_txt']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    budget = st.number_input("ميزانية السهم لحساب الربح/الخسارة:", value=20000, key=f"bud_{res['name']}")

    col_t, col_s = st.columns(2)
    with col_t:
        st.markdown(f"**🎯 مضارب (Score: {res['t_score']})**")
        # أرقام مكبرة
        st.markdown(f"دخول: <span class='price-callout'>{res['t_e']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"هدف: <span class='price-callout'>{res['t_t']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"وقف: <span class='stoploss-callout'>{res['t_s']:.2f}</span>", unsafe_allow_html=True)
        
        # تصحيح حسابات P&L (المعادلة الصحيحة)
        t_profit_pct = ((res['t_t'] - res['t_e']) / res['t_e']) * 100
        t_loss_pct = ((res['t_s'] - res['t_e']) / res['t_e']) * 100
        st.markdown(f"""
        <div class='pnl-container'>
            <div class='pnl-box pnl-win'>💰 {t_profit_pct:+.1f}% (+{ (budget * t_profit_pct/100):,.0f} ج)</div>
            <div class='pnl-box pnl-loss'>⚠️ {t_loss_pct:.1f}% ({ (budget * t_loss_pct/100):,.0f} ج)</div>
        </div>
        """, unsafe_allow_html=True)

    with col_s:
        st.markdown(f"**🔁 سوينج (Score: {res['s_score']})**")
        st.markdown(f"دخول: <span class='price-callout'>{res['s_e']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"هدف: <span class='price-callout'>{res['s_t']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"وقف: <span class='stoploss-callout'>{res['s_s']:.2f}</span>", unsafe_allow_html=True)
        
        # تصحيح حسابات P&L
        s_profit_pct = ((res['s_t'] - res['s_e']) / res['s_e']) * 100
        s_loss_pct = ((res['s_s'] - res['s_e']) / res['s_e']) * 100
        st.markdown(f"""
        <div class='pnl-container'>
            <div class='pnl-box pnl-win'>💰 {s_profit_pct:+.1f}% (+{ (budget * s_profit_pct/100):,.0f} ج)</div>
            <div class='pnl-box pnl-loss'>⚠️ {s_loss_pct:.1f}% ({ (budget * s_loss_pct/100):,.0f} ج)</div>
        </div>
        """, unsafe_allow_html=True)

# ================== NAVIGATION ==================
if st.session_state.page == 'home':
    st.title("🏹 EGX Sniper Elite v12.9")
    if st.button("📡 تحليل سهم"): go_to('analyze')
    if st.button("🔭 كشاف السوق"): go_to('scanner')
    if st.button("🚀 رادار الاختراقات"): go_to('breakout')
    if st.button("🧮 مساعد المتوسطات"): go_to('average')
    if st.button("💎 قنص الذهب"): go_to('gold')

elif st.session_state.page == 'average':
    if st.button("🏠"): go_to('home')
    st.subheader("🧮 مساعد متوسط التكلفة")
    c1, c2, c3 = st.columns(3)
    old_p, old_q = c1.number_input("السعر القديم", 0.0), c2.number_input("الكمية القديمة", 0)
    new_p = c3.number_input("السعر الجديد", 0.0)
    if old_p > 0 and old_q > 0 and new_p > 0:
        total_old = old_p * old_q
        for label, q in [("بسيط (0.5x)", int(old_q*0.5)), ("متوسط (1:1)", old_q), ("جذري (2:1)", old_q*2)]:
            cost = q * new_p
            avg = (total_old + cost) / (old_q + q)
            st.markdown(f"<div class='avg-card'><b>{label}</b>: شراء {q:,} سهم بتكلفة {cost:,.2f} ج<br>المتوسط الجديد: <span class='price-callout'>{avg:.3f} ج</span></div>", unsafe_allow_html=True)
        
        st.divider()
        # إعادة المتوسط المستهدف التلقائي
        target = st.number_input("المتوسط المستهدف؟", value=old_p-0.01)
        if new_p < target < old_p:
            needed_q = (old_q * (old_p - target)) / (target - new_p)
            st.markdown(f"<div class='target-box'><h3>خطة الوصول لهدف {target:.2f}</h3><p>✅ شراء: <b style='color:#3fb950; font-size:18px;'>{int(needed_q):,} سهم</b></p><p>✅ مبلغ: <b style='color:#3fb950; font-size:18px;'>{(needed_q*new_p):,.2f} ج</b></p></div>", unsafe_allow_html=True)

elif st.session_state.page == 'analyze':
    if st.button("🏠"): go_to('home')
    sym = st.text_input("ادخل رمز السهم (مثلاً: ATQA أو FERC)").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data: 
            render_stock_ui(analyze_stock(data[0]))
        else: st.error("عذراً، لم يتم العثور على بيانات لهذا الرمز.")
