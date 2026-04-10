import streamlit as st
import requests

# ================== CONFIG & STYLE (V12.7 PRECISE) ==================
st.set_page_config(page_title="EGX Sniper Elite v12.7 Smart", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-size: 18px !important; font-weight: bold !important; margin-bottom: 10px; }
    .stock-header { font-size: 18px !important; font-weight: bold; color: #58a6ff; }
    .price-callout { font-size: 16px !important; font-weight: bold; color: #3fb950; }
    .stoploss-callout { font-size: 14px !important; font-weight: bold; color: #f85149; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 8px; padding: 5px !important; }
    .trend-pill { padding: 4px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; margin: 2px; display: inline-block; }
    .trend-up { background-color: rgba(63, 185, 80, 0.15); color: #3fb950; border: 1px solid #3fb950; }
    .trend-down { background-color: rgba(248, 81, 73, 0.15); color: #f85149; border: 1px solid #f85149; }
    .entry-card-new { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 12px; text-align: center; margin-bottom: 15px; }
    .avg-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-bottom: 12px; border-left: 5px solid #58a6ff; }
    .target-box { background-color: #0d1117; border: 2px solid #58a6ff; border-radius: 12px; padding: 20px; margin-top: 15px; text-align: center; }
    .warning-box { background-color: #2e2a0b; border: 1px solid #ffd700; color: #ffd700; padding: 12px; border-radius: 10px; margin-top: 10px; font-weight: bold; border-left: 6px solid #ffd700; }
    .vol-container { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 8px; text-align: center; }
    .breakout-card { border: 2px solid #00ffcc !important; background-color: #0a1a1a !important; border-radius: 12px; padding: 10px; margin-bottom: 10px; }
    .gold-deal { border: 2px solid #ffd700 !important; background-color: #1c1c10 !important; border-radius: 12px; padding: 12px; margin-bottom: 15px; border-left: 8px solid #ffd700; }
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

# ================== DATA ENGINE ==================
@st.cache_data(ttl=300)
def fetch_egx_data(symbol=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    # إضافة SMA50 و SMA200 للتحليل الطويل والمتوسط
    cols = ["name", "close", "RSI", "volume", "average_volume_10d_calc", "high", "low", "change", "description", "SMA50", "SMA200"]
    if scan_all:
        payload = {
            "filter": [{"left": "volume", "operation": "greater", "right": 50000}, {"left": "close", "operation": "greater", "right": 0.4}],
            "columns": cols,
            "sort": {"sortBy": "change", "sortOrder": "desc"}, "range": [0, 100]
        }
    else:
        payload = {
            "symbols": {"tickers": [f"EGX:{symbol.upper()}"], "query": {"types": []}},
            "columns": ["close", "high", "low", "volume", "RSI", "average_volume_10d_calc", "change", "description", "SMA50", "SMA200"]
        }
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except: return []

# ================== ANALYSIS ENGINE (v12.7 Smart Logic) ==================
def analyze_stock(d_row, is_scan=False):
    try:
        d = d_row['d']
        if is_scan: name, p, rsi, v, avg_v, h, l, chg, desc, sma50, sma200 = d
        else: p, h, l, v, rsi, avg_v, chg, desc, sma50, sma200 = d; name = ""
        
        if p is None or h is None or l is None: return None
        
        # --- الإضافة 1: مستويات الدعم والمقاومة الكاملة ---
        pp = (p + h + l) / 3
        s1, r1 = (2 * pp) - h, (2 * pp) - l
        s2, r2 = pp - (h - l), pp + (h - l)
        
        # --- الإضافة 2: تحليل الاتجاهات ---
        trend_short = "صاعد" if p > pp else "هابط"
        trend_med = "صاعد" if sma50 and p > sma50 else "هابط"
        trend_long = "صاعد" if sma200 and p > sma200 else "هابط"
        
        # --- الإضافة 3: سعر الدخول الحقيقي ---
        # إذا كان السعر قرب الدعم فهو دخول آمن، إذا اخترق R1 فهو دخول اختراق
        real_entry = s1 if p > s1 else p 
        
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

        if ratio < 0.7: vol_txt, vol_col = "🔴 سيولة غائبة", "#ff4b4b"
        elif ratio < 1.3: vol_txt, vol_col = "⚪ تداول هادئ", "#8b949e"
        else: vol_txt, vol_col = "🔥 زخم انفجاري", "#ffd700"

        if rsi_val > 72: rec, col = "🛑 تشبع شراء", "#ff4b4b"
        elif is_gold: rec, col = "💎 صفقة ذهبية", "#ffd700"
        elif t_score >= 75: rec, col = "🚀 شراء قوي", "#00ff00"
        else: rec, col = "⚖️ انتظار", "#58a6ff"

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "vol_txt": vol_txt, "vol_col": vol_col,
            "s1": s1, "s2": s2, "r1": r1, "r2": r2, "pp": pp,
            "t_short": trend_short, "t_med": trend_med, "t_long": trend_long,
            "real_entry": real_entry,
            "t_e": s1, "t_t": r1, "t_s": s1 * 0.98, "t_score": t_score,
            "s_e": p, "s_t": r2, "s_s": s2, "s_score": s_score,
            "rec": rec, "col": col, "is_gold": is_gold, "is_break": is_breakout
        }
    except: return None

# ================== UI RENDERER ==================
def render_stock_ui(res, title=""):
    if not res: return
    if title: st.markdown(f"<div class='breakout-card'>{title}</div>", unsafe_allow_html=True)
    
    # رأس السهم
    st.markdown(f"""
        <div style='display: flex; justify-content: space-between; align-items: center;'>
            <span class='stock-header'>{res['name']} {res['desc'][:15]}</span>
            <span style='color:{res['col']}; font-weight:bold; border:1px solid {res['col']}; padding:2px 8px; border-radius:6px;'>{res['rec']}</span>
        </div>
    """, unsafe_allow_html=True)
    
    # لوحة الاتجاهات (الإضافة الجديدة)
    t_s_cls = "trend-up" if res['t_short'] == "صاعد" else "trend-down"
    t_m_cls = "trend-up" if res['t_med'] == "صاعد" else "trend-down"
    t_l_cls = "trend-up" if res['t_long'] == "صاعد" else "trend-down"
    st.markdown(f"""
        <div style='margin-bottom:10px;'>
            <span class='trend-pill {t_s_cls}'>قصير: {res['t_short']}</span>
            <span class='trend-pill {t_m_cls}'>متوسط: {res['t_med']}</span>
            <span class='trend-pill {t_l_cls}'>طويل: {res['t_long']}</span>
        </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("السعر الحلي", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("RSI", f"{res['rsi']:.1f}")
    with c3:
        st.markdown(f"<div class='vol-container'><div style='color:#8b949e;font-size:10px;'>الزخم</div><div style='font-size:16px;font-weight:bold;'>{res['ratio']:.1f}x</div><div style='color:{res['vol_col']};font-size:10px;'>{res['vol_txt']}</div></div>", unsafe_allow_html=True)
    
    # سعر الدخول الحقيقي (الإضافة الجديدة)
    st.markdown(f"""
        <div class='entry-card-new'>
            <span style='color:#8b949e;'>🎯 سعر الدخول الحقيقي المقترح</span><br>
            <span style='font-size:24px; color:#3fb950; font-weight:bold;'>{res['real_entry']:.2f}</span>
        </div>
    """, unsafe_allow_html=True)

    if res['p'] > res['r1'] * 1.02:
        st.markdown(f"<div class='warning-box'>⚠️ مطاردة خطر! السعر اخترق المقاومة الأولى بزيادة، انتظر التهدئة.</div>", unsafe_allow_html=True)
    
    st.divider()
    
    # مستويات الدعم والمقاومة التفصيلية
    st.subheader("📊 مستويات المناورة الفنية")
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("دعم 2 (قوي)", f"{res['s2']:.2f}")
    sc2.metric("دعم 1 (دخول)", f"{res['s1']:.2f}")
    sc3.metric("مقاومة 1 (هدف)", f"{res['r1']:.2f}")
    sc4.metric("مقاومة 2 (بعيد)", f"{res['r2']:.2f}")

    # خطة السيولة
    st.markdown("---")
    st.subheader("🛠️ خطة السيولة وتمركزات التعزيز")
    budget = st.number_input("ميزانية السهم (جنيه):", value=20000, key=f"plan_{res['name']}_{res['p']}")
    p1, p2, p3 = budget * 0.3, budget * 0.4, budget * 0.3
    
    st.markdown(f"""
    <div class='plan-container'>
        <div class='plan-step up-line'>
            <b>📈 سيناريو الصعود:</b><br>
            - ادخل بـ <span class='price-callout'>{p1:,.0f} ج</span> عند {res['s1']:.2f}.<br>
            - لو اخترق {res['r1']:.2f}، زود بـ <span class='price-callout'>{p2:,.0f} ج</span>.<br>
            - <b>التعزيز النهائي:</b> ضخ الـ <span class='price-callout'>{p3:,.0f} ج</span> الباقية عند تجاوز <b>{res['r2']:.2f}</b>.
        </div>
        <div class='plan-step down-line'>
            <b>📉 سيناريو الهبوط:</b><br>
            - لو نزل لـ <b>{res['s2']:.2f}</b>، استهلك الـ <span class='price-callout'>{p2:,.0f} ج</span> لتعديل المتوسط.<br>
            - <b>التعزيز النهائي:</b> ضخ الـ <span class='price-callout'>{p3:,.0f} ج</span> المتبقية فور عودة السعر لمنطقة <b>{res['p']:.2f}</b>.
        </div>
    </div>
    """, unsafe_allow_html=True)

# ================== NAVIGATION ==================
if st.session_state.page == 'home':
    st.title("🏹 EGX Sniper Elite v12.7 Smart")
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
        target = st.number_input("المتوسط المستهدف؟", value=old_p-0.01)
        if new_p < target < old_p:
            needed_q = (old_q * (old_p - target)) / (target - new_p)
            st.markdown(f"<div class='target-box'><h3>خطة الوصول لهدف {target:.2f}</h3><p>✅ شراء: <b style='color:#3fb950;'>{int(needed_q):,} سهم</b></p><p>✅ مبلغ: <b style='color:#3fb950;'>{(needed_q*new_p):,.2f} ج</b></p></div>", unsafe_allow_html=True)

elif st.session_state.page == 'scanner':
    if st.button("🏠"): go_to('home')
    if st.button("🔍 فحص السوق"):
        results = [an for r in fetch_egx_data(scan_all=True) if (an := analyze_stock(r, True)) and an['t_score'] >= 70]
        results.sort(key=lambda x: x['t_score'], reverse=True)
        for an in results:
            with st.expander(f"⭐ {an['t_score']} | {an['name']} | {an['t_short']}"): render_stock_ui(an)

elif st.session_state.page == 'breakout':
    if st.button("🏠"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r, True)) and an['is_break']:
            render_stock_ui(an, f"🚀 اختراق: {an['name']}")

elif st.session_state.page == 'gold':
    if st.button("🏠"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r, True)) and an['is_gold']:
            render_stock_ui(an, "💎 ذهب")

elif st.session_state.page == 'analyze':
    if st.button("🏠"): go_to('home')
    sym = st.text_input("ادخل رمز السهم (مثلاً: ATQA)").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data: render_stock_ui(analyze_stock(data[0]))
