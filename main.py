import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="EGX Sniper Elite v8.3.5", layout="wide")

st.markdown("""
    <style>
    .stock-header { font-size: 20px !important; font-weight: bold; color: #58a6ff; }
    .price-callout { font-size: 18px !important; font-weight: bold; color: #3fb950; }
    .stoploss-callout { font-size: 16px !important; font-weight: bold; color: #f85149; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 8px; }
    div[data-testid="stExpander"] { border: 1px solid #30363d; background-color: #0d1117; }
    .investor-box { background-color: #1c2128; border: 1px solid #30363d; padding: 10px; border-radius: 8px; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# ================== DATA ENGINE (Real Historical Data) ==================
@st.cache_data(ttl=300)
def fetch_egx_data(symbol=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    # طلب أهم رقمين حقيقيين للمستثمر (أعلى وأقل سعر في سنة)
    extra_cols = ["high_log_52w", "low_log_52w"]
    
    if scan_all:
        payload = {
            "filter": [
                {"left": "volume", "operation": "greater", "right": 50000},
                {"left": "close", "operation": "greater", "right": 0.4}
            ],
            "columns": ["name", "close", "RSI", "volume", "average_volume_10d_calc", "high", "low", "change", "description"] + extra_cols,
            "sort": {"sortBy": "change", "sortOrder": "desc"}, "range": [0, 50]
        }
    else:
        payload = {
            "symbols": {"tickers": [f"EGX:{symbol.upper()}"], "query": {"types": []}},
            "columns": ["close", "high", "low", "volume", "RSI", "average_volume_10d_calc", "change", "description"] + extra_cols
        }
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except: return []

# ================== ANALYSIS LOGIC (Stable) ==================
def analyze_stock(d_row, is_scan=False):
    try:
        d = d_row['d']
        # فحص طول البيانات لضمان عدم حدوث TypeError
        if len(d) < 9: return None
        
        if is_scan:
            name, p, rsi, v, avg_v, h, l, chg, desc, h_52, l_52 = d
        else:
            p, h, l, v, rsi, avg_v, chg, desc, h_52, l_52 = d; name = ""

        if p is None or h is None or l is None: return None

        # حسابات الأهداف والدعوم (Pivot Points)
        pp = (p + h + l) / 3
        s1, r1 = (2 * pp) - h, (2 * pp) - l
        s2, r2 = pp - (h - l), pp + (h - l)
        
        ratio = v / (avg_v or 1)
        mom_label = "🔥 سيولة ضخمة" if ratio > 1.8 else "✅ زخم متصاعد" if ratio > 1.1 else "🆗 مستقر"

        rsi_val = rsi if rsi is not None else 0
        t_score = int(90 if rsi_val < 38 else 75 if rsi_val < 55 else 40)
        s_score = int(85 if (ratio > 1.1 and 40 < rsi_val < 65) else 50)
        
        rec, col = ("🛑 تشبع شراء", "#ff4b4b") if rsi_val > 70 else \
                   ("🚀 شراء قوي", "#00ff00") if (t_score >= 80 or s_score >= 80) else \
                   ("⚖️ انتظار", "#58a6ff")

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio, "mom_l": mom_label,
            "t_e": s1, "t_t": r1, "t_s": s1 * 0.98, "t_score": t_score,
            "s_e": p, "s_t": r2, "s_s": s2, "s_score": s_score,
            "h_52": h_52, "l_52": l_52, "rec": rec, "col": col
        }
    except: return None

# ================== UI COMPONENTS ==================
def render_stock_ui(res, budget=10000):
    if not res: return
    
    st.markdown(f"""
        <div style='display: flex; justify-content: space-between; align-items: center;'>
            <span class='stock-header'>{res['name']} {res['desc'][:20]}</span>
            <span style='color:{res['col']}; font-weight:bold; border:1px solid {res['col']}; padding:3px 12px; border-radius:6px;'>{res['rec']}</span>
        </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("السعر الحالي", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("مؤشر RSI", f"{res['rsi']:.1f}")
    c3.metric("الزخم", f"{res['ratio']:.1f}x", res['mom_l'])

    # عرض الداتا التاريخية الحقيقية (المستثمر)
    if res['l_52'] and res['h_52']:
        st.markdown(f"""
            <div class='investor-box'>
                <b style='color:#58a6ff;'>🏗️ رؤية المستثمر (بيانات سنة حقيقية):</b><br>
                أقل سعر وصل له السهم (دعم تاريخي): <span class='stoploss-callout'>{res['l_52']:.2f}</span><br>
                أعلى سعر وصل له السهم (قمة تاريخية): <span class='price-callout'>{res['h_52']:.2f}</span>
            </div>
        """, unsafe_allow_html=True)
    
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
        st.markdown(f"الوقف القوي: <span class='stoploss-callout'>{res['s_s']:.2f}</span>", unsafe_allow_html=True)

# ... (بقية كود الـ Tabs والحاسبة بدون تغيير)
