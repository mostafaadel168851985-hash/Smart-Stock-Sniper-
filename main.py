import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="EGX Sniper Elite v8.8", layout="wide")

st.markdown("""
<style>
button[data-baseweb="tab"] { 
    padding-left: 2px !important; 
    padding-right: 2px !important; 
    margin-right: 2px !important;
    font-size: 11px !important;
}
.stTabs [data-baseweb="tab-list"] { gap: 2px !important; }

.stock-header { font-size: 18px !important; font-weight: bold; color: #58a6ff; }
.price-callout { font-size: 18px !important; font-weight: bold; color: #3fb950; }
.stoploss-callout { font-size: 16px !important; font-weight: bold; color: #f85149; }
.stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 8px; }
div[data-testid="stExpander"] { border: 1px solid #30363d; background-color: #0d1117; }
.gold-deal { border: 2px solid #ffd700 !important; background-color: #1c1c10 !important; border-radius: 12px; padding: 15px; margin-bottom: 20px; }

.breakout-box { border: 2px solid #00ffcc !important; background-color: #0f2a2a !important; border-radius: 12px; padding: 15px; margin-bottom: 20px; }

.warning-box { background-color: #2e2a0b; border: 1px solid #ffd700; color: #ffd700; padding: 12px; border-radius: 8px; margin: 10px 0; font-weight: bold; border-left: 5px solid #ffd700; }
</style>
""", unsafe_allow_html=True)

# ================== DATA ==================
@st.cache_data(ttl=300)
def fetch_egx_data(symbol=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"

    if scan_all:
        payload = {
            "filter": [
                {"left": "volume", "operation": "greater", "right": 50000},
                {"left": "close", "operation": "greater", "right": 0.4}
            ],
            "columns": ["name","close","RSI","volume","average_volume_10d_calc","high","low","change","description"],
            "sort": {"sortBy": "change", "sortOrder": "desc"},
            "range": [0, 65]
        }
    else:
        payload = {
            "symbols": {"tickers": [f"EGX:{symbol.upper()}"], "query": {"types": []}},
            "columns": ["close","high","low","volume","RSI","average_volume_10d_calc","change","description"]
        }

    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except:
        return []

# ================== ANALYSIS ==================
def analyze_stock(d_row, is_scan=False):
    try:
        d = d_row['d']

        if is_scan:
            name, p, rsi, v, avg_v, h, l, chg, desc = d
        else:
            p, h, l, v, rsi, avg_v, chg, desc = d
            name = ""

        if not p or not h or not l:
            return None

        pp = (p + h + l) / 3
        s1, r1 = (2 * pp) - h, (2 * pp) - l
        s2, r2 = pp - (h - l), pp + (h - l)

        ratio = v / (avg_v or 1)
        rsi_val = rsi or 0

        # 💎 الذهب
        is_gold = (
            ratio > 1.6 and
            48 < rsi_val < 66 and
            chg > 0.5 and
            p > ((h + l) / 2)
        )

        # 🚀 اختراق حقيقي
        is_breakout = (
            p > r1 * 1.01 and
            ratio > 1.5 and
            50 < rsi_val < 70 and
            chg > 0.7
        )

        t_score = int(90 if rsi_val < 38 else 75 if rsi_val < 55 else 40)
        s_score = int(85 if (ratio > 1.1 and 40 < rsi_val < 65) else 50)

        if rsi_val > 72:
            rec, col = "🛑 تشبع شراء", "#ff4b4b"
        elif is_breakout:
            rec, col = "🚀 اختراق مؤكد", "#00ffcc"
        elif is_gold:
            rec, col = "💎 صفقة ذهبية", "#ffd700"
        elif t_score >= 80 or s_score >= 80:
            rec, col = "🚀 شراء قوي", "#00ff00"
        else:
            rec, col = "⚖️ انتظار", "#58a6ff"

        return {
            "name": name,
            "desc": desc,
            "p": p,
            "rsi": rsi_val,
            "chg": chg,
            "ratio": ratio,
            "t_e": s1,
            "t_t": r1,
            "t_s": s1 * 0.98,
            "s_e": p,
            "s_t": r2,
            "s_s": s2,
            "rec": rec,
            "col": col,
            "is_gold": is_gold,
            "is_breakout": is_breakout
        }

    except:
        return None

# ================== UI ==================
def render_stock_ui(res):
    if not res:
        return

    st.markdown(f"""
    <div style='display:flex;justify-content:space-between;'>
    <span class='stock-header'>{res['name']} {res['desc'][:15]}</span>
    <span style='color:{res['col']};border:1px solid {res['col']};padding:2px 10px;border-radius:6px;'>{res['rec']}</span>
    </div>
    """, unsafe_allow_html=True)

    c1,c2,c3 = st.columns(3)
    c1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("RSI", f"{res['rsi']:.1f}")
    c3.metric("الزخم", f"{res['ratio']:.1f}x")

    st.divider()

    st.write(f"🎯 دخول: {res['t_e']:.2f} | هدف: {res['t_t']:.2f} | وقف: {res['t_s']:.2f}")

# ================== MAIN ==================
st.title("🏹 EGX Sniper Elite v8.8")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📡 تحليل سهم",
    "🔭 للمراقبة",
    "🧮 المتوسط",
    "💎 الذهب",
    "🚀 اختراق مؤكد"
])

# ========= tabs =========

with tab1:
    sym = st.text_input("ادخل كود السهم").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data:
            an = analyze_stock(data[0])
            if an: render_stock_ui(an)

with tab2:
    if st.button("فحص السوق"):
        for r in fetch_egx_data(scan_all=True):
            an = analyze_stock(r, True)
            if an and (an['ratio'] > 1.2):
                with st.expander(f"{an['name']} | {an['p']}"):
                    render_stock_ui(an)

with tab4:
    if st.button("💎 صيد الذهب"):
        for r in fetch_egx_data(scan_all=True):
            an = analyze_stock(r, True)
            if an and an['is_gold']:
                st.markdown(f"<div class='gold-deal'>💎 {an['name']}</div>", unsafe_allow_html=True)
                render_stock_ui(an)

# 🚀 NEW TAB
with tab5:
    st.subheader("🚀 أقوى الاختراقات")

    if st.button("كشف الاختراقات 🔥"):
        found = False

        for r in fetch_egx_data(scan_all=True):
            an = analyze_stock(r, True)

            if an and an['is_breakout']:
                found = True

                st.markdown(f"""
                <div class='breakout-box'>
                🚀 <b>{an['name']}</b> اختراق حقيقي بسيولة {an['ratio']:.1f}x
                </div>
                """, unsafe_allow_html=True)

                render_stock_ui(an)

        if not found:
            st.warning("لا يوجد اختراقات حالياً")
