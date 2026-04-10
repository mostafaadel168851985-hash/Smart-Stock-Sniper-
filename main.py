import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="EGX Sniper Pro v15.0", layout="wide")

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
    .rr-tag { font-size: 16px; font-weight: bold; color: #58a6ff; background: rgba(88, 166, 255, 0.1); padding: 5px 12px; border-radius: 8px; border: 1px solid rgba(88, 166, 255, 0.3); }
    .rr-label { font-size: 14px; font-weight: bold; margin-right: 5px; padding: 2px 8px; border-radius: 5px; }
    .rr-excellent { background: #238636; color: white; }
    .rr-good { background: #2ea043; color: white; }
    .rr-fair { background: #d29922; color: white; }
    .rr-bad { background: #f85149; color: white; }
    .avg-section { background: rgba(88, 166, 255, 0.05); border-left: 4px solid #58a6ff; padding: 15px; border-radius: 8px; margin: 10px 0; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'home'

# ================== 🔥 HELPER FUNCTIONS ==================
def get_rr_status(rr):
    if rr >= 3: return "فرصة ذهبية 🏆", "rr-excellent"
    elif rr >= 2: return "صفقة ممتازة ✅", "rr-good"
    elif rr >= 1.8: return "مقبول 👍", "rr-fair"
    else: return "خطر / عائد ضعيف ⚠️", "rr-bad"

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
def analyze_stock(d_row, is_scanner=False):
    try:
        d = d_row.get('d', [])
        if not d or len(d) < 12: return None
        name, p, rsi, v, avg_v, h, l, chg, desc, sma20, sma50, sma200 = d
        if p is None: return None
        
        ratio = v / (avg_v or 1)
        
        # الاتجاهات
        t_short = "صاعد" if (sma20 and p > sma20) else "هابط"
        t_med = "صاعد" if (sma50 and p > sma50) else "هابط"
        t_long = "صاعد" if (sma200 and p > sma200) else "هابط"

        # 1. فلاتر PRO للسكانر فقط
        if is_scanner:
            if ratio < 0.8: return None 
            if chg < -2: return None 
            if t_med != "صاعد": return None # ❗ تعديل: الالتزام بالاتجاه الصاعد فقط

        # إشارات الدخول
        if t_short == "صاعد" and t_med == "صاعد": signal, sig_cls = "شراء قوي 🔥", "buy-strong"
        elif t_short == "صاعد": signal, sig_cls = "شراء حذر ⚠️", "buy-caution"
        else: signal, sig_cls = "انتظار ⏳", "wait"

        # حساب Pivot Points
        pp = (p + (h or p) + (l or p)) / 3
        s1, r1 = (2 * pp) - (h or p), (2 * pp) - (l or p)
        s2 = pp - ((h or p) - (l or p))
        
        # 2. تعديل نطاق الدخول (Conservative Entry)
        if p < r1: entry_min, entry_max = s1, s1 * 1.01
        elif p <= r1 * 1.02: entry_min, entry_max = r1, r1 * 1.01
        else: entry_min, entry_max = p * 0.99, p
        
        entry_price = (entry_min + entry_max) / 2
        
        # حماية وقف الخسارة
        stop_loss = min(s2, entry_price * 0.97)
        
        # 3. الهدف الواقعي المعدل (Realistic Egyptian Target)
        range_size = r1 - s1
        if p < r1: target = r1
        else: target = r1 + (range_size * 0.7) 

        # حساب RR
        profit_per_share = target - entry_price
        loss_per_share = entry_price - stop_loss
        
        if loss_per_share <= 0: return None
        rr = round(profit_per_share / loss_per_share, 2)
        
        # 4. فلتر جودة RR للسكانر
        if is_scanner and rr < 1.8: return None # ❗ تعديل الحد الأدنى لـ 1.8

        rr_label, rr_class = get_rr_status(rr)

        # نظام الـ Scoring
        score = 0
        if t_med == "صاعد": score += 25 
        if t_long == "صاعد": score += 15 
        if ratio > 1.2: score += 20
        if ratio > 2: score += 15 
        if 40 < (rsi or 0) < 65: score += 15
        if rr > 1.8: score += 10

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi or 0, "chg": chg, "ratio": ratio,
            "score": score, "signal": signal, "sig_cls": sig_cls,
            "t_short": t_short, "t_med": t_med, "t_long": t_long,
            "is_gold": (ratio > 1.5 and 45 < (rsi or 0) < 65 and t_med == "صاعد" and rr >= 1.8),
            "entry_range": f"{entry_min:.2f} - {entry_max:.2f}",
            "entry_price": entry_price, "stop_loss": stop_loss, "target": target,
            "rr": rr, "rr_label": rr_label, "rr_class": rr_class,
            "vol_icon": "🔥 انفجاري" if ratio > 2 else ("⚡ نشط" if ratio > 1.2 else "⚪ هادئ")
        }
    except: return None

# ================== UI RENDERER ==================
def render_stock_ui(res):
    st.markdown(f"<div class='stock-header'>{res['name']} | {res['desc'][:20]} <span class='score-tag'>Score: {res['score']}</span></div>", unsafe_allow_html=True)
    
    st.markdown(f"""
        <span class='signal-pill {res['sig_cls']}'>{res['signal']}</span> 
        <span class='rr-tag'>RR: {res['rr']}</span> 
        <span class='rr-label {res['rr_class']}'>{res['rr_label']}</span>
    """, unsafe_allow_html=True)
    
    ts_c = "trend-up" if res['t_short'] == "صاعد" else "trend-down"
    tm_c = "trend-up" if res['t_med'] == "صاعد" else "trend-down"
    tl_c = "trend-up" if res['t_long'] == "صاعد" else "trend-down"
    st.markdown(f"<div><span class='trend-pill {ts_c}'>قصير: {res['t_short']}</span><span class='trend-pill {tm_c}'>متوسط: {res['t_med']}</span><span class='trend-pill {tl_c}'>طويل: {res['t_long']}</span></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("السعر الآن", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("السيولة", res['vol_icon'], f"{res['ratio']:.1f}x")
    c3.metric("قوة RSI", f"{res['rsi']:.1f}")

    st.markdown(f"""
    <div class='entry-card-new'>🎯 <b>نطاق الدخول:</b> {res['entry_range']}<br>🛑 <b>وقف الخسارة:</b> {res['stop_loss']:.2f}</div>
    <div class='target-box'>🏁 <b>الهدف المتوقع:</b> {res['target']:.2f}</div>
    """, unsafe_allow_html=True)

    # --- ✳️ تحسين إدارة المتوسط داخل السهم ---
    st.markdown("<div class='avg-section'>", unsafe_allow_html=True)
    st.subheader("📉 تعديل المتوسط على السهم")
    col_a, col_b = st.columns(2)
    old_p = col_a.number_input("متوسطك الحالي", value=0.0, key=f"ap_{res['name']}")
    old_q = col_b.number_input("عدد الأسهم الحالية", value=0, key=f"aq_{res['name']}")

    if old_p > 0 and old_q > 0:
        entry_p = res['entry_price']
        st.markdown("<b>سيناريوهات التعديل المقترحة:</b>", unsafe_allow_html=True)
        
        for label, mult in [("تعديل خفيف (0.5x)", 0.5), ("تعديل متوازن (1x)", 1.0), ("تعديل قوي (2x)", 2.0)]:
            new_q = int(old_q * mult)
            new_avg = ((old_p * old_q) + (entry_p * new_q)) / (old_q + new_q)
            st.write(f"🔹 {label}: اشترِ **{new_q:,}** سهم @ {entry_p:.2f} ➔ المتوسط الجديد: **{new_avg:.2f}**")
    st.markdown("</div>", unsafe_allow_html=True)

    budget = st.number_input(f"الميزانية لـ {res['name']}:", value=10000, key=f"v_{res['name']}")
    num_shares = int(budget / res['entry_price'])
    st.markdown(f"""
        <div class='plan-container'>
            💎 <b>الكمية المتاحة بالميزانية:</b> {num_shares:,} سهم<br>
            <span style='color:#3fb950'>🟢 ربح محتمل: {(res['target'] - res['entry_price']) * num_shares:,.2f} ج</span><br>
            <span style='color:#f85149'>🔴 خسارة محتملة: {(res['entry_price'] - res['stop_loss']) * num_shares:,.2f} ج</span>
        </div>
    """, unsafe_allow_html=True)

# ================== NAVIGATION ==================
if st.session_state.page == 'home':
    st.title("🏹 Sniper Elite v15.0 Pro")
    if st.button("📡 تحليل سهم"): st.session_state.page = 'analyze'; st.rerun()
    if st.button("🔭 كشاف السوق"): st.session_state.page = 'scanner'; st.rerun()
    if st.button("🚀 الاختراقات"): st.session_state.page = 'breakout'; st.rerun()
    if st.button("💎 قنص الذهب"): st.session_state.page = 'gold'; st.rerun()
    if st.button("🧮 الوصول لمتوسط مستهدف"): st.session_state.page = 'target_avg'; st.rerun()

elif st.session_state.page == 'target_avg':
    if st.button("🏠"): st.session_state.page = 'home'; st.rerun()
    st.header("🧮 حاسبة المتوسط المستهدف")
    st.info("أنا عايز أوصل لمتوسط كام؟ قولّي أشتري كام سهم")
    
    col1, col2 = st.columns(2)
    cur_p = col1.number_input("سعر الشراء الحالي", 0.0)
    cur_q = col1.number_input("الكمية الحالية", 0)
    mkt_p = col2.number_input("سعر السوق الحالي (التعديل)", 0.0)
    tar_a = col2.number_input("المتوسط المطلوب الوصول له", 0.0)

    if cur_p > 0 and cur_q > 0 and mkt_p > 0 and tar_a > 0:
        if mkt_p >= tar_a:
            st.warning("⚠️ لا يمكن الوصول لمتوسط أقل إذا كان سعر التعديل أعلى من أو يساوي المتوسط المطلوب")
        elif tar_a >= cur_p:
            st.warning("⚠️ المتوسط المطلوب أعلى من سعرك الحالي بالفعل!")
        else:
            req_q = (cur_q * (cur_p - tar_a)) / (tar_a - mkt_p)
            cost = req_q * mkt_p
            st.success(f"""
            ✅ القرار: اشترِ **{int(req_q):,}** سهم إضافي  
            💰 التكلفة الإجمالية للتعديل: **{cost:,.0f}** جنيه  
            🎯 النتيجة: سيصبح متوسطك **{tar_a:.2f}** بدلاً من {cur_p:.2f}
            """)

elif st.session_state.page == 'analyze':
    if st.button("🏠"): st.session_state.page = 'home'; st.rerun()
    sym = st.text_input("رمز السهم").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data:
            res = analyze_stock(data[0], is_scanner=False)
            if res: render_stock_ui(res)
            else: st.warning("السهم لا تتوفر له بيانات كافية للتحليل")
        else: st.error("سهم غير موجود")

elif st.session_state.page == 'scanner':
    if st.button("🏠"): st.session_state.page = 'home'; st.rerun()
    raw_data = fetch_egx_data(scan_all=True)
    results = [analyze_stock(r, is_scanner=True) for r in raw_data if analyze_stock(r, is_scanner=True)]
    results.sort(key=lambda x: (x['score'], x['rr']), reverse=True)
    for an in results[:15]:
        with st.expander(f"⭐ {an['score']} | {an['name']} | RR: {an['rr']} | {an['vol_icon']}"):
            render_stock_ui(an)

elif st.session_state.page == 'gold':
    if st.button("🏠"): st.session_state.page = 'home'; st.rerun()
    raw_data = fetch_egx_data(scan_all=True)
    for r in raw_data:
        an = analyze_stock(r, is_scanner=True)
        if an and an['is_gold']:
            with st.expander(f"✨ ذهبي: {an['name']}"): render_stock_ui(an)

elif st.session_state.page == 'breakout':
    if st.button("🏠"): st.session_state.page = 'home'; st.rerun()
    raw_data = fetch_egx_data(scan_all=True)
    for r in raw_data:
        an = analyze_stock(r, is_scanner=True)
        if an and an['score'] > 75 and an['rr'] > 1.8:
            with st.expander(f"🚀 اختراق Pro: {an['name']}"): render_stock_ui(an)
