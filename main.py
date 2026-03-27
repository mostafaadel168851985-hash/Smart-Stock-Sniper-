import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="EGX Sniper Elite v6", layout="wide")

# CSS متوازن: كروت مضغوطة لكن بخطوط واضحة للأرقام
st.markdown("""
    <style>
    .stock-header { font-size: 20px !important; font-weight: bold; color: #58a6ff; }
    .price-callout { font-size: 18px !important; font-weight: bold; color: #3fb950; }
    .stoploss-callout { font-size: 16px !important; font-weight: bold; color: #f85149; }
    .info-text { font-size: 14px; color: #8b949e; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; }
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
                {"left": "volume", "operation": "greater", "right": 50000}, # وسعنا الفلتر شوية
                {"left": "close", "operation": "greater", "right": 0.4}
            ],
            "columns": ["name", "close", "RSI", "volume", "average_volume_10d_calc", "high", "low", "change", "description"],
            "sort": {"sortBy": "change", "sortOrder": "desc"}, "range": [0, 40]
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
    
    # المعادلات الفنية
    pp = (p + h + l) / 3
    s1, r1 = (2 * pp) - h, (2 * pp) - l
    s2, r2 = pp - (h - l), pp + (h - l)
    
    # الزخم والسيولة
    ratio = v / (avg_v or 1)
    liq_msg = "🔥 قوي" if ratio > 1.4 else "✅ مستقر" if ratio > 0.7 else "⚠️ ضعيف"
    
    # الأهداف والوقف
    t_entry, t_target, t_stop = s1, r1, s1 * 0.98
    s_entry, s_target, s_stop = p, r2, s2

    t_score = int(90 if rsi < 40 else 70 if rsi < 55 else 45)
    s_score = int(85 if (ratio > 1.1 and 40 < rsi < 62) else 50)

    if t_score >= 80 or s_score >= 80: rec, col = "🚀 شراء", "#00ff00"
    elif t_score > 60: rec, col = "⚖️ مراقبة", "#58a6ff"
    else: rec, col = "🛑 انتظار", "#ff4b4b"

    return {
        "name": name, "desc": desc, "p": p, "rsi": rsi, "chg": chg, "ratio": ratio, "liq": liq_msg,
        "t_e": t_entry, "t_t": t_target, "t_s": t_stop, "t_score": t_score,
        "s_e": s_entry, "s_t": s_target, "s_s": s_stop, "s_score": s_score,
        "rec": rec, "col": col
    }

# ================== COMPONENT: STOCK CARD ==================
def render_stock_ui(res, budget=10000):
    shares = int(budget / res['p'])
    
    #Header
    st.markdown(f"""
        <div style='display: flex; justify-content: space-between; align-items: center;'>
            <span class='stock-header'>{res['name'] if res['name'] else ''} {res['desc'][:25]}</span>
            <span style='color:{res['col']}; font-weight:bold; border:1px solid {res['col']}; padding:2px 10px; border-radius:5px;'>{res['rec']}</span>
        </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("RSI", f"{res['rsi']:.1f}")
    c3.metric("الزخم", f"{res['ratio']:.1f}x", res['liq'])

    st.divider()

    col_t, col_s = st.columns(2)
    with col_t:
        st.markdown(f"**🎯 مضارب ({res['t_score']}/100)**")
        st.markdown(f"دخول: <span class='price-callout'>{res['t_e']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"هدف: <span class='price-callout'>{res['t_t']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"وقف: <span class='stoploss-callout'>{res['t_s']:.2f}</span>", unsafe_allow_html=True)
        st.write(f"💵 ربح: :green[+{(res['t_t']-res['t_e'])*shares:,.0f} ج]")

    with col_s:
        st.markdown(f"**🔁 سوينج ({res['s_score']}/100)**")
        st.markdown(f"دخول: <span class='price-callout'>{res['s_e']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"هدف: <span class='price-callout'>{res['s_t']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"وقف: <span class='stoploss-callout'>{res['s_s']:.2f}</span>", unsafe_allow_html=True)
        st.write(f"💵 ربح: :green[+{(res['s_t']-res['s_e'])*shares:,.0f} ج]")

# ================== MAIN APP ==================
st.title("🏹 EGX Sniper Elite v6")

tab1, tab2 = st.tabs(["📡 رادار الأسهم", "🚨 الماسح الذكي للفرص"])

with tab1:
    sym = st.text_input("كود السهم (مثال: TMGH, ATQA)").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data:
            with st.container(border=True):
                budget_val = st.number_input("💰 ميزانية الصفقة (ج.م)", value=10000, step=1000, key="radar_budget")
                render_stock_ui(analyze_stock(data[0]), budget=budget_val)
        else: st.error("لم نجد بيانات لهذا الكود")

with tab2:
    st.write("بيتم فحص أقوى 40 سهم في البورصة حالياً...")
    if st.button("بدء الفحص الشامل 🔍"):
        all_data = fetch_egx_data(scan_all=True)
        found = False
        for s_row in all_data:
            analysis = analyze_stock(s_row, is_scan=True)
            if analysis['t_score'] >= 78 or analysis['s_score'] >= 78:
                found = True
                with st.expander(f"🚀 {analysis['name']} | السعر: {analysis['p']} | Score: {max(analysis['t_score'], analysis['s_score'])}"):
                    render_stock_ui(analysis)
        if not found: st.warning("السوق حالياً مستقر، لا توجد فرص انفجارية مطابقة للشروط.")

