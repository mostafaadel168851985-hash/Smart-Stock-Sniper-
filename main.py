import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="EGX Sniper Elite v5", layout="wide")

# CSS مكثف لضغط الواجهة وتصغير الكروت
st.markdown("""
    <style>
    .reportview-container .main .block-container { padding-top: 1rem; }
    .stock-header { font-size: 18px !important; font-weight: bold; color: #58a6ff; margin: 0; }
    .rec-badge { padding: 2px 8px; border-radius: 5px; font-size: 14px; font-weight: bold; }
    .stMetric { padding: 5px !important; border: 1px solid #30363d !important; border-radius: 8px !important; }
    .compact-text { font-size: 13px !important; color: #8b949e; line-height: 1.2; }
    hr { margin: 10px 0 !important; }
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
    d = d_row['d']
    if is_scan: name, p, rsi, v, avg_v, h, l, chg, desc = d
    else: p, h, l, v, rsi, avg_v, chg, desc = d; name = ""
    
    pp = (p + h + l) / 3
    s1, r1 = (2 * pp) - h, (2 * pp) - l
    r2 = pp + (h - l)
    
    ratio = v / (avg_v or 1)
    if ratio > 1.5: liq_msg = "🔥 زخم انفجاري"
    elif ratio > 0.8: liq_msg = "✅ سيولة جيدة"
    else: liq_msg = "⚠️ سيولة ضعيفة"

    t_score = int(90 if rsi < 38 else 75 if rsi < 50 else 40)
    s_score = int(85 if (ratio > 1.1 and 40 < rsi < 62) else 55)

    if t_score >= 80 or s_score >= 80: rec, col = "شراء قوي", "#00ff00"
    elif t_score > 60: rec, col = "مراقبة", "#58a6ff"
    else: rec, col = "انتظار/بيع", "#ff4b4b"

    return {
        "name": name, "desc": desc, "p": p, "rsi": rsi, "chg": chg, "ratio": ratio,
        "s1": s1, "r1": r1, "r2": r2, "liq": liq_msg, "t_s": t_score, "s_s": s_score,
        "rec": rec, "col": col
    }

# ================== UI DISPLAY ==================
def show_details(code, row):
    res = analyze_stock(row)
    
    # رأس الكارت (مضغوط)
    st.markdown(f"""
        <div style='display: flex; justify-content: space-between; align-items: center;'>
            <span class='stock-header'>{code} - {res['desc'][:20]}</span>
            <span class='rec-badge' style='background-color: {res['col']}; color: black;'>{res['rec']}</span>
        </div>
    """, unsafe_allow_html=True)
    
    # حاسبة الميزانية (في الوسط بدل الـ Sidebar)
    with st.expander("💰 ميزانية الصفقة وحساب الأرباح", expanded=True):
        budget = st.number_input("المبلغ (ج.م)", value=10000, step=1000)
        num_shares = int(budget / res['p'])
        st.caption(f"عدد الأسهم المتوقع: {num_shares}")

    # المؤشرات في سطر واحد
    c1, c2, c3 = st.columns(3)
    c1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("RSI", f"{res['rsi']:.1f}")
    c3.metric("الزخم", f"{res['ratio']:.1f}x", res['liq'])

    st.divider()

    # التحليل الفني (مضغوط)
    col_t, col_s = st.columns(2)
    with col_t:
        st.markdown(f"**🎯 مضارب ({res['t_s']})**")
        st.markdown(f"<p class='compact-text'>دخول: {res['s1']:.2f}<br>هدف: {res['r1']:.2f}<br>ربح: <span style='color:#00ff00'>{(res['r1']-res['s1'])*num_shares:,.0f} ج.م</span></p>", unsafe_allow_html=True)
        st.caption("💡 ارتداد من الدعم")

    with col_s:
        st.markdown(f"**🔁 سوينج ({res['s_s']})**")
        st.markdown(f"<p class='compact-text'>دخول: {res['p']:.2f}<br>هدف: {res['r2']:.2f}<br>ربح: <span style='color:#00ff00'>{(res['r2']-res['p'])*num_shares:,.0f} ج.م</span></p>", unsafe_allow_html=True)
        st.caption("💡 اختراق مقاومة")

# ================== APP MAIN ==================
st.markdown("<h3 style='margin:0;'>🏹 EGX Sniper v5</h3>", unsafe_allow_html=True)
t1, t2 = st.tabs(["📡 رادار", "🚨 ماسح السوق"])

with t1:
    sym = st.text_input("كود السهم").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data: show_details(sym, data[0])
        else: st.error("غير موجود")

with t2:
    if st.button("فحص شامل"):
        all_d = fetch_egx_data(scan_all=True)
        for s in all_d:
            a = analyze_stock(s, is_scan=True)
            if a['t_s'] >= 80:
                with st.expander(f"🚀 {a['name']} | {a['p']} | RSI:{a['rsi']:.0f}"):
                    st.write(f"دخول: {a['s1']:.2f} | هدف: {a['r1']:.2f}")
