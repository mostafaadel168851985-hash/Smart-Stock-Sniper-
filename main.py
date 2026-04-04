import streamlit as st
import requests

# ================== CONFIG & STYLE (V12.7 EXACT) ==================
st.set_page_config(page_title="EGX Sniper Elite v12.7", layout="wide")

st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-size: 18px !important; font-weight: bold !important; margin-bottom: 10px; }
    .stock-header { font-size: 18px !important; font-weight: bold; color: #58a6ff; }
    .price-callout { font-size: 16px !important; font-weight: bold; color: #3fb950; }
    .stoploss-callout { font-size: 14px !important; font-weight: bold; color: #f85149; }
    .avg-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-bottom: 12px; border-left: 5px solid #58a6ff; }
    .target-box { background-color: #0d1117; border: 2px solid #58a6ff; border-radius: 12px; padding: 20px; margin-top: 15px; text-align: center; }
    .warning-box { background-color: #2e2a0b; border: 1px solid #ffd700; color: #ffd700; padding: 12px; border-radius: 10px; margin-top: 10px; font-weight: bold; border-left: 6px solid #ffd700; }
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
            "filter": [{"left": "volume", "operation": "greater", "right": 50000}],
            "columns": ["name", "close", "RSI", "volume", "average_volume_10d_calc", "high", "low", "change", "description"],
            "sort": {"sortBy": "change", "sortOrder": "desc"}, "range": [0, 100]
        }
    else:
        # تعديل البحث ليكون أشمل (إصلاح مشكلة الرموز مثل FERC)
        payload = {
            "filter": [{"left": "name", "operation": "match", "right": symbol.upper() if symbol else ""}],
            "columns": ["name", "close", "RSI", "volume", "average_volume_10d_calc", "high", "low", "change", "description"]
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
        is_gold = (ratio > 1.6 and 50 < rsi_val < 65 and chg > 0.5)
        is_break = (p >= h * 0.992 and ratio > 1.2 and rsi_val > 52)

        rec, col = ("🛑 تشبع", "#ff4b4b") if rsi_val > 72 else ("💎 ذهب", "#ffd700") if is_gold else ("🚀 شراء", "#00ff00") if t_score >= 75 else ("⚖️ انتظار", "#58a6ff")

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "t_e": s1, "t_t": r1, "t_s": s1 * 0.98, "t_score": t_score,
            "s_e": p, "s_t": r2, "s_s": s2, "rec": rec, "col": col, "is_gold": is_gold, "is_break": is_break
        }
    except: return None

# ================== UI RENDERER ==================
def render_stock_ui(res):
    if not res: return
    st.markdown(f"<div class='stock-header'>{res['name']} - {res['desc'][:20]} <span style='color:{res['col']}; float:left;'>{res['rec']}</span></div>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("RSI", f"{res['rsi']:.1f}")
    c3.metric("الزخم", f"{res['ratio']:.1f}x")

    # إرجاع إشعار المطاردة
    daily_entry_top = res['t_e'] * 1.008
    if res['p'] > daily_entry_top * 1.015:
        st.markdown(f"<div class='warning-box'>⚠️ مطاردة خطر! السعر بعيد عن منطقة الدخول ({daily_entry_top:.2f})</div>", unsafe_allow_html=True)

    st.divider()
    col_t, col_s = st.columns(2)
    with col_t:
        st.markdown(f"**🎯 مضارب (Score: {res['t_score']})**")
        st.write(f"دخول: {res['t_e']:.2f} | هدف: {res['t_t']:.2f} | وقف: {res['t_s']:.2f}")
    with col_s:
        st.markdown("**🔁 سوينج**")
        st.write(f"دخول: {res['s_e']:.2f} | هدف: {res['s_t']:.2f} | وقف: {res['s_s']:.2f}")

    # ميزانية الصفقة والربح بالجنيه
    st.markdown("---")
    budget = st.number_input("ميزانية السهم (ج):", value=20000, key=f"b_{res['name']}")
    profit_amt = ((res['t_t'] - res['t_e']) / res['t_e']) * budget
    st.success(f"💰 الربح المتوقع في هدف المضارب: {profit_amt:,.0f} جنيه")

# ================== NAVIGATION ==================
if st.session_state.page == 'home':
    st.title("🏹 EGX Sniper Elite v12.7")
    if st.button("📡 تحليل سهم"): go_to('analyze')
    if st.button("🔭 كشاف السوق"): go_to('scanner')
    if st.button("🚀 رادار الاختراقات"): go_to('breakout')
    if st.button("💎 قنص الذهب"): go_to('gold')
    if st.button("🧮 مساعد المتوسطات"): go_to('average')

elif st.session_state.page == 'average':
    if st.button("🏠"): go_to('home')
    st.subheader("🧮 مساعد متوسط التكلفة (شامل المستهدف)")
    c1, c2, c3 = st.columns(3)
    old_p, old_q = c1.number_input("السعر القديم", 0.0), c2.number_input("الكمية القديمة", 0)
    new_p = c3.number_input("السعر الجديد", 0.0)
    
    if old_p > 0 and old_q > 0 and new_p > 0:
        # 1. المتوسطات التلقائية
        for label, q in [("نص الكمية (0.5x)", int(old_q*0.5)), ("نفس الكمية (1:1)", old_q), ("ضعف الكمية (2:1)", old_q*2)]:
            avg = ((old_p * old_q) + (new_p * q)) / (old_q + q)
            st.markdown(f"<div class='avg-card'><b>{label}</b>: شراء {q:,} سهم<br>المتوسط الجديد: <span class='price-callout'>{avg:.3f} ج</span></div>", unsafe_allow_html=True)
        
        # 2. المتوسط المستهدف (اللي كان ممسوح)
        st.divider()
        target = st.number_input("المتوسط المستهدف الذي تريد الوصول إليه؟", value=old_p-0.01)
        if new_p < target < old_p:
            needed_q = (old_q * (old_p - target)) / (target - new_p)
            st.markdown(f"<div class='target-box'><h3>خطة الوصول لهدف {target:.2f}</h3><p>✅ شراء: <b style='color:#3fb950;'>{int(needed_q):,} سهم</b></p><p>✅ مبلغ: <b style='color:#3fb950;'>{(needed_q*new_p):,.2f} ج</b></p></div>", unsafe_allow_html=True)

elif st.session_state.page == 'gold':
    if st.button("🏠"): go_to('home')
    st.subheader("💎 الفرص الذهبية المكتشفة")
    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r)) and an['is_gold']:
            render_stock_ui(an)

elif st.session_state.page == 'analyze':
    if st.button("🏠"): go_to('home')
    sym = st.text_input("ادخل الرمز (مثلاً: FERC)").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data: render_stock_ui(analyze_stock(data[0]))

elif st.session_state.page == 'scanner':
    if st.button("🏠"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r)) and an['t_score'] >= 70:
            with st.expander(f"⭐ {an['t_score']} | {an['name']}"): render_stock_ui(an)

elif st.session_state.page == 'breakout':
    if st.button("🏠"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r)) and an['is_break']:
            render_stock_ui(an)
