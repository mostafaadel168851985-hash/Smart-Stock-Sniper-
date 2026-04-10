import streamlit as st
import requests

# ================== CONFIG & STYLE (v12.9 PRO FIXED) ==================
st.set_page_config(page_title="EGX Sniper Elite v12.9 Pro", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-size: 18px !important; font-weight: bold !important; margin-bottom: 10px; }
    .stock-header { font-size: 18px !important; font-weight: bold; color: #58a6ff; }
    .price-callout { font-size: 16px !important; font-weight: bold; color: #3fb950; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 8px; padding: 5px !important; }
    .trend-pill { padding: 4px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; margin: 2px; display: inline-block; }
    .trend-up { background-color: rgba(63, 185, 80, 0.15); color: #3fb950; border: 1px solid #3fb950; }
    .trend-down { background-color: rgba(248, 81, 73, 0.15); color: #f85149; border: 1px solid #f85149; }
    .entry-card-new { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 12px; text-align: center; margin-bottom: 15px; border-top: 4px solid #3fb950; }
    .avg-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-bottom: 12px; border-left: 5px solid #58a6ff; }
    .target-box { background-color: #0d1117; border: 2px solid #58a6ff; border-radius: 12px; padding: 20px; margin-top: 15px; text-align: center; }
    .vol-container { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 8px; text-align: center; }
    .breakout-card { border: 2px solid #00ffcc !important; background-color: #0a1a1a !important; border-radius: 12px; padding: 10px; margin-bottom: 10px; }
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

# ================== 🔥 DATA ENGINE ==================
@st.cache_data(ttl=300)
def fetch_egx_data(symbol=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    cols = ["name","close","RSI","volume","average_volume_10d_calc","high","low","change","description","SMA50","SMA200"]
    if scan_all:
        payload = {
            "filter": [{"left": "volume", "operation": "greater", "right": 10000}, {"left": "close", "operation": "greater", "right": 0.4}],
            "columns": cols, "sort": {"sortBy": "change", "sortOrder": "desc"}, "range": [0, 150]
        }
    else:
        payload = {"symbols": {"tickers": [f"EGX:{symbol.upper()}"]}, "columns": cols}
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except: return []

# ================== 🔥 ANALYSIS ENGINE ==================
def analyze_stock(d_row):
    try:
        name, p, rsi, v, avg_v, h, l, chg, desc, sma50, sma200 = d_row['d']
        if p is None or h is None or l is None: return None
        pp = (p + h + l) / 3
        s1, r1 = (2 * pp) - h, (2 * pp) - l
        s2, r2 = pp - (h - l), pp + (h - l)
        
        trend_med = "صاعد" if sma50 and p > sma50 else "هابط"
        ratio = v / (avg_v or 1)
        rsi_val = rsi if rsi else 0
        
        real_entry = p if p < r1 * 0.98 else r1
        near_support = p <= s1 * 1.02
        is_breakout = (p > r1 and ratio > 1.3 and chg > 1 and trend_med == "صاعد")
        is_gold = (ratio > 1.5 and 45 < rsi_val < 65 and trend_med == "صاعد" and sma50 and p > sma50)
        is_chase = (p > r1 * 1.02)

        smart_score = 0
        if trend_med == "صاعد": smart_score += 30
        if ratio > 1.3: smart_score += 25
        if 40 <= rsi_val <= 60: smart_score += 20
        if near_support: smart_score += 15
        if is_chase: smart_score -= 40
        
        smart_score = max(min(smart_score, 100), 0)
        vol_txt, vol_col = ("🔥 زخم", "#ffd700") if ratio > 1.3 else ("⚪ هادئ", "#8b949e")

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "vol_txt": vol_txt, "vol_col": vol_col, "s1": s1, "s2": s2, "r1": r1, "r2": r2,
            "t_med": trend_med, "real_entry": real_entry, "s_score": smart_score, 
            "is_gold": is_gold, "is_break": is_breakout, "is_chase": is_chase, "near_support": near_support
        }
    except: return None

# ================== UI RENDERER ==================
def render_stock_ui(res, title=""):
    if not res: return
    # تم إصلاح الخطأ في السطر التالي (Syntax Error Fix)
    if title: st.markdown(f"<div class='breakout-card'>{title}</div>", unsafe_allow_html=True)
    
    col_rec = "#ffd700" if res['is_gold'] else "#00ffcc" if res['is_break'] else "#3fb950"
    st.markdown(f"<div class='stock-header'>{res['name']} | {res['desc'][:15]} <span style='color:{col_rec}; float:left;'>Score: {res['s_score']}</span></div>", unsafe_allow_html=True)
    
    tm_cls = "trend-up" if res['t_med'] == "صاعد" else "trend-down"
    st.markdown(f"<span class='trend-pill {tm_cls}'>ترند متوسط: {res['t_med']}</span>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("RSI", f"{res['rsi']:.1f}")
    with c3: st.markdown(f"<div class='vol-container'>الزخم: <b>{res['ratio']:.1f}x</b><br><span style='color:{res['vol_col']}'>{res['vol_txt']}</span></div>", unsafe_allow_html=True)
    
    st.markdown(f"<div class='entry-card-new'>🎯 سعر الدخول الذكي<br><b style='font-size:24px;'>{res['real_entry']:.2f}</b></div>", unsafe_allow_html=True)
    
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("دعم 2", f"{res['s2']:.2f}"); sc2.metric("دعم 1", f"{res['s1']:.2f}"); sc3.metric("مقاومة 1", f"{res['r1']:.2f}"); sc4.metric("مقاومة 2", f"{res['r2']:.2f}")

    # --- خطة السيولة ---
    st.markdown("---")
    st.subheader("🛠️ خطة السيولة الذكية")
    budget = st.number_input("الميزانية المستهدفة لهذا السهم (جنيه):", value=20000, key=f"plan_{res['name']}_{res['p']}")
    p1, p2, p3 = budget * 0.3, budget * 0.4, budget * 0.3
    st.markdown(f"""
        <div class='plan-container'>
            <div class='plan-step up-line'><b>📈 سيناريو الصعود:</b><br>- ادخل بـ <span class='price-callout'>{p1:,.0f} ج</span> عند {res['real_entry']:.2f}.<br>- لو اخترق {res['r1']:.2f} بزخم، زود بـ <span class='price-callout'>{p2:,.0f} ج</span>.</div>
            <div class='plan-step down-line'><b>📉 سيناريو الهبوط:</b><br>- لو نزل لـ <b>{res['s2']:.2f}</b>، عدل المتوسط بـ <span class='price-callout'>{p2:,.0f} ج</span>.</div>
        </div>
    """, unsafe_allow_html=True)

# ================== NAVIGATION & LOGIC ==================
if st.session_state.page == 'home':
    st.title("🏹 EGX Sniper Pro v12.9")
    cols = st.columns(2)
    if cols[0].button("📡 تحليل سهم"): go_to('analyze')
    if cols[1].button("🔭 كشاف السوق"): go_to('scanner')
    if cols[0].button("🚀 الاختراقات"): go_to('breakout')
    if cols[1].button("💎 قنص الذهب"): go_to('gold')
    if st.button("🧮 مساعد المتوسطات"): go_to('average')

elif st.session_state.page == 'analyze':
    if st.button("🏠"): go_to('home')
    sym = st.text_input("ادخل رمز السهم").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if not data:
            for r in fetch_egx_data(scan_all=True):
                if sym == r['d'][0]: data = [r]; break
        if data: render_stock_ui(analyze_stock(data[0]))
        else: st.error("لم يتم العثور على السهم")

elif st.session_state.page == 'scanner':
    if st.button("🏠"): go_to('home')
    if st.button("🔍 فحص الفرص"):
        data = fetch_egx_data(scan_all=True)
        results = [
            an for r in data if (an := analyze_stock(r)) 
            and an['s_score'] >= 50 and an['ratio'] > 0.8
            and not an['is_chase'] and an['t_med'] == "صاعد"
            and 35 < an['rsi'] < 70
            and (an['near_support'] or an['is_break'] or an['s_score'] > 70)
        ]
        results.sort(key=lambda x: (x['s_score'], x['ratio']), reverse=True)
        for an in results:
            with st.expander(f"⭐ {an['s_score']} | {an['name']} | {an['p']}"): render_stock_ui(an)

elif st.session_state.page == 'breakout':
    if st.button("🏠"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        an = analyze_stock(r)
        if an and an['is_break'] and not an['is_chase']:
            render_stock_ui(an, f"🚀 اختراق حقيقي: {an['name']}")

elif st.session_state.page == 'gold':
    if st.button("🏠"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        an = analyze_stock(r)
        if an and an['is_gold'] and not an['is_chase']:
            render_stock_ui(an, "💎 صفقة ذهبية")

elif st.session_state.page == 'average':
    if st.button("🏠"): go_to('home')
    st.subheader("🧮 مساعد متوسط التكلفة الذكي")
    c1, c2, c3 = st.columns(3)
    old_p = c1.number_input("سعر الشراء القديم", 0.0)
    old_q = c2.number_input("كمية الأسهم الحالية", 0)
    new_p = c3.number_input("سعر الشراء الجديد (السعر الحالي)", 0.0)
    
    if old_p > 0 and old_q > 0 and new_p > 0:
        total_old = old_p * old_q
        for label, q in [("تعديل بسيط (0.5x)", int(old_q*0.5)), ("تعديل متوازن (1:1)", old_q), ("تعديل قوي (2:1)", old_q*2)]:
            cost = q * new_p
            avg = (total_old + cost) / (old_q + q)
            st.markdown(f"<div class='avg-card'><b>{label}</b>: شراء {q:,} سهم بتكلفة {cost:,.2f} ج<br>المتوسط الجديد سيكون: <span class='price-callout'>{avg:.3f} ج</span></div>", unsafe_allow_html=True)
        
        st.divider()
        st.subheader("🎯 الوصول لمتوسط مستهدف")
        target = st.number_input("ما هو السعر المتوسط الذي تطمح للوصول إليه؟", value=old_p-0.10)
        
        if new_p < target < old_p:
            needed_q = (old_q * (old_p - target)) / (target - new_p)
            st.markdown(f"""
                <div class='target-box'>
                    <h3>خطة الوصول لهدف {target:.2f}</h3>
                    <p>✅ تحتاج لشراء: <b style='color:#3fb950; font-size:20px;'>{int(needed_q):,} سهم</b></p>
                    <p>✅ التكلفة المطلوبة: <b style='color:#3fb950; font-size:20px;'>{(needed_q*new_p):,.2f} ج</b></p>
                </div>
            """, unsafe_allow_html=True)
        elif target <= new_p:
            st.warning("⚠️ لا يمكن الوصول لمتوسط أقل من سعر السوق الحالي.")
        else:
            st.info("ℹ️ السعر المستهدف أعلى من سعرك القديم بالفعل!")
