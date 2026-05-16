import streamlit as st
import streamlit.components.v1 as components
import requests
from datetime import datetime
import json
import os
import re
import urllib.parse
import time

# ================== 📱 PAGE CONFIG ==================
st.set_page_config(
    page_title="🎯 EGX Sniper Pro", 
    layout="wide", 
    page_icon="🎯",
    initial_sidebar_state="expanded"
)

# ================== 📁 CONSTANTS ==================
TRADES_FILE = "trades_data.json"
MIN_DAILY_TURNOVER = 200000
MAX_RISK_PCT = 5.0

# ================== SESSION STATE ==================
if "mode" not in st.session_state:
    st.session_state.mode = "⚖️ متوازن"
if 'page' not in st.session_state: 
    st.session_state.page = 'home'
if "sector_filter" not in st.session_state:
    st.session_state.sector_filter = "🌍 الكل"
if "all_results" not in st.session_state:
    st.session_state.all_results = None
if "last_update" not in st.session_state:
    st.session_state.last_update = None

# ================== 🎨 CSS STYLES ==================
st.markdown("""
<style>
    /* تنسيق عام */
    .main {
        padding: 0rem 1rem;
    }
    
    /* شريط جانبي */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #0a0c10 100%);
        border-right: 1px solid #30363d;
    }
    
    /* تنسيق الأزرار في الشريط الجانبي */
    .stSidebar .stButton button {
        width: 100%;
        justify-content: flex-start;
        text-align: right;
        background: transparent;
        border: none;
        border-radius: 10px;
        padding: 12px 16px;
        margin: 4px 0;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    
    .stSidebar .stButton button:hover {
        background: rgba(88, 166, 255, 0.1);
        border-right: 3px solid #58a6ff;
    }
    
    /* حالة السوق العلوية */
    .market-header {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        padding: 12px 24px;
        border-radius: 12px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 10px;
        border: 1px solid #30363d;
    }
    
    /* بطاقات النتائج */
    .result-card {
        background: linear-gradient(135deg, #0d1117, #0a0c10);
        border-radius: 16px;
        padding: 16px;
        margin-bottom: 16px;
        border: 1px solid #30363d;
        transition: all 0.2s ease;
    }
    
    .result-card:hover {
        border-color: #58a6ff;
        transform: translateY(-2px);
    }
    
    /* بطاقات خاصة لكل نوع */
    .correction-card {
        border-right: 4px solid #2E7D32;
    }
    
    .rapid-card {
        border-right: 4px solid #FF6666;
    }
    
    .breakout-card {
        border-right: 4px solid #FFD700;
    }
    
    .gold-card {
        border-right: 4px solid #FFD700;
        background: linear-gradient(135deg, #1a1a2e, #1a1a1a);
    }
    
    /* مؤشرات القوة */
    .strength-bar {
        height: 6px;
        border-radius: 3px;
        background: #30363d;
        margin: 8px 0;
        overflow: hidden;
    }
    
    .strength-fill {
        height: 100%;
        border-radius: 3px;
        transition: width 0.3s ease;
    }
    
    .strength-high { background: #4caf50; }
    .strength-mid { background: #ff9800; }
    .strength-low { background: #f44336; }
    
    /* شريط سفلي */
    .footer-bar {
        background: #0d1117;
        padding: 8px 16px;
        border-radius: 10px;
        margin-top: 20px;
        font-size: 12px;
        color: #8b949e;
        text-align: center;
        border-top: 1px solid #30363d;
    }
    
    /* تنسيقات عامة */
    .metric-value {
        font-size: 24px;
        font-weight: bold;
    }
    
    .metric-label {
        font-size: 12px;
        color: #8b949e;
    }
    
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
    }
    
    .badge-success { background: rgba(63, 185, 80, 0.2); color: #3fb950; }
    .badge-warning { background: rgba(210, 153, 34, 0.2); color: #d29922; }
    .badge-danger { background: rgba(248, 81, 73, 0.2); color: #f85149; }
    .badge-info { background: rgba(88, 166, 255, 0.2); color: #58a6ff; }
    
    /* صفوف سريعة */
    .flex-row {
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        align-items: center;
    }
    
    .flex-between {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    /* تحسين التمرير */
    .main-content {
        max-height: calc(100vh - 120px);
        overflow-y: auto;
        padding-right: 10px;
    }
    
    /* تخصيص scrollbar */
    .main-content::-webkit-scrollbar {
        width: 6px;
    }
    
    .main-content::-webkit-scrollbar-track {
        background: #0d1117;
        border-radius: 3px;
    }
    
    .main-content::-webkit-scrollbar-thumb {
        background: #30363d;
        border-radius: 3px;
    }
    
    /* تحسين الشريط الجانبي */
    .sidebar-header {
        text-align: center;
        padding: 20px 0;
        border-bottom: 1px solid #30363d;
        margin-bottom: 20px;
    }
    
    .sidebar-header h2 {
        color: #58a6ff;
        margin: 0;
        font-size: 24px;
    }
    
    /* إحصائيات سريعة */
    .quick-stats {
        background: rgba(88, 166, 255, 0.05);
        border-radius: 12px;
        padding: 12px;
        margin: 15px 0;
    }
</style>
""", unsafe_allow_html=True)


# ================== 📈 DATA FUNCTIONS ==================
@st.cache_data(ttl=300, show_spinner=False)
def get_all_data():
    url = "https://scanner.tradingview.com/egypt/scan"
    cols = ["name","close","RSI","volume","average_volume_10d_calc","high","low","change","description","SMA20","SMA50","SMA200"]
    payload = {"filter": [], "columns": cols, "range": [0, 300]}
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json().get("data", [])
        return []
    except:
        return []

def analyze_stock(d_row):
    try:
        d = d_row.get('d', [])
        if len(d) < 12:
            return None
        
        # استخراج البيانات
        name = d[0]
        p = d[1]
        rsi = d[2] or 50
        v = d[3] or 0
        avg_v = d[4] or 1
        h = d[5] or p
        l = d[6] or p
        chg = d[7] or 0
        desc = d[8] or name
        sma20 = d[9] or p
        sma50 = d[10] or p
        sma200 = d[11] or p
        
        if p is None or p <= 0:
            return None
        
        ratio = v / avg_v if avg_v > 0 else 0
        daily_turnover = p * avg_v
        
        # فلتر السيولة
        if daily_turnover < MIN_DAILY_TURNOVER:
            return None
        
        # الاتجاهات
        t_short = "صاعد" if p > sma20 else "هابط"
        t_med = "صاعد" if p > sma50 else "هابط"
        t_long = "صاعد" if p > sma200 else "هابط"
        
        # حسابات الدعم والمقاومة
        pp = (p + h + l) / 3
        r1 = (2 * pp) - l
        r2 = pp + (h - l)
        s1 = (2 * pp) - h
        s2 = pp - (h - l)
        
        # نطاق الدخول
        entry_price = p
        stop_loss = s1 * 0.99 if s1 > 0 else p * 0.96
        target = r1 if r1 > p else p * 1.05
        
        # التأكد من أن الوقف منطقي
        stop_loss = max(stop_loss, p * (1 - MAX_RISK_PCT/100))
        
        # حساب RR
        risk = (entry_price - stop_loss) / entry_price * 100
        reward = (target - entry_price) / entry_price * 100
        rr = round(reward / risk, 2) if risk > 0 else 0
        
        # Smart Score
        temp = {'t_short': t_short, 't_med': t_med, 't_long': t_long, 'ratio': ratio, 'rsi': rsi, 'rr': rr, 'chg': chg}
        smart_score = 0
        if t_short == "صاعد": smart_score += 15
        if t_med == "صاعد": smart_score += 15
        if t_long == "صاعد": smart_score += 5
        if ratio > 2.5: smart_score += 20
        elif ratio > 1.8: smart_score += 15
        elif ratio > 1.2: smart_score += 8
        if 45 < rsi < 60: smart_score += 15
        elif 35 <= rsi <= 45: smart_score += 5
        if rr >= 2: smart_score += 15
        elif rr >= 1.5: smart_score += 8
        smart_score = min(100, smart_score)
        
        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi, "chg": chg,
            "ratio": ratio, "t_short": t_short, "t_med": t_med, "t_long": t_long,
            "s1": s1, "s2": s2, "r1": r1, "r2": r2, "pp": pp,
            "entry_price": entry_price, "stop_loss": stop_loss, "target": target,
            "risk_pct": round(risk, 1), "target_pct": round(reward, 1), "rr": rr,
            "smart_score": smart_score, "daily_turnover": daily_turnover
        }
    except:
        return None

def preprocess_all_data(raw_data):
    results = []
    for r in raw_data:
        an = analyze_stock(r)
        if an:
            results.append(an)
    return results

def get_fresh_data():
    with st.spinner("🔄 جاري تحميل البيانات..."):
        raw = get_all_data()
        if raw:
            st.session_state.all_results = preprocess_all_data(raw)
            st.session_state.last_update = datetime.now().strftime("%H:%M:%S")
            return True
    return False

def get_egx30_status():
    try:
        url = "https://scanner.tradingview.com/egypt/scan"
        payload = {"filter": [{"left": "symbol", "operation": "equal", "right": "EGX30"}], "columns": ["close", "RSI", "change"], "range": [0, 1]}
        r = requests.post(url, json=payload, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            data = r.json().get("data", [])
            if data and len(data) > 0 and len(data[0].get('d', [])) >= 3:
                d = data[0]['d']
                price = d[0] if d[0] else 10000
                rsi = d[1] if d[1] else 50
                change = d[2] if d[2] else 0
                status = "🟢 صاعد" if change > 0 else "🔴 هابط" if change < -0.5 else "🟡 متذبذب"
                return {"price": price, "rsi": rsi, "change": change, "status": status}
    except:
        pass
    return {"price": 10000, "rsi": 50, "change": 0, "status": "🟡 متذبذب"}

def get_top_10(results):
    if not results:
        return []
    valid = [r for r in results if r and r.get('smart_score', 0) >= 50]
    return sorted(valid, key=lambda x: x.get('smart_score', 0), reverse=True)[:10]

def get_corrections(results):
    corrections = []
    for r in results:
        if r:
            t_long = r.get('t_long', 'هابط')
            rsi = r.get('rsi', 50)
            ratio = r.get('ratio', 0)
            if t_long == "صاعد" and 28 <= rsi <= 55 and ratio > 0.7:
                score = 0
                if rsi < 35: score = 80
                elif rsi < 45: score = 70
                else: score = 60
                if r.get('chg', 0) > 0: score += 10
                corrections.append({"stock": r, "score": min(100, score)})
    return sorted(corrections, key=lambda x: x['score'], reverse=True)[:10]

def get_breakouts(results):
    breakouts = []
    for r in results:
        if r:
            t_short = r.get('t_short', 'هابط')
            rsi = r.get('rsi', 50)
            ratio = r.get('ratio', 0)
            if t_short == "صاعد" and 50 <= rsi <= 70 and ratio > 1.5:
                score = 0
                if ratio > 2.5: score = 85
                elif ratio > 1.8: score = 75
                else: score = 65
                if r.get('chg', 0) > 1: score += 10
                breakouts.append({"stock": r, "score": min(100, score)})
    return sorted(breakouts, key=lambda x: x['score'], reverse=True)[:10]

def render_stock_card(stock, card_type="normal"):
    """عرض بطاقة سهم بتصميم عصري"""
    if not stock:
        return
    
    # تحديد لون ونوع البطاقة
    card_class = "result-card"
    if card_type == "correction":
        card_class += " correction-card"
    elif card_type == "rapid":
        card_class += " rapid-card"
    elif card_type == "breakout":
        card_class += " breakout-card"
    elif card_type == "gold":
        card_class += " gold-card"
    
    # حساب نسبة القوة للتقدم
    strength = stock.get('smart_score', 50)
    strength_class = "strength-high" if strength >= 70 else "strength-mid" if strength >= 50 else "strength-low"
    
    # تحديد لون التغير
    chg = stock.get('chg', 0)
    chg_color = "🟢" if chg > 0 else "🔴" if chg < 0 else "⚪"
    
    # بناء البطاقة
    st.markdown(f"""
    <div class="{card_class}">
        <div class="flex-between">
            <div>
                <span style="font-size: 18px; font-weight: bold; color: #58a6ff;">{stock['name']}</span>
                <span style="font-size: 12px; color: #8b949e; margin-right: 8px;">{stock['desc'][:30]}</span>
            </div>
            <span class="badge badge-info">Smart: {stock['smart_score']}</span>
        </div>
        
        <div class="flex-row" style="margin: 12px 0;">
            <div>
                <div class="metric-value" style="color: #fff;">{stock['p']:.2f}</div>
                <div class="metric-label">السعر</div>
            </div>
            <div>
                <div class="metric-value" style="color: {'#3fb950' if chg > 0 else '#f85149' if chg < 0 else '#8b949e'};">{chg_color} {chg:+.1f}%</div>
                <div class="metric-label">التغير</div>
            </div>
            <div>
                <div class="metric-value">{stock['rsi']:.0f}</div>
                <div class="metric-label">RSI</div>
            </div>
            <div>
                <div class="metric-value">{stock['ratio']:.1f}x</div>
                <div class="metric-label">السيولة</div>
            </div>
            <div>
                <div class="metric-value">{stock['rr']}</div>
                <div class="metric-label">RR</div>
            </div>
        </div>
        
        <div class="strength-bar">
            <div class="strength-fill {strength_class}" style="width: {strength}%;"></div>
        </div>
        
        <div class="flex-between" style="margin-top: 8px;">
            <div>
                <span style="font-size: 12px; color: #8b949e;">🎯 هدف: {stock['target']:.2f}</span>
                <span style="font-size: 12px; color: #8b949e; margin-right: 16px;">🛑 وقف: {stock['stop_loss']:.2f}</span>
            </div>
            <div class="flex-row" style="gap: 8px;">
                <span class="badge {'badge-success' if stock['t_short'] == 'صاعد' else 'badge-danger'}">📊 {stock['t_short']}</span>
                <span class="badge {'badge-success' if stock['t_med'] == 'صاعد' else 'badge-danger'}">📈 {stock['t_med']}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # زر التحليل التفصيلي
    with st.expander(f"📊 تحليل مفصل لـ {stock['name']}"):
        col1, col2 = st.columns(2)
        with col1:
            st.metric("نطاق الدخول", f"{stock['entry_price'] * 0.98:.2f} - {stock['entry_price'] * 1.01:.2f}")
            st.metric("المخاطرة", f"-{stock['risk_pct']:.1f}%")
        with col2:
            st.metric("العائد المتوقع", f"+{stock['target_pct']:.1f}%")
            st.metric("نسبة المخاطرة/العائد", f"1:{stock['rr']}")
        
        st.info(f"""
        **🏛️ مستويات الدعم والمقاومة:**
        - 🔴 R2: {stock['r2']:.2f}
        - 🔴 R1: {stock['r1']:.2f}
        - 🟡 PP: {stock['pp']:.2f}
        - 🟢 S1: {stock['s1']:.2f}
        - 🟢 S2: {stock['s2']:.2f}
        """)
        
        if st.button(f"💾 تسجيل الصفقة", key=f"rec_{stock['name']}"):
            record_trade(stock, st.session_state.page)
            st.success("✅ تم تسجيل الصفقة!")


# ================== PERFORMANCE FUNCTIONS ==================
def record_trade(res, trade_type):
    trades_file = "trades_data.json"
    trades = []
    if os.path.exists(trades_file):
        try:
            with open(trades_file, 'r') as f:
                trades = json.load(f)
        except:
            pass
    
    trades.append({
        "name": res['name'],
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "type": trade_type,
        "price": res['p'],
        "target": res['target'],
        "stop": res['stop_loss'],
        "rr": res['rr'],
        "smart": res['smart_score']
    })
    
    with open(trades_file, 'w') as f:
        json.dump(trades, f, ensure_ascii=False, indent=2)


# ================== MAIN APP ==================
def main():
    # تحميل البيانات إذا لزم الأمر
    if st.session_state.all_results is None:
        if not get_fresh_data():
            st.error("⚠️ فشل تحميل البيانات. تأكد من اتصالك بالإنترنت.")
            return
    
    market = get_egx30_status()
    
    # ================== الشريط العلوي ==================
    st.markdown(f"""
    <div class="market-header">
        <div>
            <span style="font-size: 20px; font-weight: bold;">🎯 EGX Sniper Pro</span>
            <span style="font-size: 12px; color: #8b949e; margin-right: 16px;">v4.0</span>
        </div>
        <div class="flex-row">
            <div><span class="badge {'badge-success' if market['change'] > 0 else 'badge-danger'}">📊 {market['status']}</span></div>
            <div><span class="badge badge-info">💰 {market['price']:,.0f}</span></div>
            <div><span class="badge badge-info">📈 RSI: {market['rsi']:.0f}</span></div>
            <div><span class="badge {'badge-success' if market['change'] > 0 else 'badge-danger'}">📉 {market['change']:+.2f}%</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ================== الشريط الجانبي ==================
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-header">
            <h2>🎯 EGX Sniper</h2>
            <p style="color: #8b949e; font-size: 12px;">نظام تحليل أسهم EGX</p>
        </div>
        """, unsafe_allow_html=True)
        
        # قائمة التنقل
        st.markdown("### 🧭 القائمة")
        
        nav_items = [
            {"icon": "🏠", "name": "الرئيسية", "page": "home", "desc": "نظرة عامة"},
            {"icon": "🏆", "name": "أفضل 10 فرص", "page": "top10", "desc": "أقوى الفرص"},
            {"icon": "🎯", "name": "صائد التصحيحات", "page": "correction", "desc": "فرص التصحيح"},
            {"icon": "⚡", "name": "قناص الاختراق", "page": "breakout", "desc": "فرص الاختراق"},
            {"icon": "🔍", "name": "تحليل سهم", "page": "analyze", "desc": "تحليل مفصل"},
            {"icon": "📊", "name": "تقييم الأداء", "page": "performance", "desc": "نتائج الصفقات"},
        ]
        
        for item in nav_items:
            if st.button(f"{item['icon']} {item['name']}", key=f"nav_{item['page']}", use_container_width=True):
                st.session_state.page = item['page']
                st.rerun()
        
        st.markdown("---")
        
        # إعدادات سريعة
        st.markdown("### ⚙️ الإعدادات")
        
        # نمط التداول
        mode_options = ["🛡️ محافظ", "⚖️ متوازن", "🚀 هجومي"]
        current_mode_index = mode_options.index(st.session_state.mode) if st.session_state.mode in mode_options else 1
        selected_mode = st.selectbox("نمط التداول", mode_options, index=current_mode_index)
        if selected_mode != st.session_state.mode:
            st.session_state.mode = selected_mode
            st.rerun()
        
        # فلتر القطاع
        sectors = ["🌍 الكل", "🏦 البنوك", "🏗️ العقارات", "🍔 الأغذية", "📡 الاتصالات", "🏭 الصناعة"]
        selected_sector = st.selectbox("فلتر القطاع", sectors, index=sectors.index(st.session_state.sector_filter) if st.session_state.sector_filter in sectors else 0)
        if selected_sector != st.session_state.sector_filter:
            st.session_state.sector_filter = selected_sector
            st.rerun()
        
        st.markdown("---")
        
        # إحصائيات سريعة
        if st.session_state.all_results:
            total = len(st.session_state.all_results)
            avg_smart = sum(r.get('smart_score', 0) for r in st.session_state.all_results if r) / total if total > 0 else 0
            
            st.markdown(f"""
            <div class="quick-stats">
                <div class="flex-between">
                    <span>📊 الأسهم</span>
                    <span style="font-weight: bold;">{total}</span>
                </div>
                <div class="flex-between">
                    <span>🎯 متوسط Smart</span>
                    <span style="font-weight: bold;">{avg_smart:.0f}</span>
                </div>
                <div class="flex-between">
                    <span>🕐 آخر تحديث</span>
                    <span style="font-weight: bold;">{st.session_state.last_update}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # زر تحديث
        if st.button("🔄 تحديث البيانات", use_container_width=True):
            if get_fresh_data():
                st.success("✅ تم التحديث!")
                st.rerun()
    
    # ================== المحتوى الرئيسي ==================
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    
    # فلتر القطاع على النتائج
    filtered_results = st.session_state.all_results
    if st.session_state.sector_filter != "🌍 الكل":
        # تطبيق فلتر القطاع (تبسيطاً، نعرض الكل حالياً)
        pass
    
    # عرض المحتوى حسب الصفحة
    if st.session_state.page == 'home':
        st.markdown("## 🏠 نظرة عامة")
        
        # إحصائيات سريعة
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 إجمالي الأسهم", len(filtered_results) if filtered_results else 0)
        with col2:
            corrections = get_corrections(filtered_results) if filtered_results else []
            st.metric("🎯 فرص تصحيح", len(corrections))
        with col3:
            breakouts = get_breakouts(filtered_results) if filtered_results else []
            st.metric("⚡ فرص اختراق", len(breakouts))
        with col4:
            top = get_top_10(filtered_results) if filtered_results else []
            st.metric("🏆 أفضل 10", f"{len(top)}/10")
        
        st.markdown("---")
        
        # عرض أهم الفرص في تبويبات
        tab1, tab2, tab3 = st.tabs(["🏆 أفضل 10 فرص", "🎯 صائد التصحيحات", "⚡ قناص الاختراق"])
        
        with tab1:
            top = get_top_10(filtered_results) if filtered_results else []
            if top:
                for stock in top[:5]:
                    render_stock_card(stock, "normal")
                if len(top) > 5:
                    with st.expander(f"عرض الـ {len(top)-5} فرص المتبقية"):
                        for stock in top[5:]:
                            render_stock_card(stock, "normal")
            else:
                st.info("لا توجد فرص حالياً")
        
        with tab2:
            corrections = get_corrections(filtered_results) if filtered_results else []
            if corrections:
                for item in corrections[:5]:
                    render_stock_card(item['stock'], "correction")
            else:
                st.info("لا توجد فرص تصحيح حالياً")
        
        with tab3:
            breakouts = get_breakouts(filtered_results) if filtered_results else []
            if breakouts:
                for item in breakouts[:5]:
                    render_stock_card(item['stock'], "rapid")
            else:
                st.info("لا توجد فرص اختراق حالياً")
    
    elif st.session_state.page == 'top10':
        st.markdown("## 🏆 أفضل 10 فرص استثمارية")
        st.caption("أقوى الفرص بناءً على Smart Score ونسبة المخاطرة/العائد")
        
        top = get_top_10(filtered_results) if filtered_results else []
        if top:
            for i, stock in enumerate(top, 1):
                st.markdown(f"### #{i}")
                render_stock_card(stock, "normal")
        else:
            st.warning("⚠️ لا توجد فرص مطابقة للمعايير حالياً")
    
    elif st.session_state.page == 'correction':
        st.markdown("## 🎯 صائد التصحيحات")
        st.caption("الأسهم القوية التي في حالة تصحيح - فرصة للدخول قبل الانطلاق")
        
        corrections = get_corrections(filtered_results) if filtered_results else []
        if corrections:
            for item in corrections:
                render_stock_card(item['stock'], "correction")
        else:
            st.info("ℹ️ لا توجد فرص تصحيح حالياً")
    
    elif st.session_state.page == 'breakout':
        st.markdown("## ⚡ قناص الاختراق")
        st.caption("الأسهم على وشك الاختراق - فرص سريعة خلال جلسة أو جلستين")
        
        breakouts = get_breakouts(filtered_results) if filtered_results else []
        if breakouts:
            for item in breakouts:
                render_stock_card(item['stock'], "rapid")
        else:
            st.info("ℹ️ لا توجد فرص اختراق حالياً")
    
    elif st.session_state.page == 'analyze':
        st.markdown("## 🔍 تحليل سهم")
        
        sym = st.text_input("🔎 أدخل رمز السهم", placeholder="مثال: COMI, TMGH, ETEL", key="analyze_input").upper().strip()
        
        if sym:
            found = None
            for stock in filtered_results:
                if stock and stock.get('name') == sym:
                    found = stock
                    break
            
            if found:
                render_stock_card(found, "normal")
                if st.button(f"💾 تسجيل الصفقة", key=f"rec_analyze_{sym}"):
                    record_trade(found, "تحليل فردي")
                    st.success("✅ تم تسجيل الصفقة!")
            else:
                st.error(f"❌ السهم '{sym}' غير موجود")
                if filtered_results:
                    suggestions = [r.get('name') for r in filtered_results[:15] if r]
                    st.info(f"💡 أمثلة: {', '.join(suggestions)}")
    
    elif st.session_state.page == 'performance':
        st.markdown("## 📊 تقييم الأداء")
        
        trades_file = "trades_data.json"
        if os.path.exists(trades_file):
            try:
                with open(trades_file, 'r') as f:
                    trades = json.load(f)
                
                if trades:
                    total = len(trades)
                    st.metric("📊 إجمالي الصفقات", total)
                    
                    st.markdown("### 📋 سجل الصفقات")
                    for trade in reversed(trades[-20:]):
                        st.markdown(f"""
                        <div style="background: #0d1117; border-radius: 10px; padding: 10px; margin-bottom: 8px;">
                            <b>{trade.get('name', 'N/A')}</b> - {trade.get('type', 'N/A')}<br>
                            📅 {trade.get('date', 'N/A')} | 🎯 Smart: {trade.get('smart', 0)} | ⚖️ RR: {trade.get('rr', 0)}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("لا توجد صفقات مسجلة بعد")
            except:
                st.info("لا توجد بيانات أداء")
        else:
            st.info("لا توجد صفقات مسجلة بعد. سجل صفقتك الأولى من أي تحليل!")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ================== الشريط السفلي ==================
    st.markdown(f"""
    <div class="footer-bar">
        <div class="flex-between">
            <span>🎯 نمط التداول: {st.session_state.mode}</span>
            <span>📂 قطاع: {st.session_state.sector_filter}</span>
            <span>🕐 آخر تحديث: {st.session_state.last_update or 'لم يتم'}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
