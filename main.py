import streamlit as st
import streamlit.components.v1 as components
import requests
from datetime import datetime
import json
import os
import re
import urllib.parse

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

# ================== 📈 EGX30 MARKET ANALYSIS ==================
@st.cache_data(ttl=600, show_spinner=False)
def get_egx30_status():
    """تحليل المؤشر العام - يحدد قوة السوق"""
    try:
        url = "https://scanner.tradingview.com/egypt/scan"
        payload = {
            "filter": [{"left": "symbol", "operation": "equal", "right": "EGX30"}],
            "columns": ["close", "RSI", "SMA50", "SMA200", "change"],
            "range": [0, 1]
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json().get("data", [])
            if data and len(data[0].get('d', [])) >= 5:
                d = data[0]['d']
                price = d[0]
                rsi = d[1] if d[1] else 50
                sma50 = d[2] if d[2] else price
                sma200 = d[3] if d[3] else price
                change = d[4] if d[4] else 0
                
                score = 0
                if price > sma200:
                    score += 1
                if price > sma50:
                    score += 1
                if 40 < rsi < 70:
                    score += 1
                if change > -0.5:
                    score += 1
                
                if score >= 3:
                    status = "🟢 سوق صاعد - مناسب للتداول"
                    color = "#00FF00"
                    market_multiplier = 1.0
                elif score >= 2:
                    status = "🟡 سوق متذبذب - تداول بحذر"
                    color = "#FFA500"
                    market_multiplier = 0.7
                else:
                    status = "🔴 سوق هابط - ركز على صائد التصحيحات فقط"
                    color = "#FF4444"
                    market_multiplier = 0.5
                
                return {
                    "status": status,
                    "color": color,
                    "market_multiplier": market_multiplier,
                    "rsi": rsi,
                    "change": change,
                    "price": price,
                    "score": score
                }
    except:
        pass
    
    return {
        "status": "🟡 تعذر تحليل السوق - تداول بحذر",
        "color": "#FFA500",
        "market_multiplier": 0.7,
        "rsi": 50,
        "change": 0,
        "price": 0,
        "score": 1
    }

# ================== 🔥 SMART SCORE IMPROVED ==================
def smart_score_pro(res):
    """Smart Score محسن - 8 عوامل"""
    score = 0
    
    # الاتجاهات (35 نقطة كحد أقصى)
    if res.get('t_short') == "صاعد": score += 15
    if res.get('t_med') == "صاعد": score += 15
    if res.get('t_long') == "صاعد": score += 5
    
    # السيولة (20 نقطة)
    if res.get('ratio', 0) > 2.5: score += 20
    elif res.get('ratio', 0) > 1.8: score += 15
    elif res.get('ratio', 0) > 1.2: score += 8
    
    # RSI (15 نقطة) - منطقة الانطلاق المثالية
    rsi = res.get('rsi', 50)
    if 50 < rsi < 60:
        score += 15  # المنطقة المثالية
    elif 45 < rsi <= 50 or 60 <= rsi < 65:
        score += 10  # جيدة
    elif 40 <= rsi <= 45:
        score += 5   # منطقة تصحيح
    elif 30 <= rsi < 40:
        score += 3   # تشبع بيع - قد ينعكس
    
    # RR Ratio (15 نقطة)
    rr = res.get('rr', 0)
    if rr >= 2.5: score += 15
    elif rr >= 2: score += 12
    elif rr >= 1.5: score += 8
    elif rr >= 1.2: score += 4
    
    # زخم الشمعة (15 نقطة) - جديد
    chg = res.get('chg', 0)
    if chg > 1.5: score += 15
    elif chg > 0.5: score += 10
    elif chg > 0: score += 5
    elif chg > -1: score += 2
    
    return min(100, int(score))

# ================== 🎯 ADVANCED CONFIDENCE SCORE ==================
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
    if ratio > 1.8:
        score += 1
    elif ratio > 1.2:
        score += 0.5
    
    # 5. قرب من المقاومة
    if r1 and r1 > p:
        dist = (r1 - p) / p * 100
        if dist < 2:
            score += 1
        elif dist < 3:
            score += 0.5
    
    # 6. الشمعة الصاعدة
    if change > 0.3:
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

# ================== 🎯 CORRECTION HUNTER (محسن) ==================
def is_correction(an, market_multiplier=1.0):
    """صائد التصحيحات - يبحث عن الأسهم القوية التي تصحح"""
    if an is None:
        return False, [], 0
    
    p = an.get('p', 0)
    rsi = an.get('rsi', 50)
    sma200 = an.get('sma200', 0)
    sma50 = an.get('sma50', 0)
    ratio = an.get('ratio', 0)
    change = an.get('chg', 0)
    t_long = an.get('t_long', 'هابط')
    t_med = an.get('t_med', 'هابط')
    rr = an.get('rr', 0)
    volume = an.get('volume', 0)
    avg_volume = an.get('avg_volume', 1)
    
    reasons = []
    score = 0
    max_score = 8
    
    # شرط 1: الاتجاه العام صاعد (إلزامي)
    if t_long == "صاعد" or (sma200 and p > sma200 * 0.98):
        score += 3
        reasons.append("📈 الاتجاه العام صاعد (فوق EMA200)")
    else:
        return False, [], 0  # إلزامي
    
    # شرط 2: RSI في منطقة التصحيح (30-50)
    if 30 <= rsi <= 50:
        score += 2
        if rsi < 35:
            reasons.append(f"🔻 RSI منخفض جداً ({rsi:.0f}) - تشبع بيع ممتاز")
        else:
            reasons.append(f"📊 RSI في منطقة تصحيح ({rsi:.0f})")
    elif 50 < rsi <= 55:
        score += 1
        reasons.append(f"📊 RSI بدأ يخرج من التصحيح ({rsi:.0f})")
    elif rsi < 30:
        score += 1
        reasons.append(f"🟢 RSI شديد الانخفاض ({rsi:.0f}) - قد ينعكس")
    else:
        return False, [], 0  # RSI أعلى من 55 يعني مش في تصحيح
    
    # شرط 3: بداية ارتداد
    if change > 0.2:
        score += 2
        reasons.append(f"📈 بداية ارتداد قوية ({change:+.2f}%)")
    elif change > 0:
        score += 1
        reasons.append(f"📈 بداية ارتداد ({change:+.2f}%)")
    elif change > -1:
        score += 0.5
        reasons.append(f"📉 استقرار قرب القاع ({change:+.2f}%)")
    else:
        reasons.append(f"⚠️ لا يزال يهبط ({change:+.2f}%)")
    
    # شرط 4: سيولة جيدة
    volume_ratio = volume / avg_volume if avg_volume > 0 else 0
    if volume_ratio > 1.5:
        score += 1
        reasons.append(f"💧 سيولة ممتازة ({volume_ratio:.1f}x)")
    elif volume_ratio > 1.0:
        score += 0.5
        reasons.append(f"💧 سيولة جيدة ({volume_ratio:.1f}x)")
    
    # شرط 5: المتوسط المتوسط صاعد (تأكيد قوة السهم)
    if t_med == "صاعد" or (sma50 and p > sma50 * 0.95):
        score += 1
        reasons.append("📊 المتوسط المتوسط صاعد - قوة مؤكدة")
    
    # شرط 6: RR جيد
    if rr >= 1.8:
        score += 1
        reasons.append(f"⚖️ RR ممتاز ({rr})")
    elif rr >= 1.3:
        score += 0.5
        reasons.append(f"⚖️ RR جيد ({rr})")
    
    # شرط 7: السعر قريب من الدعم
    s1 = an.get('s1', p * 0.97)
    if p <= s1 * 1.02:
        score += 1
        reasons.append("🎯 السعر عند منطقة دعم قوية")
    
    # تطبيق مضاعف السوق
    adjusted_score = score * market_multiplier
    strength = int((adjusted_score / max_score) * 100)
    
    # تصنيف قوة التصحيح
    if strength >= 65:
        strength_label = "🔥 فرصة تصحيح ممتازة"
        strength_color = "#00FF00"
    elif strength >= 50:
        strength_label = "✅ فرصة تصحيح جيدة"
        strength_color = "#ADFF2F"
    elif strength >= 35:
        strength_label = "🟡 فرصة تصحيح محتملة"
        strength_color = "#FFA500"
    else:
        strength_label = "❌ فرصة تصحيح ضعيفة"
        strength_color = "#FF4444"
    
    return {
        "is_correction": score >= 3,  # على الأقل 3 نقاط من 8
        "reasons": reasons,
        "strength": strength,
        "strength_label": strength_label,
        "strength_color": strength_color,
        "score": score
    }

# ================== 📂 SECTOR FILTER ==================
SECTORS = {
    "🏦 البنوك": ["CIEB", "COMI", "AAIB", "QNBA", "ALEX", "SAUD"],
    "🏗️ العقارات": ["TMGH", "OCDI", "PHDC", "HELI", "DEGC", "MENA"],
    "🍔 الأغذية": ["BFR", "EFID", "JUFO", "ORWE", "BOC"],
    "📡 الاتصالات": ["ETEL", "OTMT", "TE", "EMOB"],
    "🏭 الصناعات": ["ESRS", "MFPC", "SKPC", "ABUK"],
    "🛒 التجارة": ["RAYA", "SWDY", "AUTO"]
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
    payload = {"filter": [{"left": "volume", "operation": "greater", "right": 500000}], "columns": cols, "range": [0, 300]}
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
        if p is None or p <= 0:
            return None
        desc = desc or name
        
        # حساب السيولة
        ratio = v / avg_v if avg_v and avg_v > 0 else 0
        
        # فلتر السيولة الحقيقي (قيمة التداول بالجنيه)
        estimated_value = p * v
        if estimated_value < 2000000:  # أقل من 2 مليون جنيه
            return None
        
        # الاتجاهات
        t_short = "صاعد" if (sma20 and p > sma20) else "هابط"
        t_med = "صاعد" if (sma50 and p > sma50) else "هابط"
        t_long = "صاعد" if (sma200 and p > sma200) else "هابط"
        
        # حساب نقاط الدعم والمقاومة (نظام الـ Pivot Points الكامل)
        high = h if h else p
        low = l if l else p
        pp = (p + high + low) / 3
        r1 = (2 * pp) - low
        r2 = pp + (high - low)
        s1 = (2 * pp) - high
        s2 = pp - (high - low)
        
        # نطاق الدخول (سعر الدخول المقترح)
        entry_min = p * 0.98
        entry_max = p * 1.01
        entry_price = (entry_min + entry_max) / 2
        
        # وقف الخسارة (أسفل S2 أو -4%)
        stop_loss = min(s2 * 0.98, entry_price * 0.96) if s2 > 0 else entry_price * 0.96
        
        # الهدف (عند R1 أو +5%)
        target = max(r1, entry_price * 1.05) if r1 > 0 else entry_price * 1.05
        
        # حساب RR ونسب المخاطرة
        profit_ps = target - entry_price
        loss_ps = entry_price - stop_loss
        
        if loss_ps <= 0:
            rr = 0
            risk_pct = 0
            target_pct = 0
        else:
            rr = round(profit_ps / loss_ps, 2)
            risk_pct = (loss_ps / entry_price) * 100
            target_pct = (profit_ps / entry_price) * 100
        
        # تجميع البيانات لـ Smart Score
        temp_res = {
            't_short': t_short, 't_med': t_med, 't_long': t_long,
            'ratio': ratio, 'rsi': rsi or 0, 'rr': rr, 'chg': chg or 0
        }
        smart_score = smart_score_pro(temp_res)
        
        return {
            "name": name,
            "desc": desc,
            "p": p,
            "rsi": rsi or 0,
            "chg": chg or 0,
            "ratio": ratio,
            "volume": v,
            "avg_volume": avg_v,
            "estimated_value": estimated_value,
            "t_short": t_short,
            "t_med": t_med,
            "t_long": t_long,
            "s1": s1,
            "s2": s2,
            "r1": r1,
            "r2": r2,
            "pp": pp,
            "sma20": sma20,
            "sma50": sma50,
            "sma200": sma200,
            "entry_range": f"{entry_min:.2f} - {entry_max:.2f}",
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "target": target,
            "rr": rr,
            "risk_pct": risk_pct,
            "target_pct": target_pct,
            "smart_score": smart_score,
        }
    except Exception as e:
        return None

def preprocess(raw_data):
    results = []
    for r in raw_data:
        analyzed = analyze_stock(r)
        if analyzed:
            results.append(analyzed)
    return results

def get_top_10(results):
    valid = [r for r in results if r and r.get('smart_score', 0) >= 45]  # تصفية أولية
    sorted_results = sorted(valid, key=lambda x: x.get('smart_score', 0), reverse=True)
    return sorted_results[:10]

def get_fresh_data():
    with st.spinner("🔄 جاري تحليل الأسهم والبحث عن الفرص..."):
        raw = get_all_data()
        if raw:
            st.session_state.all_results = preprocess(raw)
            st.session_state.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
.entry-card { background: #0d1117; border: 1px solid #3fb950; border-radius: 10px; padding: 12px; margin: 10px 0; }
.correction-card { background: linear-gradient(135deg, #1a1a2e, #16213e); border-radius: 12px; padding: 15px; margin-bottom: 15px; border-right: 4px solid #e91e63; }
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
if "last_update" not in st.session_state:
    st.session_state.last_update = None

def render_mode_and_sector():
    with st.expander("🎯 نمط التداول وفلتر القطاع", expanded=False):
        st.markdown("#### 🧠 نمط التداول")
        c1, c2, c3 = st.columns(3)
        if c1.button("🛡️ محافظ", use_container_width=True): 
            st.session_state.mode = "🛡️ محافظ"
        if c2.button("⚖️ متوازن", use_container_width=True): 
            st.session_state.mode = "⚖️ متوازن"
        if c3.button("🚀 هجومي", use_container_width=True): 
            st.session_state.mode = "🚀 هجومي"
        
        color = "#238636" if "محافظ" in st.session_state.mode else "#f85149" if "هجومي" in st.session_state.mode else "#d29922"
        st.markdown(f"<div style='background:{color}; padding:5px; border-radius:8px; text-align:center; color:white; margin:10px 0;'>{st.session_state.mode}</div>", unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("#### 📂 فلتر القطاع")
        sectors = ["🌍 الكل", "🏦 البنوك", "🏗️ العقارات", "🍔 الأغذية", "📡 الاتصالات", "🏭 الصناعات", "🛒 التجارة", "📌 أخرى"]
        selected = st.selectbox("اختر قطاعاً", sectors, index=0)
        if selected != st.session_state.sector_filter:
            st.session_state.sector_filter = selected
            st.rerun()

# ================== 📄 GUIDE SECTION ==================
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
        | **السيولة** | حجم > 1.8x المتوسط | تأكيد اهتمام المؤسسات |
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
        | الاتجاه العام صاعد | السهم في ترند صاعد قوي (إلزامي) |
        | RSI بين 30-50 | السهم في منطقة تصحيح (يرتاح بعد الصعود) |
        | تغير إيجابي | بداية ارتداد من القاع |
        | سيولة جيدة | حجم تداول > المتوسط |
        | RR >= 1.5 | نسبة مخاطرة/عائد جيدة |
        | السعر عند الدعم | منطقة شراء آمنة |
        
        **قوة التصحيح:**
        - 🔥 **65-100%**: فرصة ممتازة - ادخل فوراً
        - ✅ **50-64%**: فرصة جيدة - ادخل بحذر
        - 🟡 **35-49%**: فرصة محتملة - انتظر تأكيد
        """)
    
    with st.expander("🏆 أفضل 10 فرص - أقوى الأسهم اليوم", expanded=True):
        st.markdown("""
        ### كيف يتم ترتيب أفضل 10 فرص؟
        
        يتم ترتيب **جميع الأسهم** تنازلياً حسب **Smart Score المحسن**:
        
        **ما هو Smart Score المحسن؟**
        
        درجة مركبة من **8 عوامل**:
        - الاتجاه قصير المدى (EMA20) - 15 نقطة
        - الاتجاه متوسط المدى (EMA50) - 15 نقطة
        - الاتجاه طويل المدى (EMA200) - 5 نقاط
        - سيولة ممتازة (>2.5x) - 20 نقطة
        - سيولة جيدة (>1.8x) - 15 نقطة
        - RSI مثالي (50-60) - 15 نقطة
        - RR ممتاز (>=2.5) - 15 نقطة
        - زخم الشمعة (>1.5%) - 15 نقطة
        
        **التصنيف:**
        - 80-100: 🔥 فرصة ممتازة جداً
        - 65-79: ✅ فرصة قوية
        - 50-64: ⚠️ فرصة جيدة
        - 0-49: ❄️ ضعيف
        """)
    
    with st.expander("📊 الدعم والمقاومة - Pivot Points", expanded=True):
        st.markdown("""
        ### كيف يتم حساب المستويات؟
        
        ```
        نقطة الارتكاز (PP) = (العالية + المنخفضة + الإغلاق) / 3
        المقاومة الأولى (R1) = (2 × PP) - المنخفضة
        المقاومة الثانية (R2) = PP + (العالية - المنخفضة)
        الدعم الأول (S1) = (2 × PP) - العالية
        الدعم الثاني (S2) = PP - (العالية - المنخفضة)
        ```
        
        ### كيف تستخدمها؟
        
        | المستوى | الاستخدام |
        |----------|-----------|
        | **R2** | هدف بعيد - خذ أرباح عند الاقتراب |
        | **R1** | هدف أول - خذ أرباح جزئية |
        | **PP** | نقطة التوازن - كسرها يغير الاتجاه |
        | **S1** | دعم أول - منطقة دخول محتملة |
        | **S2** | دعم قوي - وقف الخسارة تحتها |
        """)
    
    st.info("💡 **تذكير:** كل هذه المؤشرات أدوات مساعدة. القرار النهائي يعتمد على تحليلك الشخصي وإدارة المخاطر.")

# ================== UI RENDERER (الكامل مع كل الميزات) ==================
def render_stock_card(res, is_top10=False, is_gold=False):
    if res is None:
        st.warning("بيانات السهم غير متوفرة")
        return
    
    # عنوان السهم
    st.markdown(f"<div class='stock-header'>{res['name']} - {res['desc']}<span class='score-tag'>Smart: {res.get('smart_score', 0)}</span></div>", unsafe_allow_html=True)
    
    # كارت الثقة
    render_confidence_card(res)
    
    # تقييم الجودة
    if is_top10:
        if res.get('smart_score', 0) >= 80:
            st.markdown('<div class="quality-excellent">🏆 الأفضل اليوم - فرصة ممتازة</div>', unsafe_allow_html=True)
        elif res.get('smart_score', 0) >= 65:
            st.markdown('<div class="quality-good">⭐ فرصة قوية</div>', unsafe_allow_html=True)
        elif res.get('smart_score', 0) >= 50:
            st.markdown('<div class="quality-good">✅ فرصة جيدة</div>', unsafe_allow_html=True)
    elif is_gold:
        st.markdown('<div class="quality-excellent">💎 فرصة ذهبية - أولوية قصوى</div>', unsafe_allow_html=True)
    
    # عرض السيولة المحسن
    ratio = res.get('ratio', 0)
    estimated_value = res.get('estimated_value', 0)
    value_in_millions = estimated_value / 1000000
    
    if ratio > 2.5:
        vol_text = f"🚀 ممتازة جداً ({ratio:.1f}x)"
    elif ratio > 1.8:
        vol_text = f"⚡ قوية ({ratio:.1f}x)"
    elif ratio > 1.2:
        vol_text = f"🙂 جيدة ({ratio:.1f}x)"
    elif ratio > 0.8:
        vol_text = f"❄️ ضعيفة ({ratio:.1f}x)"
    else:
        vol_text = f"❓ ضعيفة جداً ({ratio:.1f}x)"
    
    # المؤشرات الأساسية
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: st.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:+.2f}%")
    with col2: st.metric("Smart Score", f"{res['smart_score']}/100")
    with col3: st.metric("RR Ratio", f"{res['rr']}")
    with col4: st.metric("RSI", f"{res['rsi']:.0f}")
    with col5: st.metric("السيولة", vol_text, f"{value_in_millions:.1f}M EGP")
    
    # التحليل الفني الكامل
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
        
        # نطاق الدخول (محفوظ كما في الأصلي)
        st.markdown(f"""
        <div class='entry-card'>
            🎯 <b>نطاق الدخول:</b> {res['entry_range']}<br>
            🛑 <b>وقف الخسارة:</b> {res['stop_loss']:.2f} <span style='color:#f85149'>(-{res['risk_pct']:.1f}%)</span><br>
            🏁 <b>المستهدف:</b> {res['target']:.2f} <span style='color:#58a6ff'>(+{res['target_pct']:.1f}%)</span>
        </div>
        """, unsafe_allow_html=True)
        
        # الدعم والمقاومة (كاملاً)
        st.markdown("### 🏛️ مستويات الدعم والمقاومة (Pivot Points)")
        st.markdown(f"""
        | المستوى | السعر | الدلالة |
        |---------|-------|---------|
        | 🔴 **مقاومة ثانية R2** | {res['r2']:.2f} | مقاومة قوية - هدف بعيد |
        | 🔴 **مقاومة أولى R1** | {res['r1']:.2f} | مقاومة أولى - هدف أول |
        | 🟡 **نقطة الارتكاز PP** | {res['pp']:.2f} | المحور - كسرها يغير الاتجاه |
        | 🟢 **دعم أول S1** | {res['s1']:.2f} | دعم أول - منطقة دخول |
        | 🟢 **دعم ثاني S2** | {res['s2']:.2f} | دعم قوي - وقف الخسارة تحتها |
        """)
    
    # إدارة المخاطر وخطة الدخول الكاملة (3 مستويات كما في الأصلي)
    with st.expander("💰 إدارة المخاطر وخطة الدخول", expanded=True):
        deal_size = st.number_input("💰 ميزانية الصفقة (ج)", value=10000, step=1000, key=f"deal_{res['name']}")
        entry_price = res['entry_price']
        
        if deal_size > 0 and entry_price > 0:
            shares_deal = int(deal_size / entry_price)
            actual_value = shares_deal * entry_price
            profit_val = (res['target'] - entry_price) * shares_deal
            loss_val = (entry_price - res['stop_loss']) * shares_deal
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("📦 عدد الأسهم", f"{shares_deal:,}")
                st.metric("💰 قيمة الصفقة", f"{actual_value:,.0f} ج")
            with col2:
                st.metric("🟢 الربح المتوقع", f"{profit_val:,.0f} ج", delta=f"+{res['target_pct']:.1f}%")
                st.metric("🔴 الخسارة المحتملة", f"{loss_val:,.0f} ج", delta=f"-{res['risk_pct']:.1f}%")
            
            # خطة الدخول المتكاملة (3 مستويات)
            st.markdown("### 🏹 خطة الدخول المتكاملة")
            
            range_size = entry_price - res['stop_loss']
            
            entry_level_1 = entry_price
            entry_level_2 = max(entry_price - (range_size * 0.5), res['stop_loss'] * 1.02)
            entry_level_3 = entry_price + (res['target'] - entry_price) * 0.3
            
            # توزيع الوزن حسب قوة الفرصة و RR
            if res['rr'] >= 2.5:
                weights = [0.6, 0.25, 0.15]
            elif res['rr'] >= 1.8:
                weights = [0.5, 0.3, 0.2]
            else:
                weights = [0.4, 0.35, 0.25]
            
            amount_1 = deal_size * weights[0]
            amount_2 = deal_size * weights[1]
            amount_3 = deal_size * weights[2]
            
            shares_1 = int(amount_1 / entry_level_1) if entry_level_1 > 0 else 0
            shares_2 = int(amount_2 / entry_level_2) if entry_level_2 > 0 else 0
            shares_3 = int(amount_3 / entry_level_3) if entry_level_3 > 0 else 0
            
            st.markdown(f"""
            <div style='background:#0d1117;border:1px solid #3fb950;border-radius:10px;padding:12px;margin:10px 0;'>
                <b>📌 المستوى الأول - الدخول الأساسي</b><br>
                🟢 السعر: <b>{entry_level_1:.2f}</b> ج<br>
                📦 الكمية: <b>{shares_1:,}</b> سهم | 💰 المبلغ: <b>{amount_1:,.0f}</b> ج ({weights[0]*100:.0f}% من الميزانية)<br>
                <small>🔹 يتم التنفيذ عند وصول السعر للنطاق</small>
            </div>
            
            <div style='background:#0d1117;border:1px solid #d29922;border-radius:10px;padding:12px;margin:10px 0;'>
                <b>📌 المستوى الثاني - تعزيز الدعم</b><br>
                🟡 السعر: <b>{entry_level_2:.2f}</b> ج<br>
                📦 الكمية: <b>{shares_2:,}</b> سهم | 💰 المبلغ: <b>{amount_2:,.0f}</b> ج ({weights[1]*100:.0f}% من الميزانية)<br>
                <small>🔹 يتم التنفيذ إذا هبط السعر للدعم دون كسر الوقف</small>
            </div>
            
            <div style='background:#0d1117;border:1px solid #58a6ff;border-radius:10px;padding:12px;margin:10px 0;'>
                <b>📌 المستوى الثالث - تأكيد الاختراق</b><br>
                🔵 السعر: <b>{entry_level_3:.2f}</b> ج<br>
                📦 الكمية: <b>{shares_3:,}</b> سهم | 💰 المبلغ: <b>{amount_3:,.0f}</b> ج ({weights[2]*100:.0f}% من الميزانية)<br>
                <small>🔹 يتم التنفيذ عند اختراق مقاومة أولى</small>
            </div>
            """, unsafe_allow_html=True)
            
            total_shares = shares_1 + shares_2 + shares_3
            total_cost = amount_1 + amount_2 + amount_3
            if total_shares > 0:
                avg_price = total_cost / total_shares
                st.info(f"📊 **متوسط السعر بعد التنفيذ الكامل:** {avg_price:.2f} ج ({total_shares:,} سهم)")
        
        # وقف الخسارة المتحرك (محفوظ)
        st.markdown("---")
        st.markdown("### 🎯 وقف الخسارة المتحرك")
        current_price_trail = st.number_input("السعر الحالي", value=res['p'], key=f"trail_{res['name']}")
        highest_price_trail = st.number_input("أعلى سعر تم الوصول إليه", value=res['p'], key=f"high_{res['name']}")
        
        entry = res['entry_price']
        rr = res['rr']
        if current_price_trail <= entry:
            trailing = entry * 0.97
        else:
            profit_pct = (current_price_trail - entry) / entry * 100
            if highest_price_trail > entry:
                trailing = highest_price_trail * 0.96
            elif profit_pct >= 5 and rr >= 1.5:
                trailing = entry + (profit_pct / 2) / 100 * entry
                trailing = min(trailing, current_price_trail * 0.98)
            elif profit_pct >= 3:
                trailing = entry
            else:
                trailing = entry * 0.97
        
        st.info(f"🛡️ **وقف الخسارة المتحرك المقترح:** {trailing:.2f} ج (الأصلي: {res['stop_loss']:.2f} ج)")
        
        st.warning("⚠️ **تذكير:** هذه الخطة استرشادية. القرار النهائي يعتمد على تحليلك الشخصي وظروف السوق.")
    
    # تحليل الوضع الحالي (PnL - محفوظ)
    with st.expander("🧠 تحليل الوضع الحالي (لو معاك السهم)", expanded=False):
        col1, col2 = st.columns(2)
        buy_price = col1.number_input("سعر الشراء", value=res['p'], key=f"buy_{res['name']}")
        qty = col2.number_input("الكمية", value=100, step=100, key=f"qty_{res['name']}")
        
        if qty > 0 and buy_price > 0:
            current = res['p']
            pnl = (current - buy_price) * qty
            pnl_pct = ((current - buy_price) / buy_price) * 100
            
            if pnl > 0:
                st.success(f"🟢 كسبان: {pnl:,.0f} ج (+{pnl_pct:.2f}%)")
                if pnl_pct >= 3:
                    st.info(f"💡 حرك الوقف لنقطة الدخول: {buy_price:.2f}")
            elif pnl < 0:
                st.error(f"🔴 خسران: {pnl:,.0f} ج ({pnl_pct:.2f}%)")
            else:
                st.info("⚖️ على التعادل")
            
            if current >= res['target']:
                st.success("🎉 تم تحقيق الهدف!")
            elif current <= res['stop_loss']:
                st.error("⚠️ كسر وقف الخسارة!")
            
            trend_score = (1 if res['t_short'] == "صاعد" else 0) + (1 if res['t_med'] == "صاعد" else 0) + (1 if res['ratio'] > 1.5 else 0)
            if trend_score >= 2:
                st.success(f"✅ استمر طالما السعر فوق {res['stop_loss']:.2f}")
            else:
                st.warning("⚠️ اتجاه ضعيف - فكر في تأمين الأرباح")
    
    # مؤشرات متقدمة (Stochastic RSI ونسبة النجاح - محفوظ)
    with st.expander("📈 مؤشرات متقدمة", expanded=False):
        rsi = res['rsi']
        if rsi <= 20:
            stoch_signal = "🟢 تشبع بيع - فرصة انعكاس قوية"
        elif rsi <= 35:
            stoch_signal = "🟡 منطقة شراء محتملة"
        elif rsi <= 65:
            stoch_signal = "⚪ منطقة حيادية"
        elif rsi <= 80:
            stoch_signal = "🟠 منطقة بيع محتملة - خطر"
        else:
            stoch_signal = "🔴 تشبع شراء - خطر كبير"
        
        st.markdown(f"""
        <div style='background:#0d1117;border:1px solid #30363d;border-radius:10px;padding:12px;margin-bottom:15px;'>
            <b>🔄 تحليل RSI (Stochastic)</b><br>
            🧠 {stoch_signal}
        </div>
        """, unsafe_allow_html=True)
        
        # نسبة النجاح المتوقعة المحسنة
        success_rate = 50
        if res['smart_score'] >= 80 and res['rr'] >= 2 and 45 < res['rsi'] < 60:
            success_rate = 80
        elif res['smart_score'] >= 65 and res['rr'] >= 1.5:
            success_rate = 70
        elif res['smart_score'] >= 50 and res['rr'] >= 1.2:
            success_rate = 60
        elif res['smart_score'] >= 40:
            success_rate = 50
        else:
            success_rate = 35
        
        st.markdown(f"""
        <div style='background:#0d1117;border:1px solid #d29922;border-radius:10px;padding:12px;margin-bottom:15px;'>
            <b>📈 نسبة النجاح المتوقعة</b><br>
            🎯 <b>{success_rate}%</b>
            <div style='height:4px; background:#333; margin-top:8px;'><div style='width:{success_rate}%; background:#d29922; height:4px;'></div></div>
        </div>
        """, unsafe_allow_html=True)
    
    # مشاركة واتساب
    msg = f"📊 تحليل سهم {res['name']}\n💰 السعر: {res['p']:.2f} ج\n🎯 ثقة القناص: {get_confidence(res)['score']}%\n🎯 الدخول: {res['entry_range']}\n🛑 الوقف: {res['stop_loss']:.2f}\n🏁 الهدف: {res['target']:.2f}\n⚖️ RR: {res['rr']}\n💧 السيولة: {res['ratio']:.1f}x"
    encoded = urllib.parse.quote(msg)
    st.markdown(f"[📱 مشاركة عبر واتساب](https://wa.me/?text={encoded})")

def render_correction_card(an, reasons, strength, strength_label, strength_color):
    """عرض بطاقة صائد التصحيحات بشكل منفصل"""
    st.markdown(f"""
    <div class="correction-card" style="border-right-color: {strength_color};">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
            <h3 style="margin: 0; color: #e91e63;">🎯 {an['name']} - {an['desc']}</h3>
            <span style="background: {strength_color}; padding: 5px 15px; border-radius: 20px; font-weight: bold;">
                {strength_label} | {strength}%
            </span>
        </div>
        <div style="height: 6px; background: #333; margin: 10px 0;">
            <div style="width: {strength}%; background: {strength_color}; height: 6px; border-radius: 3px;"></div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 10px 0;">
            <div>💰 {an['p']:.2f} ج</div>
            <div>📊 RSI: {an['rsi']:.1f}</div>
            <div>💧 سيولة: {an['ratio']:.1f}x</div>
            <div>📈 تغير: {an['chg']:+.2f}%</div>
        </div>
        <div style="background: rgba(233,30,99,0.1); border-radius: 8px; padding: 8px; margin: 10px 0;">
            ✅ <b>أسباب الاختيار:</b> {', '.join(reasons)}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # عرض التحليل الكامل للسهم
    render_stock_card(an)

# ================== PAGES ==================
def main():
    # جلب البيانات أول مرة
    if st.session_state.all_results is None:
        get_fresh_data()
    
    # تحليل السوق
    market_status = get_egx30_status()
    
    # الشاشة الرئيسية
    if st.session_state.page == 'home':
        st.title("🎯 قناص EGX - النسخة المتكاملة")
        st.caption("تحليل فني متقدم + صائد التصحيحات + مستويات دخول دقيقة")
        
        # عرض حالة السوق
        st.markdown(f"""
        <div style="background: #0d1117; border-radius: 10px; padding: 10px; margin-bottom: 20px; text-align: center;">
            <span style="color: {market_status['color']}; font-weight: bold;">📊 المؤشر العام EGX30:</span>
            <span>{market_status['status']}</span>
            <span style="margin-left: 20px;">RSI: {market_status['rsi']:.0f}</span>
            <span style="margin-left: 20px;">التغير: {market_status['change']:+.2f}%</span>
            <span style="margin-left: 20px;">قوة السوق: {market_status['market_multiplier']*100:.0f}%</span>
        </div>
        """, unsafe_allow_html=True)
        
        # نمط التداول وفلتر القطاع
        render_mode_and_sector()
        
        # الأزرار الرئيسية
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🏆 أفضل 10 فرص", use_container_width=True):
                st.session_state.page = 'top10'
                st.rerun()
        with col2:
            if st.button("🎯 صائد التصحيحات", use_container_width=True):
                st.session_state.page = 'correction'
                st.rerun()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🔍 تحليل سهم", use_container_width=True):
                st.session_state.page = 'analyze'
                st.rerun()
        with col2:
            if st.button("📊 تقييم الأداء", use_container_width=True):
                st.session_state.page = 'performance'
                st.rerun()
        with col3:
            if st.button("📖 دليل الأقسام", use_container_width=True):
                st.session_state.page = 'guide'
                st.rerun()
        
        # إدارة التطبيق
        with st.expander("⚙️ إدارة التطبيق", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 تحديث البيانات", use_container_width=True):
                    get_fresh_data()
                    st.success(f"✅ تم تحديث البيانات! {st.session_state.last_update}")
                    st.rerun()
            with col2:
                if st.button("🗑️ مسح بيانات التقييم", use_container_width=True):
                    if os.path.exists(TRADES_FILE):
                        os.remove(TRADES_FILE)
                        st.success("✅ تم مسح البيانات!")
                        st.rerun()
        
        # إحصائيات سريعة
        sector_filter = st.session_state.sector_filter
        filtered = filter_by_sector(st.session_state.all_results, sector_filter)
        if filtered:
            excellent = len([r for r in filtered if r.get('smart_score', 0) >= 80])
            good = len([r for r in filtered if 65 <= r.get('smart_score', 0) < 80])
            st.markdown(f"""
            <div style='background:#0d1117;border-radius:10px;padding:15px;margin-top:20px;'>
                <b>📊 إحصائية السوق</b><br>
                • القطاع: {sector_filter}<br>
                • إجمالي الأسهم: {len(filtered)}<br>
                • 🔥 فرص ممتازة (Smart >= 80): {excellent}<br>
                • ✅ فرص جيدة (Smart 65-79): {good}<br>
                • 🕐 آخر تحديث: {st.session_state.last_update}
            </div>
            """, unsafe_allow_html=True)
    
    # ================== أفضل 10 فرص ==================
    elif st.session_state.page == 'top10':
        if st.button("🏠 العودة للرئيسية"): 
            st.session_state.page = 'home'
            st.rerun()
        
        st.title("🏆 أفضل 10 فرص ليوم الغد")
        st.caption("مرتبة حسب Smart Score المحسن (8 عوامل)")
        
        sector_filter = st.session_state.sector_filter
        filtered = filter_by_sector(st.session_state.all_results, sector_filter)
        top = get_top_10(filtered)
        
        if top:
            for i, an in enumerate(top, 1):
                with st.expander(f"#{i} - {an['name']} | Smart: {an['smart_score']} | RR: {an['rr']} | RSI: {an['rsi']:.0f}"):
                    render_stock_card(an, is_top10=True)
                    if st.button(f"💾 تسجيل الصفقة", key=f"rec_{an['name']}"):
                        record_trade(an, "top10")
                        st.success("✅ تم تسجيل الصفقة في تقييم الأداء!")
        else:
            st.warning("⚠️ لا توجد فرص مطابقة للمعايير حالياً. حاول تحديث البيانات لاحقاً.")
    
    # ================== صائد التصحيحات ==================
    elif st.session_state.page == 'correction':
        if st.button("🏠 العودة للرئيسية"): 
            st.session_state.page = 'home'
            st.rerun()
        
        st.title("🎯 صائد التصحيحات")
        st.markdown("""
        <div class='info-box'>
        🎯 <b>كيف تم الاختيار؟</b><br>
        • الاتجاه العام صاعد (إلزامي) | • RSI في التصحيح (30-50) | • بداية ارتداد | • سيولة جيدة | • RR جيد | • السعر عند الدعم
        </div>
        """, unsafe_allow_html=True)
        
        # عرض قوة السوق
        market_status = get_egx30_status()
        st.info(f"📊 حالة السوق: {market_status['status']} - تؤثر على قوة فرص التصحيح")
        
        sector_filter = st.session_state.sector_filter
        filtered = filter_by_sector(st.session_state.all_results, sector_filter)
        
        corrections = []
        for an in filtered:
            if an:
                corr_analysis = is_correction(an, market_status['market_multiplier'])
                if corr_analysis.get('is_correction', False):
                    corrections.append({
                        'stock': an,
                        'reasons': corr_analysis['reasons'],
                        'strength': corr_analysis['strength'],
                        'strength_label': corr_analysis['strength_label'],
                        'strength_color': corr_analysis['strength_color']
                    })
        
        if corrections:
            corrections.sort(key=lambda x: x['strength'], reverse=True)
            st.markdown(f"**🎯 عدد فرص التصحيح: {len(corrections)}**")
            
            for item in corrections:
                render_correction_card(
                    item['stock'], 
                    item['reasons'], 
                    item['strength'],
                    item['strength_label'],
                    item['strength_color']
                )
                st.markdown("---")
        else:
            st.info("ℹ️ لا توجد فرص تصحيح حالياً. قد يكون السوق في قمة أو الأسهم لم تصحح بعد.")
    
    # ================== تحليل سهم فردي ==================
    elif st.session_state.page == 'analyze':
        if st.button("🏠 العودة للرئيسية"): 
            st.session_state.page = 'home'
            st.rerun()
        
        st.title("🔍 تحليل سهم")
        sym = st.text_input("🔎 أدخل رمز السهم", placeholder="مثال: COMI, TMGH, ETEL").upper().strip()
        
        if sym:
            data = [r for r in st.session_state.all_results if r and r.get('name') == sym]
            if data:
                render_stock_card(data[0])
                if st.button(f"💾 تسجيل الصفقة", key=f"rec_analyze_{sym}"):
                    record_trade(data[0], "تحليل فردي")
                    st.success("✅ تم تسجيل الصفقة في تقييم الأداء!")
            else:
                st.error(f"❌ السهم '{sym}' غير موجود في البيانات")
                symbols = [r.get('name') for r in st.session_state.all_results[:20] if r]
                if symbols:
                    st.info(f"💡 أمثلة لرموز متاحة: {', '.join(symbols[:10])}")
    
    # ================== تقييم الأداء ==================
    elif st.session_state.page == 'performance':
        if st.button("🏠 العودة للرئيسية"): 
            st.session_state.page = 'home'
            st.rerun()
        
        st.title("📊 تقييم الأداء")
        
        trades = load_trades()
        stats = get_performance_stats(trades)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📊 إجمالي الصفقات", stats['total'])
        col2.metric("✅ تم تحقيق الهدف", stats['hit_target'])
        col3.metric("❌ تم وقف الخسارة", stats['stopped_out'])
        col4.metric("⏳ لا تزال مفتوحة", stats['still_open'])
        
        col1, col2 = st.columns(2)
        col1.metric("📈 نسبة النجاح", f"{stats['success_rate']}%")
        col2.metric("⚖️ متوسط RR", stats['avg_rr'])
        
        if trades:
            st.markdown("### 📋 آخر الصفقات المسجلة")
            for trade in trades[-15:][::-1]:
                status = "🟢 تم الهدف" if trade.get('status') == 'hit_target' else "🔴 تم الوقف" if trade.get('status') == 'stopped_out' else "🟡 قيد التنفيذ"
                st.markdown(f"""
                <div style='background:#0d1117;border-radius:8px;padding:10px;margin:5px 0;'>
                    <b>{trade.get('name')}</b> ({trade.get('trade_type')}) - {status}<br>
                    📅 {trade.get('date_recorded')} | 🎯 دخول: {trade.get('entry_price', 0):.2f} | ⚖️ RR: {trade.get('rr', 0)}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("ℹ️ لا توجد صفقات مسجلة بعد. استخدم زر 'تسجيل الصفقة' عند تحليل أي سهم.")
    
    # ================== دليل الأقسام ==================
    elif st.session_state.page == 'guide':
        if st.button("🏠 العودة للرئيسية"): 
            st.session_state.page = 'home'
            st.rerun()
        render_guide()

if __name__ == "__main__":
    main()
