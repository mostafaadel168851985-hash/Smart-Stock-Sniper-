import streamlit as st
import requests

# ================== CONFIG & MODERN STYLE ==================
st.set_page_config(page_title="EGX Sniper Elite v12.0", layout="wide")

st.markdown("""
    <style>
    /* تحسين الأزرار والواجهة */
    .stButton>button { 
        width: 100%; border-radius: 12px; height: 3.5em; 
        font-size: 16px !important; font-weight: bold !important;
        background-color: #1f4068; color: white; border: none; transition: 0.3s;
    }
    .stButton>button:hover { background-color: #58a6ff; transform: translateY(-2px); }
    
    /* بطاقات العرض */
    .main-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 15px; padding: 20px; margin-bottom: 15px; }
    .stock-header { font-size: 22px !important; font-weight: bold; color: #58a6ff; }
    
    /* خطة الدخول */
    .plan-box { background-color: #0d1117; border-right: 5px solid #58a6ff; padding: 15px; border-radius: 10px; margin-top: 10px; }
    .price-val { color: #3fb950; font-weight: bold; }
    .stoploss-tag { color: #f85149; font-weight: bold; background: #2e1a1a; padding: 5px 10px; border-radius: 5px; }
    
    /* التنبيهات */
    .warning-box { background-color: #2e2a0b; border: 1px solid #ffd700; color: #ffd700; padding: 12px; border-radius: 10px; margin-top: 10px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'home'
def go_to(page_name):
    st.session_state.page = page_name
    st.rerun()

# ================== DATA ENGINE (نفس معادلاتك) ==================
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

# ================== ANALYSIS LOGIC (نفس منطق v11.8) ==================
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

        is_gold = (ratio > 1.6 and 50 < rsi_val < 65 and chg > 0.5 and trend_ok)
        is_breakout = (p >= h * 0.992 and ratio > 1.2 and rsi_val > 52)

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "t_e": s1, "t_t": r1, "t_s": s1 * 0.98, "t_score": t_score,
            "s_e": p, "s_t": r2, "s_s": s2, "s_score": int(85 if (ratio > 1.1 and 40 < rsi_val < 65) else 50),
            "is_gold": is_gold, "is_break": is_breakout, "s2": s2
        }
    except: return None

# ================== UI RENDERER ==================
def render_stock_ui(res):
    if not res: return
    
    st.markdown(f"<div class='main-card'><span class='stock-header'>{res['name']} | {res['desc'][:20]}</span></div>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("السعر الحالي", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("Score", f"{res['t_score']}")
    c3.metric("الزخم", f"{res['ratio']:.1f}x")
    
    # تحذير المطاردة (نفس منطقك)
    daily_entry_top = res['t_e'] * 1.008
    if res['p'] > daily_entry_top * 1.015:
        st.markdown(f"<div class='warning-box'>⚠️ مطاردة خطر! السعر بعيد عن منطقة الدخول ({daily_entry_top:.2f})</div>", unsafe_allow_html=True)

    st.divider()

    # --- إضافة خطة التداول الذكية ---
    st.markdown("### 🛠️ خطة الدخول المقسمة")
    budget = st.number_input("ميزانية السهم (جنيه):", value=20000, step=1000)
    p1, p2, p3 = budget * 0.3, budget * 0.4, budget * 0.3
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"""
        <div class='plan-box'>
            <b>1️⃣ دفعة جس نبض (30%): <span class='price-val'>{p1:,.0f} ج</span></b><br>
            ادخل عند: <span class='price-val'>{res['t_e']:.2f} - {daily_entry_top:.2f}</span>
        </div>
        <div class='plan-box'>
            <b>2️⃣ دفعة التأكيد (40%): <span class='price-val'>{p2:,.0f} ج</span></b><br>
            عند اختراق: <span class='price-val'>{res['t_t']:.2f}</span> أو ارتداد من <span class='price-val'>{res['s2']:.2f}</span>
        </div>
        """, unsafe_allow_html=True)
    
    with col_b:
        st.markdown(f"""
        <div class='plan-box'>
            <b>3️⃣ دفعة التعزيز (30%): <span class='price-val'>{p3:,.0f} ج</span></b><br>
            عند استهداف السوينج: <span class='price-val'>{res['s_t']:.2f}</span>
        </div>
        <div style='margin-top:15px;'>
            <span class='stoploss-tag'>🛑 وقف خسارة نهائي: {res['t_s']:.2f}</span>
        </div>
        """, unsafe_allow_html=True)

# ================== NAVIGATION ==================
if st.session_state.page == 'home':
    st.markdown("<h1 style='text-align: center; color: #58a6ff;'>🏹 EGX Sniper Elite</h1>", unsafe_allow_html=True)
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📡 تحليل سهم"): go_to('analyze')
        if st.button("🔭 كشاف السوق"): go_to('scanner')
    with c2:
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
    if st.button("بدء الفحص"):
        for r in fetch_egx_data(scan_all=True):
            if (an := analyze_stock(r, True)) and an['t_score'] >= 75:
                with st.expander(f"⭐ {an['t_score']} | {an['name']} ({an['p']:.2f})"):
                    render_stock_ui(an)

elif st.session_state.page == 'average':
    if st.button("🏠"): go_to('home')
    st.subheader("🧮 مساعد المتوسطات")
    # (نفس كود المتوسطات الخاص بك مع تحسين بسيط في العرض)
    c1, c2, c3 = st.columns(3)
    old_p = c1.number_input("السعر القديم", value=0.0)
    old_q = c2.number_input("الكمية القديمة", value=0)
    new_p = c3.number_input("السعر الجديد", value=0.0)
    if old_p > 0 and old_q > 0 and new_p > 0:
        total_old = old_p * old_q
        for label, q in [("بسيط", int(old_q*0.5)), ("متوسط (1:1)", old_q), ("جذري (2:1)", old_q*2)]:
            avg = (total_old + (q * new_p)) / (old_q + q)
            st.markdown(f"<div class='plan-box'><b>{label}:</b> شراء {q:,} سهم. المتوسط الجديد: <span class='price-val'>{avg:.3f}</span></div>", unsafe_allow_html=True)
