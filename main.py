import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="EGX Sniper Stable v7", layout="wide")

st.markdown("""
    <style>
    .stock-header { font-size: 20px !important; font-weight: bold; color: #58a6ff; }
    .price-callout { font-size: 18px !important; font-weight: bold; color: #3fb950; }
    .stoploss-callout { font-size: 16px !important; font-weight: bold; color: #f85149; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 8px; }
    div[data-testid="stExpander"] { border: 1px solid #30363d; background-color: #0d1117; }
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
    d = d_row['d']
    if is_scan: name, p, rsi, v, avg_v, h, l, chg, desc = d
    else: p, h, l, v, rsi, avg_v, chg, desc = d; name = ""
    
    # حساب المستويات
    pp = (p + h + l) / 3
    s1, r1 = (2 * pp) - h, (2 * pp) - l
    s2, r2 = pp - (h - l), pp + (h - l)
    
    ratio = v / (avg_v or 1)
    t_score = int(90 if rsi < 38 else 75 if rsi < 55 else 40)
    s_score = int(85 if (ratio > 1.1 and 40 < rsi < 65) else 50)

    # التوصية والسبب
    reason = ""
    if rsi > 70: 
        rec, col, reason = "🛑 جني أرباح", "#ff4b4b", "السهم في منطقة تشبع شرائي عالية"
    elif t_score >= 80 or s_score >= 80: 
        rec, col, reason = "🚀 شراء قوي", "#00ff00", "مؤشرات فنية إيجابية مع زخم جيد"
    elif t_score > 60: 
        rec, col, reason = "⚖️ مراقبة", "#58a6ff", "انتظر تأكيد الاختراق أو العودة للدعم"
    else: 
        rec, col, reason = "🛑 انتظار", "#ff4b4b", "السيولة ضعيفة أو السعر بعيد عن الدعم"

    return {
        "name": name, "desc": desc, "p": p, "rsi": rsi, "chg": chg, "ratio": ratio,
        "t_e": s1, "t_t": r1, "t_s": s1 * 0.98, "t_score": t_score,
        "s_e": p, "s_t": r2, "s_s": s2, "s_score": s_score,
        "rec": rec, "col": col, "reason": reason
    }

# ================== UI RENDERER ==================
def render_stock_ui(res, budget=10000):
    shares = int(budget / res['p'])
    
    st.markdown(f"""
        <div style='display: flex; justify-content: space-between; align-items: center;'>
            <span class='stock-header'>{res['name']} {res['desc'][:25]}</span>
            <span style='color:{res['col']}; font-weight:bold; border:1px solid {res['col']}; padding:3px 10px; border-radius:6px;'>{res['rec']}</span>
        </div>
        <div style='color: #ffa500; font-size: 14px; margin-bottom: 10px;'>{res['reason']}</div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("RSI", f"{res['rsi']:.1f}")
    c3.metric("الزخم", f"{res['ratio']:.1f}x")

    st.divider()

    col_t, col_s = st.columns(2)
    with col_t:
        st.markdown(f"**🎯 مضارب ({res['t_score']}/100)**")
        st.markdown(f"دخول: <span class='price-callout'>{res['t_e']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"هدف: <span class='price-callout'>{res['t_t']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"وقف: <span class='stoploss-callout'>{res['t_s']:.2f}</span>", unsafe_allow_html=True)
        st.write(f"💵 ربح: :green[+{(res['t_t']-res['t_e'])*shares:,.0f} ج]")
        st.write(f"📉 مخاطرة: :red[{(res['t_e']-res['t_s'])*shares:,.0f} ج]")

    with col_s:
        st.markdown(f"**🔁 سوينج ({res['s_score']}/100)**")
        st.markdown(f"دخول: <span class='price-callout'>{res['s_e']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"هدف: <span class='price-callout'>{res['s_t']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"وقف: <span class='stoploss-callout'>{res['s_s']:.2f}</span>", unsafe_allow_html=True)
        st.write(f"💵 ربح: :green[+{(res['s_t']-res['s_e'])*shares:,.0f} ج]")
        st.write(f"📉 مخاطرة: :red[{(res['s_e']-res['s_s'])*shares:,.0f} ج]")

# ================== MAIN APP ==================
st.title("🏹 EGX Sniper Elite Stable")

tab1, tab2 = st.tabs(["📡 رادار الأسهم", "🚨 الماسح الشامل"])

with tab1:
    sym = st.text_input("كود السهم").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data:
            with st.container(border=True):
                budget_val = st.number_input("💰 ميزانية الصفقة (ج.م)", value=10000, step=1000)
                render_stock_ui(analyze_stock(data[0]), budget=budget_val)
        else: st.error("لم نجد بيانات")

with tab2:
    if st.button("بدء الفحص الشامل للبورصة 🔍"):
        all_data = fetch_egx_data(scan_all=True)
        for s_row in all_data:
            analysis = analyze_stock(s_row, is_scan=True)
            if analysis['t_score'] >= 75 or analysis['s_score'] >= 75:
                with st.expander(f"🚀 {analysis['name']} | {analysis['p']} | Score: {max(analysis['t_score'], analysis['s_score'])}"):
                    render_stock_ui(analysis)
