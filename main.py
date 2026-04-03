import streamlit as st
import requests

# ================== CONFIG & STYLE (V8.3 ORIGINAL) ==================
st.set_page_config(page_title="EGX Sniper Elite v10.0", layout="wide")

st.markdown("""
    <style>
    /* تقليل المسافات بين التابات لتظهر في سطر واحد */
    button[data-baseweb="tab"] { 
        padding-left: 8px !important; 
        padding-right: 8px !important; 
        font-size: 13px !important; 
    }
    .stock-header { font-size: 20px !important; font-weight: bold; color: #58a6ff; }
    .price-callout { font-size: 18px !important; font-weight: bold; color: #3fb950; }
    .stoploss-callout { font-size: 16px !important; font-weight: bold; color: #f85149; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 8px; }
    div[data-testid="stExpander"] { border: 1px solid #30363d; background-color: #0d1117; }
    .avg-card { background-color: #1c2128; border: 1px solid #444c56; border-radius: 10px; padding: 15px; margin-bottom: 10px; }
    .target-box { background-color: #0d1117; border: 2px solid #58a6ff; border-radius: 10px; padding: 20px; margin-top: 10px; }
    
    .vol-container {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 10px;
        text-align: center;
    }
    .vol-label { color: #8b949e; font-size: 14px; margin-bottom: 2px; }
    .vol-value { font-size: 24px; font-weight: bold; color: white; }
    .vol-status { font-size: 13px; font-weight: bold; margin-top: 2px; }
    
    .gold-deal { border: 2px solid #ffd700 !important; background-color: #1c1c10 !important; border-radius: 12px; padding: 15px; margin-bottom: 20px; border-left: 8px solid #ffd700; }
    .breakout-card { border: 2px solid #00ffcc !important; background-color: #0a1a1a !important; border-radius: 12px; padding: 10px; margin-bottom: 10px; }
    .warning-box { background-color: #2e2a0b; border: 1px solid #ffd700; color: #ffd700; padding: 12px; border-radius: 8px; margin: 10px 0; font-weight: bold; border-left: 5px solid #ffd700; }
    </style>
    """, unsafe_allow_html=True)

# ================== DATA ENGINE ==================
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

# ================== ANALYSIS LOGIC ==================
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
        rsi_val = rsi if rsi is not None else 0
        
        if ratio < 0.7: vol_txt, vol_col = "🔴 سيولة غائبة", "#ff4b4b"
        elif 0.7 <= ratio < 1.3: vol_txt, vol_col = "⚪ تداول هادئ", "#8b949e"
        elif 1.3 <= ratio < 1.9: vol_txt, vol_col = "🟢 دخول سيولة", "#3fb950"
        else: vol_txt, vol_col = "🔥 زخم انفجاري", "#ffd700"

        is_gold = (ratio > 1.6 and 48 < rsi_val < 66 and chg > 0.5 and p > ((h + l) / 2))
        is_breakout = (p > r1 * 0.998 and ratio > 1.2 and rsi_val > 50)

        t_score = int(90 if rsi_val < 38 else 75 if rsi_val < 55 else 40)
        s_score = int(85 if (ratio > 1.1 and 40 < rsi_val < 65) else 50)
        
        if rsi_val > 72: rec, col = "🛑 تشبع شراء", "#ff4b4b"
        elif is_gold: rec, col = "💎 صفقة ذهبية", "#ffd700"
        elif t_score >= 80 or s_score >= 80: rec, col = "🚀 شراء قوي", "#00ff00"
        else: rec, col = "⚖️ انتظار", "#58a6ff"

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "vol_txt": vol_txt, "vol_col": vol_col,
            "t_e": s1, "t_t": r1, "t_s": s1 * 0.98, "t_score": t_score,
            "s_e": p, "s_t": r2, "s_s": s2, "s_score": s_score,
            "rec": rec, "col": col, "is_gold": is_gold, "is_break": is_breakout
        }
    except: return None

# ================== UI COMPONENTS ==================
def render_stock_ui(res, is_break=False):
    if not res: return
    
    if is_break:
        st.markdown(f"<div class='breakout-card'>🚀 <b>اختراق حقيقي: {res['name']} (Score: {res['t_score']})</b></div>", unsafe_allow_html=True)

    st.markdown(f"""
        <div style='display: flex; justify-content: space-between; align-items: center;'>
            <span class='stock-header'>{res['name']} {res['desc'][:15]}</span>
            <span style='color:{res['col']}; font-weight:bold; border:1px solid {res['col']}; padding:3px 12px; border-radius:6px; font-size:15px;'>{res['rec']}</span>
        </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("السعر الحالي", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("مؤشر RSI", f"{res['rsi']:.1f}")
    
    with c3:
        st.markdown(f"""
            <div class='vol-container'>
                <div class='vol-label'>الزخم</div>
                <div class='vol-value'>{res['ratio']:.1f}x</div>
                <div class='vol-status' style='color:{res['vol_col']}'>{res['vol_txt']}</div>
            </div>
        """, unsafe_allow_html=True)
    
    daily_entry_top = res['t_e'] * 1.008
    if res['p'] > daily_entry_top * 1.01:
        st.markdown(f"<div class='warning-box'>⚠️ تنبيه: السعر ({res['p']:.2f}) أعلى من نطاق الدخول الآمن ({daily_entry_top:.2f}). مطاردة!</div>", unsafe_allow_html=True)
    
    st.divider()

    col_t, col_s = st.columns(2)
    with col_t:
        st.markdown(f"**🎯 مضارب يومي ({res['t_score']})**")
        st.markdown(f"نطاق دخول: <span class='price-callout'>{res['t_e']:.2f} - {daily_entry_top:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"هدف: <span class='price-callout'>{res['t_t']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"وقف: <span class='stoploss-callout'>{res['t_s']:.2f}</span>", unsafe_allow_html=True)

    with col_s:
        st.markdown(f"**🔁 سوينج أسبوعي ({res['s_score']})**")
        st.markdown(f"نطاق دخول: <span class='price-callout'>{res['s_e']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"هدف: <span class='price-callout'>{res['s_t']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"وقف: <span class='stoploss-callout'>{res['s_s']:.2f}</span>", unsafe_allow_html=True)

# ================== MAIN APP STRUCTURE ==================
st.title("🏹 EGX Sniper Elite v10.0")

# --- تفعيل التسميات الجديدة والمختصرة ---
tab1, tab2, tab3, tab4 = st.tabs(["📡 تحليل سهم", "🔭 للمراقبة", "🧮 حساب متوسط", "💎 قنص الذهب"])

with tab1:
    sym = st.text_input("ادخل كود السهم").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data:
            an = analyze_stock(data[0])
            if an: render_stock_ui(an)

with tab2:
    col_l, col_r = st.columns(2)
    with col_l: scan_btn = st.button("🔍 فحص سريع")
    with col_r: break_btn = st.button("🚀 كشف الاختراقات")

    if scan_btn:
        all_d = fetch_egx_data(scan_all=True)
        for r in all_d:
            an = analyze_stock(r, is_scan=True)
            if an and (an['t_score'] >= 75 or an['rsi'] > 45):
                with st.expander(f"🚀 {an['name']} | P: {an['p']} | Score: {an['t_score']}"): render_stock_ui(an)
                
    if break_btn:
        all_d = fetch_egx_data(scan_all=True)
        found = False
        for r in all_d:
            an = analyze_stock(r, is_scan=True)
            if an and an['is_break']:
                found = True
                render_stock_ui(an, is_break=True)
        if not found: st.warning("لا توجد اختراقات مؤكدة حالياً.")

with tab3:
    st.subheader("🧮 حاسبة متوسط التكلفة الذكية")
    col_input1, col_input2, col_input3 = st.columns(3)
    old_p = col_input1.number_input("سعرك القديم", value=0.0, step=0.01)
    old_q = col_input2.number_input("الكمية الحالية", value=0, step=10)
    new_p = col_input3.number_input("السعر الجديد", value=0.0, step=0.01)
    
    if old_p > 0 and old_q > 0 and new_p > 0:
        current_total = old_p * old_q
        st.divider()
        st.markdown("#### 💡 اقتراحات التعديل:")
        scenarios = [{"label": "تعديل بسيط (نصف الكمية)", "add_qty": int(old_q * 0.5)},
                     {"label": "تعديل متوسط (1:1)", "add_qty": old_q},
                     {"label": "تعديل جذري (2:1)", "add_qty": old_q * 2}]
        for sc in scenarios:
            new_avg = (current_total + (new_p * sc['add_qty'])) / (old_q + sc['add_qty'])
            st.markdown(f"<div class='avg-card'><b>{sc['label']}</b>: شراء {sc['add_qty']} سهم. المتوسط الجديد: <span style='color:#3fb950;'>{new_avg:.3f} ج</span></div>", unsafe_allow_html=True)
        
        st.markdown("### 🎯 الوصول لمتوسط محدد")
        target_avg = st.number_input("المتوسط المستهدف؟", value=old_p-0.01)
        if target_avg > new_p and target_avg < old_p:
            needed_q = (old_q * (old_p - target_avg)) / (target_avg - new_p)
            st.markdown(f"<div class='target-box'>للوصول لـ {target_avg:.3f}: اشتري <b style='color:#3fb950;'>{int(needed_q):,}</b> سهم بتكلفة {needed_q*new_p:,.0f} ج</div>", unsafe_allow_html=True)

with tab4:
    st.subheader("💎 قناص الصفقات الذهبية")
    if st.button("صيد الذهب الآن 🏹"):
        all_d = fetch_egx_data(scan_all=True)
        found = False
        for r in all_d:
            an = analyze_stock(r, is_scan=True)
            if an and an['is_gold']:
                found = True
                st.markdown(f"<div class='gold-deal'><b>💎 {an['name']} (Score: {an['t_score']})</b>: {an['vol_txt']} ({an['ratio']:.1f}x)</div>", unsafe_allow_html=True)
                render_stock_ui(an)
        if not found: st.warning("لا يوجد ذهب حالياً.")
