import streamlit as st
import requests

# ================== CONFIG & STYLE (V13.0 PRO) ==================
st.set_page_config(page_title="EGX Sniper Elite v13.0", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-size: 18px !important; font-weight: bold !important; margin-bottom: 10px; }
    .stock-header { font-size: 18px !important; font-weight: bold; color: #58a6ff; }
    .price-callout { font-size: 16px !important; font-weight: bold; color: #3fb950; }
    .stoploss-callout { font-size: 14px !important; font-weight: bold; color: #f85149; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 8px; padding: 5px !important; }
    .avg-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-bottom: 12px; border-left: 5px solid #58a6ff; }
    .target-box { background-color: #0d1117; border: 2px solid #58a6ff; border-radius: 12px; padding: 20px; margin-top: 15px; text-align: center; }
    .warning-box { background-color: #2e2a0b; border: 1px solid #ffd700; color: #ffd700; padding: 12px; border-radius: 10px; margin-top: 10px; font-weight: bold; border-left: 6px solid #ffd700; }
    .vol-container { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 8px; text-align: center; }
    .plan-container { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-top: 15px; }
    .plan-step { margin-bottom: 8px; padding-right: 10px; }
    .up-line { border-right: 4px solid #3fb950; }
    .down-line { border-right: 4px solid #f85149; }
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
    # البحث بالفلتر لضمان إيجاد أي رمز (مثل FERC)
    if not scan_all and symbol:
        payload = {
            "filter": [{"left": "name", "operation": "match", "right": symbol.upper()}],
            "columns": ["name", "close", "RSI", "volume", "average_volume_10d_calc", "high", "low", "change", "description"]
        }
    else:
        payload = {
            "filter": [{"left": "volume", "operation": "greater", "right": 10000}],
            "columns": ["name", "close", "RSI", "volume", "average_volume_10d_calc", "high", "low", "change", "description"],
            "sort": {"sortBy": "change", "sortOrder": "desc"}, "range": [0, 150]
        }
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except: return []

# ================== ANALYSIS ENGINE ==================
def analyze_stock(d_row):
    try:
        d = d_row['d']
        name, p, rsi, v, avg_v, h, l, chg, desc = d
        
        if p is None or h is None or l is None: return None
        pp = (p + h + l) / 3
        s1, r1 = (2 * pp) - h, (2 * pp) - l
        s2, r2 = pp - (h - l), pp + (h - l)
        
        ratio = v / (avg_v or 1)
        rsi_val = rsi or 0
        
        t_score = int(90 if rsi_val < 38 else 75 if rsi_val < 55 else 40)
        is_breakout = (p >= h * 0.992 and ratio > 1.2)
        is_gold = (ratio > 1.6 and 50 < rsi_val < 65 and chg > 0.5)

        rec, col = ("🛑 تشبع", "#ff4b4b") if rsi_val > 72 else ("💎 ذهب", "#ffd700") if is_gold else ("🚀 شراء", "#00ff00") if t_score >= 75 else ("⚖️ انتظار", "#58a6ff")

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "t_e": s1, "t_t": r1, "t_s": s1 * 0.98, "t_score": t_score,
            "s_e": p, "s_t": r2, "s_s": s2, "rec": rec, "col": col, 
            "is_gold": is_gold, "is_break": is_breakout
        }
    except: return None

# ================== UI RENDERER ==================
def render_stock_ui(res):
    if not res: return
    st.markdown(f"""<div style='display: flex; justify-content: space-between; align-items: center;'>
        <span class='stock-header'>{res['name']} - {res['desc'][:20]}</span>
        <span style='color:{res['col']}; font-weight:bold; border:1px solid {res['col']}; padding:2px 8px; border-radius:6px;'>{res['rec']}</span>
    </div>""", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("RSI", f"{res['rsi']:.1f}")
    c3.metric("الزخم", f"{res['ratio']:.1f}x")

    # إشعار المطاردة (مهم جداً للثقة في التطبيق)
    daily_entry_top = res['t_e'] * 1.008
    if res['p'] > daily_entry_top * 1.015:
        st.markdown(f"<div class='warning-box'>⚠️ مطاردة خطر! السعر عالي جداً عن منطقة الدخول ({daily_entry_top:.2f})</div>", unsafe_allow_html=True)

    st.divider()
    col_t, col_s = st.columns(2)
    with col_t:
        st.markdown(f"**🎯 مضارب (Score: {res['t_score']})**")
        st.write(f"دخول: {res['t_e']:.2f}")
        st.write(f"هدف: {res['t_t']:.2f}")
        st.write(f"وقف: {res['t_s']:.2f}")
    with col_s:
        st.markdown("**🔁 سوينج**")
        st.write(f"دخول: {res['s_e']:.2f}")
        st.write(f"هدف: {res['s_t']:.2f}")
        st.write(f"وقف: {res['s_s']:.2f}")

    # ميزانية الصفقة وحسابات الربح بالجنيه
    st.markdown("---")
    budget = st.number_input("ميزانية السهم (ج):", value=20000, key=f"b_{res['name']}")
    p1, p2, p3 = budget * 0.3, budget * 0.4, budget * 0.3
    
    st.markdown(f"""
    <div class='plan-container'>
        <div class='plan-step up-line'>
            <b>📈 سيناريو الصعود (الربح المتوقع: {( (res['t_t']-res['t_e'])/res['t_e'] * budget ):,.0f} ج):</b><br>
            - ادخل بـ {p1:,.0f} ج عند {res['t_e']:.2f}.<br>
            - زود بـ {p2:,.0f} ج عند اختراق {res['t_t']:.2f}.
        </div>
        <div class='plan-step down-line'>
            <b>📉 سيناريو الهبوط:</b><br>
            - لو نزل لـ {res['s_s']:.2f}، استهلك {p2:,.0f} ج لتعديل المتوسط.
        </div>
    </div>
    """, unsafe_allow_html=True)

# ================== NAVIGATION ==================
if st.session_state.page == 'home':
    st.title("🏹 EGX Sniper Elite v13.0")
    if st.button("📡 تحليل سهم"): go_to('analyze')
    if st.button("🔭 كشاف السوق"): go_to('scanner')
    if st.button("🚀 رادار الاختراقات"): go_to('breakout')
    if st.button("🧮 مساعد المتوسطات"): go_to('average')

elif st.session_state.page == 'analyze':
    if st.button("🏠"): go_to('home')
    sym = st.text_input("ادخل رمز السهم (FERC, ATQA, COMI)").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data: render_stock_ui(analyze_stock(data[0]))
        else: st.error("لم يتم العثور على الرمز، تأكد من كتابته بشكل صحيح.")

elif st.session_state.page == 'average':
    if st.button("🏠"): go_to('home')
    st.subheader("🧮 مساعد متوسط التكلفة")
    c1, c2, c3 = st.columns(3)
    p_old, q_old = c1.number_input("السعر القديم", 0.0), c2.number_input("الكمية القديمة", 0)
    p_now = c3.number_input("السعر الحالي", 0.0)
    if p_old > 0 and q_old > 0 and p_now > 0:
        for label, q in [("نص الكمية (0.5x)", int(q_old*0.5)), ("نفس الكمية (1:1)", q_old), ("ضعف الكمية (2:1)", q_old*2)]:
            avg = ((p_old * q_old) + (p_now * q)) / (q_old + q)
            st.markdown(f"<div class='avg-card'><b>{label}</b>: شراء {q:,} سهم<br>المتوسط الجديد: {avg:.3f} ج</div>", unsafe_allow_html=True)

elif st.session_state.page == 'scanner':
    if st.button("🏠"): go_to('home')
    if st.button("🔍 فحص السوق"):
        for r in fetch_egx_data(scan_all=True):
            if an := analyze_stock(r):
                with st.expander(f"{an['name']} - Score: {an['t_score']}"): render_stock_ui(an)

elif st.session_state.page == 'breakout':
    if st.button("🏠"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r)) and an['is_break']:
            with st.expander(f"🚀 اختراق: {an['name']}"): render_stock_ui(an)
