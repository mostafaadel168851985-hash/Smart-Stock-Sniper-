import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="EGX Sniper Pro v15.1", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-size: 18px !important; font-weight: bold !important; margin-bottom: 10px; }
    .stock-header { font-size: 24px !important; font-weight: bold; color: #58a6ff; border-bottom: 2px solid #30363d; margin-bottom: 15px; }
    .score-tag { float: left; background: #238636; color: white; padding: 2px 15px; border-radius: 10px; font-size: 18px; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 10px; padding: 10px !important; }
    .plan-card { background: #0d1117; border: 1px solid #3fb950; border-radius: 15px; padding: 20px; margin: 15px 0; border-top: 5px solid #3fb950; }
    .target-box { border: 2px solid #58a6ff; border-radius: 12px; padding: 15px; text-align: center; background: #0d1117; font-size: 20px; font-weight: bold; }
    .avg-section { background: #161b22; border: 1px solid #30363d; border-radius: 15px; padding: 25px; margin-top: 20px; }
    .result-text { font-size: 24px; font-weight: bold; color: #58a6ff; text-align: center; padding: 10px; background: rgba(88,166,255,0.1); border-radius: 10px; }
    .success-msg { color: #3fb950; font-weight: bold; font-size: 18px; margin-top: 10px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'home'

# ================== 🔥 DATA & ANALYSIS ==================
@st.cache_data(ttl=300)
def fetch_egx_data(symbol=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    cols = ["name","close","RSI","volume","average_volume_10d_calc","high","low","change","description","SMA20","SMA50","SMA200"]
    payload = {"filter": [{"left": "name", "operation": "match", "right": symbol.upper()}] if symbol else [], "columns": cols, "range": [0, 150] if scan_all else [0, 1]}
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except: return []

def analyze_stock(d_row):
    try:
        d = d_row.get('d', [])
        name, p, rsi, v, avg_v, h, l, chg, desc, sma20, sma50, sma200 = d
        p = p or 0
        ratio = v / (avg_v or 1)
        
        # تم إلغاء كل فلاتر المنع - التحليل سيظهر دائماً
        pp = (p + (h or p) + (l or p)) / 3
        s1, r1 = (2 * pp) - (h or p), (2 * pp) - (l or p)
        s2 = pp - ((h or p) - (l or p))
        
        entry_price = p
        stop_loss = min(s2, entry_price * 0.97) if s2 < entry_price else entry_price * 0.95
        target = r1 if p < r1 else r1 + (r1 - s1)
        
        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi or 0, "chg": chg or 0, "ratio": ratio,
            "entry_price": entry_price, "stop_loss": stop_loss, "target": target,
            "score": int((ratio * 15) + (rsi / 2 if rsi else 25))
        }
    except: return None

# ================== UI RENDERER ==================
def render_analysis(res):
    st.markdown(f"<div class='stock-header'>{res['name']} <span class='score-tag'>Score: {res['score']}</span></div>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("السعر الحالي", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("نشاط السيولة", f"{res['ratio']:.1f}x")
    c3.metric("RSI", f"{res['rsi']:.1f}")

    st.markdown(f"<div class='target-box'>🏁 الهدف المتوقع: {res['target']:.2f}</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='plan-card'>", unsafe_allow_html=True)
    st.subheader("💰 إدارة الصفقة")
    budget = st.number_input("ميزانية الاستثمار (جنية):", value=10000, step=1000)
    
    if res['p'] > 0:
        num_shares = int(budget / res['p'])
        profit = (res['target'] - res['p']) * num_shares
        loss = (res['p'] - res['stop_loss']) * num_shares
        
        col_p, col_l = st.columns(2)
        col_p.markdown(f"<div style='color:#3fb950; font-size:20px;'><b>✅ ربح محتمل:</b><br>{profit:,.2f} ج</div>", unsafe_allow_html=True)
        col_l.markdown(f"<div style='color:#f85149; font-size:20px;'><b>🛑 وقف خسارة:</b><br>{res['stop_loss']:.2f} ج<br>({loss:,.2f} ج)</div>", unsafe_allow_html=True)
        st.markdown(f"<br>💎 <b>عدد الأسهم:</b> {num_shares:,} سهم", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ================== NAVIGATION ==================
if st.session_state.page == 'home':
    st.title("🏹 Sniper Elite v15.1")
    if st.button("📡 تحليل سهم"): st.session_state.page = 'analyze'; st.rerun()
    if st.button("🧮 حاسبة المتوسطات"): st.session_state.page = 'average'; st.rerun()

elif st.session_state.page == 'analyze':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    sym = st.text_input("رمز السهم").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data:
            res = analyze_stock(data[0])
            if res: render_analysis(res)
        else: st.error("السهم غير موجود في قاعدة بيانات البورصة")

elif st.session_state.page == 'average':
    if st.button("🏠"): st.session_state.page = 'home'; st.rerun()
    st.markdown("## 🧮 حاسبة المتوسطات")
    
    with st.container():
        st.markdown("<div class='avg-section'>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.write("### الوضع الحالي")
            p_old = st.number_input("سعر الشراء القديم", value=0.0, format="%.2f", key="p_old")
            q_old = st.number_input("الكمية الحالية", value=0, key="q_old")
        with col2:
            st.write("### الشراء الجديد")
            p_new = st.number_input("سعر الشراء الجديد", value=0.0, format="%.2f", key="p_new")
            q_new = st.number_input("الكمية الجديدة", value=0, key="q_new")
        
        if q_old + q_new > 0:
            avg = ((p_old * q_old) + (p_new * q_new)) / (q_old + q_new)
            st.markdown(f"<div class='result-text'>📊 المتوسط الجديد: {avg:.3f} ج.م</div>", unsafe_allow_html=True)
        
        st.markdown("<br><hr>", unsafe_allow_html=True)
        st.subheader("🎯 الوصول لمتوسط مستهدف")
        st.write("احسب محتاج تشتري كم سهم عشان توصل لسعر متوسط معين")
        target_avg = st.number_input("المتوسط المستهدف (Target Average)", value=0.0, format="%.2f")
        
        if target_avg > 0 and p_new > 0 and q_old > 0:
            if (target_avg - p_new) != 0:
                needed = (q_old * (p_old - target_avg)) / (target_avg - p_new)
                if needed > 0:
                    st.markdown(f"<div class='success-msg'>✅ لخفض المتوسط لـ {target_avg:.2f}:<br>يجب شراء {int(needed):,} سهم إضافي على سعر {p_new:.2f}</div>", unsafe_allow_html=True)
                    st.info(f"💰 السيولة المطلوبة: {(needed * p_new):,.2f} ج")
                else:
                    st.warning("⚠️ المتوسط المستهدف غير منطقي بناءً على السعر الجديد.")
        st.markdown("</div>", unsafe_allow_html=True)
