import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="EGX Sniper Pro v15.2", layout="wide")

st.markdown("""
    <style>
    /* تحسين شكل الأزرار */
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; font-size: 18px !important; font-weight: bold !important; margin-bottom: 12px; transition: 0.3s; }
    .stButton>button:hover { background-color: #2188ff; color: white; border-color: #2188ff; }
    
    /* الهيدر والعناصر الرئيسية */
    .stock-header { font-size: 26px !important; font-weight: bold; color: #58a6ff; border-bottom: 2px solid #30363d; margin-bottom: 15px; padding-bottom: 10px; }
    .score-tag { float: left; background: #238636; color: white; padding: 4px 18px; border-radius: 12px; font-size: 18px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
    
    /* كروت البيانات */
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 12px; padding: 15px !important; }
    .plan-card { background: #0d1117; border: 1px solid #3fb950; border-radius: 15px; padding: 25px; margin: 15px 0; border-top: 6px solid #3fb950; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
    .target-box { border: 2px solid #58a6ff; border-radius: 15px; padding: 20px; text-align: center; background: #161b22; font-size: 22px; font-weight: bold; color: #58a6ff; margin: 10px 0; }
    
    /* قسم الحاسبة */
    .avg-section { background: #1c2128; border: 1px solid #444c56; border-radius: 20px; padding: 30px; margin-top: 20px; }
    .avg-title { text-align: center; color: #adbac7; font-size: 20px; margin-bottom: 20px; }
    .result-text { font-size: 28px; font-weight: 900; color: #3fb950; text-align: center; padding: 15px; background: rgba(63,185,80,0.1); border-radius: 12px; border: 1px solid #3fb950; }
    .target-needed { font-size: 20px; font-weight: bold; color: #f08b37; text-align: center; margin-top: 15px; padding: 10px; border: 1px dashed #f08b37; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'home'

# ================== 🔥 DATA ENGINE ==================
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
        h = h or p
        l = l or p
        ratio = v / (avg_v or 1)
        
        # حسابات فنية مبسطة للخطة
        pp = (p + h + l) / 3
        s1, r1 = (2 * pp) - h, (2 * pp) - l
        s2 = pp - (h - l)
        
        # تحديد الأهداف ووقف الخسارة
        stop_loss = min(s2, p * 0.97) if s2 < p else p * 0.95
        target = r1 if p < r1 else r1 + (r1 - s1)
        
        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi or 0, "chg": chg or 0, "ratio": ratio,
            "stop_loss": stop_loss, "target": target,
            "score": int((min(ratio, 2) * 25) + (rsi / 2 if rsi else 25))
        }
    except: return None

# ================== UI RENDERER ==================
def render_analysis(res):
    st.markdown(f"<div class='stock-header'>{res['name']} <span class='score-tag'>Score: {res['score']}</span></div>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("السعر الحالي", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("السيولة النسبية", f"{res['ratio']:.1f}x")
    c3.metric("RSI (الزخم)", f"{res['rsi']:.1f}")

    st.markdown(f"<div class='target-box'>🎯 الهدف المتوقع: {res['target']:.2f} ج.م</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='plan-card'>", unsafe_allow_html=True)
    st.subheader("💰 إدارة الصفقة (خطة المحفظة)")
    
    budget = st.number_input("الميزانية المخصصة للسهم (جنية):", value=10000, step=1000)
    
    if res['p'] > 0:
        shares = int(budget / res['p'])
        profit_total = (res['target'] - res['p']) * shares
        loss_total = (res['p'] - res['stop_loss']) * shares
        
        cp, cl = st.columns(2)
        cp.markdown(f"<div style='color:#3fb950; font-size:22px;'><b>📈 ربح محتمل:</b><br>{profit_total:,.2f} ج</div>", unsafe_allow_html=True)
        cl.markdown(f"<div style='color:#f85149; font-size:22px;'><b>📉 وقف خسارة:</b><br>{res['stop_loss']:.2f} ج<br>({loss_total:,.2f} ج)</div>", unsafe_allow_html=True)
        
        st.markdown(f"<hr style='border-color:#30363d;'><h4 style='text-align:center;'>💎 عدد الأسهم المقترح: {shares:,} سهم</h4>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ================== NAVIGATION ==================
if st.session_state.page == 'home':
    st.title("🏹 Sniper Pro v15.2")
    st.info("مرحباً بك! اختر الخدمة المطلوبة لبدء التحليل.")
    if st.button("🔍 تحليل فوري لأي سهم"): st.session_state.page = 'analyze'; st.rerun()
    if st.button("🧮 حاسبة التعديل والمتوسطات"): st.session_state.page = 'average'; st.rerun()

elif st.session_state.page == 'analyze':
    if st.button("🏠 الرجوع للرئيسية"): st.session_state.page = 'home'; st.rerun()
    sym = st.text_input("ادخل رمز السهم (مثال: ATQA, NCCW)").upper().strip()
    if sym:
        with st.spinner('جاري جلب البيانات من البورصة...'):
            data = fetch_egx_data(symbol=sym)
            if data:
                res = analyze_stock(data[0])
                if res: render_analysis(res)
            else: st.error("عفواً، لم نجد بيانات لهذا الرمز. تأكد من كتابة الرمز بشكل صحيح.")

elif st.session_state.page == 'average':
    if st.button("🏠 الرجوع للرئيسية"): st.session_state.page = 'home'; st.rerun()
    st.markdown("<h2 style='text-align:center;'>🧮 حاسبة متوسط التكلفة الذكية</h2>", unsafe_allow_html=True)
    
    with st.container():
        st.markdown("<div class='avg-section'>", unsafe_allow_html=True)
        
        st.markdown("<p class='avg-title'>📉 بيانات المركز الحالي</p>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        p_old = c1.number_input("سعر الشراء (القديم)", value=0.0, format="%.2f", step=0.01)
        q_old = c2.number_input("الكمية الحالية", value=0, step=1)
        
        st.markdown("<p class='avg-title'>🛒 بيانات الشراء الجديد (التبريد)</p>", unsafe_allow_html=True)
        c3, c4 = st.columns(2)
        p_new = c3.number_input("السعر الحالي / الجديد", value=0.0, format="%.2f", step=0.01)
        q_new = c4.number_input("الكمية الجديدة", value=0, step=1)
        
        total_q = q_old + q_new
        if total_q > 0:
            new_avg = ((p_old * q_old) + (p_new * q_new)) / total_q
            st.markdown(f"<div class='result-text'>📊 المتوسط الجديد: {new_avg:.3f} ج.م</div>", unsafe_allow_html=True)
        
        st.markdown("<br><hr style='border-color:#444c56;'><br>", unsafe_allow_html=True)
        
        # --- قسم المتوسط المستهدف ---
        st.markdown("<p class='avg-title' style='color:#f08b37;'>🎯 الوصول لمتوسط محدد</p>", unsafe_allow_html=True)
        target_avg = st.number_input("اكتب المتوسط اللي عايز توصله (مثلاً 8.5)", value=0.0, format="%.2f")
        
        if target_avg > 0 and p_new > 0 and q_old > 0:
            if (target_avg > p_new and target_avg < p_old) or (target_avg < p_new and target_avg > p_old):
                needed_shares = (q_old * (p_old - target_avg)) / (target_avg - p_new)
                if needed_shares > 0:
                    st.markdown(f"<div class='target-needed'>✅ محتاج تشتري <b>{int(needed_shares):,}</b> سهم على سعر <b>{p_new:.2f}</b> عشان متوسطك ينزل لـ <b>{target_avg:.2f}</b></div>", unsafe_allow_html=True)
                    st.info(f"💰 السيولة المطلوبة لتحقيق هذا الهدف: {(needed_shares * p_new):,.2f} ج.م")
                else:
                    st.warning("⚠️ الحسابات تشير إلى أنك لا تحتاج لشراء مزيد من الأسهم للوصول لهذا الرقم.")
            else:
                st.warning("⚠️ تأكد أن المتوسط المستهدف يقع بين السعر القديم والسعر الجديد.")
        
        st.markdown("</div>", unsafe_allow_html=True)
