import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="EGX Master Sniper v13.8", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-weight: bold; }
    .stock-header { font-size: 22px !important; font-weight: bold; color: #58a6ff; border-bottom: 2px solid #30363d; padding-bottom: 10px; }
    .score-tag { float: left; background: #238636; color: white; padding: 2px 10px; border-radius: 10px; font-size: 16px; }
    .entry-box { background-color: #0d1117; border: 1px solid #3fb950; border-radius: 12px; padding: 15px; text-align: center; margin: 10px 0; }
    .signal-pill { padding: 5px 15px; border-radius: 20px; font-weight: bold; display: inline-block; margin: 5px; }
    .buy { background: rgba(63, 185, 80, 0.2); color: #3fb950; border: 1px solid #3fb950; }
    .wait { background: rgba(240, 139, 55, 0.2); color: #f08b37; border: 1px solid #f08b37; }
    .sell { background: rgba(248, 81, 73, 0.2); color: #f85149; border: 1px solid #f85149; }
    .avg-card { background: #1c2128; border-right: 5px solid #58a6ff; padding: 15px; border-radius: 8px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'home'
def go_to(p): 
    st.session_state.page = p
    st.rerun()

# ================== 🔥 DATA & ANALYSIS ==================
@st.cache_data(ttl=300)
def fetch_egx_data(symbol=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    cols = ["name","close","RSI","volume","average_volume_10d_calc","high","low","change","description","SMA20","SMA50","SMA200"]
    if scan_all:
        payload = {"filter": [{"left": "volume", "operation": "greater", "right": 5000}], "columns": cols, "sort": {"sortBy": "change", "sortOrder": "desc"}, "range": [0, 100]}
    else:
        payload = {"filter": [{"left": "name", "operation": "match", "right": symbol.upper()}], "columns": cols, "range": [0, 1]}
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except: return []

def analyze_stock(d_row):
    try:
        d = d_row['d']
        name, p, rsi, v, avg_v, h, l, chg, desc, sma20, sma50, sma200 = d
        
        # 1. الاتجاهات والإشارات
        t_short = "صاعد" if (sma20 and p > sma20) else "هابط"
        t_med = "صاعد" if (sma50 and p > sma50) else "هابط"
        
        # 2. إشارة السهم
        if rsi > 75: signal, sig_cls = "تشبع شراء ⚠️", "sell"
        elif rsi < 30: signal, sig_cls = "مبالغ في بيعه 📡", "buy"
        elif t_short == "صاعد" and p > (sma20 or 0): signal, sig_cls = "شراء ✅", "buy"
        else: signal, sig_cls = "انتظار ⏳", "wait"
        
        # 3. الزخم والسكور
        ratio = v / (avg_v or 1)
        vol_icon = "🔥 انفجاري" if ratio > 1.5 else "⚪ هادئ"
        
        score = 0
        if t_med == "صاعد": score += 30
        if ratio > 1.2: score += 30
        if 40 < (rsi or 0) < 60: score += 20
        if chg > 0: score += 20

        # 4. Range الدخول والأهداف
        pp = (p + (h or p) + (l or p)) / 3
        r1, s1 = (2 * pp) - (l or p), (2 * pp) - (h or p)
        s2 = pp - ((h or p) - (l or p))
        
        entry_min, entry_max = s1 * 0.99, s1 * 1.01
        if p > r1: entry_min, entry_max = r1, r1 * 1.01 # حالة الاختراق
        
        # 5. مؤشر الصفقة
        risk = p - s2 if p > s2 else 0.1
        reward = r1 - p if r1 > p else 0.1
        rr = round(reward/risk, 2)
        rr_status = "قوية 🔥" if rr > 2 else "مقبولة 👍" if rr > 1 else "ضعيفة ⚠️"

        return {
            "name": name, "p": p, "rsi": rsi or 0, "chg": chg, "ratio": ratio,
            "vol_icon": vol_icon, "score": score, "signal": signal, "sig_cls": sig_cls,
            "entry_range": f"{entry_min:.2f} - {entry_max:.2f}",
            "stop": s2, "target": r1, "rr_status": rr_status, "desc": desc
        }
    except: return None

# ================== UI ==================
if st.session_state.page == 'home':
    st.title("🎯 EGX Master Sniper v13.8")
    c1, c2 = st.columns(2)
    if c1.button("📡 تحليل سهم"): go_to('analyze')
    if c2.button("🔭 كشاف السوق"): go_to('scanner')
    if st.button("🧮 مساعد المتوسطات والخطة"): go_to('average')

elif st.session_state.page == 'analyze':
    if st.button("🏠"): go_to('home')
    sym = st.text_input("رمز السهم").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data:
            res = analyze_stock(data[0])
            st.markdown(f"<div class='stock-header'>{res['name']} <span class='score-tag'>Score: {res['score']}</span></div>", unsafe_allow_html=True)
            st.markdown(f"<span class='signal-pill {res['sig_cls']}'>{res['signal']}</span>", unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
            c2.metric("الزخم", res['vol_icon'], f"{res['ratio']:.1f}x")
            c3.metric("RSI", f"{res['rsi']:.1f}")

            st.markdown(f"""
            <div class='entry-box'>
                <b>🎯 نطاق الدخول الذكي:</b> {res['entry_range']}<br>
                <b>🛑 وقف الخسارة:</b> {res['stop']:.2f}<br>
                <b>🏁 الهدف الأول:</b> {res['target']:.2f}<br>
                <b>💎 مؤشر الصفقة:</b> {res['rr_status']}
            </div>
            """, unsafe_allow_html=True)
        else: st.error("لم يتم العثور على السهم")

elif st.session_state.page == 'scanner':
    if st.button("🏠"): go_to('home')
    if st.button("🔍 فحص الفرص"):
        data = fetch_egx_data(scan_all=True)
        for r in data:
            an = analyze_stock(r)
            if an and an['score'] >= 50:
                with st.expander(f"⭐ {an['score']} | {an['name']} | {an['signal']}"):
                    st.write(f"الدخول: {an['entry_range']} | الهدف: {an['target']:.2f}")

elif st.session_state.page == 'average':
    if st.button("🏠"): go_to('home')
    st.header("🧮 حاسبة التعديل والسيولة")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🛠️ الوصول للمتوسط المستهدف")
        curr_p = st.number_input("سعر السهم الحالي في المحفظة", value=0.0)
        curr_q = st.number_input("الكمية الحالية", value=0)
        market_p = st.number_input("سعر السهم الآن في السوق", value=0.0)
        target_avg = st.number_input("المتوسط الذي تريد الوصول إليه", value=0.0)
        
        if curr_p > 0 and market_p < target_avg < curr_p:
            # معادلة حساب الكمية المطلوبة للوصول لمتوسط معين
            # Target_Avg = (Curr_P*Curr_Q + Market_P*Required_Q) / (Curr_Q + Required_Q)
            req_q = (curr_q * (curr_p - target_avg)) / (target_avg - market_p)
            st.markdown(f"""
            <div class='avg-card'>
                ✅ للوصول لمتوسط <b>{target_avg:.2f}</b>:<br>
                يجب شراء: <b>{int(req_q)} سهم</b><br>
                بتكلفة تقريبية: <b>{req_q * market_p:,.0f} جنيه</b>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        st.subheader("💰 توزيع مبلغ معين")
        total_cash = st.number_input("المبلغ المتاح للشراء (جنيه)", value=10000)
        buy_p = st.number_input("سعر الشراء المتوقع", value=1.0)
        if total_cash > 0 and buy_p > 0:
            total_q = total_cash / buy_p
            st.markdown(f"""
            <div class='avg-card'>
                🔹 تشتري بالمبلغ ده: <b>{int(total_q)} سهم</b><br>
                📍 دخول أول (50%): {int(total_q*0.5)} سهم<br>
                📍 تدعيم (50%): {int(total_q*0.5)} سهم
            </div>
            """, unsafe_allow_html=True)
