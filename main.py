import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="EGX Sniper Pro v14.5", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-size: 18px !important; font-weight: bold !important; margin-bottom: 10px; }
    .stock-header { font-size: 22px !important; font-weight: bold; color: #58a6ff; border-bottom: 2px solid #30363d; padding-bottom: 5px; }
    .score-tag { float: left; background: #238636; color: white; padding: 2px 12px; border-radius: 10px; font-size: 16px; margin-top: 5px; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 8px; padding: 5px !important; }
    .trend-pill { padding: 4px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; margin: 2px; display: inline-block; }
    .trend-up { background-color: rgba(63, 185, 80, 0.15); color: #3fb950; border: 1px solid #3fb950; }
    .trend-down { background-color: rgba(248, 81, 73, 0.15); color: #f85149; border: 1px solid #f85149; }
    .signal-pill { padding: 5px 15px; border-radius: 20px; font-weight: bold; display: inline-block; margin: 10px 0; }
    .buy-strong { background: #238636; color: white; border: 1px solid #3fb950; }
    .buy-caution { background: rgba(240, 139, 55, 0.2); color: #f08b37; border: 1px solid #f08b37; }
    .wait { background: #161b22; color: #8b949e; border: 1px solid #30363d; }
    .entry-card-new { background-color: #0d1117; border: 1px solid #3fb950; border-radius: 12px; padding: 15px; text-align: center; margin-bottom: 15px; border-top: 4px solid #3fb950; }
    .target-box { border: 2px solid #58a6ff; border-radius: 12px; padding: 15px; text-align: center; background: #0d1117; margin-top: 10px; }
    .plan-container { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-top: 15px; }
    .rr-tag { font-size: 18px; font-weight: bold; color: #58a6ff; background: rgba(88, 166, 255, 0.1); padding: 5px 15px; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'home'
def go_to(page_name):
    st.session_state.page = page_name
    st.rerun()

# ================== 🔥 DATA ENGINE ==================
@st.cache_data(ttl=300)
def fetch_egx_data(symbol=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    cols = ["name","close","RSI","volume","average_volume_10d_calc","high","low","change","description","SMA20","SMA50","SMA200"]
    if scan_all:
        payload = {"filter": [{"left": "volume", "operation": "greater", "right": 5000}], "columns": cols, "sort": {"sortBy": "change", "sortOrder": "desc"}, "range": [0, 150]}
    else:
        payload = {"filter": [{"left": "name", "operation": "match", "right": symbol.upper()}], "columns": cols, "range": [0, 1]}
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except: return []

# ================== 🔥 ANALYSIS ENGINE ==================
def analyze_stock(d_row):
    try:
        d = d_row.get('d', [])
        if len(d) < 12: return None
        name, p, rsi, v, avg_v, h, l, chg, desc, sma20, sma50, sma200 = d
        if p is None: return None
        
        # 1. فلترة الأسهم التعبانة (قليلة السيولة)
        ratio = v / (avg_v or 1)
        if ratio < 0.7: return None # تجاهل الأسهم اللي مفيش عليها فوليوم

        # 2. الاتجاهات
        t_short = "صاعد" if (sma20 and p > sma20) else "هابط"
        t_med = "صاعد" if (sma50 and p > sma50) else "هابط"
        t_long = "صاعد" if (sma200 and p > sma200) else "هابط"
        
        # 3. Signal Logic (تعديل 3)
        if t_short == "صاعد" and t_med == "صاعد":
            signal, sig_cls = "شراء قوي 🔥", "buy-strong"
        elif t_short == "صاعد":
            signal, sig_cls = "شراء حذر ⚠️", "buy-caution"
        else:
            signal, sig_cls = "انتظار ⏳", "wait"

        # 4. مستويات الدعم والمقاومة
        pp = (p + (h or p) + (l or p)) / 3
        s1, r1 = (2 * pp) - (h or p), (2 * pp) - (l or p)
        s2 = pp - ((h or p) - (l or p))
        
        # 5. Entry Logic (تعديل 1)
        if p < r1:
            entry_min, entry_max = s1 * 0.995, s1 * 1.01
        elif p <= r1 * 1.02:
            entry_min, entry_max = r1, r1 * 1.01
        else:
            entry_min, entry_max = p * 0.99, p
        
        entry_price = (entry_min + entry_max) / 2
        stop_loss = s2
        target = r1 if p < r1 else r1 * 1.1 # هدف تقديري لو مخترق

        # 6. Risk/Reward (تعديل 2 و 5)
        profit_per_share = target - entry_price
        loss_per_share = entry_price - stop_loss
        rr = round(profit_per_share / (loss_per_share if loss_per_share > 0 else 0.01), 2)

        # 7. السكور
        score = 0
        if t_med == "صاعد": score += 30
        if ratio > 1.2: score += 30
        if 40 < (rsi or 0) < 65: score += 20
        if rr > 2: score += 20

        is_gold = (ratio > 1.5 and 45 < (rsi or 0) < 65 and t_med == "صاعد")
        early_break = (p >= r1 * 0.97 and ratio > 1.1)
        strong_break = (p > r1 and ratio > 1.3)

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi or 0, "chg": chg, "ratio": ratio,
            "score": score, "signal": signal, "sig_cls": sig_cls,
            "t_short": t_short, "t_med": t_med, "t_long": t_long,
            "is_gold": is_gold, "early_break": early_break, "strong_break": strong_break,
            "entry_range": f"{entry_min:.2f} - {entry_max:.2f}",
            "entry_price": entry_price, "stop_loss": stop_loss, "target": target,
            "rr": rr, "vol_icon": "🔥 انفجاري" if ratio > 1.5 else "⚪ هادئ"
        }
    except: return None

# ================== UI RENDERER ==================
def render_stock_ui(res):
    st.markdown(f"<div class='stock-header'>{res['name']} <span class='score-tag'>Score: {res['score']}</span></div>", unsafe_allow_html=True)
    st.markdown(f"<span class='signal-pill {res['sig_cls']}'>{res['signal']}</span> <span class='rr-tag'>RR: {res['rr']}</span>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("السعر الآن", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("الزخم (Volume)", res['vol_icon'], f"{res['ratio']:.1f}x")
    c3.metric("قوة RSI", f"{res['rsi']:.1f}")

    st.markdown(f"""
    <div class='entry-card-new'>🎯 <b>نطاق الدخول المقترح:</b> {res['entry_range']}<br>🛑 <b>وقف خسارة (بناءً على الدخول):</b> {res['stop_loss']:.2f}</div>
    <div class='target-box'>🏁 <b>الهدف الأول:</b> {res['target']:.2f}</div>
    """, unsafe_allow_html=True)

    st.subheader("💰 إدارة الصفقة")
    budget = st.number_input(f"ميزانية {res['name']}:", value=10000, key=f"b_{res['name']}")
    
    num_shares = budget / res['entry_price']
    p_val = (res['target'] - res['entry_price']) * num_shares
    l_val = (res['entry_price'] - res['stop_loss']) * num_shares

    st.markdown(f"""
        <div class='plan-container'>
            💎 <b>عدد الأسهم:</b> {int(num_shares):,}<br>
            <span style='color:#3fb950'>🟢 ربح محتمل: {p_val:,.2f} ج</span><br>
            <span style='color:#f85149'>🔴 خسارة محتملة: {l_val:,.2f} ج</span><br>
            ⚠️ <i>الحسابات مبنية على متوسط سعر الدخول وليس السعر الحالي.</i>
        </div>
    """, unsafe_allow_html=True)

# ================== NAVIGATION ==================
if st.session_state.page == 'home':
    st.title("🏹 Sniper Elite v14.5 Pro")
    c1, c2 = st.columns(2)
    if c1.button("📡 تحليل سهم"): go_to('analyze')
    if c2.button("🔭 كشاف السوق"): go_to('scanner')
    if c1.button("🚀 الاختراقات"): go_to('breakout')
    if c2.button("💎 قنص الذهب"): go_to('gold')
    st.button("🧮 حاسبة المتوسطات", on_click=lambda: go_to('average'))

elif st.session_state.page == 'analyze':
    st.button("🏠", on_click=lambda: go_to('home'))
    sym = st.text_input("رمز السهم").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data: 
            res = analyze_stock(data[0])
            if res: render_stock_ui(res)
            else: st.warning("السهم سيولته ضعيفة جداً للتحليل الآمن")
        else: st.error("رمز غير صحيح")

elif st.session_state.page == 'scanner':
    st.button("🏠", on_click=lambda: go_to('home'))
    data = fetch_egx_data(scan_all=True)
    for r in data:
        an = analyze_stock(r)
        if an and an['score'] >= 60:
            with st.expander(f"⭐ {an['score']} | {an['name']} | RR: {an['rr']}"): render_stock_ui(an)

elif st.session_state.page == 'gold':
    st.button("🏠", on_click=lambda: go_to('home'))
    data = fetch_egx_data(scan_all=True)
    for r in data:
        an = analyze_stock(r)
        if an and an['is_gold']:
            with st.expander(f"✨ ذهبي: {an['name']} | RR: {an['rr']}"): render_stock_ui(an)

elif st.session_state.page == 'breakout':
    st.button("🏠", on_click=lambda: go_to('home'))
    data = fetch_egx_data(scan_all=True)
    for r in data:
        an = analyze_stock(r)
        if an and (an['strong_break'] or an['early_break']):
            tag = "🔥" if an['strong_break'] else "🟡"
            with st.expander(f"{tag} اختراق: {an['name']} | RR: {an['rr']}"): render_stock_ui(an)

elif st.session_state.page == 'average':
    st.button("🏠", on_click=lambda: go_to('home'))
    # (نفس كود حاسبة المتوسطات السابق)
    st.header("🧮 حاسبة المتوسطات")
    curr_p = st.number_input("السعر القديم", 0.0)
    curr_q = st.number_input("الكمية", 0)
    market_p = st.number_input("سعر السوق", 0.0)
    target_avg = st.number_input("المتوسط المستهدف", 0.0)
    if curr_p > 0 and market_p < target_avg < curr_p:
        req_q = (curr_q * (curr_p - target_avg)) / (target_avg - market_p)
        st.success(f"اشتر {int(req_q):,} سهم")
