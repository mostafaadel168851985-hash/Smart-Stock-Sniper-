import streamlit as st
import requests

# ================== CONFIG & STYLE (V13.1 FIXED) ==================
st.set_page_config(page_title="EGX Sniper Elite v13.1", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; font-size: 18px !important; font-weight: bold !important; margin-bottom: 10px; background-color: #1f4068; color: white; border: none; }
    .stock-header { font-size: 24px !important; font-weight: bold; color: #58a6ff; }
    .price-callout { font-size: 20px !important; font-weight: bold; color: #3fb950; }
    .stoploss-callout { font-size: 18px !important; font-weight: bold; color: #f85149; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 8px; padding: 10px !important; }
    
    .pnl-container { display: flex; gap: 10px; margin-top: 10px; }
    .pnl-box { flex: 1; padding: 10px; border-radius: 10px; text-align: center; font-weight: bold; }
    .pnl-win { background-color: rgba(63, 185, 80, 0.1); color: #3fb950; border: 1px solid #3fb950; }
    .pnl-loss { background-color: rgba(248, 81, 73, 0.1); color: #f85149; border: 1px solid #f85149; }
    
    .plan-container { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-top: 15px; }
    .plan-step { margin-bottom: 10px; padding-right: 12px; border-right: 4px solid #58a6ff; }
    .avg-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-bottom: 12px; border-left: 5px solid #58a6ff; }
    .target-box { background-color: #0d1117; border: 2px solid #58a6ff; border-radius: 12px; padding: 20px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'home'
def go_to(page_name):
    st.session_state.page = page_name
    st.rerun()

# ================== DATA ENGINE (FIXED SEARCH) ==================
@st.cache_data(ttl=60)
def fetch_egx_data(symbol=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    if scan_all:
        payload = {
            "filter": [{"left": "volume", "operation": "greater", "right": 10000}, {"left": "close", "operation": "greater", "right": 0.1}],
            "columns": ["name", "close", "RSI", "volume", "average_volume_10d_calc", "high", "low", "change", "description"],
            "sort": {"sortBy": "change", "sortOrder": "desc"}, "range": [0, 150]
        }
    else:
        # البحث بالاسم لضمان جلب FERC وغيرها
        payload = {
            "filter": [{"left": "name", "operation": "match", "right": symbol.upper()}],
            "columns": ["name", "close", "high", "low", "volume", "RSI", "average_volume_10d_calc", "change", "description"]
        }
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except: return []

# ================== ANALYSIS ENGINE ==================
def analyze_stock(d_row):
    try:
        d = d_row['d']
        name, p, h, l, v, rsi, avg_v, chg, desc = d
        if p is None: return None
        
        pp = (p + h + l) / 3
        s1, r1 = (2 * pp) - h, (2 * pp) - l
        s2, r2 = pp - (h - l), pp + (h - l)
        
        ratio = v / (avg_v or 1)
        rsi_val = rsi or 0
        
        # تصحيح الحسابات لنسب الربح والخسارة
        def calc_pnl(entry, target): return ((target - entry) / entry) * 100 if entry != 0 else 0

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "t_e": s1, "t_t": r1, "t_s": s1 * 0.98,
            "s_e": p, "s_t": r2, "s_s": s2,
            "is_gold": (ratio > 1.5 and 45 < rsi_val < 65),
            "is_break": (p >= h * 0.99 and ratio > 1.1)
        }
    except: return None

# ================== UI RENDERER ==================
def render_stock_ui(res):
    if not res: return
    st.markdown(f"<div class='stock-header'>{res['name']} - {res['desc'][:25]}</div>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("RSI", f"{res['rsi']:.1f}")
    c3.metric("الزخم", f"{res['ratio']:.1f}x")
    
    budget = st.number_input("الميزانية (ج):", value=20000, key=f"b_{res['name']}")
    
    col_t, col_s = st.columns(2)
    with col_t:
        st.markdown("**🎯 مضارب**")
        st.markdown(f"دخول: <span class='price-callout'>{res['t_e']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"هدف: <span class='price-callout'>{res['t_t']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"وقف: <span class='stoploss-callout'>{res['t_s']:.2f}</span>", unsafe_allow_html=True)
        
        p_pct = ((res['t_t'] - res['t_e']) / res['t_e']) * 100
        l_pct = ((res['t_s'] - res['t_e']) / res['t_e']) * 100
        st.markdown(f"""<div class='pnl-container'>
            <div class='pnl-box pnl-win'>ربح: {p_pct:+.1f}%<br>({(budget*p_pct/100):,.0f} ج)</div>
            <div class='pnl-box pnl-loss'>خسارة: {l_pct:.1f}%<br>({(budget*l_pct/100):,.0f} ج)</div>
        </div>""", unsafe_allow_html=True)

    with col_s:
        st.markdown("**🔁 سوينج**")
        st.markdown(f"دخول: <span class='price-callout'>{res['s_e']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"هدف: <span class='price-callout'>{res['s_t']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"وقف: <span class='stoploss-callout'>{res['s_s']:.2f}</span>", unsafe_allow_html=True)
        
        p_pct = ((res['s_t'] - res['s_e']) / res['s_e']) * 100
        l_pct = ((res['s_s'] - res['s_e']) / res['s_e']) * 100
        st.markdown(f"""<div class='pnl-container'>
            <div class='pnl-box pnl-win'>ربح: {p_pct:+.1f}%<br>({(budget*p_pct/100):,.0f} ج)</div>
            <div class='pnl-box pnl-loss'>خسارة: {l_pct:.1f}%<br>({(budget*l_pct/100):,.0f} ج)</div>
        </div>""", unsafe_allow_html=True)

    # --- خطة الدخول ---
    st.markdown("---")
    st.subheader("🛠️ خطة السيولة والتمركز")
    p1, p2, p3 = budget * 0.3, budget * 0.4, budget * 0.3
    st.markdown(f"""
    <div class='plan-container'>
        <div class='plan-step' style='border-right-color:#3fb950'>
            <b>📈 في حالة الصعود:</b><br>
            • اشتري بـ <span style='color:#3fb950'>{p1:,.0f} ج</span> الآن عند {res['t_e']:.2f}.<br>
            • زود بـ <span style='color:#3fb950'>{p2:,.0f} ج</span> لو السهم اخترق {res['t_t']:.2f}.<br>
            • <b>التعزيز:</b> ضخ الـ {p3:,.0f} ج الباقية عند تجاوز {res['s_t']:.2f}.
        </div>
        <div class='plan-step' style='border-right-color:#f85149'>
            <b>📉 في حالة الهبوط (تعديل):</b><br>
            • لو نزل السهم لـ {res['s_s']:.2f}، زود بـ <span style='color:#3fb950'>{p2:,.0f} ج</span> لتحسين المتوسط.<br>
            • تنبيه: لو كسر السعر {res['s_s'] * 0.98:.2f} اخرج فوراً.
        </div>
    </div>
    """, unsafe_allow_html=True)

# ================== PAGES ==================
if st.session_state.page == 'home':
    st.title("🏹 EGX Sniper Elite v13.1")
    if st.button("📡 تحليل سهم"): go_to('analyze')
    if st.button("🔭 كشاف السوق"): go_to('scanner')
    if st.button("🚀 رادار الاختراقات"): go_to('breakout')
    if st.button("🧮 مساعد المتوسطات"): go_to('average')

elif st.session_state.page == 'analyze':
    if st.button("🏠"): go_to('home')
    sym = st.text_input("ادخل الرمز (مثلاً: ATQA أو FERC)").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data: render_stock_ui(analyze_stock(data[0]))
        else: st.error("لم يتم العثور على الرمز، جرب كتابة الاسم.")

elif st.session_state.page == 'scanner':
    if st.button("🏠"): go_to('home')
    if st.button("🔍 فحص السوق"):
        for r in fetch_egx_data(scan_all=True):
            if an := analyze_stock(r):
                with st.expander(f"📊 {an['name']}"): render_stock_ui(an)

elif st.session_state.page == 'average':
    if st.button("🏠"): go_to('home')
    st.subheader("🧮 مساعد متوسط التكلفة")
    c1, c2, c3 = st.columns(3)
    old_p, old_q = c1.number_input("السعر القديم", 0.0), c2.number_input("الكمية القديمة", 0)
    new_p = c3.number_input("السعر الحالي", 0.0)
    if old_p > 0 and old_q > 0 and new_p > 0:
        t_old = old_p * old_q
        # الجزء المفقود: خيارات الكميات
        for label, q in [("نص الكمية (0.5x)", int(old_q*0.5)), ("نفس الكمية (1:1)", old_q), ("ضعف الكمية (2:1)", old_q*2)]:
            cost = q * new_p
            avg = (t_old + cost) / (old_q + q)
            st.markdown(f"<div class='avg-card'><b>{label}</b>: شراء {q:,} سهم<br>المتوسط الجديد: <span class='price-callout'>{avg:.3f} ج</span></div>", unsafe_allow_html=True)
        
        st.divider()
        target = st.number_input("المتوسط المستهدف؟", value=old_p*0.95)
        if new_p < target < old_p:
            needed = (old_q * (old_p - target)) / (target - new_p)
            st.markdown(f"<div class='target-box'><h3>خطة هدف {target:.2f}</h3><p>✅ شراء: <b>{int(needed):,} سهم</b></p><p>✅ سيولة: <b>{(needed*new_p):,.2f} ج</b></p></div>", unsafe_allow_html=True)

elif st.session_state.page == 'breakout':
    if st.button("🏠"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r)) and an['is_break']:
            with st.expander(f"🚀 اختراق: {an['name']}"): render_stock_ui(an)
