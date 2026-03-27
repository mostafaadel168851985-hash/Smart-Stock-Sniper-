import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="EGX Sniper Elite v4", layout="wide")

# CSS لتنسيق الخطوط وحجم الكروت
st.markdown("""
    <style>
    .stock-title { font-size: 24px !important; font-weight: bold; color: #58a6ff; }
    .metric-label { font-size: 14px !important; }
    div[data-testid="stExpander"] { border: 1px solid #30363d; }
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

# ================== LOGIC ==================
def analyze_stock(d_row, is_scan=False):
    if is_scan: name, p, rsi, v, avg_v, h, l, chg, desc = d_row['d']
    else: p, h, l, v, rsi, avg_v, chg, desc = d_row['d']; name = ""
    
    # التقنيات الأساسية
    pp = (p + h + l) / 3
    s1, s2, r1, r2 = (2*pp)-h, pp-(h-l), (2*pp)-l, pp+(h-l)
    ratio = v / (avg_v or 1)
    
    # الحسابات المالية (Score)
    t_score = int(90 if rsi < 40 else 70 if rsi < 55 else 40)
    s_score = int(85 if (ratio > 1.2 and 45 < rsi < 65) else 50)
    
    # التوصية النهائية
    if t_score >= 80 or s_score >= 80: rec, rec_col = "🚀 شراء قوي", "#00ff00"
    elif t_score > 60: rec, rec_col = "⚖️ شراء جزئي / مراقبة", "#58a6ff"
    else: rec, rec_col = "⚠️ انتظار / جنى أرباح", "#ff4b4b"

    return {
        "name": name, "desc": desc, "p": p, "rsi": rsi, "v": v, "avg_v": avg_v, "chg": chg,
        "s1": s1, "s2": s2, "r1": r1, "r2": r2, "t_score": t_score, "s_score": s_score,
        "ratio": ratio, "rec": rec, "rec_col": rec_col
    }

# ================== UI DISPLAY ==================
def show_details(code, row):
    res = analyze_stock(row)
    st.markdown(f"<div class='stock-title'>{code} - {res['desc']}</div>", unsafe_allow_html=True)
    
    # قسم حاسبة الأرباح
    with st.sidebar:
        st.header("💰 حاسبة الأرباح")
        investment = st.number_input("المبلغ المستثمر (بالجنيه)", value=10000, step=1000)
        shares = investment / res['p']
        st.write(f"عدد الأسهم التقريبي: {int(shares)} سهم")
        st.divider()

    m1, m2, m3 = st.columns(3)
    m1.metric("السعر الحالي", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    m2.metric("RSI (14)", f"{res['rsi']:.1f}")
    m3.metric("قوة السيولة", f"{res['ratio']:.1f}x")

    st.markdown(f"### التوصية الحالية: <span style='color:{res['rec_col']}'>{res['rec)']}</span>", unsafe_allow_html=True)
    
    st.divider()
    
    # تحليل المضارب
    t_col, s_col = st.columns(2)
    with t_col:
        st.subheader(f"🎯 المضارب ({res['t_score']}/100)")
        st.write(f"✅ دخول: **{res['s1']:.2f}** | مستهدف: **{res['r1']:.2f}**")
        profit_t = (res['r1'] - res['s1']) * shares
        st.success(f"💵 ربح متوقع: {profit_t:,.2f} ج.م")
        st.info(f"💡 AI: {'فرصة ارتداد لحظي قوية' if res['rsi'] < 40 else 'ادخل بحذر عند الدعم'}")

    with s_col:
        st.subheader(f"🔁 السوينج ({res['s_score']}/100)")
        st.write(f"✅ دخول: **{(res['s1']+res['r1'])/2:.2f}** | مستهدف: **{res['r2']:.2f}**")
        profit_s = (res['r2'] - ((res['s1']+res['r1'])/2)) * shares
        st.success(f"💵 ربح متوقع: {profit_s:,.2f} ج.م")
        st.info(f"💡 AI: {'تجميع فني ممتاز' if res['ratio'] > 1 else 'انتظر تأكيد السيولة'}")

# ================== MAIN APP ==================
st.title("🏹 EGX Sniper Elite v4")

t1, t2 = st.tabs(["📡 رادار الأسهم", "🚨 الماسح الشامل"])

with t1:
    code = st.text_input("كود السهم").upper().strip()
    if code:
        data = fetch_egx_data(symbol=code)
        if data: show_details(code, data[0])
        else: st.error("بيانات غير متوفرة")

with t2:
    if st.button("بدء المسح الشامل 🔍"):
        all_stocks = fetch_egx_data(scan_all=True)
        for row in all_stocks:
            res = analyze_stock(row, is_scan=True)
            if res['t_score'] >= 75:
                with st.expander(f"🚀 {res['name']} - سعر: {res['p']} | Score: {res['t_score']}"):
                    st.write(f"التوصية: {res['rec']}")
                    st.write(f"🎯 دخول: {res['s1']:.2f} | هدف: {res['r1']:.2f}")
