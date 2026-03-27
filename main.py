import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="EGX Sniper Elite v4", layout="wide")

# CSS لتنسيق الخطوط وجعل شكل الكارت احترافي
st.markdown("""
    <style>
    .stock-title { font-size: 22px !important; font-weight: bold; color: #58a6ff; margin-bottom: 10px; }
    .stMetric { background-color: #161b22; border-radius: 10px; padding: 10px; border: 1px solid #30363d; }
    div[data-testid="stExpander"] { border: 1px solid #30363d; background-color: #0d1117; }
    </style>
    """, unsafe_allow_html=True)

# ================== DATA ENGINE ==================
@st.cache_data(ttl=300)
def fetch_egx_data(symbol=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    if scan_all:
        payload = {
            "filter": [{"left": "volume", "operation": "greater", "right": 100000}, {"left": "close", "operation": "greater", "right": 0.5}],
            "columns": ["name", "close", "RSI", "volume", "average_volume_10d_calc", "high", "low", "change", "description"],
            "sort": {"sortBy": "change", "sortOrder": "desc"}, "range": [0, 50]
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

# ================== LOGIC & SCORING ==================
def analyze_stock(d_row, is_scan=False):
    if is_scan:
        name, p, rsi, v, avg_v, h, l, chg, desc = d_row['d']
    else:
        p, h, l, v, rsi, avg_v, chg, desc = d_row['d']
        name = ""
    
    # مستويات فيبوناتشي ودعوم (Pivot Points)
    pp = (p + h + l) / 3
    s1, r1 = (2 * pp) - h, (2 * pp) - l
    r2 = pp + (h - l)
    
    # حساب السكور وقوة السيولة
    ratio = v / (avg_v or 1)
    t_score = 90 if rsi < 35 else 75 if rsi < 50 else 50
    s_score = 85 if (ratio > 1.2 and 40 < rsi < 60) else 60
    
    # التوصية النهائية
    if t_score >= 85 or s_score >= 85: 
        rec, rec_col = "🚀 شراء قوي", "#00ff00"
    elif t_score > 65: 
        rec, rec_col = "⚖️ مراقبة / دخول تدريجي", "#58a6ff"
    else: 
        rec, rec_col = "🛑 حذر / جني أرباح", "#ff4b4b"

    return {
        "name": name, "desc": desc, "p": p, "rsi": rsi, "v": v, "ratio": ratio, 
        "chg": chg, "s1": s1, "r1": r1, "r2": r2, "t_score": t_score, 
        "s_score": s_score, "rec": rec, "rec_col": rec_col
    }

# ================== UI DISPLAY ==================
def show_details(code, row):
    res = analyze_stock(row)
    
    # حاسبة الأرباح في الجانب
    with st.sidebar:
        st.header("💰 حاسبة المحفظة")
        budget = st.number_input("المبلغ المخصص (ج.م)", value=10000, step=1000)
        num_shares = int(budget / res['p'])
        st.info(f"ستقوم بشراء: {num_shares} سهم")
        st.divider()

    # العنوان
    st.markdown(f"<div class='stock-title'>🔍 {code} - {res['desc']}</div>", unsafe_allow_html=True)
    
    # المؤشرات الرئيسية
    c1, c2, c3 = st.columns(3)
    c1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("RSI", f"{res['rsi']:.1f}")
    c3.metric("الزخم", f"{res['ratio']:.1f}x")

    st.markdown(f"### التوصية الحالية: <span style='color:{res['rec_col']}'>{res['rec']}</span>", unsafe_allow_html=True)
    
    st.divider()

    # تقسيم التحليل
    col_t, col_s = st.columns(2)
    
    with col_t:
        st.subheader(f"🎯 المضارب ({res['t_score']}/100)")
        st.success(f"✅ دخول: {res['s1']:.2f}")
        st.write(f"🚀 هدف: {res['r1']:.2f}")
        profit = (res['r1'] - res['s1']) * num_shares
        st.warning(f"💵 ربح متوقع: {profit:,.2f} ج.م")
        st.info(f"💡 AI: {'السهم في منطقة تجميع مثالية' if res['rsi'] < 45 else 'انتظر تهدئة السعر قليلاً'}")

    with col_s:
        st.subheader(f"🔁 السوينج ({res['s_score']}/100)")
        st.success(f"✅ دخول: {res['p']:.2f}")
        st.write(f"🚀 هدف: {res['r2']:.2f}")
        profit_s = (res['r2'] - res['p']) * num_shares
        st.warning(f"💵 ربح متوقع: {profit_s:,.2f} ج.م")
        st.info(f"💡 AI: {'سيولة واعدة لاختراق المقاومة' if res['ratio'] > 1.1 else 'السهم يحتاج سيولة إضافية'}")

# ================== MAIN APP ==================
st.markdown("## 🏹 EGX Sniper Elite v4")

tab1, tab2 = st.tabs(["📡 رادار الأسهم", "🚨 الماسح الشامل"])

with tab1:
    symbol = st.text_input("ادخل كود السهم (مثال: TMGH)").upper().strip()
    if symbol:
        data = fetch_egx_data(symbol=symbol)
        if data: show_details(symbol, data[0])
        else: st.error("عفواً، لم نجد بيانات لهذا السهم.")

with tab2:
    if st.button("بدء المسح الشامل للبورصة 🔍"):
        all_data = fetch_egx_data(scan_all=True)
        for stock in all_data:
            analysis = analyze_stock(stock, is_scan=True)
            if analysis['t_score'] >= 80:
                with st.expander(f"🚀 {analysis['name']} - سعر: {analysis['p']} | Score: {analysis['t_score']}"):
                    st.write(f"التوصية: {analysis['rec']}")
                    st.write(f"🎯 دخول: {analysis['s1']:.2f} | هدف: {analysis['r1']:.2f}")
