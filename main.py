import streamlit as st
import requests

# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="EGX Sniper Elite v8.3", layout="wide")

st.markdown("""
    <style>
    .stock-header { font-size: 20px !important; font-weight: bold; color: #58a6ff; }
    .price-callout { font-size: 18px !important; font-weight: bold; color: #3fb950; }
    .stoploss-callout { font-size: 16px !important; font-weight: bold; color: #f85149; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 8px; }
    div[data-testid="stExpander"] { border: 1px solid #30363d; background-color: #0d1117; }
    .avg-card { background-color: #1c2128; border: 1px solid #444c56; border-radius: 10px; padding: 15px; margin-bottom: 10px; }
    .target-box { background-color: #0d1117; border: 2px solid #58a6ff; border-radius: 10px; padding: 20px; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# ================== DATA ENGINE ==================
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
            name, p, rsi, v, avg_v, h, l, chg, desc = d
        else: 
            p, h, l, v, rsi, avg_v, chg, desc = d; name = ""
        
        if p is None or h is None or l is None: return None
        
        pp = (p + h + l) / 3
        s1, r1 = (2 * pp) - h, (2 * pp) - l
        s2, r2 = pp - (h - l), pp + (h - l)
        
        ratio = v / (avg_v or 1)
        if ratio > 1.8: mom_label = "🔥 سيولة ضخمة"
        elif ratio > 1.1: mom_label = "✅ زخم متصاعد"
        elif ratio > 0.7: mom_label = "🆗 مستقر"
        else: mom_label = "⚠️ ضعيف جداً"

        rsi_val = rsi if rsi is not None else 0
        t_score = int(90 if rsi_val < 38 else 75 if rsi_val < 55 else 40)
        s_score = int(85 if (ratio > 1.1 and 40 < rsi_val < 65) else 50)
        
        if rsi_val > 70: 
            rec, col = "🛑 تشبع شراء", "#ff4b4b"
        elif t_score >= 80 or s_score >= 80: 
            rec, col = "🚀 شراء قوي", "#00ff00"
        else: 
            rec, col = "⚖️ انتظار", "#58a6ff"

        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio, "mom_l": mom_label,
            "t_e": s1, "t_t": r1, "t_s": s1 * 0.98, "t_score": t_score,
            "s_e": p, "s_t": r2, "s_s": s2, "s_score": s_score,
            "rec": rec, "col": col
        }
    except: return None

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
st.title("🏹 EGX Sniper Elite v8.3")

tab1, tab2, tab3 = st.tabs(["📡 رادار البحث", "🚨 الماسح الشامل", "🧮 حاسبة المتوسطات"])

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
            else: st.error("بيانات السهم غير مكتملة.")
        else: st.error("لم يتم العثور على بيانات.")

with tab2:
    if st.button("بدء فحص أقوى فرص السوق 🔍"):
        all_d = fetch_egx_data(scan_all=True)
        found = False
        for r in all_d:
            an = analyze_stock(r, is_scan=True)
            if an is None: continue
            if an['t_score'] >= 75 or an['s_score'] >= 75:
                found = True
                with st.expander(f"🚀 {an['name']} | السعر: {an['p']} | Score: {max(an['t_score'], an['s_score'])}"):
                    render_stock_ui(an)
        if not found: st.warning("لا توجد فرص انفجارية حالياً.")

with tab3:
    st.subheader("🧮 حاسبة متوسط التكلفة الذكية")
    st.write("استخدم هذه الحاسبة لتعرف كيف سيؤثر الشراء الجديد على متوسط سعرك في السهم.")
    
    col_input1, col_input2, col_input3 = st.columns(3)
    old_p = col_input1.number_input("سعرك القديم (المتوسط الحالي)", value=0.0, step=0.01)
    old_q = col_input2.number_input("الكمية التي تملكها حالياً", value=0, step=10)
    new_p = col_input3.number_input("السعر الجديد الذي ستشتري به", value=0.0, step=0.01)
    
    # التحقق من أن البيانات الأساسية موجودة قبل عرض الاقتراحات والحاسبة الذكية
    if old_p > 0 and old_q > 0 and new_p > 0:
        current_total = old_p * old_q
        
        st.divider()
        st.markdown("#### 💡 اقتراحات تعديل المتوسط التقليدية:")
        
        scenarios = [
            {"label": "تعديل بسيط (شراء نصف كميتك)", "add_qty": int(old_q * 0.5)},
            {"label": "تعديل متوسط (مضاعفة الكمية - 1:1)", "add_qty": old_q},
            {"label": "تعديل جذري (شراء ضعف كميتك - 2:1)", "add_qty": old_q * 2}
        ]
        
        for sc in scenarios:
            new_total_qty = old_q + sc['add_qty']
            new_avg = (current_total + (new_p * sc['add_qty'])) / new_total_qty
            reduction = ((old_p - new_avg) / old_p) * 100
            
            st.markdown(f"""
            <div class='avg-card'>
                <b style='color:#58a6ff;'>{sc['label']}</b><br>
                شراء عدد <span style='color:#3fb950;'>{sc['add_qty']}</span> سهم جديد بتكلفة <span style='color:#3fb950;'>{(sc['add_qty']*new_p):,.2f} ج</span><br>
                متوسط سعرك الجديد سيكون: <span style='color:#3fb950; font-size:18px;'>{new_avg:.3f} ج</span><br>
                <small style='color:#8b949e;'>نسبة تخفيض التكلفة: {reduction:.1f}%</small>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # الحساب للمتوسط المستهدف (Target Average Calculator)
        st.markdown("### 🎯 حاسبة الهدف المحدد (Target Average)")
        target_avg = st.number_input("ادخل المتوسط الذي ترغب في الوصول إليه", value=old_p-0.01, step=0.01)
        
        if target_avg > 0:
            if target_avg <= new_p:
                st.error(f"❌ مستحيل! المتوسط لا يمكن أن يكون أقل من سعر الشراء الجديد ({new_p}).")
            elif target_avg >= old_p:
                st.warning("⚠️ هذا السعر أعلى من متوسطك الحالي، لا داعي للتعديل.")
            else:
                # المعادلة: الكمية المطلوبة = (الكمية القديمة * (السعر القديم - المستهدف)) / (المستهدف - السعر الجديد)
                needed_q = (old_q * (old_p - target_avg)) / (target_avg - new_p)
                total_cash = needed_q * new_p
                
                st.markdown(f"""
                <div class='target-box'>
                    <h4 style='color:#58a6ff; margin-top:0;'>الخطة المطلوبة للوصول لهدفك:</h4>
                    للوصول لمتوسط <span style='color:#3fb950;'>{target_avg:.3f} ج</span>:<br><br>
                    ✅ يجب شراء عدد: <b style='font-size:22px; color:#3fb950;'>{int(needed_q):,}</b> سهم جديد<br>
                    ✅ إجمالي المبلغ المطلوب: <b style='font-size:22px; color:#3fb950;'>{total_cash:,.2f} ج.م</b><br>
                    <p style='font-size:13px; color:#8b949e; margin-top:10px;'>إجمالي عدد أسهمك سيصبح: {int(old_q + needed_q):,} سهم.</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("ℹ️ يرجى إدخال السعر القديم والكمية وسعر الشراء الجديد لتفعيل الحاسبة والاقتراحات.")
