import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="EGX Sniper Elite v8.7", layout="wide")

st.markdown("""
    <style>
    /* 1. ضغط التابات لأقصى درجة ممكنة للموبايل */
    button[data-baseweb="tab"] { 
        padding-left: 2px !important; 
        padding-right: 2px !important; 
        margin-right: 2px !important;
        font-size: 11px !important; /* تصغير الخط قليلاً لضمان ظهور الـ 4 تابات */
    }
    .stTabs [data-baseweb="tab-list"] { gap: 2px !important; }

    /* 2. تحسينات الواجهة */
    .stock-header { font-size: 18px !important; font-weight: bold; color: #58a6ff; }
    .price-callout { font-size: 18px !important; font-weight: bold; color: #3fb950; }
    .stoploss-callout { font-size: 16px !important; font-weight: bold; color: #f85149; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 8px; }
    div[data-testid="stExpander"] { border: 1px solid #30363d; background-color: #0d1117; }
    .gold-deal { border: 2px solid #ffd700 !important; background-color: #1c1c10 !important; border-radius: 12px; padding: 15px; margin-bottom: 20px; }
    
    /* 3. صندوق التنبيه المطور */
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
            "sort": {"sortBy": "change", "sortOrder": "desc"}, "range": [0, 65]
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
        is_gold = (ratio > 1.6 and 48 < rsi_val < 66 and chg > 0.5 and p > ((h + l) / 2))

        t_score = int(90 if rsi_val < 38 else 75 if rsi_val < 55 else 40)
        s_score = int(85 if (ratio > 1.1 and 40 < rsi_val < 65) else 50)
        
        if rsi_val > 72: rec, col = "🛑 تشبع شراء", "#ff4b4b"
        elif is_gold: rec, col = "💎 صفقة ذهبية", "#ffd700"
        elif t_score >= 80 or s_score >= 80: rec, col = "🚀 شراء قوي", "#00ff00"
        else: rec, col = "⚖️ انتظار", "#58a6ff"

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "t_e": s1, "t_t": r1, "t_s": s1 * 0.98, "t_score": t_score,
            "s_e": p, "s_t": r2, "s_s": s2, "s_score": s_score,
            "rec": rec, "col": col, "is_gold": is_gold
        }
    except: return None

# ================== UI COMPONENTS ==================
def render_stock_ui(res):
    if not res: return
    
    st.markdown(f"""
        <div style='display: flex; justify-content: space-between; align-items: center;'>
            <span class='stock-header'>{res['name']} {res['desc'][:15]}</span>
            <span style='color:{res['col']}; font-weight:bold; border:1px solid {res['col']}; padding:2px 10px; border-radius:6px; font-size:14px;'>{res['rec']}</span>
        </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("RSI", f"{res['rsi']:.1f}")
    c3.metric("الزخم", f"{res['ratio']:.1f}x")
    
    # --- نظام التنبيه الذكي المطور ---
    # السماحية 1% فوق الحد العلوي لنطاق الدخول اليومي لمنع المطاردة
    daily_entry_top = res['t_e'] * 1.008
    safety_limit = daily_entry_top * 1.01 
    
    if res['p'] > safety_limit:
        st.markdown(f"""
            <div class='warning-box'>
                ⚠️ تنبيه: السعر ({res['p']:.2f}) أعلى من نطاق الدخول الآمن ({daily_entry_top:.2f}). 
                دخولك الآن يعتبر "مطاردة للسهم" بمخاطرة عالية!
            </div>
        """, unsafe_allow_html=True)
    
    st.divider()

    col_t, col_s = st.columns(2)
    with col_t:
        st.write("**🎯 مضارب يومي**")
        # تعديل المسمى وسقف النطاق للوضوح
        st.markdown(f"نطاق دخول: <span class='price-callout'>{res['t_e']:.2f} - {daily_entry_top:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"هدف: <span class='price-callout'>{res['t_t']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"وقف: <span class='stoploss-callout'>{res['t_s']:.2f}</span>", unsafe_allow_html=True)

    with col_s:
        st.write("**🔁 سوينج أسبوعي**")
        st.markdown(f"نطاق دخول: <span class='price-callout'>{res['s_e']:.2f} - {res['s_e']*1.008:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"هدف: <span class='price-callout'>{res['s_t']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"وقف: <span class='stoploss-callout'>{res['s_s']:.2f}</span>", unsafe_allow_html=True)

# ================== MAIN APP STRUCTURE ==================
st.title("🏹 EGX Sniper Elite v8.7")

# تابات مضغوطة جداً لتناسب الموبايل وتظهر في صف واحد
tab1, tab2, tab3, tab4 = st.tabs(["📡 تحليل سهم", "🔭 للمراقبة", "🧮 حساب المتوسط", "💎 قنص الذهب"])

with tab1:
    sym = st.text_input("ادخل كود السهم").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data:
            an = analyze_stock(data[0])
            if an: render_stock_ui(an)
        else: st.error("غير موجود")

with tab2:
    if st.button("بدء الفحص السريع 🔍"):
        all_d = fetch_egx_data(scan_all=True)
        for r in all_d:
            an = analyze_stock(r, is_scan=True)
            if an and (an['t_score'] >= 75 or an['s_score'] >= 75):
                with st.expander(f"🚀 {an['name']} | {an['p']}"): render_stock_ui(an)

with tab3:
    st.subheader("🧮 حاسبة متوسط التكلفة")
    col1, col2, col3 = st.columns(3)
    old_p = col1.number_input("سعرك", value=0.0)
    old_q = col2.number_input("كميتك", value=0)
    new_p = col3.number_input("جديد", value=0.0)
    if old_p > 0 and old_q > 0 and new_p > 0:
        target = st.number_input("المستهدف؟", value=old_p-0.01)
        if target < old_p and target > new_p:
            needed = (old_q * (old_p - target)) / (target - new_p)
            st.success(f"للوصول لـ {target:.3f}: اشتري {int(needed):,} سهم")

with tab4:
    st.subheader("💎 قناص الصفقات الذهبية")
    if st.button("صيد الذهب الآن 🏹"):
        all_d = fetch_egx_data(scan_all=True)
        found = False
        for r in all_d:
            an = analyze_stock(r, is_scan=True)
            if an and an['is_gold']:
                found = True
                st.markdown(f"<div class='gold-deal'><b>💎 {an['name']}</b>: اختراق فني بسيولة {an['ratio']:.1f}x</div>", unsafe_allow_html=True)
                render_stock_ui(an)
        if not found: st.warning("لا يوجد حالياً.")
