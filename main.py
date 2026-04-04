import streamlit as st
import requests

# ================== CONFIG & STYLE (V12.7 PRECISE LOOK) ==================
st.set_page_config(page_title="EGX Sniper Elite v15.0", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-size: 18px !important; font-weight: bold !important; margin-bottom: 10px; }
    .stock-header { font-size: 18px !important; font-weight: bold; color: #58a6ff; }
    .price-callout { font-size: 16px !important; font-weight: bold; color: #3fb950; }
    .stoploss-callout { font-size: 14px !important; font-weight: bold; color: #f85149; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 8px; padding: 5px !important; }
    .warning-box { background-color: #2e2a0b; border: 1px solid #ffd700; color: #ffd700; padding: 12px; border-radius: 10px; margin-top: 10px; font-weight: bold; border-left: 6px solid #ffd700; }
    .plan-container { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-top: 15px; }
    .avg-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-bottom: 12px; border-left: 5px solid #58a6ff; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'home'
def go_to(page_name):
    st.session_state.page = page_name
    st.rerun()

# ================== DATA ENGINE (FIXED TO FIND ALL SYMBOLS) ==================
@st.cache_data(ttl=300)
def fetch_egx_data(symbol=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    if not scan_all and symbol:
        # تعديل البحث ليكون أكثر مرونة لإيجاد FERC وغيرها
        payload = {"filter": [{"left": "name", "operation": "match", "right": symbol.upper()}],
                   "columns": ["name", "close", "RSI", "volume", "average_volume_10d_calc", "high", "low", "change", "description"]}
    else:
        payload = {"filter": [{"left": "volume", "operation": "greater", "right": 10000}],
                   "columns": ["name", "close", "RSI", "volume", "average_volume_10d_calc", "high", "low", "change", "description"],
                   "sort": {"sortBy": "change", "sortOrder": "desc"}, "range": [0, 100]}
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except: return []

# ================== ANALYSIS ENGINE (V11.8 ORIGINAL LOGIC) ==================
def analyze_stock(d_row):
    try:
        d = d_row['d']
        name, p, rsi, v, avg_v, h, l, chg, desc = d
        if p is None or h is None or l is None: return None
        
        # حسابات Pivot Points الدقيقة (المعلومات اللي بتثق فيها)
        pp = (p + h + l) / 3
        s1, r1 = (2 * pp) - h, (2 * pp) - l
        s2, r2 = pp - (h - l), pp + (h - l)
        
        ratio = v / (avg_v or 1)
        rsi_val = rsi or 0
        trend_ok = p > pp

        # السكور (المعلومات التقنية)
        t_score = int(90 if rsi_val < 38 else 75 if rsi_val < 55 else 40)
        if not trend_ok: t_score -= 20
        t_score = max(t_score, 0)

        is_gold = (ratio > 1.6 and 50 < rsi_val < 65 and chg > 0.5 and trend_ok)
        is_break = (p >= h * 0.992 and ratio > 1.2 and rsi_val > 52)

        rec, col = ("🛑 تشبع شراء", "#ff4b4b") if rsi_val > 72 else ("💎 ذهب", "#ffd700") if is_gold else ("🚀 شراء قوي", "#00ff00") if t_score >= 75 else ("⚖️ انتظار", "#58a6ff")

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "t_e": s1, "t_t": r1, "t_s": s1 * 0.98, "t_score": t_score,
            "s_e": p, "s_t": r2, "s_s": s2, "rec": rec, "col": col, "is_gold": is_gold, "is_break": is_break
        }
    except: return None

# ================== UI RENDERER ==================
def render_stock_ui(res):
    if not res: return
    
    # 1. الترويسة والحالة
    st.markdown(f"<div class='stock-header'>{res['name']} - {res['desc'][:20]} <span style='color:{res['col']}; float:left;'>{res['rec']}</span></div>", unsafe_allow_html=True)
    
    # 2. معلومات السوق الأساسية
    c1, c2, c3 = st.columns(3)
    c1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("RSI", f"{res['rsi']:.1f}")
    c3.metric("الزخم (Vol Ratio)", f"{res['ratio']:.1f}x")

    # 3. إشعار مطاردة السهم (معلومة حيوية)
    daily_entry_top = res['t_e'] * 1.008
    if res['p'] > daily_entry_top * 1.015:
        st.markdown(f"<div class='warning-box'>⚠️ مطاردة خطر! السعر الحالي بعيد عن منطقة الدخول المثالية ({daily_entry_top:.2f})</div>", unsafe_allow_html=True)

    st.divider()

    # 4. معلومات المضارب والسوينج (الأهداف والوقف)
    col_t, col_s = st.columns(2)
    with col_t:
        st.markdown(f"**🎯 مضارب (Score: {res['t_score']})**")
        st.markdown(f"دخول: <span class='price-callout'>{res['t_e']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"هدف: <span class='price-callout'>{res['t_t']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"وقف: <span class='stoploss-callout'>{res['t_s']:.2f}</span>", unsafe_allow_html=True)
    with col_s:
        st.markdown("**🔁 سوينج**")
        st.markdown(f"دخول: <span class='price-callout'>{res['s_e']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"هدف: <span class='price-callout'>{res['s_t']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"وقف: <span class='stoploss-callout'>{res['s_s']:.2f}</span>", unsafe_allow_html=True)

    # 5. خطة الميزانية وحسابات الربح/الخسارة (معلومات مالية)
    st.markdown("---")
    st.subheader("🛠️ إدارة السيولة (إجمالي الـ 20 ألف)")
    budget = st.number_input("ميزانية السهم (ج):", value=20000, key=f"b_{res['name']}")
    
    p1, p2, p3 = budget * 0.3, budget * 0.4, budget * 0.3
    # حساب الربح المتوقع بالجنيه
    profit_amt = ((res['t_t'] - res['t_e']) / res['t_e']) * budget
    
    st.markdown(f"""
    <div class='plan-container'>
        <div style='border-right: 4px solid #3fb950; padding-right:10px; margin-bottom:10px;'>
            <b>📈 سيناريو الصعود (الربح المتوقع: {profit_amt:,.0f} ج):</b><br>
            • ادخل بـ {p1:,.0f} ج عند {res['t_e']:.2f}.<br>
            • زود بـ {p2:,.0f} ج عند اختراق {res['t_t']:.2f}.
        </div>
        <div style='border-right: 4px solid #f85149; padding-right:10px;'>
            <b>📉 سيناريو الهبوط:</b><br>
            • لو نزل لـ {res['s_s']:.2f}، استهلك {p2:,.0f} ج لتعديل المتوسط.<br>
            • الوقف النهائي كسر {res['t_s']:.2f}.
        </div>
    </div>
    """, unsafe_allow_html=True)

# ================== PAGES ==================
if st.session_state.page == 'home':
    st.title("🏹 EGX Sniper Elite v15.0")
    if st.button("📡 تحليل سهم"): go_to('analyze')
    if st.button("🔭 كشاف السوق"): go_to('scanner')
    if st.button("🚀 رادار الاختراقات والذهب"): go_to('gold')
    if st.button("🧮 مساعد المتوسطات"): go_to('average')

elif st.session_state.page == 'analyze':
    if st.button("🏠"): go_to('home')
    sym = st.text_input("ادخل رمز السهم (FERC, ATQA, الخ)").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data: render_stock_ui(analyze_stock(data[0]))
        else: st.error("لم يتم العثور على السهم.")

elif st.session_state.page == 'average':
    if st.button("🏠"): go_to('home')
    st.subheader("🧮 مساعد المتوسطات الكامل")
    c1, c2, c3 = st.columns(3)
    p_old, q_old = c1.number_input("السعر القديم", 0.0), c2.number_input("الكمية القديمة", 0)
    p_now = c3.number_input("السعر الحالي", 0.0)
    if p_old > 0 and q_old > 0 and p_now > 0:
        for label, q_add in [("بسيط (0.5x)", int(q_old*0.5)), ("متوسط (1:1)", q_old), ("جذري (2:1)", q_old*2)]:
            avg = ((p_old * q_old) + (p_now * q_add)) / (q_old + q_add)
            st.markdown(f"<div class='avg-card'><b>{label}</b>: شراء {q_add:,} سهم<br>المتوسط الجديد: {avg:.3f} ج</div>", unsafe_allow_html=True)

elif st.session_state.page == 'scanner':
    if st.button("🏠"): go_to('home')
    if st.button("🔍 فحص السوق"):
        for r in fetch_egx_data(scan_all=True):
            if an := analyze_stock(r):
                with st.expander(f"{an['name']} (Score: {an['t_score']})"): render_stock_ui(an)

elif st.session_state.page == 'gold':
    if st.button("🏠"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        ans = analyze_stock(r)
        if ans and (ans['is_gold'] or ans['is_break']):
            type_f = "💎 ذهب" if ans['is_gold'] else "🚀 اختراق"
            with st.expander(f"{type_f}: {ans['name']}"): render_stock_ui(ans)
