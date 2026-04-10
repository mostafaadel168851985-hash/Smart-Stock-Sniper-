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
    .entry-card-new { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 15px; text-align: center; margin-bottom: 15px; border-top: 4px solid #3fb950; }
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
        
        # ================== 🎯 ENTRY + RISK SYSTEM (تعديلاتك الجديدة) ==================
        near_support = p <= s1 * 1.02
        is_early_break = (p >= r1 * 0.97 and ratio > 1.1 and trend_med == "صاعد")
        is_strong_break = (p > r1 and ratio > 1.3 and chg > 0.5 and trend_med == "صاعد")
        is_chase = (p > r1 * 1.02)

        # 🎯 تحديد منطقة الدخول
        if near_support:
            entry_min, entry_max = s1 * 0.99, s1 * 1.01
        elif is_strong_break:
            entry_min, entry_max = r1, r1 * 1.01
        elif is_early_break:
            entry_min, entry_max = r1 * 0.98, r1
        else:
            entry_min, entry_max = p * 0.99, p * 1.01

        entry_avg = (entry_min + entry_max) / 2
        stop_loss = s2
        target1, target2 = r1, r2

        # ⚖️ حساب المخاطرة والعائد
        risk = entry_avg - stop_loss
        reward = target2 - entry_avg
        rr = round(reward / risk, 2) if risk > 0 else 0

        if rr >= 2: rr_rating = "🔥 صفقة ممتازة"
        elif rr >= 1.5: rr_rating = "👍 صفقة مقبولة"
        else: rr_rating = "⚠️ صفقة ضعيفة"

        # 🧠 Smart Score
        smart_score = 0
        if trend_med == "صاعد": smart_score += 30
        if ratio > 1.3: smart_score += 25
        if 40 <= rsi_val <= 60: smart_score += 20
        if near_support: smart_score += 15
        if is_chase: smart_score -= 40
        smart_score = max(min(smart_score, 100), 0)
        
        vol_txt, vol_col = ("🔥 زخم", "#ffd700") if ratio > 1.3 else ("⚪ هادئ", "#8b949e")
        is_gold = (ratio > 1.5 and 45 < rsi_val < 65 and trend_med == "صاعد" and sma50 and p > sma50)

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "vol_txt": vol_txt, "vol_col": vol_col, "s1": s1, "s2": s2, "r1": r1, "r2": r2,
            "t_med": trend_med, "s_score": smart_score, "is_gold": is_gold,
            "entry_min": entry_min, "entry_max": entry_max, "entry_avg": entry_avg,
            "stop_loss": stop_loss, "target1": target1, "target2": target2,
            "risk_value": risk, "reward_value": reward, "rr": rr, "rr_rating": rr_rating,
            "is_early_break": is_early_break, "is_strong_break": is_strong_break,
            "is_chase": is_chase, "near_support": near_support
        }
    except: return None

# ================== UI RENDERER ==================
def render_stock_ui(res, title=""):
    if not res: return
    if title: st.markdown(f"<div class='breakout-card'>{title}</div>", unsafe_allow_html=True)
    
    col_rec = "#ffd700" if res['is_gold'] else "#00ffcc" if (res['is_strong_break'] or res['is_early_break']) else "#3fb950"
    st.markdown(f"<div class='stock-header'>{res['name']} | {res['desc'][:15]} <span style='color:{col_rec}; float:left;'>Score: {res['s_score']}</span></div>", unsafe_allow_html=True)
    
    tm_cls = "trend-up" if res['t_med'] == "صاعد" else "trend-down"
    st.markdown(f"<span class='trend-pill {tm_cls}'>ترند متوسط: {res['t_med']}</span>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("RSI", f"{res['rsi']:.1f}")
    with c3: st.markdown(f"<div class='vol-container'>الزخم: <b>{res['ratio']:.1f}x</b><br><span style='color:{res['vol_col']}'>{res['vol_txt']}</span></div>", unsafe_allow_html=True)
    
    # 🎨 واجهة الدخول المطورة (تعديلاتك)
    st.markdown(f"""
    <div class='entry-card-new'>
    🎯 <b>منطقة الدخول:</b><br>
    {res['entry_min']:.2f} → {res['entry_max']:.2f}<br>
    <span style='color:#8b949e;'>متوسط التنفيذ: {res['entry_avg']:.2f}</span><br><br>
    🛑 <b>وقف الخسارة:</b><br>
    <span style='color:#f85149;'>{res['stop_loss']:.2f}</span><br><br>
    🎯 <b>الأهداف:</b><br>
    {res['target1']:.2f} → {res['target2']:.2f}<br><br>
    ⚖️ <b>تحليل الصفقة:</b><br>
    📉 المخاطرة: {res['risk_value']:.2f} ج | 📈 العائد: {res['reward_value']:.2f} ج<br>
    💰 النسبة: 1 : {res['rr']}<br>
    <b>{res['rr_rating']}</b>
    </div>
    """, unsafe_allow_html=True)

    # --- خطة السيولة ---
    st.markdown("---")
    st.subheader("🛠️ خطة السيولة الذكية")
    budget = st.number_input("الميزانية المستهدفة (جنيه):", value=20000, key=f"plan_{res['name']}_{res['p']}")
    p1, p2, p3 = budget * 0.3, budget * 0.4, budget * 0.3
    st.markdown(f"""
        <div class='plan-container'>
            <div class='plan-step up-line'><b>📈 سيناريو الصعود:</b><br>- ادخل بـ <span class='price-callout'>{p1:,.0f} ج</span> عند {res['entry_avg']:.2f}.<br>- لو اخترق {res['target1']:.2f} بزخم، زود بـ <span class='price-callout'>{p2:,.0f} ج</span>.</div>
            <div class='plan-step down-line'><b>📉 سيناريو الهبوط:</b><br>- لو نزل لـ <b>{res['stop_loss']:.2f}</b>، راقب تفعيل وقف الخسارة أو عدل المتوسط بـ {p2:,.0f} ج فقط لو ارتد.</div>
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
            and an['s_score'] >= 50 and not an['is_chase']
            and (an['near_support'] or an['is_strong_break'] or an['is_early_break'])
        ]
        results.sort(key=lambda x: (x['s_score'], x['rr']), reverse=True)
        for an in results:
            with st.expander(f"⭐ {an['s_score']} | {an['name']} | RR: {an['rr']}"): render_stock_ui(an)

elif st.session_state.page == 'breakout':
    if st.button("🏠"): go_to('home')
    data = fetch_egx_data(scan_all=True)
    for r in data:
        an = analyze_stock(r)
        if an and not an['is_chase']:
            if an['is_strong_break']:
                render_stock_ui(an, f"🚀 اختراق قوي: {an['name']}")
            elif an['is_early_break']:
                render_stock_ui(an, f"🟡 اختراق مبكر: {an['name']}")

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
    old_p, old_q = c1.number_input("سعر الشراء القديم", 0.0), c2.number_input("كمية الأسهم", 0)
    new_p = c3.number_input("سعر الشراء الجديد", 0.0)
    if old_p > 0 and old_q > 0 and new_p > 0:
        total_old = old_p * old_q
        for label, q in [("تعديل بسيط (0.5x)", int(old_q*0.5)), ("تعديل متوازن (1:1)", old_q), ("تعديل قوي (2:1)", old_q*2)]:
            cost, avg = q * new_p, (total_old + (q * new_p)) / (old_q + q)
            st.markdown(f"<div class='avg-card'><b>{label}</b>: شراء {q:,} سهم<br>المتوسط الجديد: <span class='price-callout'>{avg:.3f} ج</span></div>", unsafe_allow_html=True)
