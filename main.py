import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="EGX Sniper Elite v11.7", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-size: 18px !important; font-weight: bold !important; margin-bottom: 10px; }
    .stock-header { font-size: 18px !important; font-weight: bold; color: #58a6ff; }
    .price-callout { font-size: 16px !important; font-weight: bold; color: #3fb950; }
    .stoploss-callout { font-size: 14px !important; font-weight: bold; color: #f85149; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 8px; padding: 5px !important; }
    
    /* Average Cards Style */
    .avg-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-bottom: 12px; border-left: 5px solid #58a6ff; }
    .avg-title { color: #58a6ff; font-weight: bold; font-size: 16px; margin-bottom: 8px; display: block; }
    .avg-detail { color: #ffffff; font-size: 15px; margin: 4px 0; }
    .avg-res { color: #3fb950; font-weight: bold; font-size: 18px; }
    
    /* Warning & Breakout Style */
    .warning-box { background-color: #2e2a0b; border: 1px solid #ffd700; color: #ffd700; padding: 12px; border-radius: 10px; margin-top: 10px; font-weight: bold; border-left: 6px solid #ffd700; }
    .breakout-card { border: 2px solid #00ffcc !important; background-color: #0a1a1a !important; border-radius: 12px; padding: 10px; margin-bottom: 10px; }
    .gold-deal { border: 2px solid #ffd700 !important; background-color: #1c1c10 !important; border-radius: 12px; padding: 12px; margin-bottom: 15px; border-left: 8px solid #ffd700; }
    
    .vol-container { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 8px; text-align: center; }
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

# ================== ANALYSIS ==================
def analyze_stock(d_row, is_scan=False):
    try:
        d = d_row['d']
        if is_scan: name, p, rsi, v, avg_v, h, l, chg, desc = d
        else: p, h, l, v, rsi, avg_v, chg, desc = d; name = ""
        
        if p is None or h is None or l is None: return None
        pp = (p + h + l) / 3
        s1, r1 = (2 * pp) - h, (2 * pp) - l
        
        ratio = v / (avg_v or 1)
        rsi_val = rsi if rsi else 0
        
        # Check if price is too high (Chase Warning)
        is_chasing = p > (s1 * 1.03) # Warning if price is 3% above entry
        
        is_breakout = (p >= h * 0.992 and ratio > 1.2 and rsi_val > 52)
        is_gold = (ratio > 1.6 and 50 < rsi_val < 65 and chg > 0.5)

        if ratio < 0.7: vol_txt, vol_col = "🔴 غائبة", "#ff4b4b"
        elif ratio < 1.3: vol_txt, vol_col = "⚪ هادئ", "#8b949e"
        else: vol_txt, vol_col = "🔥 انفجاري", "#ffd700"

        rec, col = ("🛑 تشبع", "#ff4b4b") if rsi_val > 75 else ("💎 ذهبية", "#ffd700") if is_gold else ("🚀 شراء", "#00ff00") if rsi_val < 55 else ("⚖️ انتظار", "#58a6ff")

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "vol_txt": vol_txt, "vol_col": vol_col, "s1": s1, "r1": r1,
            "rec": rec, "col": col, "is_gold": is_gold, "is_break": is_breakout, "is_chasing": is_chasing
        }
    except: return None

# ================== UI RENDER ==================
def render_stock_ui(res, title=""):
    if not res: return
    if title: st.markdown(f"<div class='breakout-card'>{title}</div>", unsafe_allow_html=True)
    
    st.markdown(f"<div style='display: flex; justify-content: space-between;'><span class='stock-header'>{res['name']} {res['desc'][:15]}</span><span style='color:{res['col']}; font-weight:bold;'>{res['rec']}</span></div>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("RSI", f"{res['rsi']:.1f}")
    with c3: st.markdown(f"<div class='vol-container'><div style='color:#8b949e;font-size:10px;'>الزخم</div><div style='font-size:16px;font-weight:bold;'>{res['ratio']:.1f}x</div><div style='color:{res['vol_col']};font-size:10px;'>{res['vol_txt']}</div></div>", unsafe_allow_html=True)
    
    if res['is_chasing']:
        st.markdown(f"<div class='warning-box'>⚠️ السعر ({res['p']:.2f}) أعلى من الدخول ({res['s1']:.2f}). مطاردة خطر!</div>", unsafe_allow_html=True)
    else:
        st.success(f"✅ سعر دخول مثالي: {res['s1']:.2f}")

# ================== PAGES ==================
if st.session_state.page == 'home':
    st.title("🏹 EGX Sniper v11.7")
    if st.button("📡 تحليل سهم"): go_to('analyze')
    if st.button("🔭 كشاف السوق"): go_to('scanner')
    if st.button("🚀 رادار الاختراقات"): go_to('breakout')
    if st.button("🧮 مساعد المتوسطات"): go_to('average')
    if st.button("💎 قنص الذهب"): go_to('gold')

elif st.session_state.page == 'average':
    if st.button("⬅️ عودة"): go_to('home')
    st.subheader("🧮 مساعد متوسط التكلفة")
    col1, col2, col3 = st.columns(3)
    old_p = col1.number_input("قديم", value=0.0, format="%.2f")
    old_q = col2.number_input("كمية", value=0)
    new_p = col3.number_input("جديد", value=0.0, format="%.2f")
    
    if old_p > 0 and old_q > 0 and new_p > 0:
        st.markdown("### 💡 اقتراحات تعديل المتوسط:")
        total_cost_old = old_p * old_q
        
        configs = [
            ("تعديل بسيط (شراء نصف كميتك)", int(old_q * 0.5)),
            ("تعديل متوسط (مضاعفة الكمية 1:1)", old_q),
            ("تعديل جذري (شراء ضعف كميتك 2:1)", old_q * 2)
        ]
        
        for title, n_q in configs:
            n_cost = n_q * new_p
            new_avg = (total_cost_old + n_cost) / (old_q + n_q)
            drop_pct = ((old_p - new_avg) / old_p) * 100
            
            st.markdown(f"""
            <div class='avg-card'>
                <span class='avg-title'>{title}</span>
                <div class='avg-detail'>شراء عدد <b style='color:#3fb950;'>{n_q:,}</b> سهم بتكلفة <b style='color:#3fb950;'>{n_cost:,.2f} ج</b></div>
                <div class='avg-detail'>متوسط سعرك الجديد سيكون: <span class='avg-res'>{new_avg:.3f} ج</span></div>
                <div style='color:#8b949e; font-size:12px;'>% نسبة تخفيض التكلفة: {drop_pct:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)

        st.divider()
        target = st.number_input("المتوسط المستهدف الذي ترغب فيه؟", value=old_p * 0.95)
        if new_p < target < old_p:
            needed = (old_q * (old_p - target)) / (target - new_p)
            st.info(f"🎯 للوصول لمتوسط {target:.3f}: اشتري {int(needed):,} سهم جديد.")

elif st.session_state.page == 'breakout':
    if st.button("⬅️ عودة"): go_to('home')
    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r, True)) and an['is_break']:
            render_stock_ui(an, f"🚀 {an['name']} : اختراق حقيقي")

elif st.session_state.page == 'analyze':
    if st.button("⬅️ عودة"): go_to('home')
    sym = st.text_input("كود السهم").upper()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data: render_stock_ui(analyze_stock(data[0]))

elif st.session_state.page == 'scanner':
    if st.button("⬅️ عودة"): go_to('home')
    if st.button("بدء الفحص الشامل"):
        for r in fetch_egx_data(scan_all=True):
            if (an := analyze_stock(r, True)) and an['rsi'] < 60:
                with st.expander(f"📈 {an['name']} | Price: {an['p']}"): render_stock_ui(an)

elif st.session_state.page == 'gold':
    if st.button("⬅️ عودة"): go_to('home')
    found = False
    for r in fetch_egx_data(scan_all=True):
        if (an := analyze_stock(r, True)) and an['is_gold']:
            found = True
            st.markdown(f"<div class='gold-deal'>💎 فرصة ذهبية: {an['name']}</div>", unsafe_allow_html=True)
            render_stock_ui(an)
    if not found: st.warning("لا يوجد فرص ذهبية حالياً.")
