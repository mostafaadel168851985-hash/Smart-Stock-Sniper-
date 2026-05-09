import streamlit as st
import streamlit.components.v1 as components
import requests
from datetime import datetime, date
import json
import os
import re
import urllib.parse
import pandas as pd
from io import BytesIO

# ================== 📱 MOBILE DETECTION ==================
user_agent = st.context.headers.get('User-Agent', '')
is_mobile = bool(re.search(r'Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini', user_agent))
if is_mobile:
    st.session_state.mobile_view = True
else:
    st.session_state.mobile_view = False

# ================== 📁 PERFORMANCE TRACKING ==================
TRADES_FILE = "trades_data.json"

def load_trades():
    if os.path.exists(TRADES_FILE):
        try:
            with open(TRADES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except:
            return []
    return []

def save_trades(trades):
    try:
        with open(TRADES_FILE, 'w', encoding='utf-8') as f:
            json.dump(trades, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error: {e}")

def record_trade(res, trade_type):
    if res is None:
        return
    trades = load_trades()
    today = datetime.now().strftime("%Y-%m-%d")
    
    for t in trades:
        if t.get('name') == res.get('name') and t.get('date_recorded') == today:
            return
    
    trades.append({
        "name": res.get('name', 'N/A'),
        "desc": res.get('desc', 'N/A'),
        "entry_price": res.get('entry_price', 0),
        "target": res.get('target', 0),
        "stop_loss": res.get('stop_loss', 0),
        "target_pct": res.get('target_pct', 0),
        "risk_pct": res.get('risk_pct', 0),
        "rr": res.get('rr', 0),
        "rsi_at_entry": res.get('rsi', 50),
        "smart_score": res.get('smart_score', 0),
        "trade_type": trade_type,
        "date_recorded": today,
        "status": "pending",
        "profit_pct": None,
        "entry_hit": False
    })
    save_trades(trades)

def get_performance_stats(trades):
    trades = [t for t in trades if t is not None]
    total = len(trades)
    if total == 0:
        return {'total': 0, 'hit_target': 0, 'stopped_out': 0, 'still_open': 0, 'success_rate': 0, 'avg_rr': 0}
    
    hit_target = len([t for t in trades if t.get('status') == 'hit_target'])
    stopped_out = len([t for t in trades if t.get('status') == 'stopped_out'])
    still_open = len([t for t in trades if t.get('status') in ['pending', 'still_open']])
    closed = hit_target + stopped_out
    success_rate = (hit_target / closed * 100) if closed > 0 else 0
    avg_rr = sum(t.get('rr', 0) for t in trades) / total if total > 0 else 0
    
    return {
        'total': total, 'hit_target': hit_target, 'stopped_out': stopped_out, 
        'still_open': still_open, 'success_rate': round(success_rate, 1), 'avg_rr': round(avg_rr, 2)
    }

# ================== 🔥 SMART SCORE (الدرجة الذكية) ==================
"""
💡 SMART SCORE - كيف يعمل؟

الـ Smart Score هو درجة مركبة من 0 إلى 100 تقيم قوة السهم بناءً على 8 عوامل:

1. الاتجاه قصير المدى (EMA20): +15 نقطة إذا كان السهم فوق EMA20
2. الاتجاه متوسط المدى (EMA50): +15 نقطة إذا كان السهم فوق EMA50  
3. الاتجاه طويل المدى (EMA200): +5 نقاط إذا كان السهم فوق EMA200
4. السيولة (نشاط التداول): +20 إذا كان الحجم > ضعف المتوسط، +10 إذا كان > 1.5x
5. RSI في المنطقة الصحية (50-65): +20 نقطة (زخم صحي غير مشبع)
6. RSI في منطقة القوة (65-75): +10 نقاط (قوي لكن يقترب من التشبع)
7. RSI في منطقة الضعف (40-50): +5 نقاط (ضعيف لكن قد ينعكس)
8. نسبة المخاطرة/العائد (RR): +20 إذا كانت >= 2، +10 إذا كانت >= 1.5

التصنيف النهائي:
- 70-100: 🔥 فرصة قوية جداً
- 50-69: ✅ فرصة جيدة
- 30-49: ⚠️ تحت المراقبة
- 0-29: ❄️ ضعيف
"""
def smart_score_pro(res):
    score = 0
    if res.get('t_short') == "صاعد": score += 15
    if res.get('t_med') == "صاعد": score += 15
    if res.get('t_long') == "صاعد": score += 5
    if res.get('ratio', 0) > 2: score += 20
    elif res.get('ratio', 0) > 1.5: score += 10
    if 50 < res.get('rsi', 50) < 65: score += 20
    elif 65 <= res.get('rsi', 50) < 75: score += 10
    elif 40 <= res.get('rsi', 50) < 50: score += 5
    if res.get('rr', 0) >= 2: score += 20
    elif res.get('rr', 0) >= 1.5: score += 10
    return int(score)

# ================== 🎯 ADVANCED CONFIDENCE SCORE (قرار القناص) ==================
"""
🎯 قرار القناص - نظام التقييم المتقدم

هذا النظام يجمع 6 مؤشرات فنية مختلفة في تقييم واحد موحد:

┌─────────────┬─────────────────────────────────────────────────────┐
│  المؤشر     │  الشرط                                              │
├─────────────┼─────────────────────────────────────────────────────┤
│ 1. الاتجاه  │ السعر فوق EMA200 أو الاتجاه الطويل "صاعد"           │
│ 2. الزخم    │ الاتجاهين القصير والمتوسط كلاهما "صاعد"             │
│ 3. RSI      │ بين 45 و 65 (منطقة الانطلاق الصحية)                 │
│ 4. السيولة  │ حجم التداول أكبر من 1.5x المتوسط (سيولة ممتازة)     │
│ 5. الاختراق │ السعر قرب من المقاومة R1 (أقل من 2%)               │
│ 6. الشمعة   │ الشمعة الأخيرة صاعدة (تغير السعر > 0.2%)            │
└─────────────┴─────────────────────────────────────────────────────┘

النتائج:
- 85-100%: 🔥 دخول الآن (فرصة ذهبية) - جميع المؤشرات متوافقة
- 65-84%:  ✅ شراء حذر / مراقبة - معظم المؤشرات إيجابية
- 40-64%:  🟡 انتظار (تجميع) - بعض المؤشرات إيجابية
- 0-39%:   ❌ تجنب السهم حالياً - المؤشرات سلبية
"""
def get_confidence(res):
    score = 0
    total = 6
    
    p = res.get('p', 0)
    rsi = res.get('rsi', 50)
    ratio = res.get('ratio', 0)
    change = res.get('chg', 0)
    t_short = res.get('t_short', 'هابط')
    t_med = res.get('t_med', 'هابط')
    t_long = res.get('t_long', 'هابط')
    sma200 = res.get('sma200', p)
    r1 = res.get('r1', p * 1.05)
    
    # 1. الاتجاه العام
    if t_long == "صاعد" or (sma200 and p > sma200):
        score += 1
    
    # 2. الزخم
    if t_med == "صاعد" and t_short == "صاعد":
        score += 1
    
    # 3. RSI في منطقة الانطلاق
    if 45 < rsi < 65:
        score += 1
    
    # 4. السيولة
    if ratio > 1.5:
        score += 1
    elif ratio > 1.2:
        score += 0.5
    
    # 5. قرب من المقاومة (الاختراق)
    if r1 and r1 > p:
        dist = (r1 - p) / p * 100
        if dist < 2:
            score += 1
        elif dist < 3:
            score += 0.5
    
    # 6. الشمعة الصاعدة
    if change > 0.2:
        score += 1
    elif change > 0:
        score += 0.5
    
    percent = int((score / total) * 100)
    
    if percent >= 85:
        advice, color, emoji = "🔥 دخول الآن (فرصة ذهبية)", "#00FF00", "🔥"
    elif percent >= 65:
        advice, color, emoji = "✅ شراء حذر / مراقبة", "#ADFF2F", "✅"
    elif percent >= 40:
        advice, color, emoji = "🟡 انتظار (تجميع)", "#FFFF00", "🟡"
    else:
        advice, color, emoji = "❌ تجنب السهم حالياً", "#FF4B4B", "❌"
    
    return {'score': percent, 'advice': advice, 'color': color, 'emoji': emoji}

def render_confidence_card(res):
    conf = get_confidence(res)
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, #1a1a2e, #16213e); border-radius: 12px; padding: 12px; margin: 10px 0; border-right: 4px solid {conf["color"]};'>
        <div style='display: flex; justify-content: space-between; align-items: center;'>
            <span style='font-size: 18px; font-weight: bold;'>{conf["emoji"]} قرار القناص</span>
            <span style='font-size: 28px; font-weight: bold; color: {conf["color"]};'>{conf["score"]}%</span>
        </div>
        <div style='margin-top: 5px;'><span style='color: {conf["color"]};'>{conf["advice"]}</span></div>
    </div>
    """, unsafe_allow_html=True)
    return conf["score"]

# ================== 🎯 CORRECTION HUNTER (صائد التصحيحات) ==================
"""
🎯 صائد التصحيحات - كيف يختار الأسهم؟

هذا القسم متخصص في اكتشاف الأسهم القوية التي تصحح ثم تستعد للانطلاق:

┌─────────────────────┬────────────────────────────────────────────────┐
│  الشرط              │  التوضيح                                       │
├─────────────────────┼────────────────────────────────────────────────┤
│ الاتجاه العام صاعد  │ السهم في ترند صاعد (فوق EMA200)               │
│ RSI في التصحيح      │ RSI بين 30 و 50 (السهم يرتاح بعد الصعود)     │
│ بداية ارتداد        │ التغير إيجابي (+0.1% فأكثر)                   │
│ سيولة جيدة          │ حجم التداول > المتوسط (اهتمام)                │
│ RR جيد              │ نسبة المخاطرة/العائد >= 1.5                   │
└─────────────────────┴────────────────────────────────────────────────┘

لماذا هذا مهم؟
- الأسهم القوية لا تنزل للأبد، بل تصحح ثم تنطلق مرة أخرى
- الدخول في منطقة التصحيح يعطيك مخاطرة أقل وعائد أكبر
- هذا هو نفس أسلوب "الشراء من القاع" الذي يستخدمه المحترفون
"""
def is_correction(an):
    if an is None:
        return False, [], 0
    
    p = an.get('p', 0)
    rsi = an.get('rsi', 50)
    sma200 = an.get('sma200', 0)
    ratio = an.get('ratio', 0)
    change = an.get('chg', 0)
    t_long = an.get('t_long', 'هابط')
    rr = an.get('rr', 0)
    
    reasons = []
    score = 0
    max_score = 7
    
    if t_long == "صاعد" or (sma200 and p > sma200):
        score += 3
        reasons.append("📈 الاتجاه العام صاعد (فوق EMA200)")
    else:
        return False, [], 0
    
    if 30 <= rsi <= 50:
        score += 2
        if rsi < 35:
            reasons.append(f"🔻 RSI منخفض جداً ({rsi:.0f}) - تشبع بيع ممتاز")
        else:
            reasons.append(f"📊 RSI في منطقة تصحيح ({rsi:.0f})")
    elif rsi < 30:
        score += 1
        reasons.append(f"🟢 RSI منخفض جداً ({rsi:.0f}) - تشبع بيع")
    else:
        return False, [], 0
    
    if change > 0:
        score += 1
        reasons.append(f"📈 بداية ارتداد ({change:+.2f}%)")
    
    if ratio > 1.2:
        score += 1
        reasons.append(f"💧 سيولة جيدة ({ratio:.1f}x)")
    
    if rr >= 1.5:
        score += 1
        reasons.append(f"⚖️ RR جيد ({rr})")
    
    strength = int((score / max_score) * 100)
    return score >= 4, reasons, strength

# ================== 🏆 TOP 10 (أفضل 10 فرص) ==================
"""
🏆 أفضل 10 فرص - كيف يتم الاختيار؟

يتم ترتيب جميع الأسهم تنازلياً حسب Smart Score، ثم يتم عرض أول 10 أسهم فقط.

لماذا Smart Score؟
- يجمع 8 عوامل مختلفة (الاتجاهات، السيولة، RSI، RR)
- يعطي نظرة شاملة لقوة السهم
- يضمن أن أول 10 أسهم هي الأقوى في السوق كله
"""
def get_top_10(results):
    valid = [r for r in results if r]
    sorted_results = sorted(valid, key=lambda x: x.get('smart_score', 0), reverse=True)
    return sorted_results[:10]

# ================== 📂 SECTOR FILTER (فلتر القطاع) ==================
"""
📂 فلتر القطاع - كيف يعمل؟

يصنف الأسهم إلى قطاعات بناءً على رمز السهم:
- 🏦 البنوك: CIEB, COMI, AAIB, QNBA
- 🏗️ العقارات: TMGH, OCDI, PHDC, HELI  
- 🍔 الأغذية: BFR, EFID, JUFO
- 📡 الاتصالات: ETEL, OTMT, TE
- 📌 أخرى: كل ما تبقى

الفائدة: التركيز على قطاع معين بدلاً من السوق كله
"""
SECTORS = {
    "🏦 البنوك": ["CIEB", "COMI", "AAIB", "QNBA"],
    "🏗️ العقارات": ["TMGH", "OCDI", "PHDC", "HELI"],
    "🍔 الأغذية": ["BFR", "EFID", "JUFO"],
    "📡 الاتصالات": ["ETEL", "OTMT", "TE"],
}

def get_sector(name):
    name_upper = name.upper()
    for sector, symbols in SECTORS.items():
        for sym in symbols:
            if sym in name_upper:
                return sector
    return "📌 أخرى"

def filter_by_sector(results, sector):
    if sector == "🌍 الكل" or not results:
        return results
    filtered = []
    for an in results:
        if an and get_sector(an.get('name', '')) == sector:
            filtered.append(an)
    return filtered

# ================== 📈 DATA & ANALYSIS ENGINE ==================
@st.cache_data(ttl=300, show_spinner=False)
def get_all_data():
    url = "https://scanner.tradingview.com/egypt/scan"
    cols = ["name","close","RSI","volume","average_volume_10d_calc","high","low","change","description","SMA20","SMA50","SMA200"]
    payload = {"filter": [{"left": "volume", "operation": "greater", "right": 1000}], "columns": cols, "range": [0, 300]}
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        if r.status_code != 200:
            return []
        return r.json().get("data", [])
    except:
        return []

def analyze_stock(d_row):
    try:
        d = d_row.get('d', [])
        if len(d) != 12:
            return None
        name, p, rsi, v, avg_v, h, l, chg, desc, sma20, sma50, sma200 = d
        if p is None:
            return None
        desc = desc or name
        ratio = v / avg_v if avg_v and avg_v > 0 else 0
        t_short = "صاعد" if (sma20 and p > sma20) else "هابط"
        t_med = "صاعد" if (sma50 and p > sma50) else "هابط"
        t_long = "صاعد" if (sma200 and p > sma200) else "هابط"
        
        entry_min, entry_max = p * 0.98, p * 1.01
        entry_price = (entry_min + entry_max) / 2
        pp = (p + (h or p) + (l or p)) / 3
        s1, r1 = (2 * pp) - (h or p), (2 * pp) - (l or p)
        s2, r2 = pp - ((h or p) - (l or p)), pp + ((h or p) - (l or p))
        stop_loss = min(s2, entry_price * 0.97)
        target = max(r1, entry_price * 1.05)
        profit_ps = target - entry_price
        loss_ps = entry_price - stop_loss
        if loss_ps <= 0:
            return None
        rr = round(profit_ps / loss_ps, 2)
        
        temp_res = {'t_short': t_short, 't_med': t_med, 't_long': t_long, 'ratio': ratio, 'rsi': rsi or 0, 'rr': rr}
        smart_score = smart_score_pro(temp_res)
        
        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi or 0, "chg": chg or 0, "ratio": ratio,
            "t_short": t_short, "t_med": t_med, "t_long": t_long,
            "s1": s1, "s2": s2, "r1": r1, "r2": r2, "pp": pp, "sma20": sma20, "sma50": sma50, "sma200": sma200,
            "entry_range": f"{entry_min:.2f} - {entry_max:.2f}", "entry_price": entry_price,
            "stop_loss": stop_loss, "target": target, "rr": rr, 
            "risk_pct": (loss_ps/entry_price)*100, "target_pct": (profit_ps/entry_price)*100,
            "smart_score": smart_score,
        }
    except:
        return None

def preprocess(raw_data):
    return [analyze_stock(r) for r in raw_data if analyze_stock(r)]

def get_fresh_data():
    with st.spinner("🔄 جاري تحميل البيانات..."):
        raw = get_all_data()
        if raw:
            st.session_state.all_results = preprocess(raw)
            return True
    return False

# ================== 📈 TRADINGVIEW CHART ==================
def render_chart(symbol, height=400):
    full_symbol = f"EGX:{symbol}"
    chart_html = f"""
    <div class="tradingview-widget-container">
        <div id="tv_chart_{symbol}"></div>
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script>
        new TradingView.widget({{
            "container_id": "tv_chart_{symbol}",
            "width": "100%",
            "height": {height},
            "symbol": "{full_symbol}",
            "interval": "D",
            "timezone": "Africa/Cairo",
            "theme": "dark",
            "style": "1",
            "locale": "ar",
            "hideideas": true
        }});
        </script>
    </div>
    """
    components.html(chart_html, height=height)

# ================== 🎨 STYLES ==================
st.set_page_config(page_title="🎯 قناص EGX", layout="wide", page_icon="🎯")
st.markdown("""
<style>
.stButton>button { width: 100%; border-radius: 10px; height: 45px; font-weight: bold; }
.stock-header { font-size: 22px; font-weight: bold; color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 8px; }
.score-tag { float: right; background: #238636; color: white; padding: 2px 12px; border-radius: 15px; font-size: 14px; }
.quality-excellent { background: #1f4f2b; color: white; padding: 5px; border-radius: 8px; text-align: center; }
.quality-good { background: #1f3a4f; color: white; padding: 5px; border-radius: 8px; text-align: center; }
.quality-normal { background: #4a4a4a; color: white; padding: 5px; border-radius: 8px; text-align: center; }
.warning-box { background: rgba(248,81,73,0.15); border-right: 4px solid #f85149; padding: 10px; border-radius: 8px; margin: 10px 0; }
.success-box { background: rgba(63,185,80,0.15); border-right: 4px solid #3fb950; padding: 10px; border-radius: 8px; margin: 10px 0; }
.info-box { background: rgba(88,166,255,0.15); border-right: 4px solid #58a6ff; padding: 10px; border-radius: 8px; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

# ================== SESSION INIT ==================
if "mode" not in st.session_state:
    st.session_state.mode = "⚖️ متوازن"
if 'page' not in st.session_state:
    st.session_state.page = 'home'
if "sector_filter" not in st.session_state:
    st.session_state.sector_filter = "🌍 الكل"
if "all_results" not in st.session_state:
    st.session_state.all_results = None

def render_mode():
    with st.expander("🎯 نمط التداول", expanded=False):
        c1, c2, c3 = st.columns(3)
        if c1.button("🛡️ محافظ"): st.session_state.mode = "🛡️ محافظ"
        if c2.button("⚖️ متوازن"): st.session_state.mode = "⚖️ متوازن"
        if c3.button("🚀 هجومي"): st.session_state.mode = "🚀 هجومي"
    color = "#238636" if "محافظ" in st.session_state.mode else "#f85149" if "هجومي" in st.session_state.mode else "#d29922"
    st.markdown(f"<div style='background:{color}; padding:8px; border-radius:8px; text-align:center; color:white; margin-bottom:15px;'>{st.session_state.mode}</div>", unsafe_allow_html=True)

def render_sector_sidebar():
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📂 فلتر القطاع")
    st.sidebar.markdown("اختر قطاعاً لتصفية الأسهم:")
    sectors = ["🌍 الكل", "🏦 البنوك", "🏗️ العقارات", "🍔 الأغذية", "📡 الاتصالات", "📌 أخرى"]
    selected = st.sidebar.selectbox("القطاع", sectors, index=0)
    if selected != st.session_state.sector_filter:
        st.session_state.sector_filter = selected
        st.rerun()

# ================== 📄 GUIDE SECTION (شرح الأقسام) ==================
def render_guide():
    st.markdown("""
    <div class='info-box'>
    📚 <b>دليل الأقسام - كيف يعمل كل قسم؟</b>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("🎯 قرار القناص - نظام التقييم المتقدم", expanded=True):
        st.markdown("""
        ### كيف يتم حساب "قرار القناص"؟
        
        النظام يجمع **6 مؤشرات فنية مختلفة** في تقييم واحد:
        
        | المؤشر | الشرط | لماذا؟ |
        |--------|-------|--------|
        | **الاتجاه العام** | السعر فوق EMA200 | يضمن أن السهم في ترند صاعد |
        | **الزخم** | EMA20 و EMA50 صاعدين | يؤكد قوة الحركة الحالية |
        | **RSI** | بين 45 و 65 | منطقة انطلاق صحية (غير مشبعة) |
        | **السيولة** | حجم > 1.5x المتوسط | تأكيد اهتمام المؤسسات |
        | **الاختراق** | قرب من المقاومة R1 (<2%) | السهم على وشك اختراق |
        | **الشمعة** | الشمعة الأخيرة صاعدة | تأكيد فوري للحركة |
        
        **النتائج:**
        - 🔥 **85-100%**: دخول الآن (جميع المؤشرات متوافقة)
        - ✅ **65-84%**: شراء حذر (معظم المؤشرات إيجابية)  
        - 🟡 **40-64%**: انتظار (بعض المؤشرات إيجابية)
        - ❌ **0-39%**: تجنب (المؤشرات سلبية)
        """)
    
    with st.expander("🎯 صائد التصحيحات - فرص الشراء من القاع", expanded=True):
        st.markdown("""
        ### كيف يختار "صائد التصحيحات" الأسهم؟
        
        هذا القسم يبحث عن **الأسهم القوية التي تصحح**:
        
        | الشرط | الدلالة |
        |--------|---------|
        | الاتجاه العام صاعد | السهم في ترند صاعد قوي |
        | RSI بين 30-50 | السهم في منطقة تصحيح (يرتاح بعد الصعود) |
        | تغير إيجابي | بداية ارتداد من القاع |
        | سيولة جيدة | حجم تداول > المتوسط |
        | RR >= 1.5 | نسبة مخاطرة/عائد جيدة |
        
        **لماذا هذه الفرصة مربحة؟**
        - الدخول في منطقة التصحيح = مخاطرة أقل
        - السهم القوي يعود للصعود بعد التصحيح
        - نفس استراتيجية "الشراء من القاع" التي يستخدمها المحترفون
        """)
    
    with st.expander("🏆 أفضل 10 فرص - أقوى الأسهم اليوم", expanded=True):
        st.markdown("""
        ### كيف يتم ترتيب أفضل 10 فرص؟
        
        يتم ترتيب **جميع الأسهم** تنازلياً حسب **Smart Score**:
        
        **ما هو Smart Score؟**
        
        درجة مركبة من **8 عوامل**:
        - الاتجاه قصير المدى (EMA20) - 15 نقطة
        - الاتجاه متوسط المدى (EMA50) - 15 نقطة
        - الاتجاه طويل المدى (EMA200) - 5 نقاط
        - سيولة عالية (ratio > 2) - 20 نقطة
        - سيولة جيدة (ratio > 1.5) - 10 نقاط
        - RSI صحي (50-65) - 20 نقطة
        - RR ممتاز (>=2) - 20 نقطة
        - RR جيد (>=1.5) - 10 نقاط
        
        **التصنيف:**
        - 70-100: 🔥 فرصة قوية جداً
        - 50-69: ✅ فرصة جيدة
        - 30-49: ⚠️ تحت المراقبة
        - 0-29: ❄️ ضعيف
        """)
    
    with st.expander("📂 فلتر القطاع - التخصص في قطاع معين", expanded=True):
        st.markdown("""
        ### كيف يعمل فلتر القطاع؟
        
        يصنف الأسهم إلى قطاعات بناءً على رمز السهم:
        
        | القطاع | الرموز |
        |--------|--------|
        | 🏦 البنوك | CIEB, COMI, AAIB, QNBA |
        | 🏗️ العقارات | TMGH, OCDI, PHDC, HELI |
        | 🍔 الأغذية | BFR, EFID, JUFO |
        | 📡 الاتصالات | ETEL, OTMT, TE |
        
        **الفائدة:** التركيز على قطاع معين بدلاً من تشتيت الانتباه في السوق كله
        """)
    
    with st.expander("⚖️ RR Ratio - نسبة المخاطرة إلى العائد", expanded=True):
        st.markdown("""
        ### ما هو RR Ratio؟
        
        **RR = (الهدف - سعر الدخول) / (سعر الدخول - وقف الخسارة)**
        
        | القيمة | المعنى |
        |--------|--------|
        | RR < 1 | ❌ سيء - المخاطرة أكبر من العائد |
        | RR = 1 | ⚠️ متوسط - المخاطرة = العائد |
        | RR = 1.5 | ✅ جيد - العائد أكبر 1.5 مرة من المخاطرة |
        | RR >= 2 | 🔥 ممتاز - العائد ضعف المخاطرة |
        
        **مثال:** لو دخلت بـ 100 ج، وقف الخسارة 95 ج (مخاطرة 5ج)، والهدف 110 ج (ربح 10ج)
        - RR = 10 / 5 = 2 (ممتاز)
        """)
    
    st.info("💡 **تذكير:** كل هذه المؤشرات أدوات مساعدة. القرار النهائي يعتمد على تحليلك الشخصي وإدارة المخاطر.")

# ================== UI RENDERER ==================
def render_stock_card(res, title_extra=""):
    if res is None:
        return
    st.markdown(f"<div class='stock-header'>{res['name']} - {res['desc']}<span class='score-tag'>Smart: {res.get('smart_score', 0)}</span></div>", unsafe_allow_html=True)
    render_confidence_card(res)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:+.1f}%")
    with col2: st.metric("Smart Score", f"{res['smart_score']}/100")
    with col3: st.metric("RR Ratio", f"{res['rr']}")
    with col4: st.metric("RSI", f"{res['rsi']:.0f}")
    
    with st.expander("📊 التحليل الفني", expanded=True):
        render_chart(res['name'])
        
        # الاتجاهات
        t_short = "🟢 صاعد" if res['t_short'] == "صاعد" else "🔴 هابط"
        t_med = "🟢 صاعد" if res['t_med'] == "صاعد" else "🔴 هابط"
        t_long = "🟢 صاعد" if res['t_long'] == "صاعد" else "🔴 هابط"
        st.markdown(f"""
        <div style='background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:10px;margin:10px 0;'>
            <b>📌 الاتجاهات:</b><br>
            قصير المدى (EMA20): {t_short}<br>
            متوسط المدى (EMA50): {t_med}<br>
            طويل المدى (EMA200): {t_long}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style='background:#0d1117;border:1px solid #3fb950;border-radius:10px;padding:12px;margin-top:10px;'>
            🎯 <b>نطاق الدخول:</b> {res['entry_range']}<br>
            🛑 <b>وقف الخسارة:</b> {res['stop_loss']:.2f} <span style='color:#f85149'>(-{res['risk_pct']:.1f}%)</span><br>
            🏁 <b>المستهدف:</b> {res['target']:.2f} <span style='color:#58a6ff'>(+{res['target_pct']:.1f}%)</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🏛️ مستويات الدعم والمقاومة")
        st.markdown(f"""
        | المستوى | السعر | الدلالة |
        |---------|-------|---------|
        | 🔴 **مقاومة ثانية R2** | {res['r2']:.2f} | مقاومة قوية |
        | 🔴 **مقاومة أولى R1** | {res['r1']:.2f} | مقاومة أولى |
        | 🟡 **نقطة الارتكاز PP** | {res['pp']:.2f} | المحور |
        | 🟢 **دعم أول S1** | {res['s1']:.2f} | دعم أول |
        | 🟢 **دعم ثاني S2** | {res['s2']:.2f} | دعم قوي |
        """)
    
    with st.expander("💰 خطة الدخول وإدارة المخاطر"):
        deal = st.number_input("💰 ميزانية الصفقة (ج)", value=10000, step=1000, key=f"deal_{res['name']}")
        if deal > 0 and res['entry_price'] > 0:
            shares = int(deal / res['entry_price'])
            actual_value = shares * res['entry_price']
            profit_val = (res['target'] - res['entry_price']) * shares
            loss_val = (res['entry_price'] - res['stop_loss']) * shares
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("📦 عدد الأسهم", f"{shares:,}")
                st.metric("💰 قيمة الصفقة", f"{actual_value:,.0f} ج")
            with col2:
                st.metric("🟢 الربح المتوقع", f"{profit_val:,.0f} ج", delta=f"+{res['target_pct']:.1f}%")
                st.metric("🔴 الخسارة المحتملة", f"{loss_val:,.0f} ج", delta=f"-{res['risk_pct']:.1f}%")
            
            st.info(f"📊 نسبة المخاطرة إلى العائد: 1:{res['rr']}")
            if res['rr'] >= 2:
                st.success("✅ نسبة ممتازة - العائد ضعف المخاطرة")
            elif res['rr'] >= 1.5:
                st.success("✅ نسبة جيدة - العائد أكبر من المخاطرة")
            else:
                st.warning("⚠️ نسبة منخفضة - المخاطرة أكبر من العائد")
    
    # مشاركة واتساب
    msg = f"📊 تحليل سهم {res['name']}\n💰 السعر: {res['p']:.2f} ج\n🎯 ثقة القناص: {get_confidence(res)['score']}%\n🎯 الدخول: {res['entry_range']}\n🛑 الوقف: {res['stop_loss']:.2f}\n🏁 الهدف: {res['target']:.2f}\n⚖️ RR: {res['rr']}"
    encoded = urllib.parse.quote(msg)
    st.markdown(f"[📱 مشاركة عبر واتساب](https://wa.me/?text={encoded})")

# ================== NAVIGATION & PAGES ==================
if st.session_state.all_results is None:
    get_fresh_data()

render_sector_sidebar()

if st.session_state.page == 'home':
    st.title("🎯 قناص EGX - الإصدار الخفيف")
    st.markdown("""
    <div class='info-box'>
    📌 <b>مرحباً بك في قناص EGX</b><br>
    • 🎯 <b>قرار القناص:</b> تقييم متكامل لفرصة السهم (6 مؤشرات)<br>
    • 🎯 <b>صائد التصحيحات:</b> اكتشاف الأسهم القوية التي تصحح<br>
    • 🏆 <b>أفضل 10 فرص:</b> أقوى الأسهم حسب Smart Score<br>
    • 📂 <b>فلتر القطاع:</b> ركز على قطاع معين من الشريط الجانبي
    </div>
    """, unsafe_allow_html=True)
    
    render_mode()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏆 أفضل 10 فرص", use_container_width=True):
            st.session_state.page = 'top10'
            st.rerun()
    with col2:
        if st.button("🎯 صائد التصحيحات", use_container_width=True):
            st.session_state.page = 'correction'
            st.rerun()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔍 تحليل سهم", use_container_width=True):
            st.session_state.page = 'analyze'
            st.rerun()
    with col2:
        if st.button("📊 تقييم الأداء", use_container_width=True):
            st.session_state.page = 'performance'
            st.rerun()
    
    with st.expander("⚙️ إدارة التطبيق", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 تحديث البيانات", use_container_width=True):
                get_fresh_data()
                st.success("✅ تم تحديث البيانات!")
                st.rerun()
        with col2:
            if st.button("📖 دليل الأقسام", use_container_width=True):
                st.session_state.page = 'guide'
                st.rerun()
        
        if st.button("🗑️ مسح بيانات التقييم", use_container_width=True):
            if os.path.exists(TRADES_FILE):
                os.remove(TRADES_FILE)
                st.success("✅ تم مسح البيانات!")
                st.rerun()
    
    filtered = filter_by_sector(st.session_state.all_results, st.session_state.sector_filter)
    if filtered:
        gold_count = len([r for r in filtered if r.get('smart_score', 0) >= 70])
        good_count = len([r for r in filtered if 50 <= r.get('smart_score', 0) < 70])
        st.markdown(f"""
        <div style='background:#0d1117;border-radius:10px;padding:15px;margin-top:20px;'>
            <b>📊 إحصائية السوق اليوم</b><br>
            • إجمالي الأسهم: {len(filtered)}<br>
            • 🔥 فرص قوية (Smart >= 70): {gold_count}<br>
            • ✅ فرص جيدة (Smart 50-69): {good_count}
        </div>
        """, unsafe_allow_html=True)

# ================== أفضل 10 فرص ==================
elif st.session_state.page == 'top10':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    render_mode()
    
    st.markdown("""
    <div class='info-box'>
    🏆 <b>أفضل 10 فرص - كيف تم الاختيار؟</b><br>
    تم ترتيب جميع الأسهم حسب <b>Smart Score</b> (درجة مركبة من 8 عوامل)، وتم عرض أول 10 أسهم فقط.
    </div>
    """, unsafe_allow_html=True)
    
    filtered = filter_by_sector(st.session_state.all_results, st.session_state.sector_filter)
    top = get_top_10(filtered)
    st.markdown(f"## 🏆 أفضل {len(top)} فرص حسب Smart Score")
    for i, an in enumerate(top, 1):
        with st.expander(f"#{i} - {an['name']} | Smart: {an['smart_score']} | RR: {an['rr']}"):
            render_stock_card(an)
            if st.button(f"💾 تسجيل الصفقة", key=f"rec_{an['name']}"):
                record_trade(an, "top10")
                st.success("تم تسجيل الصفقة!")

# ================== صائد التصحيحات ==================
elif st.session_state.page == 'correction':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    render_mode()
    
    st.markdown("""
    <div class='info-box'>
    🎯 <b>صائد التصحيحات - كيف تم الاختيار؟</b><br>
    • <b>الاتجاه العام صاعد:</b> السهم في ترند صاعد (فوق EMA200)<br>
    • <b>RSI في التصحيح:</b> RSI بين 30-50 (السهم يرتاح بعد الصعود)<br>
    • <b>بداية ارتداد:</b> التغير إيجابي (بدأ يصعد من القاع)<br>
    • <b>سيولة جيدة:</b> حجم التداول أكبر من المتوسط<br>
    • <b>RR جيد:</b> نسبة المخاطرة/العائد >= 1.5
    </div>
    """, unsafe_allow_html=True)
    
    filtered = filter_by_sector(st.session_state.all_results, st.session_state.sector_filter)
    corrections = []
    for an in filtered:
        is_corr, reasons, strength = is_correction(an)
        if is_corr:
            corrections.append({'stock': an, 'reasons': reasons, 'strength': strength})
    
    if corrections:
        corrections.sort(key=lambda x: x['strength'], reverse=True)
        st.markdown(f"**🎯 عدد فرص التصحيح: {len(corrections)}**")
        for item in corrections:
            an = item['stock']
            reasons = item['reasons']
            strength = item['strength']
            color = "#4caf50" if strength >= 70 else "#ff9800" if strength >= 50 else "#f44336"
            
            st.markdown(f"""
            <div style='background:#0d1117;border:2px solid #e91e63;border-radius:12px;padding:15px;margin-bottom:15px;'>
                <div style='display:flex;justify-content:space-between;align-items:center;'>
                    <h3 style='color:#e91e63;margin:0'>🎯 {an['name']} - {an['desc']}</h3>
                    <span style='background:{color}; padding:4px 12px; border-radius:20px; color:white; font-weight:bold;'>{strength}%</span>
                </div>
                <div style='height:6px; background:#333; border-radius:3px; margin:10px 0;'>
                    <div style='width:{strength}%; background:{color}; height:6px; border-radius:3px;'></div>
                </div>
                <div style='margin-top:10px;'>
                    <b>📊 المعطيات:</b><br>
                    • السعر: {an['p']:.2f} ج | RSI: {an['rsi']:.1f}<br>
                    • السيولة: {an['ratio']:.1f}x | التغير: {an['chg']:+.2f}%<br>
                    • Smart Score: {an['smart_score']}/100 | RR: {an['rr']}
                </div>
                <div style='margin-top:10px;'>
                    <b>✅ أسباب الفرصة:</b>
                    {"".join([f'<div style="color:#e91e63;">✓ {r}</div>' for r in reasons])}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            render_confidence_card(an)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"📊 تحليل {an['name']}", key=f"corr_analyze_{an['name']}"):
                    render_stock_card(an)
            with col2:
                if st.button(f"💾 تسجيل الصفقة", key=f"corr_rec_{an['name']}"):
                    record_trade(an, "correction")
                    st.success("تم تسجيل الصفقة!")
    else:
        st.info("🧐 لا توجد فرص تصحيح حالياً. استمر في متابعة الأسهم القوية التي تصحح.")

# ================== تحليل سهم فردي ==================
elif st.session_state.page == 'analyze':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    render_mode()
    st.title("🔍 تحليل سهم")
    sym = st.text_input("أدخل رمز السهم").upper().strip()
    if sym:
        data = [r for r in st.session_state.all_results if r and r.get('name') == sym]
        if data:
            render_stock_card(data[0])
        else:
            st.error("❌ السهم غير موجود")
            symbols = [r.get('name') for r in st.session_state.all_results[:20] if r]
            st.info(f"💡 أمثلة: {', '.join(symbols[:10])}")

# ================== تقييم الأداء ==================
elif st.session_state.page == 'performance':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    st.title("📊 تقييم الأداء")
    
    trades = load_trades()
    stats = get_performance_stats(trades)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📊 إجمالي الصفقات", stats['total'])
    col2.metric("✅ حققت الهدف", stats['hit_target'])
    col3.metric("❌ كسرت الوقف", stats['stopped_out'])
    col4.metric("⏳ لا تزال مفتوحة", stats['still_open'])
    
    col1, col2 = st.columns(2)
    col1.metric("📈 نسبة النجاح", f"{stats['success_rate']}%")
    col2.metric("⚖️ متوسط RR", stats['avg_rr'])
    
    if trades:
        st.markdown("### 📋 سجل الصفقات")
        for trade in trades[-20:][::-1]:
            if trade.get('status') == 'hit_target':
                status, color = "🟢 حققت الهدف", "#3fb950"
            elif trade.get('status') == 'stopped_out':
                status, color = "🔴 كسرت الوقف", "#f85149"
            else:
                status, color = "🟡 لا تزال مفتوحة", "#d29922"
            
            st.markdown(f"""
            <div style='background:#0d1117;border-left:4px solid {color}; border-radius:8px; padding:10px; margin:5px 0;'>
                <b>{trade.get('name', 'N/A')}</b> ({trade.get('trade_type', 'N/A')}) - {status}<br>
                📅 {trade.get('date_recorded', 'N/A')} | 🎯 دخول: {trade.get('entry_price', 0):.2f} | RR: {trade.get('rr', 0)}
            </div>
            """, unsafe_allow_html=True)

# ================== دليل الأقسام ==================
elif st.session_state.page == 'guide':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    st.title("📚 دليل الأقسام والمؤشرات")
    render_guide()
