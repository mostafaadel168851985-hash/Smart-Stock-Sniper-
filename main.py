import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="EGX Sniper Elite v7", layout="wide")

st.markdown("""
    <style>
    .stock-header { font-size: 20px !important; font-weight: bold; color: #58a6ff; }
    .price-callout { font-size: 18px !important; font-weight: bold; color: #3fb950; }
    .stoploss-callout { font-size: 16px !important; font-weight: bold; color: #f85149; }
    .reason-text { font-size: 14px; color: #ffa500; font-style: italic; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 8px; }
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
            "sort": {"sortBy": "change", "sortOrder": "desc"}, "range": [0, 40]
        }
    else:
        payload = {"symbols": {"tickers": [f"EGX:{symbol.upper()}"], "query": {"types": []}}, "columns": ["close", "high", "low", "volume", "RSI", "average_volume_10d_calc", "change", "description"]}
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except: return []

# ================== LOGIC ==================
def analyze_stock(d_row, is_scan=False):
    d = d_row['d']
    if is_scan: name, p, rsi, v, avg_v, h, l, chg, desc = d
    else: p, h, l, v, rsi, avg_v, chg, desc = d; name = ""
    
    pp = (p + h + l) / 3
    s1, r1, s2, r2 = (2*pp)-h, (2*pp)-l, pp-(h-l), pp+(h-l)
    ratio = v / (avg_v or 1)
    
    # AI Reason Logic
    reason = ""
    if rsi > 70: reason = "⚠️ تشبع شرائي عالي (مخاطرة هبوط)"
    elif ratio < 0.6: reason = "⚠️ ضعف في سيولة التداول"
    elif p > r1: reason = "⚠️ السعر يتداول عند مقاومة قوية"
    else: reason = "✅ المؤشرات الفنية مستقرة"

    t_score = int(90 if rsi < 35 else 75 if rsi < 55 else 40)
    s_score = int(85 if (ratio > 1.1 and 40 < rsi < 65) else 55)

    if (t_score >= 80 or s_score >= 80) and rsi < 65: rec, col = "🚀 دخول مؤكد", "#00ff00"
    elif t_score > 60: rec, col = "⚖️ مراقبة / انتظار", "#58a6ff"
    else: rec, col = "🛑 جني أرباح / تجنب", "#ff4b4b"

    return {
        "name": name, "desc": desc, "p": p, "rsi": rsi, "chg": chg, "ratio": ratio,
        "t_e": s1, "t_t": r1, "t_s": s1 * 0.98, "t_score": t_score,
        "s_e": p, "s_t": r2, "s_s": s2, "s_score": s_score,
        "rec": rec, "col": col, "reason": reason
    }

# ================== UI ==================
def render_stock_ui(res, budget=10000):
    shares = int(budget / res['p'])
    st.markdown(f"<div style='display: flex; justify-content: space-between; align-items: center;'> <span class='stock-header'>{res['name']} {res['desc'][:20]}</span> <span style='color:{res['col']}; font-weight:bold; border:1px solid {res['col']}; padding:3px 12px; border-radius:6px;'>{res['rec']}</span> </div>", unsafe_allow_html=True)
    st.markdown(f"<div class='reason-text'>{res['reason']}</div>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("RSI", f"{res['rsi']:.1f}")
    c3.metric("السيولة", f"{res['ratio']:.1f}x")
    st.divider()

    col_t, col_s = st.columns(2)
    with col_t:
        st.markdown(f"**🎯 مضارب ({res['t_score']})**")
        st.markdown(f"دخول: <span class='price-callout'>{res['t_e']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"هدف: <span class='price-callout'>{res['t_t']:.2f}</span>", unsafe_allow_html=True)
        st.write(f"💵 ربح: {(res['t_t']-res['t_e'])*shares:,.0f} ج")

    with col_s:
        st.markdown(f"**🔁 سوينج ({res['s_score']})**")
        st.markdown(f"دخول: <span class='price-callout'>{res['s_e']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"هدف: <span class='price-callout'>{res['s_t']:.2f}</span>", unsafe_allow_html=True)
        st.write(f"💵 ربح: {(res['s_t']-res['s_e'])*shares:,.0f} ج")

# ================== MAIN ==================
st.title("🏹 EGX Sniper Elite v7")
tab1, tab2 = st.tabs(["📡 رادار الأسهم", "🚨 الماسح الذكي"])

with tab1:
    sym = st.text_input("كود السهم").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data:
            with st.container(border=True):
                b = st.number_input("💰 الميزانية (ج.م)", value=10000, step=1000)
                render_stock_ui(analyze_stock(data[0]), budget=b)

with tab2:
    if st.button("بدء الفحص 🔍"):
        all_d = fetch_egx_data(scan_all=True)
        for r in all_d:
            an = analyze_stock(r, is_scan=True)
            if an['t_score'] >= 78:
                with st.expander(f"🚀 {an['name']} | {an['p']} | {an['rec']}"):
                    render_stock_ui(an)
