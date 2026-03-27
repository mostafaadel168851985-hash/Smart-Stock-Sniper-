import streamlit as st
import requests

# ================== CONFIG ==================
st.set_page_config(page_title="EGX Sniper PRO", layout="wide")

# قائمة المتابعة الخاصة بك
WATCHLIST = ["TMGH", "COMI", "ETEL", "SWDY", "EFID", "ATQA", "ALCN", "RMDA"]

COMPANIES = {
    "TMGH": "طلعت مصطفى", "COMI": "البنك التجاري الدولي", "ETEL": "المصرية للاتصالات",
    "SWDY": "السويدي إليكتريك", "EFID": "إيديتا", "ATQA": "مصر الوطنية للصلب - عتاقة",
    "ALCN": "الأسكندرية لتداول الحاويات", "RMDA": "العاشر من رمضان - راميدا"
}

# ================== DATA ENGINE (TRADINGVIEW REAL-TIME) ==================
@st.cache_data(ttl=300) # كاش لمدة 5 دقائق للحفاظ على السرعة
def get_real_data(symbol):
    try:
        url = "https://scanner.tradingview.com/egypt/scan"
        payload = {
            "symbols": {"tickers": [f"EGX:{symbol.upper()}"], "query": {"types": []}},
            "columns": ["close", "high", "low", "volume", "RSI", "Pivot.M.Classic.S1", "Pivot.M.Classic.R1"]
        }
        r = requests.post(url, json=payload, timeout=10).json()
        if not r.get("data"): return None
        d = r["data"][0]["d"]
        return {
            "p": float(d[0]), "h": float(d[1]), "l": float(d[2]),
            "v": float(d[3]), "rsi": float(d[4]), "s1": float(d[5]), "r1": float(d[6])
        }
    except:
        return None

# ================== INDICATORS & LOGIC ==================
def calculate_pivots(p, h, l):
    pp = (p + h + l) / 3
    s1 = (2 * pp) - h
    s2 = pp - (h - l)
    r1 = (2 * pp) - l
    r2 = pp + (h - l)
    return s1, s2, r1, r2

def get_ai_analysis(p, s1, s2, r1, r2, rsi, v):
    # 1. تحليل المضارب (قصير جداً - لحظي)
    trader_score = 50
    if rsi < 35: trader_score += 30
    if abs(p - s1)/s1 < 0.02: trader_score += 20
    trader_entry = round(s1 + 0.02, 2)
    trader_sl = round(s1 - (s1 * 0.02), 2)
    
    # 2. تحليل السوينج (أيام لأسابيع)
    swing_score = 60
    if 40 <= rsi <= 60: swing_score += 20
    if v > 1_000_000: swing_score += 10
    swing_entry = round((s1 + r1) / 2, 2)
    swing_sl = round(s2, 2)

    # 3. تحليل المستثمر (طويل الأمد)
    invest_score = 70 if p > s1 else 50
    if rsi < 50: invest_score += 10
    invest_entry = round(s2, 2)
    invest_sl = round(s2 * 0.95, 2)

    return {
        "trader": {"score": min(trader_score, 100), "entry": trader_entry, "sl": trader_sl, "comment": "🎯 قناص: دخول قرب الدعم لارتداد سريع"},
        "swing": {"score": min(swing_score, 100), "entry": swing_entry, "sl": swing_sl, "comment": "🔁 موجة: انتظار تأكيد الاختراق للفوليوم"},
        "invest": {"score": min(invest_score, 100), "entry": invest_entry, "sl": invest_sl, "comment": "🏦 استثمار: تجميع هادئ عند مناطق الدعم القوية"}
    }

# ================== REPORT UI ==================
def show_full_report(code, data):
    p, h, l, v, rsi = data['p'], data['h'], data['l'], data['v'], data['rsi']
    s1, s2, r1, r2 = calculate_pivots(p, h, l)
    ai = get_ai_analysis(p, s1, s2, r1, r2, rsi, v)
    
    # التوصية النهائية
    final_rec = "مراقبة"
    if ai['trader']['score'] > 80 or ai['swing']['score'] > 80: final_rec = "🔥 شراء مؤكد"
    elif rsi > 75: final_rec = "⚠️ تشبع شراء (بيع)"

    st.markdown(f"""
    <div style="border: 1px solid #464b5d; padding: 20px; border-radius: 10px; background-color: #161b22;">
        <h2 style="color: #58a6ff;">{code} - {COMPANIES.get(code,'')}</h2>
        <p>💰 السعر: <b>{p:.2f}</b> | 📉 RSI: <b>{rsi:.1f}</b> | 💧 فوليوم: <b>{v:,.0f}</b></p>
        <p>🧱 دعم: {s1:.2f} / {s2:.2f} | 🚧 مقاومة: {r1:.2f} / {r2:.2f}</p>
        <hr>
        <h4>🎯 تحليل المضارب (Trader)</h4>
        <b>القوة: {ai['trader']['score']}/100</b><br>
        {ai['trader']['comment']}<br>
        دخول: <span style="color:#238636">{ai['trader']['entry']}</span> | وقف: <span style="color:#da3633">{ai['trader']['sl']}</span>
        <br><br>
        <h4>🔁 تحليل السوينج (Swing)</h4>
        <b>القوة: {ai['swing']['score']}/100</b><br>
        {ai['swing']['comment']}<br>
        دخول: <span style="color:#238636">{ai['swing']['entry']}</span> | وقف: <span style="color:#da3633">{ai['swing']['sl']}</span>
        <br><br>
        <h4>🏦 تحليل المستثمر (Investor)</h4>
        <b>القوة: {ai['invest']['score']}/100</b><br>
        {ai['invest']['comment']}<br>
        دخول: <span style="color:#238636">{ai['invest']['entry']}</span> | وقف: <span style="color:#da3633">{ai['invest']['sl']}</span>
        <hr>
        <h3>📌 التوصية: {final_rec}</h3>
        <p style="background-color: #30363d; padding: 10px; border-radius: 5px;">
        📝 <b>ملحوظة للمحبوس:</b> السهم حالياً يختبر منطقة {s1:.2f}. لو معاك السهم لا تبيع تحت {s2:.2f}. التعديل الأفضل يكون عند ارتداد الـ RSI من مستويات الـ 30.
        </p>
    </div>
    """, unsafe_allow_html=True)

# ================== MAIN APP ==================
st.title("🏹 EGX Sniper PRO")
st.caption("التحليل مبني على بيانات TradingView الحقيقية ومعادلات RSI 14")

tab1, tab2, tab3 = st.tabs(["📡 رادار الأسهم", "🛠️ إدخال يدوي", "🚨 الماسح الذكي"])

with tab1:
    code = st.text_input("كود السهم (مثال: ATQA)").upper().strip()
    if code:
        with st.spinner('جاري سحب البيانات الحقيقية...'):
            data = get_real_data(code)
            if data:
                show_full_report(code, data)
            else:
                st.error("بيانات السهم غير متوفرة حالياً")

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
        for s in WATCHLIST:
            d = get_real_data(s)
            if d:
                s1, _, r1, _ = calculate_pivots(d['p'], d['h'], d['l'])
                scores = get_ai_analysis(d['p'], s1, 0, r1, 0, d['rsi'], d['v'])
                if scores['trader']['score'] > 70 or scores['swing']['score'] > 70:
                    st.success(f"🚀 {s}: فرصة دخول جيدة | RSI: {d['rsi']:.1f} | القوة: {max(scores['trader']['score'], scores['swing']['score'])}")

