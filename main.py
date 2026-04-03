import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="EGX Sniper Elite v8.4", layout="wide")

st.markdown("""
    <style>
    .stock-header { font-size: 20px !important; font-weight: bold; color: #58a6ff; }
    .price-callout { font-size: 18px !important; font-weight: bold; color: #3fb950; }
    .stoploss-callout { font-size: 16px !important; font-weight: bold; color: #f85149; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 8px; }
    div[data-testid="stExpander"] { border: 1px solid #30363d; background-color: #0d1117; }
    .avg-card { background-color: #1c2128; border: 1px solid #444c56; border-radius: 10px; padding: 15px; margin-bottom: 10px; }
    .target-box { background-color: #0d1117; border: 2px solid #58a6ff; border-radius: 10px; padding: 20px; margin-top: 10px; }
    .gold-deal { border: 2px solid #ffd700 !important; background-color: #1c1c10 !important; border-radius: 12px; padding: 15px; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# ================== DATA ENGINE ==================
@st.cache_data(ttl=300)
def fetch_egx_data(symbol=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    if scan_all:
        payload = {
            "filter": [
                {"left": "volume", "operation": "greater", "right": 50000},
                {"left": "close", "operation": "greater", "right": 0.4}
            ],
            "columns": ["name", "close", "RSI", "volume", "average_volume_10d_calc", "high", "low", "change", "description"],
            "sort": {"sortBy": "change", "sortOrder": "desc"}, "range": [0, 60]
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
        if is_scan: 
            name, p, rsi, v, avg_v, h, l, chg, desc = d
        else: 
            p, h, l, v, rsi, avg_v, chg, desc = d; name = ""
        
        if p is None or h is None or l is None: return None
        
        # النقاط الفنية الأساسية
        pp = (p + h + l) / 3
        s1, r1 = (2 * pp) - h, (2 * pp) - l
        s2, r2 = pp - (h - l), pp + (h - l)
        
        ratio = v / (avg_v or 1)
        rsi_val = rsi if rsi is not None else 0
        
        # --- فلتر "الصفقة الذهبية" (Confirmation Logic) ---
        is_gold = False
        if ratio > 1.5 and 50 < rsi_val < 68 and chg > 1.0:
            # السعر لازم يكون بيقفل فوق متوسط اليوم (دليل سيطرة المشتري)
            if p > ((h + l) / 2):
                is_gold = True

        if ratio > 1.8: mom_label = "🔥 سيولة ضخمة"
        elif ratio > 1.1: mom_label = "✅ زخم متصاعد"
        elif ratio > 0.7: mom_label = "🆗 مستقر"
        else: mom_label = "⚠️ ضعيف جداً"

        t_score = int(90 if rsi_val < 38 else 75 if rsi_val < 55 else 40)
        s_score = int(85 if (ratio > 1.1 and 40 < rsi_val < 65) else 50)
        
        if rsi_val > 70: rec, col = "🛑 تشبع شراء", "#ff4b4b"
        elif is_gold: rec, col = "💎 صفقة ذهبية", "#ffd700"
        elif t_score >= 80 or s_score >= 80: rec, col = "🚀 شراء قوي", "#00ff00"
        else: rec, col = "⚖️ انتظار", "#58a6ff"

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio, "mom_l": mom_label,
            "t_e": s1, "t_t": r1, "t_s": s1 * 0.98, "t_score": t_score,
            "s_e": p, "s_t": r2, "s_s": s2, "s_score": s_score,
            "rec": rec, "col": col, "is_gold": is_gold
        }
    except: return None

# ================== UI COMPONENTS ==================
def render_stock_ui(res, budget=10000):
    if not res: return
    shares = int(budget / res['p']) if res['p'] > 0 else 0
    
    st.markdown(f"""
        <div style='display: flex; justify-content: space-between; align-items: center;'>
            <span class='stock-header'>{res['name']} {res['desc'][:20]}</span>
            <span style='color:{res['col']}; font-weight:bold; border:1px solid {res['col']}; padding:3px 12px; border-radius:6px;'>{res['rec']}</span>
        </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("السعر الحالي", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("مؤشر RSI", f"{res['rsi']:.1f}")
    c3.metric("الزخم (فوليوم)", f"{res['ratio']:.1f}x", res['mom_l'])
    
    st.divider()

    col_t, col_s = st.columns(2)
    with col_t:
        st.markdown(f"**🎯 مضارب يومي ({res['t_score']})**")
        st.markdown(f"دخول: <span class='price-callout'>{res['t_e']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"هدف: <span class='price-callout'>{res['t_t']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"وقف: <span class='stoploss-callout'>{res['t_s']:.2f}</span>", unsafe_allow_html=True)

    with col_s:
        st.markdown(f"**🔁 سوينج أسبوعي ({res['s_score']})**")
        st.markdown(f"دخول: <span class='price-callout'>{res['s_e']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"هدف: <span class='price-callout'>{res['s_t']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"وقف: <span class='stoploss-callout'>{res['s_s']:.2f}</span>", unsafe_allow_html=True)

# ================== MAIN APP STRUCTURE ==================
st.title("🏹 EGX Sniper Elite v8.4")

tab1, tab2, tab3, tab4 = st.tabs(["📡 رادار البحث", "🚨 الماسح الشامل", "🧮 حاسبة المتوسطات", "🎯 قناص الصفقات الذهبية"])

with tab1:
    sym = st.text_input("ادخل كود السهم (مثال: TMGH, ATQA)").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data:
            analysis = analyze_stock(data[0])
            if analysis:
                with st.container(border=True):
                    render_stock_ui(analysis)
            else: st.error("بيانات السهم غير مكتملة.")
        else: st.error("لم يتم العثور على بيانات.")

with tab2:
    if st.button("بدء فحص كامل السوق 🔍"):
        all_d = fetch_egx_data(scan_all=True)
        for r in all_d:
            an = analyze_stock(r, is_scan=True)
            if an and (an['t_score'] >= 75 or an['s_score'] >= 75):
                with st.expander(f"🚀 {an['name']} | السعر: {an['p']} | Score: {max(an['t_score'], an['s_score'])}"):
                    render_stock_ui(an)

with tab3:
    st.subheader("🧮 حاسبة المتوسطات الذكية")
    col_input1, col_input2, col_input3 = st.columns(3)
    old_p = col_input1.number_input("سعرك القديم", value=0.0, step=0.01)
    old_q = col_input2.number_input("كميتك الحالية", value=0, step=10)
    new_p = col_input3.number_input("السعر الجديد", value=0.0, step=0.01)
    
    if old_p > 0 and old_q > 0 and new_p > 0:
        st.divider()
        target_avg = st.number_input("المتوسط المستهدف؟", value=old_p-0.01, step=0.01)
        if target_avg < old_p and target_avg > new_p:
            needed_q = (old_q * (old_p - target_avg)) / (target_avg - new_p)
            st.success(f"للوصول لمتوسط {target_avg:.3f}: اشتري {int(needed_q):,} سهم بتكلفة {(needed_q*new_p):,.2f} ج")

with tab4:
    st.subheader("💎 فرص الاختراق المؤكدة (High Probability)")
    st.info("هذه القائمة تعرض فقط الأسهم التي حققت اختراقاً حقيقياً مدعوماً بسيولة ضخمة وعزم صاعد.")
    
    if st.button("صيد الصفقات الذهبية الآن 🏹"):
        all_d = fetch_egx_data(scan_all=True)
        gold_found = False
        for r in all_d:
            an = analyze_stock(r, is_scan=True)
            if an and an['is_gold']:
                gold_found = True
                st.markdown(f"""<div class='gold-deal'>
                    <h3 style='color:#ffd700; margin-bottom:5px;'>💎 {an['name']} - {an['desc']}</h3>
                    <b>لماذا هذه الصفقة؟</b> اختراق بسيولة {an['ratio']:.1f}x ضعف المعتاد مع عزم RSI مثالي ({an['rsi']:.1f}).
                </div>""", unsafe_allow_html=True)
                with st.container(border=True):
                    render_stock_ui(an)
        
        if not gold_found:
            st.warning("لا توجد صفقات ذهبية مكتملة الشروط حالياً. انتظر زيادة الفوليوم!")
