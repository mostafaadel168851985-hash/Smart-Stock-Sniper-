import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="EGX Sniper Elite v14.8", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-size: 18px !important; font-weight: bold !important; margin-bottom: 10px; }
    .stock-header { font-size: 22px !important; font-weight: bold; color: #58a6ff; border-bottom: 2px solid #30363d; padding-bottom: 5px; }
    .score-tag { float: left; background: #238636; color: white; padding: 2px 12px; border-radius: 10px; font-size: 16px; margin-top: 5px; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 8px; padding: 5px !important; }
    .trend-pill { padding: 4px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; margin: 2px; display: inline-block; }
    .trend-up { background-color: rgba(63, 185, 80, 0.15); color: #3fb950; border: 1px solid #3fb950; }
    .trend-down { background-color: rgba(248, 81, 73, 0.15); color: #f85149; border: 1px solid #f85149; }
    .signal-pill { padding: 5px 15px; border-radius: 20px; font-weight: bold; display: inline-block; margin: 10px 0; }
    .buy-strong { background: #238636; color: white; border: 1px solid #3fb950; }
    .buy-caution { background: rgba(240, 139, 55, 0.2); color: #f08b37; border: 1px solid #f08b37; }
    .wait { background: #161b22; color: #8b949e; border: 1px solid #30363d; }
    .entry-card-new { background-color: #0d1117; border: 1px solid #3fb950; border-radius: 12px; padding: 15px; text-align: center; margin-bottom: 15px; border-top: 4px solid #3fb950; }
    .target-box { border: 2px solid #58a6ff; border-radius: 12px; padding: 15px; text-align: center; background: #0d1117; margin-top: 10px; }
    .plan-container { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-top: 15px; }
    .rr-tag { font-size: 16px; font-weight: bold; color: #58a6ff; background: rgba(88, 166, 255, 0.1); padding: 5px 12px; border-radius: 8px; border: 1px solid rgba(88, 166, 255, 0.3); }
    .rr-label { font-size: 14px; font-weight: bold; margin-right: 5px; padding: 2px 8px; border-radius: 5px; }
    .rr-excellent { background: #238636; color: white; }
    .rr-good { background: #2ea043; color: white; }
    .rr-fair { background: #d29922; color: white; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'home'

# ================== 🔥 HELPER FUNCTIONS ==================
def get_rr_status(rr):
    if rr >= 3: return "فرصة ذهبية 🏆", "rr-excellent"
    elif rr >= 2: return "صفقة ممتازة ✅", "rr-good"
    return "مقبول 👍", "rr-fair"

# ================== 🔥 DATA ENGINE ==================
@st.cache_data(ttl=300)
def fetch_egx_data(symbol=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    cols = ["name","close","RSI","volume","average_volume_10d_calc","high","low","change","description","SMA20","SMA50","SMA200"]
    if scan_all:
        payload = {"filter": [{"left": "volume", "operation": "greater", "right": 5000}], "columns": cols, "sort": {"sortBy": "change", "sortOrder": "desc"}, "range": [0, 150]}
    else:
        payload = {"filter": [{"left": "name", "operation": "match", "right": symbol.upper()}], "columns": cols, "range": [0, 1]}
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except: return []

# ================== 🔥 ANALYSIS ENGINE ==================
def analyze_stock(d_row):
    try:
        d = d_row.get('d', [])
        if not d or len(d) < 12: return None
        name, p, rsi, v, avg_v, h, l, chg, desc, sma20, sma50, sma200 = d
        if p is None: return None
        
        # 1. فلترة سيولة أقوى (تعديل 4)
        ratio = v / (avg_v or 1)
        if ratio < 0.8: return None 

        t_short = "صاعد" if (sma20 and p > sma20) else "هابط"
        t_med = "صاعد" if (sma50 and p > sma50) else "هابط"
        t_long = "صاعد" if (sma200 and p > sma200) else "هابط"
        
        if t_short == "صاعد" and t_med == "صاعد": signal, sig_cls = "شراء قوي 🔥", "buy-strong"
        elif t_short == "صاعد": signal, sig_cls = "شراء حذر ⚠️", "buy-caution"
        else: signal, sig_cls = "انتظار ⏳", "wait"

        pp = (p + (h or p) + (l or p)) / 3
        s1, r1 = (2 * pp) - (h or p), (2 * pp) - (l or p)
        s2 = pp - ((h or p) - (l or p))
        
        if p < r1:
            entry_min, entry_max = s1 * 0.995, s1 * 1.01
        elif p <= r1 * 1.02:
            entry_min, entry_max = r1, r1 * 1.01
        else:
            entry_min, entry_max = p * 0.99, p
        
        entry_price = (entry_min + entry_max) / 2
        
        # 2. حماية الوقف (تعديل 3)
        stop_loss = min(s2, entry_price * 0.97)

        # 3. هدف معتمد على السعر (تعديل 2)
        if p < r1:
            target = r1
        else:
            target = r1 + (r1 - s1)

        profit_per_share = target - entry_price
        loss_per_share = entry_price - stop_loss
        
        # 4. فلترة RR الصارم (تعديل 1 و 5)
        if loss_per_share <= 0: return None
        rr = round(profit_per_share / loss_per_share, 2)
        if rr < 1.5: return None 

        rr_label, rr_class = get_rr_status(rr)

        score = 0
        if t_med == "صاعد": score += 30
        if ratio > 1.2: score += 30
        if 40 < (rsi or 0) < 65: score += 20
        if rr > 2: score += 20

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi or 0, "chg": chg, "ratio": ratio,
            "score": score, "signal": signal, "sig_cls": sig_cls,
            "t_short": t_short, "t_med": t_med, "t_long": t_long,
            "is_gold": (ratio > 1.5 and 45 < (rsi or 0) < 65 and t_med == "صاعد"),
            "entry_range": f"{entry_min:.2f} - {entry_max:.2f}",
            "entry_price": entry_price, "stop_loss": stop_loss, "target": target,
            "rr": rr, "rr_label": rr_label, "rr_class": rr_class,
            "vol_icon": "🔥 انفجاري" if ratio > 1.5 else "⚪ هادئ"
        }
    except: return None

# ================== UI RENDERER ==================
def render_stock_ui(res):
    st.markdown(f"<div class='stock-header'>{res['name']} | {res['desc'][:20]} <span class='score-tag'>Score: {res['score']}</span></div>", unsafe_allow_html=True)
    st.markdown(f"<span class='signal-pill {res['sig_cls']}'>{res['signal']}</span> <span class='rr-tag'>RR: {res['rr']}</span> <span class='rr-label {res['rr_class']}'>{res['rr_label']}</span>", unsafe_allow_html=True)
    
    ts_c, tm_c, tl_c = ("trend-up" if res[t] == "صاعد" else "trend-down" for t in ['t_short', 't_med', 't_long'])
    st.markdown(f"<div><span class='trend-pill {ts_c}'>قصير: {res['t_short']}</span><span class='trend-pill {tm_c}'>متوسط: {res['t_med']}</span><span class='trend-pill {tl_c}'>طويل: {res['t_long']}</span></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("الزخم", res['vol_icon'], f"{res['ratio']:.1f}x")
    c3.metric("RSI", f"{res['rsi']:.1f}")

    st.markdown(f"<div class='entry-card-new'>🎯 <b>نطاق الدخول:</b> {res['entry_range']}<br>🛑 <b>وقف الخسارة الذكي:</b> {res['stop_loss']:.2f}</div><div class='target-box'>🏁 <b>الهدف (Market Based):</b> {res['target']:.2f}</div>", unsafe_allow_html=True)

# ================== NAVIGATION ==================
if st.session_state.page == 'home':
    st.title("🏹 Sniper Elite v14.8")
    for pg in ['analyze', 'scanner', 'breakout', 'gold', 'average']:
        if st.button(pg.replace('analyze','📡 تحليل سهم').replace('scanner','🔭 كشاف السوق').replace('breakout','🚀 الاختراقات').replace('gold','💎 قنص الذهب').replace('average','🧮 حاسبة المتوسطات')):
            st.session_state.page = pg; st.rerun()

elif st.session_state.page == 'analyze':
    if st.button("🏠"): st.session_state.page = 'home'; st.rerun()
    sym = st.text_input("رمز السهم").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data:
            res = analyze_stock(data[0])
            if res: render_stock_ui(res)
            else: st.warning("السهم لا يحقق شروط المخاطرة (RR < 1.5) أو السيولة ضعيفة")
        else: st.error("سهم غير موجود")

elif st.session_state.page == 'scanner':
    if st.button("🏠"): st.session_state.page = 'home'; st.rerun()
    raw_data = fetch_egx_data(scan_all=True)
    for r in raw_data:
        an = analyze_stock(r)
        if an and an['score'] >= 60:
            with st.expander(f"⭐ {an['score']} | {an['name']} | RR: {an['rr']}"): render_stock_ui(an)

elif st.session_state.page == 'breakout':
    if st.button("🏠"): st.session_state.page = 'home'; st.rerun()
    raw_data = fetch_egx_data(scan_all=True)
    for r in raw_data:
        an = analyze_stock(r)
        # 5. شرط الاختراق الأقوى (تعديل 6)
        if an and an['score'] > 70 and an['rr'] > 1.5 and an['t_med'] == "صاعد":
            with st.expander(f"🚀 اختراق مؤكد: {an['name']} | RR: {an['rr']}"): render_stock_ui(an)

elif st.session_state.page == 'gold':
    if st.button("🏠"): st.session_state.page = 'home'; st.rerun()
    raw_data = fetch_egx_data(scan_all=True)
    for r in raw_data:
        an = analyze_stock(r)
        if an and an['is_gold']:
            with st.expander(f"✨ ذهبي: {an['name']}"): render_stock_ui(an)

elif st.session_state.page == 'average':
    if st.button("🏠"): st.session_state.page = 'home'; st.rerun()
    st.header("🧮 حاسبة المتوسطات")
    c1, c2 = st.columns(2)
    p1, q1 = c1.number_input("سعر قديم", 0.0), c1.number_input("كمية قديمة", 0)
    p2, q2 = c2.number_input("سعر تعديل", 0.0), c2.number_input("كمية جديدة", 0)
    if (q1 + q2) > 0: st.info(f"المتوسط: {((p1 * q1) + (p2 * q2)) / (q1 + q2):.3f}")
