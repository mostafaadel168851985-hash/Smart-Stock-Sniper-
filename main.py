import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="EGX Sniper Elite v13.4", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-weight: bold; }
    .stock-header { font-size: 20px; font-weight: bold; color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 10px; }
    .entry-card { background-color: #0d1117; border: 1px solid #3fb950; border-radius: 12px; padding: 15px; text-align: center; }
    .error-box { padding: 20px; background-color: rgba(248, 81, 73, 0.1); border: 1px solid #f85149; border-radius: 10px; color: #f85149; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'home'
def go_to(p): 
    st.session_state.page = p
    st.rerun()

# ================== 🔥 DATA ENGINE ==================
@st.cache_data(ttl=300)
def fetch_egx_data(symbol=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    cols = ["name","close","RSI","volume","average_volume_10d_calc","high","low","change","description","SMA20","SMA50","SMA200","high_1M","low_1M","Price_52_Week_High","Price_52_Week_Low","Perf.W","Perf.M"]
    
    if scan_all:
        payload = {
            "filter": [{"left": "volume", "operation": "greater", "right": 5000}],
            "columns": cols, "sort": {"sortBy": "change", "sortOrder": "desc"}, "range": [0, 200]
        }
    else:
        # البحث بمرونة أكتر عن السهم
        payload = {
            "filter": [{"left": "name", "operation": "match", "right": symbol.upper()}],
            "columns": cols, "range": [0, 1]
        }
        
    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code == 200:
            data = r.json().get("data", [])
            return data
        return []
    except:
        return []

# ================== 🔥 ANALYSIS ENGINE ==================
def analyze_stock(d_row):
    try:
        if not d_row or 'd' not in d_row: return None
        d = d_row['d']
        
        # التأكد من عدد العناصر (18 عمود)
        if len(d) < 18: return None
        
        name, p, rsi, v, avg_v, h, l, chg, desc, sma20, sma50, sma200, h1m, l1m, h52, l52, pw, pm = d
        
        if p is None: return None
        
        # حسابات فنية
        pp = (p + (h or p) + (l or p)) / 3
        s1, r1 = (2 * pp) - (h or p), (2 * pp) - (l or p)
        s2 = pp - ((h or p) - (l or p))
        
        ratio = v / (avg_v or 1)
        rsi_val = rsi or 0
        
        # شروط الذهب والاختراق
        is_gold = (ratio > 1.4 and 45 < rsi_val < 65 and sma50 and p > sma50)
        at_high = (h52 and p >= h52 * 0.98)
        
        # أهداف ودخول
        entry_avg = p
        risk = max(entry_avg - s2, 0.01)
        reward = max(r1 - entry_avg, 0.01)
        rr = round(reward / risk, 2)

        return {
            "name": name, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "s1": s1, "s2": s2, "r1": r1, "is_gold": is_gold, "at_high": at_high,
            "desc": desc, "rr": rr, "pw": pw or 0, "pm": pm or 0
        }
    except:
        return None

# ================== UI ==================
if st.session_state.page == 'home':
    st.title("🏹 Sniper Elite v13.4")
    c1, c2 = st.columns(2)
    if c1.button("📡 تحليل سهم"): go_to('analyze')
    if c2.button("🔭 كشاف السوق"): go_to('scanner')
    if c1.button("💎 قنص الذهب"): go_to('gold')
    if c2.button("🚀 الاختراقات"): go_to('breakout')

elif st.session_state.page == 'analyze':
    if st.button("🏠"): go_to('home')
    sym = st.text_input("اكتب رمز السهم (مثلاً ATQA)").strip()
    if sym:
        with st.spinner('جاري البحث...'):
            data = fetch_egx_data(symbol=sym)
            if data:
                res = analyze_stock(data[0])
                if res:
                    st.markdown(f"<div class='stock-header'>{res['name']} - {res['desc']}</div>", unsafe_allow_html=True)
                    col1, col2, col3 = st.columns(3)
                    col1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
                    col2.metric("RSI", f"{res['rsi']:.1f}")
                    col3.metric("الزخم", f"{res['ratio']:.1f}x")
                    
                    st.markdown(f"""
                    <div class='entry-card'>
                    🎯 الدخول: {res['p']:.2f}<br>
                    🛑 الوقف: {res['s2']:.2f}<br>
                    🏁 الهدف: {res['r1']:.2f}<br>
                    ⚖️ نسبة RR: 1:{res['rr']}
                    </div>
                    """, unsafe_allow_html=True)
                else: st.warning("بيانات السهم غير مكتملة حالياً")
            else: st.error("لم يتم العثور على السهم. تأكد من الرمز الصحيح")

elif st.session_state.page == 'scanner':
    if st.button("🏠"): go_to('home')
    if st.button("🔍 ابدأ الفحص"):
        data = fetch_egx_data(scan_all=True)
        if data:
            for r in data:
                an = analyze_stock(r)
                if an and an['p'] > 0.5:
                    with st.expander(f"{an['name']} | سعر: {an['p']} | زخم: {an['ratio']:.1f}"):
                        st.write(f"الهدف: {an['r1']:.2f} | الوقف: {an['s2']:.2f}")
        else: st.write("لا توجد بيانات حالياً")

elif st.session_state.page == 'gold':
    if st.button("🏠"): go_to('home')
    data = fetch_egx_data(scan_all=True)
    found = False
    if data:
        for r in data:
            an = analyze_stock(r)
            if an and an['is_gold']:
                st.success(f"💎 فرصة ذهبية: {an['name']}")
                st.write(f"السعر: {an['p']} | RSI: {an['rsi']:.1f}")
                found = True
    if not found: st.info("لا توجد أسهم ذهبية مطابقة للشروط الآن")

elif st.session_state.page == 'breakout':
    if st.button("🏠"): go_to('home')
    data = fetch_egx_data(scan_all=True)
    if data:
        for r in data:
            an = analyze_stock(r)
            if an and an['at_high']:
                st.info(f"🚀 اختراق قمة: {an['name']}")
                st.write(f"السعر الحالي: {an['p']}")
