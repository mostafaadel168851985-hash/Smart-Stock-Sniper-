import streamlit as st
import requests

# ================== CONFIG ==================
st.set_page_config(page_title="EGX Sniper PRO", layout="wide")

WATCHLIST = ["TMGH", "COMI", "ETEL", "SWDY", "EFID", "ATQA", "ALCN", "RMDA", "MAAL"]

COMPANIES = {
    "TMGH": "طلعت مصطفى", "COMI": "البنك التجاري الدولي", "ETEL": "المصرية للاتصالات",
    "SWDY": "السويدي إليكتريك", "EFID": "إيديتا", "ATQA": "مصر الوطنية للصلب - عتاقة",
    "ALCN": "الأسكندرية لتداول الحاويات", "RMDA": "راميدا", "MAAL": "عبر المحيطات للملاحة"
}

# ================== DATA ENGINE (HISTORICAL CONTEXT) ==================
@st.cache_data(ttl=300)
def get_market_data(symbol):
    try:
        url = "https://scanner.tradingview.com/egypt/scan"
        payload = {
            "symbols": {"tickers": [f"EGX:{symbol.upper()}"], "query": {"types": []}},
            "columns": [
                "close", "high", "low", "volume", 
                "RSI", "average_volume_10d_calc", "change"
            ]
        }
        r = requests.post(url, json=payload, timeout=10).json()
        if not r.get("data"): return None
        d = r["data"][0]["d"]
        return {
            "p": float(d[0]), "h": float(d[1]), "l": float(d[2]),
            "v": float(d[3]), "rsi": float(d[4]), "avg_v": float(d[5]), "chg": float(d[6])
        }
    except: return None

# ================== ANALYSIS LOGIC ==================
def calculate_pivots(p, h, l):
    pp = (p + h + l) / 3
    return (2*pp)-h, pp-(h-l), (2*pp)-l, pp+(h-l)

def get_liquidity_status(v, avg_v):
    # مقارنة الفوليوم الحالي بمتوسط 10 أيام (بيانات تاريخية حقيقية)
    ratio = v / avg_v if avg_v > 0 else 1
    if ratio > 1.5: return "🔥 انفجار سيولة (أعلى من المتوسط)", "#3fb950"
    if ratio > 0.8: return "✅ سيولة طبيعية", "#58a6ff"
    return "⚠️ سيولة ضعيفة جداً", "#f85149"

def get_ai_logic(p, s1, s2, r1, r2, rsi, v, avg_v):
    # تحليل المضارب
    t_score = 80 if (rsi < 40 and p <= s1*1.01) else 50
    if rsi > 70: t_score = 20
    
    # تحليل السوينج (يعتمد على السيولة التاريخية)
    s_score = 60
    if v > avg_v and 45 < rsi < 60: s_score = 90
    
    return {
        "trader": {"score": t_score, "entry": round(s1, 2), "sl": round(s1*0.98, 2), "cmnt": "قناص: الدخول المثالي قرب الدعم لارتداد سريع."},
        "swing": {"score": s_score, "entry": round((s1+r1)/2, 2), "sl": round(s2, 2), "cmnt": "سوينج: انتظار اختراق المقاومة بفوليوم عالي."},
        "invest": {"score": 75 if rsi < 50 else 50, "entry": round(s2, 2), "sl": round(s2*0.95, 2), "cmnt": "مستثمر: تجميع هادئ في مناطق الدعوم التاريخية."}
    }

# ================== UI DISPLAY (FIXED HTML) ==================
def show_full_report(code, d):
    s1, s2, r1, r2 = calculate_pivots(d['p'], d['h'], d['l'])
    liq_txt, liq_col = get_liquidity_status(d['v'], d['avg_v'])
    ai = get_ai_logic(d['p'], s1, s2, r1, r2, d['rsi'], d['v'], d['avg_v'])
    
    # إصلاح عرض الـ HTML لضمان عدم ظهور الأكواد
    report_html = f"""
    <div style="border: 1px solid #30363d; padding: 20px; border-radius: 10px; background-color: #0d1117; color: #c9d1d9; font-family: sans-serif;">
        <h2 style="color: #58a6ff; margin-bottom:5px;">{code} - {COMPANIES.get(code, 'سهم جديد')}</h2>
        <div style="display: flex; justify-content: space-between; margin-bottom: 15px;">
            <span>💰 السعر: <b>{d['p']:.2f}</b></span>
            <span>📉 RSI: <b>{d['rsi']:.1f}</b></span>
        </div>
        <div style="margin-bottom: 15px;">
            💧 السيولة: <span style="color: {liq_col}; font-weight: bold;">{liq_txt}</span><br>
            📊 فوليوم اليوم: {d['v']:,.0f} (المتوسط: {d['avg_v']:,.0f})
        </div>
        <p style="font-size: 0.9em; color: #8b949e;">🧱 دعم: {s1:.2f} / {s2:.2f} | 🚧 مقاومة: {r1:.2f} / {r2:.2f}</p>
        <hr style="border: 0.5px solid #30363d;">
        
        <div style="margin-bottom: 15px;">
            <h4 style="color: #ff7b72; margin-bottom:5px;">🎯 تحليل المضارب | {ai['trader']['score']}/100</h4>
            <p style="margin:0;">{ai['trader']['cmnt']}</p>
            <p style="margin:5px 0;">دخول: <span style="color:#3fb950">{ai['trader']['entry']}</span> | وقف: <span style="color:#f85149">{ai['trader']['sl']}</span></p>
        </div>

        <div style="margin-bottom: 15px;">
            <h4 style="color: #d2a8ff; margin-bottom:5px;">🔁 تحليل السوينج | {ai['swing']['score']}/100</h4>
            <p style="margin:0;">{ai['swing']['cmnt']}</p>
            <p style="margin:5px 0;">دخول: <span style="color:#3fb950">{ai['swing']['entry']}</span> | وقف: <span style="color:#f85149">{ai['swing']['sl']}</span></p>
        </div>

        <div style="margin-bottom: 15px;">
            <h4 style="color: #79c0ff; margin-bottom:5px;">🏦 تحليل المستثمر | {ai['invest']['score']}/100</h4>
            <p style="margin:0;">{ai['invest']['cmnt']}</p>
            <p style="margin:5px 0;">دخول: <span style="color:#3fb950">{ai['invest']['entry']}</span> | وقف: <span style="color:#f85149">{ai['invest']['sl']}</span></p>
        </div>

        <div style="background-color: #161b22; padding: 15px; border-radius: 8px; border-left: 4px solid #f85149;">
            <b>📝 ملحوظة للمحبوس:</b> أفضل منطقة للتبريد حالياً هي قرب <b>{s2:.2f}</b>. لا تقم بالبيع بخسارة طالما السعر يحافظ على إغلاق فوق {s1:.2f} والسيولة في تحسن.
        </div>
    </div>
    """
    st.markdown(report_html, unsafe_allow_html=True)

# ================== MAIN APP UI ==================
st.title("🏹 EGX Sniper PRO")

t1, t2, t3 = st.tabs(["📡 رادار الأسهم", "🛠️ تحليل يدوي", "🚨 الماسح الذكي"])

with t1:
    code = st.text_input("كود السهم (مثال: MAAL, ATQA)").upper().strip()
    if code:
        res = get_market_data(code)
        if res: show_full_report(code, res)
        else: st.error("عذراً، لم نتمكن من جلب بيانات هذا السهم.")

with t2:
    st.info("استخدم هذا القسم إذا كان لديك بيانات من مصدر خارجي")
    p_m = st.number_input("السعر", value=0.0)
    h_m = st.number_input("أعلى سعر", value=0.0)
    l_m = st.number_input("أقل سعر", value=0.0)
    v_m = st.number_input("الفوليوم", value=0)
    rsi_m = st.slider("RSI", 0, 100, 50)
    if p_m > 0:
        manual = {"p": p_m, "h": h_m, "l": l_m, "v": v_m, "rsi": rsi_m, "avg_v": v_m}
        show_full_report("MANUAL", manual)

with t3:
    if st.button("فحص أسهم المتابعة لبكرة 🔍"):
        for s in WATCHLIST:
            d = get_market_data(s)
            if d:
                s1, s2, r1, r2 = calculate_pivots(d['p'], d['h'], d['l'])
                ai = get_ai_logic(d['p'], s1, s2, r1, r2, d['rsi'], d['v'], d['avg_v'])
                if max(ai['trader']['score'], ai['swing']['score']) >= 75:
                    st.success(f"🚀 {s} | فرصة قوية (Score: {max(ai['trader']['score'], ai['swing']['score'])}) | RSI: {d['rsi']:.1f}")
                else:
                    st.info(f"⚪ {s} | مراقبة (Score: {max(ai['trader']['score'], ai['swing']['score'])})")
