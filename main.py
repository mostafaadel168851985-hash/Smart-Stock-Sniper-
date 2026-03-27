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

# ================== DATA ENGINE (RSI 14 FIX) ==================
@st.cache_data(ttl=120)
def get_data(symbol):
    try:
        url = "https://scanner.tradingview.com/egypt/scan"
        payload = {
            "symbols": {"tickers": [f"EGX:{symbol.upper()}"], "query": {"types": []}},
            # طلبنا الـ RSI 14 الحقيقي من السيرفر مباشرة
            "columns": ["close", "high", "low", "volume", "RSI", "change"]
        }
        r = requests.post(url, json=payload, timeout=10).json()
        if not r.get("data"):
            return None
        d = r["data"][0]["d"]
        return {
            "p": float(d[0]), "h": float(d[1]), "l": float(d[2]),
            "v": float(d[3]), "rsi": float(d[4]), "chg": float(d[5])
        }
    except:
        return None

# ================== MATH INDICATORS ==================
def calculate_pivots(p, h, l):
    piv = (p + h + l) / 3
    s1 = (2 * piv) - h
    s2 = piv - (h - l)
    r1 = (2 * piv) - l
    r2 = piv + (h - l)
    return s1, s2, r1, r2

def liquidity_status(vol):
    if vol > 2_000_000: return "🔥 سيولة عالية جداً"
    if vol > 500_000: return "✅ سيولة جيدة"
    return "⚠️ سيولة ضعيفة"

# ================== SMART ENTRY LOGIC ==================
def get_entry_zone(p, s1, r1, rsi):
    # الدخول الذكي يعتمد على قرب السعر من الدعم مع RSI منخفض
    if rsi < 40:
        return round(s1, 2), round(s1 * 1.015, 2), "تجميع (قرب الدعم)"
    elif 40 <= rsi <= 60:
        mid = (s1 + r1) / 2
        return round(mid, 2), round(mid * 1.01, 2), "اختراق منتصف القناة"
    else:
        return round(r1, 2), round(r1 * 1.02, 2), "اختراق مقاومة (مخاطرة)"

# ================== SCORING SYSTEM ==================
def calculate_score(data, s1, r1):
    p, rsi, vol = data['p'], data['rsi'], data['v']
    score = 0
    # RSI Score (الأفضل بين 35 و 55 للدخول)
    if 30 <= rsi <= 50: score += 35
    elif 50 < rsi <= 65: score += 20
    
    # Volume Score
    if vol > 1_000_000: score += 25
    
    # Position Score (قربه من الدعم ميزة)
    dist_to_s1 = (p - s1) / s1
    if 0 <= dist_to_s1 <= 0.03: score += 40
    
    return min(score, 100)

# ================== REPORT UI ==================
def show_report(code, data):
    p, h, l, v, rsi = data['p'], data['h'], data['l'], data['v'], data['rsi']
    s1, s2, r1, r2 = calculate_pivots(p, h, l)
    liq = liquidity_status(v)
    z_low, z_high, z_type = get_entry_zone(p, s1, r1, rsi)
    score = calculate_score(data, s1, r1)

    # تحديد التوصية بناءً على القوة
    rec = "مراقبة"
    if score >= 75: rec = "⚡ شراء قوي"
    elif score >= 50: rec = "✅ دخول تدريجي"
    elif rsi > 75: rec = "🚫 تشبع شراء - بيع"

    st.markdown(f"""
    <div style="border:1px solid #4CAF50; padding:20px; border-radius:10px; background-color:#0e1117;">
        <h2 style="color:#4CAF50;">{code} - {COMPANIES.get(code,'')}</h2>
        <table style="width:100%">
            <tr><td>💰 السعر الحالي: <b>{p:.2f}</b></td><td>📉 RSI الحقيقي: <b>{rsi:.1f}</b></td></tr>
            <tr><td>🧱 دعم 1: <b>{s1:.2f}</b></td><td>🚧 مقاومة 1: <b>{r1:.2f}</b></td></tr>
            <tr><td>💧 السيولة: {liq}</td><td>📊 Score: <b>{score}/100</b></td></tr>
        </table>
        <hr>
        <h4 style="margin-bottom:5px;">🎯 منطقة الدخول المقترحة: <span style="color:#f63366;">{z_low} - {z_high}</span></h4>
        <small>النوع: {z_type}</small>
        <hr>
        <h4>📌 التوصية الحالية: <span style="font-size:24px;">{rec}</span></h4>
        <p style="color:#888;">وقف الخسارة: كسر {s2:.2f} بإغلاق | المستهدف: {r1:.2f} ثم {r2:.2f}</p>
    </div>
    """, unsafe_allow_html=True)

# ================== MAIN UI ==================
st.title("🏹 EGX Sniper PRO")
st.caption("نسخة مطورة: RSI 14 حقيقي + فلتر الدخول الذكي")

tab1, tab2, tab3 = st.tabs(["📡 التحليل الآلي", "🛠️ التحليل اليدوي", "🚨 Scanner"])

with tab1:
    code = st.text_input("ادخل كود السهم (مثال: ATQA, ALCN)").upper().strip()
    if code:
        data = get_data(code)
        if data:
            show_report(code, data)
        else:
            st.error("السهم غير موجود أو لا توجد بيانات حالياً")

with tab2:
    col1, col2 = st.columns(2)
    with col1:
        p_manual = st.number_input("السعر الحالي", step=0.01)
        h_manual = st.number_input("أعلى سعر (اليوم)", step=0.01)
    with col2:
        l_manual = st.number_input("أقل سعر (اليوم)", step=0.01)
        v_manual = st.number_input("فوليوم التداول", step=1000)
    
    # هنا الـ RSI لازم يدوي لأننا في Mode يدوي
    rsi_manual = st.slider("قيمة RSI (لو مش عارفها سيبها 50)", 0, 100, 50)
    
    if p_manual > 0:
        manual_data = {"p": p_manual, "h": h_manual, "l": l_manual, "v": v_manual, "rsi": rsi_manual}
        show_report("MANUAL", manual_data)

with tab3:
    if st.button("تشغيل الماسح الذكي"):
        with st.spinner("جاري فحص قائمة المتابعة..."):
            found = False
            for s in WATCHLIST:
                data = get_data(s)
                if data:
                    s1, _, r1, _ = calculate_pivots(data['p'], data['h'], data['l'])
                    score = calculate_score(data, s1, r1)
                    if score >= 60:
                        st.success(f"🚀 فرصة قوية: {s} | Score: {score} | RSI: {data['rsi']:.1f}")
                        found = True
            if not found:
                st.warning("لا توجد فرص مثالية حالياً حسب الشروط.")

