import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="EGX Sniper Elite v8.1", layout="wide")

# تصميم الواجهة: توازن بين ضغط العناصر ووضوح الأرقام المهمة
st.markdown("""
    <style>
    .stock-header { font-size: 20px !important; font-weight: bold; color: #58a6ff; }
    .price-callout { font-size: 18px !important; font-weight: bold; color: #3fb950; }
    .stoploss-callout { font-size: 16px !important; font-weight: bold; color: #f85149; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 8px; }
    div[data-testid="stExpander"] { border: 1px solid #30363d; background-color: #0d1117; }
    </style>
    """, unsafe_allow_html=True)

# ================== DATA ENGINE (TradingView Connection) ==================
@st.cache_data(ttl=300)
def fetch_egx_data(symbol=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    if scan_all:
        payload = {
            "filter": [
                {"left": "volume", "operation": "greater", "right": 50000},
                {"left": "close", "operation": "greater", "right": 0.4}
            ],
            "columns": ["name", "close", "RSI", "volume", "average_volume_10d_calc", "high", "low", "change", "description"],
            "sort": {"sortBy": "change", "sortOrder": "desc"}, "range": [0, 50]
        }
    else:
        payload = {
            "symbols": {"tickers": [f"EGX:{symbol.upper()}"], "query": {"types": []}},
            "columns": ["close", "high", "low", "volume", "RSI", "average_volume_10d_calc", "change", "description"]
        }
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except: return []

# ================== ANALYSIS LOGIC ==================
def analyze_stock(d_row, is_scan=False):
    try:
        d = d_row['d']
        if is_scan: 
            # في حالة الماسح الشامل
            name, p, rsi, v, avg_v, h, l, chg, desc = d
        else: 
            # في حالة البحث الفردي
            p, h, l, v, rsi, avg_v, chg, desc = d; name = ""
        
        # --- حماية من البيانات الفارغة (NaN/None) ---
        # هذا التعديل يمنع توقف التطبيق في حالة وجود بيانات ناقصة للسهم
        if p is None or h is None or l is None: return None
        
        # حساب نقط الارتكاز والدعوم
        pp = (p + h + l) / 3
        s1, r1 = (2 * pp) - h, (2 * pp) - l
        s2, r2 = pp - (h - l), pp + (h - l)
        
        # حساب وترجمة الزخم (Momentum)
        ratio = v / (avg_v or 1)
        if ratio > 1.8: mom_label = "🔥 سيولة ضخمة"
        elif ratio > 1.1: mom_label = "✅ زخم متصاعد"
        elif ratio > 0.7: mom_label = "🆗 مستقر"
        else: mom_label = "⚠️ ضعيف جداً"

        # --- إصلاح مشكلة الـ RSI (TypeError Fix) ---
        # التحقق من أن RSI ليس فارغاً قبل المقارنة الرقمية
        if rsi is not None:
            t_score = int(90 if rsi < 38 else 75 if rsi < 55 else 40)
        else:
            t_score = 0 # سكور صفر للأسهم التي لا تملك بيانات RSI
            rsi = 0 # قيمة افتراضية للعرض
        
        s_score = int(85 if (ratio > 1.1 and 40 < rsi < 65) else 50)
        
        # منطق التوصية (Recommendation Logic)
        if rsi > 70: 
            rec, col = "🛑 تشبع شراء", "#ff4b4b"
        elif t_score >= 80 or s_score >= 80: 
            rec, col = "🚀 شراء قوي", "#00ff00"
        else: 
            rec, col = "⚖️ انتظار", "#58a6ff"

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi, "chg": chg, "ratio": ratio, "mom_l": mom_label,
            "t_e": s1, "t_t": r1, "t_s": s1 * 0.98, "t_score": t_score,
            "s_e": p, "s_t": r2, "s_s": s2, "s_score": s_score,
            "rec": rec, "col": col
        }
    except:
        # في حالة حدوث أي خطأ غير متوقع في سهم معين، نتخطاه بسلام
        return None

# ================== UI COMPONENTS ==================
def render_stock_ui(res, budget=10000):
    if not res: return
    shares = int(budget / res['p']) if res['p'] > 0 else 0
    
    st.markdown(f"""
        <div style='display: flex; justify-content: space-between; align-items: center;'>
            <span class='stock-header'>{res['name']} {res['desc'][:20]}</span>
            <span style='color:{res['col']}; font-weight:bold; border:1px solid {res['col']}; padding:3px 12px; border-radius:6px;'>{res['rec']}</span>
        </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("السعر الحالي", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    c2.metric("مؤشر RSI", f"{res['rsi']:.1f}")
    c3.metric("الزخم", f"{res['ratio']:.1f}x", res['mom_l'])
    
    st.divider()

    col_t, col_s = st.columns(2)
    with col_t:
        st.markdown(f"**🎯 مضارب يومي ({res['t_score']})**")
        st.markdown(f"دخول: <span class='price-callout'>{res['t_e']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"هدف: <span class='price-callout'>{res['t_t']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"وقف: <span class='stoploss-callout'>{res['t_s']:.2f}</span>", unsafe_allow_html=True)
        if shares > 0:
            st.write(f"💵 ربح متوقع: :green[+{(res['t_t']-res['t_e'])*shares:,.0f} ج]")
            st.write(f"📉 مخاطرة (لو ضرب وقف): :red[{(res['t_e']-res['t_s'])*shares:,.0f} ج]")

    with col_s:
        st.markdown(f"**🔁 سوينج أسبوعي ({res['s_score']})**")
        st.markdown(f"دخول: <span class='price-callout'>{res['s_e']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"هدف: <span class='price-callout'>{res['s_t']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"وقف: <span class='stoploss-callout'>{res['s_s']:.2f}</span>", unsafe_allow_html=True)
        if shares > 0:
            st.write(f"💵 ربح متوقع: :green[+{(res['s_t']-res['s_e'])*shares:,.0f} ج]")
            st.write(f"📉 مخاطرة (لو ضرب وقف): :red[{(res['s_e']-res['s_s'])*shares:,.0f} ج]")

# ================== MAIN APP STRUCTURE ==================
st.title("🏹 EGX Sniper Elite v8.1")

tab1, tab2 = st.tabs(["📡 رادار البحث", "🚨 الماسح الشامل للفرص"])

with tab1:
    sym = st.text_input("ادخل كود السهم (مثال: TMGH, ATQA)").upper().strip()
    if sym:
        data = fetch_egx_data(symbol=sym)
        if data:
            analysis = analyze_stock(data[0])
            if analysis:
                with st.container(border=True):
                    b = st.number_input("💰 ميزانية الصفقة (ج.م)", value=10000, step=1000)
                    render_stock_ui(analysis, budget=b)
            else:
                st.error("بيانات السهم غير مكتملة للتحليل.")
        else:
            st.error("لم يتم العثور على بيانات لهذا السهم. تأكد من الكود.")

with tab2:
    if st.button("بدء فحص أقوى فرص السوق 🔍"):
        all_d = fetch_egx_data(scan_all=True)
        found = False
        for r in all_d:
            an = analyze_stock(r, is_scan=True)
            # تخطي الأسهم التي فشل تحليلها
            if an is None: continue
            
            if an['t_score'] >= 75 or an['s_score'] >= 75:
                found = True
                with st.expander(f"🚀 {an['name']} | السعر: {an['p']} | Score: {max(an['t_score'], an['s_score'])}"):
                    render_stock_ui(an)
        if not found:
            st.warning("لا توجد فرص انفجارية حالياً. السوق في حالة استقرار.")
