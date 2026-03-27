import streamlit as st
import requests
import pandas as pd

# ================== CONFIG ==================
st.set_page_config(page_title="EGX Sniper Elite", layout="wide")

# ================== DATA ENGINE (FULL MARKET) ==================
@st.cache_data(ttl=300)
def get_market_data(symbol=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    
    # فلتر المسح الشامل لكل البورصة
    if scan_all:
        payload = {
            "filter": [{"left": "RSI", "operation": "less", "right": 50}],
            "options": {"lang": "en"},
            "symbols": {"query": {"types": []}, "tickers": []},
            "columns": ["name", "close", "RSI", "volume", "average_volume_10d_calc", "high", "low", "change"],
            "sort": {"sortBy": "volume", "sortOrder": "desc"},
            "range": [0, 100]
        }
    else:
        payload = {
            "symbols": {"tickers": [f"EGX:{symbol.upper()}"], "query": {"types": []}},
            "columns": ["close", "high", "low", "volume", "RSI", "average_volume_10d_calc", "change"]
        }

    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except:
        return []

# ================== LOGIC & CALCULATIONS ==================
def analyze_stock(d_row, is_scan=False):
    # ترتيب البيانات بناءً على نوع الطلب
    if is_scan:
        name, p, rsi, v, avg_v, h, l, chg = d_row['d']
    else:
        p, h, l, v, rsi, avg_v, chg = d_row['d']
        name = ""

    # Pivot Points
    pp = (p + h + l) / 3
    s1, s2 = (2*pp)-h, pp-(h-l)
    r1, r2 = (2*pp)-l, pp+(h-l)
    
    # Liquidity
    ratio = v / (avg_v or 1)
    liq_status = "🔥 انفجارية" if ratio > 1.5 else "✅ جيدة" if ratio > 0.8 else "⚠️ ضعيفة"
    
    # Scores & Entries
    t_score = 90 if rsi < 35 else 70 if rsi < 50 else 40
    t_entry = round(s1, 2)
    t_target = round(r1, 2)
    
    s_score = 85 if (v > avg_v and 40 < rsi < 60) else 55
    s_entry = round((s1+r1)/2, 2)
    s_target = round(r2, 2)

    return {
        "name": name, "p": p, "rsi": rsi, "v": v, "avg_v": avg_v, "chg": chg,
        "s1": s1, "s2": s2, "r1": r1, "r2": r2, "liq": liq_status,
        "t_score": t_score, "t_entry": t_entry, "t_target": t_target,
        "s_score": s_score, "s_entry": s_entry, "s_target": s_target
    }

# ================== UI COMPONENTS ==================
def show_analysis(code, data_row):
    res = analyze_stock(data_row)
    
    with st.container(border=True):
        st.title(f"📊 {code}")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
        col2.metric("RSI", f"{res['rsi']:.1f}")
        col3.metric("السيولة", res['liq'])
        col4.metric("فوليوم/متوسط", f"{res['v']/res['avg_v']:.1f}x")

        st.write(f"🧱 **الدعم:** {res['s1']:.2f} | {res['s2']:.2f}  ---  🚧 **المقاومة:** {res['r1']:.2f} | {res['r2']:.2f}")
        
        st.divider()
        
        # تحليل المضارب
        t_col, s_col = st.columns(2)
        with t_col:
            st.subheader(f"🎯 المضارب ({res['t_score']}/100)")
            st.info("💡 **تعليق AI:** " + ("فرصة ارتداد سريعة" if res['rsi'] < 40 else "انتظر تهدئة السعر"))
            st.write(f"✅ **دخول:** {res['t_entry']}")
            st.write(f"🚀 **مستهدف:** {res['t_target']}")
            st.write(f"🚫 **وقف:** {round(res['s1']*0.98, 2)}")

        with s_col:
            st.subheader(f"🔁 السوينج ({res['s_score']}/100)")
            st.info("💡 **تعليق AI:** " + ("تجميع مثالي لبناء مركز" if res['s_score'] > 70 else "السهم يحتاج سيولة إضافية"))
            st.write(f"✅ **دخول:** {res['s_entry']}")
            st.write(f"🚀 **مستهدف:** {res['s_target']}")
            st.write(f"🚫 **وقف:** {res['s2']:.2f}")

        st.divider()
        st.warning(f"📝 **ملحوظة للمحبوس:** السهم حالياً يختبر {res['s1']:.2f}. التعديل (Average) يكون ناجحاً عند ارتداد RSI من مستوى 30 أو عند لمس {res['s2']:.2f}.")

# ================== MAIN APP ==================
st.title("🏹 EGX Sniper Elite")

tab1, tab2 = st.tabs(["📡 رادار الأسهم", "🚨 الماسح الشامل للبورصة"])

with tab1:
    code = st.text_input("كود السهم (مثال: TMGH)").upper().strip()
    if code:
        data = get_market_data(symbol=code)
        if data:
            show_analysis(code, data[0])
        else:
            st.error("السهم غير موجود")

with tab2:
    st.write("سيقوم النظام بمسح **كامل السوق المصري** لاختيار أفضل الفرص بناءً على السيولة والـ RSI.")
    if st.button("بدء المسح الشامل 🔍"):
        all_data = get_market_data(scan_all=True)
        if all_data:
            found_count = 0
            for row in all_data:
                res = analyze_stock(row, is_scan=True)
                # فلتر الفرص القوية
                if res['t_score'] >= 80 or res['s_score'] >= 80:
                    with st.expander(f"🚀 {res['name']} - سعر: {res['p']} | RSI: {res['rsi']:.1f}"):
                        st.write(f"💧 **السيولة:** {res['liq']}")
                        st.write(f"🎯 **دخول مضارب:** {res['t_entry']} | **هدف:** {res['t_target']}")
                        st.write(f"🔁 **دخول سوينج:** {res['s_entry']} | **هدف:** {res['s_target']}")
                    found_count += 1
            if found_count == 0:
                st.warning("لا توجد فرص انفجارية حالياً، السوق في منطقة انتظار.")
        else:
            st.error("فشل الاتصال ببيانات البورصة.")

