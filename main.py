import streamlit as st
import requests

# ================== CONFIG ==================
st.set_page_config(page_title="EGX Sniper Elite v3", layout="wide")

# ================== DATA ENGINE ==================
@st.cache_data(ttl=300)
def fetch_egx_data(symbol=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    
    # فلتر المسح الشامل لكل البورصة مع استبعاد الأسهم الضعيفة
    if scan_all:
        payload = {
            "filter": [
                {"left": "volume", "operation": "greater", "right": 100000}, # الأسهم النشطة فقط
                {"left": "close", "operation": "greater", "right": 0.5}      # استبعاد أسهم القروش المتلاعبة
            ],
            "options": {"lang": "en"},
            "symbols": {"query": {"types": []}, "tickers": []},
            "columns": ["name", "close", "RSI", "volume", "average_volume_10d_calc", "high", "low", "change", "description"],
            "sort": {"sortBy": "change", "sortOrder": "desc"},
            "range": [0, 50]
        }
    else:
        payload = {
            "symbols": {"tickers": [f"EGX:{symbol.upper()}"], "query": {"types": []}},
            "columns": ["close", "high", "low", "volume", "RSI", "average_volume_10d_calc", "change", "description"]
        }

    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except:
        return []

# ================== LOGIC ==================
def calculate_metrics(d_row, is_scan=False):
    if is_scan:
        name, p, rsi, v, avg_v, h, l, chg, desc = d_row['d']
    else:
        p, h, l, v, rsi, avg_v, chg, desc = d_row['d']
        name = ""

    # Pivot Points (Real Technical Levels)
    pp = (p + h + l) / 3
    s1, s2 = (2*pp)-h, pp-(h-l)
    r1, r2 = (2*pp)-l, pp+(h-l)
    
    # Liquidity Analysis
    ratio = v / (avg_v or 1)
    if ratio > 1.8: liq, l_col, l_msg = "🔥 انفجارية", "green", "دخول سيولة ضخمة غير معتادة"
    elif ratio > 0.9: liq, l_col, l_msg = "✅ جيدة", "#58a6ff", "تداول طبيعي ونشط"
    else: liq, l_col, l_msg = "⚠️ ضعيفة", "orange", "حذر.. السهم يفتقد للزخم حالياً"

    # AI Comment Logic (Improved)
    if rsi < 35 and ratio > 1: ai_msg = "💎 فرصة ذهبية: تشبع بيعي مع بداية دخول سيولة."
    elif rsi > 70: ai_msg = "🛑 حذر: السهم في منطقة شراء مفرط، انتظر تصحيح."
    elif 45 < rsi < 55 and ratio > 1.2: ai_msg = "📈 انطلاقة: السهم يجمع سيولة للاختراق."
    else: ai_msg = "⚖️ استقرار: السهم في منطقة تداول عرضية."

    return {
        "name": name, "desc": desc, "p": p, "rsi": rsi, "v": v, "avg_v": avg_v, "chg": chg,
        "s1": s1, "s2": s2, "r1": r1, "r2": r2, "liq": liq, "l_col": l_col, 
        "ai_msg": ai_msg, "ratio": ratio
    }

# ================== UI DISPLAY ==================
def show_details(code, row):
    res = calculate_metrics(row)
    st.title(f"🔍 {code} - {res['desc']}")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    m2.metric("RSI", f"{res['rsi']:.1f}")
    m3.metric("حالة السيولة", res['liq'])
    m4.metric("قوة الزخم", f"{res['ratio']:.1f}x")

    st.info(f"🤖 **تحليل الذكاء الاصطناعي:** {res['ai_msg']}")
    
    st.divider()
    t_col, s_col = st.columns(2)
    with t_col:
        st.subheader("🎯 منطقة المضارب (Trader)")
        st.success(f"✅ دخول: {res['s1']:.2f}")
        st.write(f"🚀 مستهدف: {res['r1']:.2f}")
        st.error(f"🚫 وقف: {res['s1']*0.98:.2f}")

    with s_col:
        st.subheader("🔁 منطقة السوينج (Swing)")
        st.success(f"✅ دخول: {(res['s1']+res['r1'])/2:.2f}")
        st.write(f"🚀 مستهدف: {res['r2']:.2f}")
        st.error(f"🚫 وقف: {res['s2']:.2f}")

# ================== MAIN APP ==================
st.title("🏹 EGX Sniper Elite")

t1, t2 = st.tabs(["📡 رادار الأسهم", "🚨 الماسح الشامل للبورصة"])

with t1:
    code = st.text_input("كود السهم").upper().strip()
    if code:
        data = fetch_egx_data(symbol=code)
        if data: show_details(code, data[0])
        else: st.error("بيانات السهم غير متوفرة حالياً")

with t2:
    if st.button("بدء المسح الشامل للسوق المصري 🔍"):
        all_stocks = fetch_egx_data(scan_all=True)
        if all_stocks:
            for row in all_stocks:
                res = calculate_metrics(row, is_scan=True)
                # إظهار الفرص التي لديها RSI تحت 50 (في بداية صعود)
                if res['rsi'] < 55:
                    with st.expander(f"🚀 {res['name']} - سعر: {res['p']} | RSI: {res['rsi']:.1f} | سيولة: {res['liq']}"):
                        st.write(f"📝 {res['ai_msg']}")
                        st.write(f"🎯 **دخول مضارب:** {res['s1']:.2f} | **هدف:** {res['r1']:.2f}")
                        st.write(f"🔁 **دخول سوينج:** {(res['s1']+res['r1'])/2:.2f} | **هدف:** {res['r2']:.2f}")
        else: st.warning("لم يتم العثور على فرص تطابق الشروط حالياً.")
