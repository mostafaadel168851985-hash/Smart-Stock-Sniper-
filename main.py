import streamlit as st
import requests

# ================== CONFIG & STYLE (V12.7 PRECISE) ==================
st.set_page_config(page_title="EGX Sniper Elite v12.7", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-size: 18px !important; font-weight: bold !important; margin-bottom: 10px; }
    .stock-header { font-size: 18px !important; font-weight: bold; color: #58a6ff; }
    .price-callout { font-size: 16px !important; font-weight: bold; color: #3fb950; }
    .stoploss-callout { font-size: 14px !important; font-weight: bold; color: #f85149; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 8px; padding: 5px !important; }
    
    .avg-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-bottom: 12px; border-left: 5px solid #58a6ff; }
    .target-box { background-color: #0d1117; border: 2px solid #58a6ff; border-radius: 12px; padding: 20px; margin-top: 15px; text-align: center; }
    
    .warning-box { background-color: #2e2a0b; border: 1px solid #ffd700; color: #ffd700; padding: 12px; border-radius: 10px; margin-top: 10px; font-weight: bold; border-left: 6px solid #ffd700; }
    .vol-container { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 8px; text-align: center; }
    .breakout-card { border: 2px solid #00ffcc !important; background-color: #0a1a1a !important; border-radius: 12px; padding: 10px; margin-bottom: 10px; }
    .gold-deal { border: 2px solid #ffd700 !important; background-color: #1c1c10 !important; border-radius: 12px; padding: 12px; margin-bottom: 15px; border-left: 8px solid #ffd700; }
    
    .plan-container { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-top: 15px; }
    .plan-step { margin-bottom: 8px; padding-right: 10px; }
    .up-line { border-right: 4px solid #3fb950; }
    .down-line { border-right: 4px solid #f85149; }
    </style>
""", unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'home'
def go_to(page_name):
    st.session_state.page = page_name
    st.rerun()

# ================== DATA ENGINE ==================
@st.cache_data(ttl=300)
def fetch_egx_data(symbol=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    if scan_all:
        payload = {
            "filter": [{"left": "volume", "operation": "greater", "right": 50000}, {"left": "close", "operation": "greater", "right": 0.4}],
            "columns": ["name", "close", "RSI", "volume", "average_volume_10d_calc", "high", "low", "change", "description"],
            "sort": {"sortBy": "change", "sortOrder": "desc"}, "range": [0, 100]
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

# ================== ANALYSIS ENGINE (v11.8 Logic) ==================
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
        rsi_val = rsi if rsi else 0
        trend_ok = p > pp
        volume_ok = ratio > 1

        t_score = int(90 if rsi_val < 38 else 75 if rsi_val < 55 else 40)
        if not trend_ok: t_score -= 20
        if not volume_ok: t_score -= 15
        t_score = max(t_score, 0)

        s_score = int(85 if (ratio > 1.1 and 40 < rsi_val < 65) else 50)
        is_breakout = (p >= h * 0.992 and ratio > 1.2 and rsi_val > 52)
        is_gold = (ratio > 1.6 and 50 < rsi_val < 65 and chg > 0.5 and trend_ok)

        # ✅ إضافة تقييم الاختراق
        break_strength = "weak"
        if is_breakout and ratio > 1.5 and rsi_val < 65 and chg > 1:
            break_strength = "strong"

        if ratio < 0.7: vol_txt, vol_col = "🔴 سيولة غائبة", "#ff4b4b"
        elif ratio < 1.3: vol_txt, vol_col = "⚪ تداول هادئ", "#8b949e"
        else: vol_txt, vol_col = "🔥 زخم انفجاري", "#ffd700"

        if rsi_val > 72: rec, col = "🛑 تشبع شراء", "#ff4b4b"
        elif is_gold: rec, col = "💎 صفقة ذهبية", "#ffd700"
        elif t_score >= 75: rec, col = "🚀 شراء قوي", "#00ff00"
        else: rec, col = "⚖️ انتظار", "#58a6ff"

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "vol_txt": vol_txt, "vol_col": vol_col,
            "t_e": s1, "t_t": r1, "t_s": s1 * 0.98, "t_score": t_score,
            "s_e": p, "s_t": r2, "s_s": s2, "s_score": s_score,
            "rec": rec, "col": col, "is_gold": is_gold, "is_break": is_breakout,
            "break_strength": break_strength
        }
    except: return None

# ================== UI RENDERER ==================
def render_stock_ui(res, title=""):
    if not res: return
    if title: st.markdown(f"<div class='breakout-card'>{title}</div>", unsafe_allow_html=True)

    # ✅ عرض تقييم الاختراق
    if res['is_break']:
        if res['break_strength'] == "strong":
            st.success("🚀 اختراق حقيقي")
        else:
            st.warning("⚠️ اختراق ضعيف")

    st.markdown(f"""
        <div style='display: flex; justify-content: space-between; align-items: center;'>
            <span class='stock-header'>{res['name']} {res['desc'][:15]}</span>
            <span style='color:{res['col']}; font-weight:bold; border:1px solid {res['col']}; padding:2px 8px; border-radius:6px;'>{res['rec']}</span>
        </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("RSI", f"{res['rsi']:.1f}")
    with c3:
        st.markdown(f"<div class='vol-container'><div style='font-size:16px;font-weight:bold;'>{res['ratio']:.1f}x</div></div>", unsafe_allow_html=True)
    
    daily_entry_top = res['t_e'] * 1.008
    if res['p'] > daily_entry_top * 1.015:
        st.markdown(f"<div class='warning-box'>⚠️ مطاردة خطر! السعر عالي جداً عن منطقة الدخول ({daily_entry_top:.2f})</div>", unsafe_allow_html=True)
    
    st.divider()

    # ================== إضافة الربح والخسارة ==================
    st.markdown("---")
    st.subheader("💰 تحليل الصفقة")

    entry = res['t_e']
    target = res['t_t']
    stop = res['t_s']

    budget_calc = st.number_input("حجم الصفقة", value=20000, key=f"calc_{res['name']}_{res['p']}")

    profit = ((target - entry) / entry) * budget_calc
    loss = ((entry - stop) / entry) * budget_calc
    rr = profit / loss if loss != 0 else 0

    st.markdown(f"""
    <div class='plan-container'>
        <div class='plan-step up-line'>📈 ربح متوقع: <b>{profit:,.0f} ج</b></div>
        <div class='plan-step down-line'>📉 خسارة محتملة: <b>{loss:,.0f} ج</b></div>
        <div style='text-align:center;'>⚖️ Risk/Reward = <b>{rr:.2f}</b></div>
    </div>
    """, unsafe_allow_html=True)

# ================== MAIN ==================
st.title("🏹 EGX Sniper Elite v12.7")

sym = st.text_input("ادخل كود السهم")

if sym:
    data = fetch_egx_data(symbol=sym)
    if data:
        res = analyze_stock(data[0])
        render_stock_ui(res)
