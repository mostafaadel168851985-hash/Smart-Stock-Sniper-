import streamlit as st
import requests

# ================== CONFIG ==================
st.set_page_config(page_title="EGX Sniper PRO", layout="wide")

WATCHLIST = ["TMGH", "COMI", "ETEL", "SWDY", "EFID", "ATQA", "ALCN", "RMDA"]

COMPANIES = {
    "TMGH": "طلعت مصطفى", "COMI": "البنك التجاري الدولي", "ETEL": "المصرية للاتصالات",
    "SWDY": "السويدي إليكتريك", "EFID": "إيديتا", "ATQA": "مصر الوطنية للصلب - عتاقة",
    "ALCN": "الأسكندرية لتداول الحاويات", "RMDA": "العاشر من رمضان - راميدا"
}

# ================== DATA ENGINE ==================
@st.cache_data(ttl=300)
def get_real_data(symbol):
    try:
        url = "https://scanner.tradingview.com/egypt/scan"
        payload = {
            "symbols": {"tickers": [f"EGX:{symbol.upper()}"], "query": {"types": []}},
            "columns": ["close", "high", "low", "volume", "RSI", "change"]
        }
        r = requests.post(url, json=payload, timeout=10).json()
        if not r.get("data"): return None
        d = r["data"][0]["d"]
        return {
            "p": float(d[0]), "h": float(d[1]), "l": float(d[2]),
            "v": float(d[3]), "rsi": float(d[4]), "chg": float(d[5])
        }
    except: return None

# ================== SMART LOGIC ==================
def calculate_pivots(p, h, l):
    pp = (p + h + l) / 3
    s1, s2 = (2 * pp) - h, pp - (h - l)
    r1, r2 = (2 * pp) - l, pp + (h - l)
    return s1, s2, r1, r2

def get_liquidity_label(v, symbol):
    # مقياس سيولة ذكي: الأسهم الكبيرة محتاجة فوليوم أكبر لتصنيفها "عالية"
    big_caps = ["TMGH", "COMI", "SWDY", "ETEL"]
    limit = 5_000_000 if symbol in big_caps else 1_500_000
    
    if v > limit * 2: return "🔥 انفجارية (High Spike)", "green"
    if v > limit: return "✅ عالية (Good Flow)", "#58a6ff"
    if v > limit / 2: return "🟡 متوسطة", "orange"
    return "⚠️ ضعيفة", "red"

def get_dynamic_ai(p, s1, s2, r1, r2, rsi, v, symbol):
    # تخصيص التعليقات بناءً على حالة الـ RSI والسعر
    
    # 1. المضارب
    t_entry = round(s1 * 1.005, 2)
    if rsi < 30:
        t_cmnt = "🚨 فرصة ارتداد قوية جداً من منطقة تشبع بيعي"
        t_score = 95
    elif rsi > 70:
        t_cmnt = "🛑 خطر! السهم في منطقة تشبع شرائي، انتظر تصحيح"
        t_score = 30
    else:
        t_cmnt = f"🎯 قناص: الدخول الأفضل قرب الدعم {s1:.2f}"
        t_score = 70 if p > s1 else 50

    # 2. السوينج
    s_entry = round((s1 + r1) / 2, 2)
    if 40 <= rsi <= 60:
        s_cmnt = "📈 السهم في منطقة تجميع مثالية لبناء مركز مالي"
        s_score = 85
    else:
        s_cmnt = "🔁 انتظر استقرار السعر بين الدعم والمقاومة"
        s_score = 60

    # 3. المستثمر
    i_entry = round(s2, 2)
    i_cmnt = "🏦 استثمار: السهم جيد للمدى الطويل طالما فوق الدعم الرئيسي"
    i_score = 80 if p > s1 else 60

    return {
        "trader": {"score": t_score, "entry": t_entry, "sl": round(s1*0.98, 2), "comment": t_cmnt},
        "swing": {"score": s_score, "entry": s_entry, "sl": round(s2, 2), "comment": s_cmnt},
        "invest": {"score": i_score, "entry": i_entry, "sl": round(s2*0.95, 2), "comment": i_cmnt}
    }

# ================== REPORT UI ==================
def show_full_report(code, data):
    p, h, l, v, rsi = data['p'], data['h'], data['l'], data['v'], data['rsi']
    s1, s2, r1, r2 = calculate_pivots(p, h, l)
    liq_txt, liq_col = get_liquidity_label(v, code)
    ai = get_dynamic_ai(p, s1, s2, r1, r2, rsi, v, code)
    
    st.markdown(f"""
    <div style="border: 1px solid #464b5d; padding: 20px; border-radius: 10px; background-color: #161b22;">
        <h2 style="color: #58a6ff;">{code} - {COMPANIES.get(code,'')}</h2>
        <table style="width:100%; border-collapse: collapse;">
            <tr>
                <td>💰 السعر: <b>{p:.2f}</b></td>
                <td>📉 RSI: <b>{rsi:.1f}</b></td>
            </tr>
            <tr>
                <td>💧 السيولة: <span style="color:{liq_col};">{liq_txt}</span></td>
                <td>📊 فوليوم: {v:,.0f}</td>
            </tr>
        </table>
        <p style="margin-top:10px;">🧱 دعم: {s1:.2f} / {s2:.2f} | 🚧 مقاومة: {r1:.2f} / {r2:.2f}</p>
        <hr>
        <h4>🎯 تحليل المضارب (Trader) <span style="float:right;">{ai['trader']['score']}/100</span></h4>
        <p style="color:#8b949e;">{ai['trader']['comment']}</p>
        <p>دخول: <span style="color:#3fb950">{ai['trader']['entry']}</span> | وقف: <span style="color:#f85149">{ai['trader']['sl']}</span></p>
        
        <h4>🔁 تحليل السوينج (Swing) <span style="float:right;">{ai['swing']['score']}/100</span></h4>
        <p style="color:#8b949e;">{ai['swing']['comment']}</p>
        <p>دخول: <span style="color:#3fb950">{ai['swing']['entry']}</span> | وقف: <span style="color:#f85149">{ai['swing']['sl']}</span></p>
        
        <h4>🏦 تحليل المستثمر (Investor) <span style="float:right;">{ai['invest']['score']}/100</span></h4>
        <p style="color:#8b949e;">{ai['invest']['comment']}</p>
        <p>دخول: <span style="color:#3fb950">{ai['invest']['entry']}</span> | وقف: <span style="color:#f85149">{ai['invest']['sl']}</span></p>
        <hr>
        <p style="background-color: #30363d; padding: 15px; border-radius: 8px;">
        📝 <b>ملحوظة للمحبوس:</b> السهم حالياً يختبر قوة الدعم عند {s1:.2f}. لو "متعلق" بأسعار عالية، أفضل منطقة للتبريد (Average down) هي {s2:.2f} بشرط استقرار السوق. لا تتسرع في البيع بخسارة طالما RSI لم يكسر الـ 30 لأسفل.
        </p>
    </div>
    """, unsafe_allow_html=True)

# ================== APP MAIN ==================
st.title("🏹 EGX Sniper PRO")

tab1, tab2, tab3 = st.tabs(["📡 رادار الأسهم", "🛠️ إدخال يدوي", "🚨 الماسح الذكي"])

with tab1:
    code = st.text_input("كود السهم").upper().strip()
    if code:
        data = get_real_data(code)
        if data: show_full_report(code, data)
        else: st.error("بيانات السهم غير متوفرة")

with tab2:
    col1, col2 = st.columns(2)
    with col1:
        pm = st.number_input("السعر الحالي", format="%.2f")
        hm = st.number_input("أعلى سعر", format="%.2f")
    with col2:
        lm = st.number_input("أقل سعر", format="%.2f")
        vm = st.number_input("الفوليوم", step=1000)
    rsim = st.slider("RSI الحقيقي", 0, 100, 50)
    if pm > 0:
        manual_data = {"p": pm, "h": hm, "l": lm, "v": vm, "rsi": rsim}
        show_full_report("MANUAL", manual_data)

with tab3:
    if st.button("فحص قائمة المتابعة لبكرة 🔍"):
        cols = st.columns(2)
        for i, s in enumerate(WATCHLIST):
            d = get_real_data(s)
            if d:
                with cols[i % 2]:
                    s1, s2, r1, r2 = calculate_pivots(d['p'], d['h'], d['l'])
                    ai = get_dynamic_ai(d['p'], s1, s2, r1, r2, d['rsi'], d['v'], s)
                    max_score = max(ai['trader']['score'], ai['swing']['score'])
                    if max_score >= 75:
                        st.success(f"🚀 {s} | القوة: {max_score} | دخول: {ai['trader']['entry']}")
                    else:
                        st.info(f"⚪ {s} | القوة: {max_score} | مراقبة")
