import streamlit as st
import requests

# ================== CONFIG ==================
st.set_page_config(page_title="EGX Sniper PRO", layout="wide")

# قائمة المتابعة
WATCHLIST = ["TMGH", "COMI", "ETEL", "SWDY", "EFID", "ATQA", "ALCN", "RMDA", "MAAL"]

COMPANIES = {
    "TMGH": "طلعت مصطفى", "COMI": "البنك التجاري الدولي", "ETEL": "المصرية للاتصالات",
    "SWDY": "السويدي إليكتريك", "EFID": "إيديتا", "ATQA": "عتاقة (الصلب)",
    "ALCN": "الأسكندرية للحاويات", "RMDA": "راميدا", "MAAL": "عبر المحيطات"
}

# ================== DATA ENGINE ==================
@st.cache_data(ttl=300)
def get_market_data(symbol):
    try:
        url = "https://scanner.tradingview.com/egypt/scan"
        payload = {
            "symbols": {"tickers": [f"EGX:{symbol.upper()}"], "query": {"types": []}},
            "columns": ["close", "high", "low", "volume", "RSI", "average_volume_10d_calc"]
        }
        r = requests.post(url, json=payload, timeout=10).json()
        if not r.get("data"): return None
        d = r["data"][0]["d"]
        return {
            "p": float(d[0]), "h": float(d[1]), "l": float(d[2]),
            "v": float(d[3]), "rsi": float(d[4]), "avg_v": float(d[5]) or 1
        }
    except: return None

# ================== ANALYTICS ==================
def get_logic(p, h, l, rsi, v, avg_v):
    # حساب الدعوم والمقاومات
    pp = (p + h + l) / 3
    s1, s2 = (2*pp)-h, pp-(h-l)
    r1, r2 = (2*pp)-l, pp+(h-l)
    
    # نسبة السيولة
    liq_ratio = v / avg_v
    if liq_ratio > 1.5: liq_txt, liq_col = "🔥 انفجارية", "#00ff00"
    elif liq_ratio > 0.8: liq_txt, liq_col = "✅ جيدة", "#58a6ff"
    else: liq_txt, liq_col = "⚠️ ضعيفة", "#ff4b4b"

    # تحليل المستويات
    scores = {}
    # 1. المضارب
    scores['trader'] = 85 if rsi < 40 else 50
    t_entry = round(s1, 2)
    
    # 2. السوينج
    scores['swing'] = 90 if (v > avg_v and 45 < rsi < 60) else 60
    s_entry = round((s1+r1)/2, 2)
    
    return {
        "s1": s1, "s2": s2, "r1": r1, "r2": r2,
        "liq_txt": liq_txt, "liq_col": liq_col,
        "scores": scores, "t_entry": t_entry, "s_entry": s_entry
    }

# ================== UI DISPLAY ==================
def render_card(code, d, res):
    # استخدمنا st.container بدل الـ HTML المعقد لتجنب المشاكل السابقة
    with st.container(border=True):
        st.subheader(f"{code} - {COMPANIES.get(code, '')}")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("السعر الحالي", f"{d['p']:.2f}")
        c2.metric("RSI (14)", f"{d['rsi']:.1f}")
        c3.markdown(f"**السيولة:** <span style='color:{res['liq_col']}'>{res['liq_txt']}</span>", unsafe_allow_html=True)
        
        st.write(f"🧱 **الدعم:** {res['s1']:.2f} / {res['s2']:.2f} | 🚧 **المقاومة:** {res['r1']:.2f} / {res['r2']:.2f}")
        st.divider()
        
        # تحليل المضارب
        col_t, col_s, col_i = st.columns(3)
        with col_t:
            st.write("🎯 **المضارب**")
            st.write(f"القوة: {res['scores']['trader']}/100")
            st.write(f"دخول: :green[{res['t_entry']}]")
            st.write(f"وقف: :red[{round(res['s1']*0.98, 2)}]")
            
        with col_s:
            st.write("🔁 **السوينج**")
            st.write(f"القوة: {res['scores']['swing']}/100")
            st.write(f"دخول: :green[{res['s_entry']}]")
            st.write(f"وقف: :red[{round(res['s2'], 2)}]")
            
        with col_i:
            st.write("🏦 **المستثمر**")
            st.write("القوة: 70/100")
            st.write(f"دخول: :green[{round(res['s2'], 2)}]")
            
        st.divider()
        st.info(f"📝 **ملحوظة للمحبوس:** لا تبيع بخسارة طالما السهم فوق {res['s2']:.2f}. التعديل الأفضل عند {res['s2']:.2f}.")

# ================== MAIN APP ==================
st.title("🏹 EGX Sniper PRO")

t1, t2, t3 = st.tabs(["📡 رادار الأسهم", "🛠️ تحليل يدوي", "🚨 الماسح الذكي"])

with t1:
    code = st.text_input("ادخل كود السهم").upper().strip()
    if code:
        data = get_market_data(code)
        if data:
            res = get_logic(data['p'], data['h'], data['l'], data['rsi'], data['v'], data['avg_v'])
            render_card(code, data, res)
        else:
            st.error("السهم غير موجود")

with t2:
    p_m = st.number_input("السعر", value=0.0)
    h_m = st.number_input("أعلى سعر", value=0.0)
    l_m = st.number_input("أقل سعر", value=0.0)
    v_m = st.number_input("الفوليوم", value=1)
    rsi_m = st.slider("RSI", 0, 100, 50)
    if p_m > 0:
        res_m = get_logic(p_m, h_m, l_m, rsi_m, v_m, v_m)
        render_card("MANUAL", {"p":p_m, "rsi":rsi_m}, res_m)

with t3:
    if st.button("فحص قائمة المتابعة لبكرة 🔍"):
        for s in WATCHLIST:
            d = get_market_data(s)
            if d:
                res = get_logic(d['p'], d['h'], d['l'], d['rsi'], d['v'], d['avg_v'])
                score = max(res['scores'].values())
                
                # إظهار سعر الدخول مباشرة في الـ Scanner
                if score >= 75:
                    st.success(f"🚀 {s} | القوة: {score} | دخول مضارب: {res['t_entry']} | دخول سوينج: {res['s_entry']}")
                else:
                    st.info(f"⚪ {s} | القوة: {score} | سعر الدخول المقترح: {res['t_entry']}")

