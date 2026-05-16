import streamlit as st
import streamlit.components.v1 as components
import requests
from datetime import datetime, date
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

# ================== 🎨 CSS محسن بالكامل ==================
st.markdown("""
<style>
    /* تنسيق عام - خطوط أكبر */
    .main-header {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 20px;
        text-align: center;
    }
    .main-header h1 {
        color: #58a6ff;
        margin: 0;
        font-size: 32px;
    }
    .main-header p {
        color: #8b949e;
        margin: 5px 0 0;
        font-size: 14px;
    }
    
    /* ================== تنسيق الشريط الجانبي ================== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117, #0a0c10);
        border-right: 1px solid #30363d;
        padding: 20px 10px;
    }
    
    /* عنوان الشريط الجانبي */
    .sidebar-title {
        text-align: center;
        padding: 15px 0;
        border-bottom: 2px solid #30363d;
        margin-bottom: 20px;
    }
    .sidebar-title h2 {
        color: #58a6ff;
        margin: 0;
        font-size: 24px;
    }
    .sidebar-title p {
        color: #8b949e;
        font-size: 12px;
        margin: 5px 0 0;
    }
    
    /* أزرار التنقل في الشريط الجانبي - واضحة وكبيرة */
    .stSidebar .stButton button {
        width: 100%;
        text-align: right;
        background-color: #1f2937;
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 14px 18px;
        margin: 6px 0;
        font-size: 16px;
        font-weight: 600;
        color: #e5e7eb;
        transition: all 0.2s ease;
        cursor: pointer;
    }
    .stSidebar .stButton button:hover {
        background-color: #374151;
        border-color: #3b82f6;
        color: white;
        transform: translateX(-3px);
    }
    
    /* ================== حالة السوق ================== */
    .market-status {
        background: #0d1117;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 20px;
        border: 1px solid #30363d;
        text-align: center;
        font-size: 16px;
    }
    
    /* ================== بطاقات الأسهم ================== */
    .stock-card {
        background: linear-gradient(135deg, #0d1117, #0a0c10);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid #30363d;
        transition: all 0.2s ease;
    }
    .stock-card:hover {
        border-color: #58a6ff;
        transform: translateY(-2px);
    }
    
    .stock-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
        border-bottom: 1px solid #30363d;
        padding-bottom: 12px;
    }
    .stock-name {
        font-size: 22px;
        font-weight: bold;
        color: #58a6ff;
    }
    .stock-desc {
        font-size: 14px;
        color: #8b949e;
        margin-right: 10px;
    }
    .smart-badge {
        background: #238636;
        padding: 6px 16px;
        border-radius: 25px;
        font-size: 14px;
        font-weight: bold;
        color: white;
    }
    
    /* صفوف البيانات */
    .flex-row {
        display: flex;
        flex-wrap: wrap;
        gap: 24px;
        align-items: center;
        margin: 15px 0;
    }
    .metric-box {
        text-align: center;
        min-width: 80px;
    }
    .metric-value {
        font-size: 28px;
        font-weight: bold;
    }
    .metric-label {
        font-size: 13px;
        color: #8b949e;
        margin-top: 4px;
    }
    
    /* شريط القوة */
    .strength-bar {
        height: 6px;
        background: #30363d;
        border-radius: 3px;
        margin: 12px 0;
        overflow: hidden;
    }
    .strength-fill {
        height: 100%;
        border-radius: 3px;
        transition: width 0.3s;
    }
    .strength-high { background: #3fb950; }
    .strength-mid { background: #d29922; }
    .strength-low { background: #f85149; }
    
    /* ================== بطاقة ثقة القناص ================== */
    .confidence-card {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border-radius: 14px;
        padding: 16px;
        margin: 15px 0;
        border-right: 4px solid;
    }
    .confidence-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    .confidence-title {
        font-size: 18px;
        font-weight: bold;
    }
    .confidence-score {
        font-size: 32px;
        font-weight: bold;
    }
    .confidence-advice {
        font-size: 16px;
        margin-top: 8px;
    }
    
    /* ================== مستويات الدخول ================== */
    .entry-level {
        background: #0d1117;
        border-radius: 12px;
        padding: 14px;
        margin: 10px 0;
        border-right: 3px solid;
    }
    .level-1 { border-right-color: #3fb950; }
    .level-2 { border-right-color: #d29922; }
    .level-3 { border-right-color: #58a6ff; }
    
    /* ================== تبويبات ================== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #0d1117;
        border-radius: 10px;
        padding: 10px 20px;
        font-size: 16px;
        font-weight: 500;
    }
    
    /* ================== شريط سفلي ================== */
    .footer {
        background: #0d1117;
        padding: 12px 20px;
        border-radius: 12px;
        margin-top: 30px;
        font-size: 14px;
        color: #8b949e;
        text-align: center;
        border-top: 1px solid #30363d;
    }
    .flex-between {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 10px;
    }
</style>
""", unsafe_allow_html=True)


# ================== 📁 PERFORMANCE TRACKING ==================
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
    except:
        pass

def record_trade(res, trade_type):
    if res is None:
        return
    trades = load_trades()
    today = datetime.now().strftime("%Y-%m-%d")
    
    for t in trades:
        if (t.get('name') == res.get('name') and 
            t.get('date_recorded') == today and
            t.get('trade_type') == trade_type):
            return
    
    trades.append({
        "name": res.get('name', 'N/A'),
        "desc": res.get('desc', 'N/A'),
        "entry_price": res.get('entry_price', 0),
        "entry_min": res.get('entry_min', 0),
        "entry_max": res.get('entry_max', 0),
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
    if not trades:
        return {'total': 0, 'hit_target': 0, 'stopped_out': 0, 'still_open': 0, 'success_rate': 0, 'avg_rr': 0}
    
    hit_target = len([t for t in trades if t.get('status') == 'hit_target'])
    stopped_out = len([t for t in trades if t.get('status') == 'stopped_out'])
    still_open = len([t for t in trades if t.get('status') in ['pending', 'still_open']])
    closed = hit_target + stopped_out
    success_rate = (hit_target / closed * 100) if closed > 0 else 0
    avg_rr = sum(t.get('rr', 0) for t in trades) / len(trades) if trades else 0
    
    return {
        'total': len(trades), 'hit_target': hit_target, 'stopped_out': stopped_out,
        'still_open': still_open, 'success_rate': round(success_rate, 1), 'avg_rr': round(avg_rr, 2)
    }


# ================== 📈 MARKET & DATA FUNCTIONS ==================
@st.cache_data(ttl=600, show_spinner=False)
def get_egx30_status():
    try:
        url = "https://scanner.tradingview.com/egypt/scan"
        payload = {
            "filter": [{"left": "symbol", "operation": "equal", "right": "EGX30"}],
            "columns": ["close", "RSI", "SMA50", "SMA200", "change"],
            "range": [0, 1]
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json().get("data", [])
            if data and len(data) > 0:
                d = data[0].get('d', [])
                if len(d) >= 5:
                    price = d[0] if d[0] else 10000
                    rsi = d[1] if d[1] else 50
                    sma50 = d[2] if d[2] else price
                    sma200 = d[3] if d[3] else price
                    change = d[4] if d[4] else 0
                    
                    score = 0
                    if price > sma200: score += 1
                    if price > sma50: score += 1
                    if 40 < rsi < 70: score += 1
                    if change > -0.5: score += 1
                    
                    if score >= 3:
                        status = "🟢 سوق صاعد - مناسب للتداول"
                        color = "#00FF00"
                    elif score >= 2:
                        status = "🟡 سوق متذبذب - تداول بحذر"
                        color = "#FFA500"
                    else:
                        status = "🔴 سوق هابط - ركز على التصحيحات"
                        color = "#FF4444"
                    
                    return {"status": status, "color": color, "rsi": rsi, "change": change, "price": price}
    except:
        pass
    return {"status": "🟡 سوق متذبذب", "color": "#FFA500", "rsi": 50, "change": 0, "price": 10000}

@st.cache_data(ttl=300, show_spinner=False)
def get_all_data():
    url = "https://scanner.tradingview.com/egypt/scan"
    cols = ["name", "close", "RSI", "volume", "average_volume_10d_calc", "high", "low", "change", "description", "SMA20", "SMA50", "SMA200"]
    payload = {"filter": [], "columns": cols, "range": [0, 300]}
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json().get("data", [])
        return []
    except:
        return []

def fetch_single_stock(symbol):
    url = "https://scanner.tradingview.com/egypt/scan"
    cols = ["name", "close", "RSI", "volume", "average_volume_10d_calc", "high", "low", "change", "description", "SMA20", "SMA50", "SMA200"]
    payload = {"filter": [{"left": "name", "operation": "match", "right": symbol.upper()}], "columns": cols, "range": [0, 1]}
    try:
        r = requests.post(url, json=payload, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        if r.status_code == 200:
            data = r.json().get("data", [])
            if data and len(data) > 0:
                return data
        return []
    except:
        return []


# ================== 🔥 SMART SCORE & ANALYSIS ==================
def smart_score_pro(res):
    score = 0
    if res.get('t_short') == "صاعد": score += 15
    if res.get('t_med') == "صاعد": score += 15
    if res.get('t_long') == "صاعد": score += 5
    if res.get('ratio', 0) > 2.5: score += 20
    elif res.get('ratio', 0) > 1.8: score += 15
    elif res.get('ratio', 0) > 1.2: score += 8
    if 50 < res.get('rsi', 50) < 65: score += 15
    elif 45 < res.get('rsi', 50) <= 50: score += 10
    elif 35 <= res.get('rsi', 50) <= 45: score += 5
    if res.get('rr', 0) >= 2.5: score += 15
    elif res.get('rr', 0) >= 2: score += 12
    elif res.get('rr', 0) >= 1.5: score += 8
    return min(100, int(score))

def calculate_stochastic_rsi(rsi):
    if rsi <= 20: return {"k": 90, "d": 85, "signal": "🟢 تشبع بيع - فرصة انعكاس"}
    elif rsi <= 35: return {"k": 70, "d": 65, "signal": "🟡 منطقة شراء محتملة"}
    elif rsi <= 65: return {"k": 50, "d": 50, "signal": "⚪ منطقة حيادية"}
    elif rsi <= 80: return {"k": 30, "d": 35, "signal": "🟠 منطقة بيع محتملة"}
    else: return {"k": 10, "d": 15, "signal": "🔴 تشبع شراء - خطر"}

def get_rr_rating(rr):
    if rr < 1: return "❌ ضعيف", "مخاطرة أعلى من العائد"
    elif rr < 1.5: return "⚠️ متوسط", "مضاربة سريعة فقط"
    elif rr < 2: return "✅ جيد", "صفقة كويسة"
    else: return "🔥 ممتاز", "فرصة قوية جداً"

def get_volume_rating(ratio):
    if ratio == 0: return "❓ غير معروف", "لا توجد بيانات كافية"
    elif ratio < 1: return "❄️ ضعيفة", "سيولة ضعيفة"
    elif ratio < 1.5: return "🙂 عادية", "سيولة طبيعية"
    elif ratio < 2: return "⚡ نشطة", "اهتمام بالسهم"
    else: return "🚀 قوية", "سيولة عالية"

def expected_success_rate(res):
    score = 0
    trends = [res.get('t_short', 'هابط'), res.get('t_med', 'هابط'), res.get('t_long', 'هابط')]
    if all(t == "صاعد" for t in trends):
        score += 30
    elif trends.count("صاعد") >= 2:
        score += 20
    
    ratio = res.get('ratio', 0)
    if ratio > 2: score += 25
    elif ratio > 1.5: score += 15
    elif ratio > 1: score += 8
    
    if res.get('rr', 0) >= 2: score += 10
    elif res.get('rr', 0) >= 1.5: score += 5
    
    success_rate = min(85, max(0, score))
    level = "🔥 ممتازة" if success_rate >= 70 else "✅ جيدة" if success_rate >= 55 else "⚠️ متوسطة"
    return success_rate, level


# ================== 🎯 SYSTEME DE CONFIDENCE (7 COUCHES) ==================
def calculate_technical_score(stock):
    """التحليل الفني المتقدم - الطبقة الأولى"""
    score = 0
    # اتجاهات (40 نقطة)
    if stock.get('t_long') == "صاعد": score += 15
    if stock.get('t_med') == "صاعد": score += 15
    if stock.get('t_short') == "صاعد": score += 10
    # RSI (20 نقطة)
    rsi = stock.get('rsi', 50)
    if 45 <= rsi <= 55: score += 20
    elif 40 <= rsi <= 60: score += 15
    elif 35 <= rsi <= 65: score += 10
    # RR Ratio (20 نقطة)
    rr = stock.get('rr', 0)
    if rr >= 2.5: score += 20
    elif rr >= 2: score += 15
    elif rr >= 1.5: score += 10
    # SMA20 (20 نقطة)
    if stock.get('above_sma20', False): score += 20
    elif stock.get('p', 0) > stock.get('sma20', 0): score += 20
    return min(100, score)

def calculate_liquidity_score(stock):
    """تحليل السيولة - الطبقة الثانية"""
    ratio = stock.get('ratio', 0)
    score = 0
    if ratio > 2.5: score += 50
    elif ratio > 1.8: score += 40
    elif ratio > 1.2: score += 30
    elif ratio > 0.8: score += 20
    else: score += 10
    
    if stock.get('daily_turnover', 0) > 5000000: score += 30
    elif stock.get('daily_turnover', 0) > 2000000: score += 20
    elif stock.get('daily_turnover', 0) > MIN_DAILY_TURNOVER: score += 10
    
    return min(100, score)

def calculate_momentum_score(stock):
    """تحليل الزخم - الطبقة الثالثة"""
    chg = stock.get('chg', 0)
    rsi = stock.get('rsi', 50)
    score = 0
    
    if chg > 2: score += 40
    elif chg > 1: score += 30
    elif chg > 0: score += 20
    elif chg > -1: score += 10
    
    if 55 <= rsi <= 70: score += 40
    elif 50 <= rsi < 55: score += 30
    elif 45 <= rsi < 50: score += 20
    
    return min(100, score)

def calculate_trend_score(stock, market_status):
    """تحليل الاتجاه العام - الطبقة الرابعة"""
    score = 0
    if stock.get('t_long') == "صاعد": score += 35
    if stock.get('t_med') == "صاعد": score += 35
    
    if "صاعد" in market_status.get('status', ''): score += 30
    elif "متذبذب" in market_status.get('status', ''): score += 15
    
    return min(100, score)

def get_confidence_score(stock, market_status):
    """
    نظام الثقة فائق الدقة - 4 طبقات تحليل متقدمة
    كل طبقة تعطي درجة من 0-100
    """
    
    scores = {
        "technical": calculate_technical_score(stock),
        "liquidity": calculate_liquidity_score(stock),
        "momentum": calculate_momentum_score(stock),
        "trend": calculate_trend_score(stock, market_status)
    }
    
    weights = {
        "technical": 35,
        "liquidity": 25,
        "momentum": 20,
        "trend": 20
    }
    
    total_weighted = 0
    total_weight = 0
    weak_layers = []
    
    for layer, score in scores.items():
        weight = weights[layer]
        total_weighted += score * weight
        total_weight += weight
        
        if score < 50:
            weak_layers.append(layer)
    
    final_score = int(total_weighted / total_weight) if total_weight > 0 else 0
    
    # قرارات بناءً على الثقة
    if final_score >= 85:
        advice = "🔥🔥 فرصة ذهبية مؤكدة - دخول قوي"
        color = "#00FF00"
        emoji = "🔥🔥"
        risk_level = "منخفض"
    elif final_score >= 75:
        advice = "🔥 فرصة ممتازة - دخول"
        color = "#ADFF2F"
        emoji = "🔥"
        risk_level = "منخفض-متوسط"
    elif final_score >= 65:
        advice = "✅ فرصة جيدة - دخول بحذر"
        color = "#FFD700"
        emoji = "✅"
        risk_level = "متوسط"
    elif final_score >= 55:
        advice = "🟡 مراقبة - انتظار تأكيد إضافي"
        color = "#FFA500"
        emoji = "🟡"
        risk_level = "مرتفع"
    else:
        advice = "❌ تجنب - غير مطابق للمعايير"
        color = "#FF4444"
        emoji = "❌"
        risk_level = "عالي جداً"
    
    return {
        'score': final_score,
        'advice': advice,
        'color': color,
        'emoji': emoji,
        'risk_level': risk_level,
        'layers': scores,
        'weak_layers': weak_layers
    }


# ================== 🎯 CORRECTION HUNTER ==================
def is_correction_hunter(an):
    if an is None:
        return False, [], 0
    
    p = an.get('p', 0)
    rsi = an.get('rsi', 50)
    sma200 = an.get('sma200', 0)
    ratio = an.get('ratio', 0)
    change_pct = an.get('chg', 0)
    t_long = an.get('t_long', 'هابط')
    rr = an.get('rr', 0)
    
    reasons = []
    score = 0
    max_score = 10
    
    if t_long == "صاعد" or (sma200 and p > sma200):
        score += 3
        reasons.append("📈 الاتجاه العام صاعد")
    else:
        return False, ["الاتجاه العام هابط"], 0
    
    if 28 <= rsi <= 55:
        score += 3
        if rsi < 35:
            reasons.append(f"🔻 RSI منخفض جداً ({rsi:.0f}) - تشبع بيع ممتاز")
        elif rsi < 45:
            reasons.append(f"🔻 RSI منخفض ({rsi:.0f}) - منطقة تصحيح جيدة")
        else:
            reasons.append(f"📊 RSI في منطقة محايدة ({rsi:.0f})")
    else:
        return False, [f"RSI خارج نطاق التصحيح ({rsi:.0f})"], 0
    
    if change_pct > 0:
        score += 2
        reasons.append(f"📈 تغير إيجابي ({change_pct:+.2f}%)")
    elif change_pct > -1:
        score += 1
        reasons.append(f"⚖️ تغير طفيف ({change_pct:+.2f}%) - استقرار")
    
    if ratio > 1.2:
        score += 1
        reasons.append(f"💧 سيولة ممتازة ({ratio:.1f}x)")
    elif ratio > 0.7:
        score += 0.5
        reasons.append(f"💧 سيولة جيدة ({ratio:.1f}x)")
    
    if rr >= 1.5:
        score += 1
        reasons.append(f"⚖️ RR جيد ({rr})")
    
    strength_percent = int((score / max_score) * 100)
    
    if score >= 4:
        return True, reasons, strength_percent
    else:
        return False, [f"درجة منخفضة ({score}/{max_score})"], strength_percent


# ================== ⚡ RAPID BREAKOUT ==================
def is_rapid_breakout(an):
    if an is None:
        return {"is_breakout": False, "reasons": [], "strength": 0, "label": "", "color": "#555"}
    
    p = an.get('p', 0)
    rsi = an.get('rsi', 50)
    ratio = an.get('ratio', 0)
    change = an.get('chg', 0)
    t_short = an.get('t_short', 'هابط')
    t_med = an.get('t_med', 'هابط')
    r1 = an.get('r1', p * 1.05)
    
    reasons = []
    score = 0
    max_score = 7
    
    if 52 <= rsi <= 75:
        score += 2
        reasons.append(f"⚡ زخم قوي (RSI: {rsi:.0f})")
    elif 45 <= rsi < 52:
        score += 1
        reasons.append(f"📈 زخم إيجابي (RSI: {rsi:.0f})")
    else:
        return {"is_breakout": False, "reasons": reasons, "strength": 0, "label": "", "color": "#555"}
    
    if ratio > 2.2:
        score += 2
        reasons.append(f"💥 سيولة استثنائية ({ratio:.1f}x)")
    elif ratio > 1.5:
        score += 1.5
        reasons.append(f"🚀 سيولة قوية ({ratio:.1f}x)")
    elif ratio > 1.0:
        score += 1
        reasons.append(f"📊 سيولة جيدة ({ratio:.1f}x)")
    else:
        return {"is_breakout": False, "reasons": reasons, "strength": 0, "label": "", "color": "#555"}
    
    if p >= r1 * 0.98:
        score += 2
        reasons.append(f"🎯 على وشك اختراق R1 ({r1:.2f})")
    elif p >= r1 * 0.95:
        score += 1
        reasons.append(f"📍 قريب من المقاومة R1")
    else:
        return {"is_breakout": False, "reasons": reasons, "strength": 0, "label": "", "color": "#555"}
    
    if t_short == "صاعد" and t_med == "صاعد":
        score += 1
        reasons.append("📊 الاتجاهات صاعدة")
    
    strength = int((score / max_score) * 100)
    
    if strength >= 70:
        label = "🔥 اختراق وشيك خلال ساعات"
        color = "#FF6666"
    elif strength >= 55:
        label = "⚡ اختراق متوقع خلال جلسة"
        color = "#FFB347"
    elif strength >= 40:
        label = "🟡 مراقبة لاصطياد الاختراق"
        color = "#FFD700"
    else:
        return {"is_breakout": False, "reasons": reasons, "strength": 0, "label": "", "color": "#555"}
    
    return {
        "is_breakout": True,
        "reasons": reasons,
        "strength": strength,
        "label": label,
        "color": color
    }


# ================== 📊 STOCK ANALYSIS ==================
def analyze_stock(d_row):
    try:
        d = d_row.get('d', [])
        if len(d) < 12:
            return None
        
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
        
        # الدعوم والمقاومات
        pp = (p + h + l) / 3
        r1 = (2 * pp) - l
        r2 = pp + (h - l)
        s1 = (2 * pp) - h
        s2 = pp - (h - l)
        
        # نطاق الدخول
        entry_min = p * 0.98
        entry_max = p * 1.01
        entry_price = (entry_min + entry_max) / 2
        
        # وقف الخسارة الفني
        technical_stop = s1 * 0.99 if s1 > 0 else p * 0.96
        max_risk_stop = p * (1 - MAX_RISK_PCT / 100)
        stop_loss = max(technical_stop, max_risk_stop)
        
        # الهدف
        target = r1 if r1 > p else p * 1.05
        
        # حساب RR
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
        
        # Smart Score
        temp_res = {
            't_short': t_short, 't_med': t_med, 't_long': t_long,
            'ratio': ratio, 'rsi': rsi, 'rr': rr, 'chg': chg
        }
        smart_score = smart_score_pro(temp_res)
        
        # قوة التنفيذ
        execution_strength = 0
        if ratio > 2 and p > sma20 and p > sma50:
            execution_strength += 40
        elif ratio > 1.5 and p > sma20:
            execution_strength += 25
        
        if (target - stop_loss) / entry_price > 0.1:
            execution_strength += 30
        elif (target - stop_loss) / entry_price > 0.05:
            execution_strength += 15
        
        if t_short == "صاعد" and t_med == "صاعد":
            execution_strength += 30
        elif t_short == "صاعد":
            execution_strength += 15
        
        execution_strength = min(100, execution_strength)
        
        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi, "chg": chg, "ratio": ratio,
            "t_short": t_short, "t_med": t_med, "t_long": t_long,
            "s1": s1, "s2": s2, "r1": r1, "r2": r2, "pp": pp,
            "sma20": sma20, "sma50": sma50, "sma200": sma200,
            "entry_min": entry_min, "entry_max": entry_max, "entry_price": entry_price,
            "entry_range": f"{entry_min:.2f} - {entry_max:.2f}",
            "stop_loss": stop_loss, "target": target,
            "rr": rr, "risk_pct": risk_pct, "target_pct": target_pct,
            "smart_score": smart_score, "execution_strength": execution_strength,
            "daily_turnover": daily_turnover, "above_sma20": p > sma20
        }
    except Exception as e:
        print(f"Analysis Error: {e}")
        return None

def preprocess_all_data(raw_data):
    results = []
    for r in raw_data:
        an = analyze_stock(r)
        if an:
            results.append(an)
    return results

def get_fresh_data():
    with st.spinner("🔄 جاري تحميل بيانات السوق..."):
        raw_data = get_all_data()
        if raw_data:
            st.session_state.all_results = preprocess_all_data(raw_data)
            st.session_state.last_update = datetime.now().strftime("%H:%M:%S")
            return True
        return False


# ================== 📈 TRADINGVIEW CHART ==================
def render_tradingview_chart(symbol, height=400):
    full_symbol = f"EGX:{symbol}"
    chart_html = f"""
    <div class="tradingview-widget-container">
        <div id="tradingview_chart_{symbol.replace(':', '_')}"></div>
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script>
        new TradingView.widget({{
            "container_id": "tradingview_chart_{symbol.replace(':', '_')}",
            "width": "100%",
            "height": {height},
            "symbol": "{full_symbol}",
            "interval": "D",
            "timezone": "Africa/Cairo",
            "theme": "dark",
            "style": "1",
            "locale": "ar",
            "hideideas": true,
            "studies": ["RSI@tv-basicstudies", "MASimple@tv-basicstudies"]
        }});
        </script>
    </div>
    """
    components.html(chart_html, height=height)


# ================== 📤 SHARE ON WHATSAPP ==================
def share_on_whatsapp(res):
    message = f"""📊 *EGX Sniper Pro - تحليل سهم {res['name']}*

💰 السعر الحالي: {res['p']:.2f} ج ({res['chg']:+.1f}%)
🎯 Smart Score: {res['smart_score']}/100
📈 RSI: {res['rsi']:.1f}
⚖️ RR Ratio: {res['rr']}
📊 السيولة: {res['ratio']:.1f}x

📌 الاتجاهات:
- قصير المدى: {res['t_short']}
- متوسط المدى: {res['t_med']}
- طويل المدى: {res['t_long']}

🎯 نطاق الدخول: {res['entry_range']}
🛑 وقف الخسارة: {res['stop_loss']:.2f} (-{res['risk_pct']:.1f}%)
🏁 الهدف: {res['target']:.2f} (+{res['target_pct']:.1f}%)

---
تم التحليل بواسطة EGX Sniper Pro"""
    
    encoded_msg = urllib.parse.quote(message)
    return f"https://wa.me/?text={encoded_msg}"


# ================== 🖥️ RENDER STOCK CARD WITH CONFIDENCE ==================
def render_stock_card(res, is_top10=False):
    if res is None:
        st.warning("بيانات السهم غير متوفرة")
        return
    
    market_status = get_egx30_status()
    confidence = get_confidence_score(res, market_status)
    
    # ================== بطاقة السهم الرئيسية ==================
    st.markdown(f"""
    <div class="stock-card">
        <div class="stock-header">
            <div>
                <span class="stock-name">{res['name']}</span>
                <span class="stock-desc">- {res['desc'][:50]}</span>
            </div>
            <span class="smart-badge">🎯 Smart: {res['smart_score']}</span>
        </div>
        
        <div class="flex-row">
            <div class="metric-box">
                <div class="metric-value">{res['p']:.2f}</div>
                <div class="metric-label">السعر</div>
            </div>
            <div class="metric-box">
                <div class="metric-value" style="color: {'#3fb950' if res['chg'] > 0 else '#f85149' if res['chg'] < 0 else '#8b949e'};">{res['chg']:+.1f}%</div>
                <div class="metric-label">التغير</div>
            </div>
            <div class="metric-box">
                <div class="metric-value">{res['rsi']:.0f}</div>
                <div class="metric-label">RSI</div>
            </div>
            <div class="metric-box">
                <div class="metric-value">{res['ratio']:.1f}x</div>
                <div class="metric-label">السيولة</div>
            </div>
            <div class="metric-box">
                <div class="metric-value">{res['rr']}</div>
                <div class="metric-label">RR</div>
            </div>
        </div>
        
        <div class="strength-bar">
            <div class="strength-fill {'strength-high' if res['smart_score'] >= 70 else 'strength-mid' if res['smart_score'] >= 50 else 'strength-low'}" style="width: {res['smart_score']}%;"></div>
        </div>
    """, unsafe_allow_html=True)
    
    # ================== بطاقة ثقة القناص (نظام الـ 4 طبقات) ==================
    st.markdown(f"""
    <div class="confidence-card" style="border-right-color: {confidence['color']};">
        <div class="confidence-header">
            <span class="confidence-title">{confidence['emoji']} نظام ثقة القناص (4 طبقات)</span>
            <span class="confidence-score" style="color: {confidence['color']};">{confidence['score']}%</span>
        </div>
        <div class="confidence-advice" style="color: {confidence['color']};">{confidence['advice']}</div>
        <div style="font-size: 12px; color: #8b949e; margin-top: 8px;">⚠️ مستوى الخطر: {confidence['risk_level']}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # عرض تفاصيل الطبقات في expander
    with st.expander("📊 تفاصيل طبقات التحليل (4 طبقات متقدمة)"):
        cols = st.columns(4)
        layers = list(confidence['layers'].items())
        layer_names = {
            "technical": "📈 التحليل الفني",
            "liquidity": "💧 السيولة",
            "momentum": "⚡ الزخم",
            "trend": "📊 الاتجاه"
        }
        for i, (layer, score) in enumerate(layers):
            col = cols[i % 4]
            color = "#3fb950" if score >= 70 else "#d29922" if score >= 55 else "#f85149"
            col.markdown(f"""
            <div style="text-align: center; background: #0d1117; border-radius: 10px; padding: 10px;">
                <div style="font-size: 12px; color: #8b949e;">{layer_names.get(layer, layer)}</div>
                <div style="font-size: 24px; font-weight: bold; color: {color};">{score}%</div>
            </div>
            """, unsafe_allow_html=True)
    
    # ================== ملخص التداول ==================
    st.markdown(f"""
        <div class="flex-between" style="margin: 15px 0 5px 0;">
            <div>
                <span style="background: rgba(63,185,80,0.2); padding: 4px 12px; border-radius: 20px; font-size: 13px;">🎯 هدف: {res['target']:.2f}</span>
                <span style="background: rgba(248,81,73,0.2); padding: 4px 12px; border-radius: 20px; font-size: 13px; margin-right: 10px;">🛑 وقف: {res['stop_loss']:.2f}</span>
            </div>
            <div class="flex-row" style="gap: 8px;">
                <span style="background: {'rgba(63,185,80,0.2)' if res['t_short'] == 'صاعد' else 'rgba(248,81,73,0.2)'}; padding: 4px 12px; border-radius: 20px; font-size: 13px;">
                    📊 {res['t_short']}
                </span>
                <span style="background: {'rgba(63,185,80,0.2)' if res['t_med'] == 'صاعد' else 'rgba(248,81,73,0.2)'}; padding: 4px 12px; border-radius: 20px; font-size: 13px;">
                    📈 {res['t_med']}
                </span>
                <span style="background: {'rgba(63,185,80,0.2)' if res['t_long'] == 'صاعد' else 'rgba(248,81,73,0.2)'}; padding: 4px 12px; border-radius: 20px; font-size: 13px;">
                    📉 {res['t_long']}
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ================== التحليل التفصيلي (Expander) ==================
    with st.expander(f"📊 التحليل الفني والتفاصيل - {res['name']}"):
        # الشارت
        st.markdown("### 📈 شارت السهم")
        render_tradingview_chart(res['name'], height=350)
        
        # مستويات الدعم والمقاومة
        st.markdown("### 🏛️ مستويات الدعم والمقاومة (ثابتة طول الجلسة)")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            🔴 **مقاومة ثانية R2:** {res['r2']:.2f}\n
            🔴 **مقاومة أولى R1:** {res['r1']:.2f} (الهدف الرئيسي)\n
            🟡 **نقطة الارتكاز PP:** {res['pp']:.2f}
            """)
        with col2:
            st.markdown(f"""
            🟢 **دعم أول S1:** {res['s1']:.2f} (وقف الخسارة تحته)\n
            🟢 **دعم ثاني S2:** {res['s2']:.2f}\n
            📏 **نطاق الدخول:** {res['entry_range']}
            """)
        
        # ================== خطة الدخول 3 مستويات ==================
        st.markdown("### 🏹 خطة الدخول المتكاملة (3 مستويات)")
        
        entry_price = res['entry_price']
        stop_loss = res['stop_loss']
        target = res['target']
        
        range_size = entry_price - stop_loss
        entry_level_1 = entry_price
        entry_level_2 = max(entry_price - (range_size * 0.5), stop_loss * 1.02)
        entry_level_3 = entry_price + (target - entry_price) * 0.3
        
        if res['rr'] >= 2.5:
            weights = [0.6, 0.25, 0.15]
        elif res['rr'] >= 1.8:
            weights = [0.5, 0.3, 0.2]
        else:
            weights = [0.4, 0.35, 0.25]
        
        deal_size = st.number_input("💰 ميزانية الصفقة (ج)", value=10000, step=1000, key=f"deal_{res['name']}")
        
        if deal_size > 0:
            shares_1 = int((deal_size * weights[0]) / entry_level_1) if entry_level_1 > 0 else 0
            shares_2 = int((deal_size * weights[1]) / entry_level_2) if entry_level_2 > 0 else 0
            shares_3 = int((deal_size * weights[2]) / entry_level_3) if entry_level_3 > 0 else 0
            
            st.markdown(f"""
            <div class="entry-level level-1">
                <b>📌 المستوى الأول - الدخول الأساسي</b><br>
                🟢 السعر: <b>{entry_level_1:.2f}</b> ج | 📦 الكمية: <b>{shares_1:,}</b> سهم | 💰 {weights[0]*100:.0f}% من الميزانية
            </div>
            <div class="entry-level level-2">
                <b>📌 المستوى الثاني - تعزيز الدعم</b><br>
                🟡 السعر: <b>{entry_level_2:.2f}</b> ج | 📦 الكمية: <b>{shares_2:,}</b> سهم | 💰 {weights[1]*100:.0f}% من الميزانية
            </div>
            <div class="entry-level level-3">
                <b>📌 المستوى الثالث - تأكيد الاختراق</b><br>
                🔵 السعر: <b>{entry_level_3:.2f}</b> ج | 📦 الكمية: <b>{shares_3:,}</b> سهم | 💰 {weights[2]*100:.0f}% من الميزانية
            </div>
            """, unsafe_allow_html=True)
            
            total_shares = shares_1 + shares_2 + shares_3
            total_cost = (shares_1 * entry_level_1) + (shares_2 * entry_level_2) + (shares_3 * entry_level_3)
            if total_shares > 0:
                avg_price = total_cost / total_shares
                st.info(f"📊 **متوسط السعر بعد التنفيذ الكامل:** {avg_price:.2f} ج ({total_shares:,} سهم)")
        
        # ================== المؤشرات المتقدمة ==================
        st.markdown("### 📈 المؤشرات المتقدمة")
        
        col1, col2 = st.columns(2)
        with col1:
            stoch = calculate_stochastic_rsi(res['rsi'])
            st.markdown(f"""
            <div style="background: #0d1117; border-radius: 10px; padding: 12px;">
                <b>🔄 Stochastic RSI</b><br>
                📈 K={stoch['k']:.1f} | D={stoch['d']:.1f}<br>
                🧠 {stoch['signal']}
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            success_rate, success_level = expected_success_rate(res)
            st.markdown(f"""
            <div style="background: #0d1117; border-radius: 10px; padding: 12px;">
                <b>📈 نسبة النجاح المتوقعة</b><br>
                🎯 <b>{success_rate}%</b> - {success_level}
            </div>
            """, unsafe_allow_html=True)
        
        # ================== واتساب ==================
        whatsapp_url = share_on_whatsapp(res)
        st.markdown(f"""
        <a href="{whatsapp_url}" target="_blank" style="display: block; background-color: #25D366; color: white; text-align: center; padding: 12px; border-radius: 12px; text-decoration: none; margin-top: 15px; font-weight: bold; font-size: 16px;">
            📱 مشاركة التحليل عبر واتساب
        </a>
        """, unsafe_allow_html=True)


# ================== 📋 FILTERS & HELPERS ==================
def filter_by_sector(results, sector):
    if sector == "🌍 الكل" or not results:
        return results
    return results

def get_top_10(results):
    if not results:
        return []
    valid = [r for r in results if r and r.get('smart_score', 0) >= 50]
    return sorted(valid, key=lambda x: x.get('smart_score', 0), reverse=True)[:10]

def get_corrections(results):
    corrections = []
    for r in results:
        if r:
            is_corr, _, score = is_correction_hunter(r)
            if is_corr:
                corrections.append({"stock": r, "score": score})
    return sorted(corrections, key=lambda x: x['score'], reverse=True)[:10]

def get_rapid_breakouts_list(results):
    breakouts = []
    for r in results:
        if r:
            analysis = is_rapid_breakout(r)
            if analysis.get('is_breakout', False):
                breakouts.append({"stock": r, "analysis": analysis, "score": analysis['strength']})
    return sorted(breakouts, key=lambda x: x['score'], reverse=True)[:10]


# ================== 🧭 SIDEBAR NAVIGATION ==================
def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-title">
            <h2>🎯 EGX Sniper Pro</h2>
            <p>نظام تحليل أسهم البورصة المصرية</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("#### 🧭 أقسام التطبيق")
        
        # أزرار التنقل - واضحة ومكتوب عليها النص
        nav_buttons = {
            "🏠 الرئيسية": "home",
            "🏆 أفضل 10 فرص": "top10",
            "🎯 صائد التصحيحات": "correction",
            "⚡ قناص الاختراق": "rapid",
            "🔍 تحليل سهم": "analyze",
            "📊 تقييم الأداء": "performance"
        }
        
        for label, page in nav_buttons.items():
            if st.button(label, key=f"nav_{page}", use_container_width=True):
                st.session_state.page = page
                st.rerun()
        
        st.markdown("---")
        
        st.markdown("#### ⚙️ الإعدادات")
        
        # نمط التداول
        mode_options = ["🛡️ محافظ", "⚖️ متوازن", "🚀 هجومي"]
        selected_mode = st.selectbox("نمط التداول", mode_options, index=1)
        if selected_mode != st.session_state.mode:
            st.session_state.mode = selected_mode
        
        # فلتر القطاع
        sectors = ["🌍 الكل", "🏦 البنوك", "🏗️ العقارات", "🍔 الأغذية", "📡 الاتصالات", "🏭 الصناعة"]
        selected_sector = st.selectbox("فلتر القطاع", sectors)
        if selected_sector != st.session_state.sector_filter:
            st.session_state.sector_filter = selected_sector
        
        st.markdown("---")
        
        # تحديث البيانات
        if st.button("🔄 تحديث البيانات", use_container_width=True):
            if get_fresh_data():
                st.success("✅ تم التحديث!")
                st.rerun()
        
        # معلومات
        if st.session_state.last_update:
            st.caption(f"🕐 آخر تحديث: {st.session_state.last_update}")
        
        # إحصائيات سريعة
        if st.session_state.all_results:
            st.markdown("---")
            st.markdown("#### 📊 إحصائيات سريعة")
            total = len(st.session_state.all_results)
            avg_smart = sum(r.get('smart_score', 0) for r in st.session_state.all_results if r) / total if total > 0 else 0
            st.metric("📊 إجمالي الأسهم", total)
            st.metric("🎯 متوسط Smart", f"{avg_smart:.0f}")


# ================== 📄 PAGES ==================
def show_home():
    st.markdown("## 🏠 نظرة عامة")
    
    if not st.session_state.all_results:
        st.warning("⚠️ لا توجد بيانات. اضغط على 'تحديث البيانات'")
        return
    
    # إحصائيات سريعة
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📊 إجمالي الأسهم", len(st.session_state.all_results))
    with col2:
        corrections = get_corrections(st.session_state.all_results)
        st.metric("🎯 فرص تصحيح", len(corrections))
    with col3:
        breakouts = get_rapid_breakouts_list(st.session_state.all_results)
        st.metric("⚡ فرص اختراق", len(breakouts))
    with col4:
        top = get_top_10(st.session_state.all_results)
        st.metric("🏆 أفضل 10", f"{len(top)}/10")
    
    st.markdown("---")
    
    # عرض الفرص في تبويبات
    tab1, tab2, tab3 = st.tabs(["🏆 أفضل 10 فرص", "🎯 صائد التصحيحات", "⚡ قناص الاختراق"])
    
    with tab1:
        top = get_top_10(st.session_state.all_results)
        if top:
            for stock in top[:5]:
                render_stock_card(stock, is_top10=True)
        else:
            st.info("لا توجد فرص حالياً")
    
    with tab2:
        corrections = get_corrections(st.session_state.all_results)
        if corrections:
            for item in corrections[:5]:
                render_stock_card(item['stock'])
        else:
            st.info("لا توجد فرص تصحيح حالياً")
    
    with tab3:
        breakouts = get_rapid_breakouts_list(st.session_state.all_results)
        if breakouts:
            for item in breakouts[:5]:
                render_stock_card(item['stock'])
        else:
            st.info("لا توجد فرص اختراق حالياً")

def show_top10():
    st.markdown("## 🏆 أفضل 10 فرص استثمارية")
    st.caption("أقوى الفرص بناءً على Smart Score ونظام الثقة (4 طبقات)")
    
    if not st.session_state.all_results:
        st.warning("⚠️ لا توجد بيانات")
        return
    
    top = get_top_10(st.session_state.all_results)
    if top:
        for i, stock in enumerate(top, 1):
            st.markdown(f"### #{i}")
            render_stock_card(stock, is_top10=True)
            if st.button(f"💾 تسجيل الصفقة", key=f"rec_top_{stock['name']}"):
                record_trade(stock, "أفضل 10")
                st.success("✅ تم تسجيل الصفقة!")
    else:
        st.warning("⚠️ لا توجد فرص مطابقة للمعايير حالياً")

def show_correction():
    st.markdown("## 🎯 صائد التصحيحات")
    st.caption("الأسهم القوية التي في حالة تصحيح - RSI بين 28-55")
    
    if not st.session_state.all_results:
        st.warning("⚠️ لا توجد بيانات")
        return
    
    corrections = get_corrections(st.session_state.all_results)
    if corrections:
        for item in corrections:
            render_stock_card(item['stock'])
            if st.button(f"💾 تسجيل الصفقة", key=f"rec_corr_{item['stock']['name']}"):
                record_trade(item['stock'], "صائد تصحيحات")
                st.success("✅ تم تسجيل الصفقة!")
    else:
        st.info("ℹ️ لا توجد فرص تصحيح حالياً")

def show_rapid():
    st.markdown("## ⚡ قناص الاختراق")
    st.caption("الأسهم على وشك الاختراق - RSI بين 45-75 وسيولة عالية")
    
    if not st.session_state.all_results:
        st.warning("⚠️ لا توجد بيانات")
        return
    
    breakouts = get_rapid_breakouts_list(st.session_state.all_results)
    if breakouts:
        for item in breakouts:
            render_stock_card(item['stock'])
            if st.button(f"💾 تسجيل الصفقة", key=f"rec_rapid_{item['stock']['name']}"):
                record_trade(item['stock'], "اختراق سريع")
                st.success("✅ تم تسجيل الصفقة!")
    else:
        st.info("ℹ️ لا توجد فرص اختراق حالياً")

def show_analyze():
    st.markdown("## 🔍 تحليل سهم")
    st.caption("أدخل رمز السهم للحصول على تحليل مفصل مع نظام الثقة")
    
    sym = st.text_input("🔎 أدخل رمز السهم", placeholder="مثال: COMI, TMGH, ETEL", key="analyze_input").upper().strip()
    
    if sym:
        with st.spinner("🔍 جاري البحث..."):
            data = fetch_single_stock(sym)
            if data:
                stock = analyze_stock(data[0])
                if stock:
                    render_stock_card(stock)
                    if st.button(f"💾 تسجيل الصفقة", key=f"rec_analyze_{sym}"):
                        record_trade(stock, "تحليل فردي")
                        st.success("✅ تم تسجيل الصفقة!")
                else:
                    st.error("❌ فشل تحليل السهم - قد يكون ذو سيولة ضعيفة")
            else:
                st.error(f"❌ السهم '{sym}' غير موجود")
                if st.session_state.all_results:
                    suggestions = [r.get('name') for r in st.session_state.all_results[:15] if r]
                    st.info(f"💡 أمثلة: {', '.join(suggestions)}")

def show_performance():
    st.markdown("## 📊 تقييم الأداء")
    
    trades = load_trades()
    stats = get_performance_stats(trades)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📊 إجمالي الصفقات", stats['total'])
    col2.metric("✅ حققت الهدف", stats['hit_target'])
    col3.metric("❌ ضربت الوقف", stats['stopped_out'])
    col4.metric("⏳ مفتوحة", stats['still_open'])
    
    col1, col2 = st.columns(2)
    col1.metric("📈 نسبة النجاح", f"{stats['success_rate']}%")
    col2.metric("⚖️ متوسط RR", stats['avg_rr'])
    
    if trades:
        st.markdown("### 📋 سجل الصفقات")
        for trade in trades[-20:][::-1]:
            status = "🟢 هدف" if trade.get('status') == 'hit_target' else "🔴 وقف" if trade.get('status') == 'stopped_out' else "🟡 مفتوح"
            st.markdown(f"""
            <div style="background: #0d1117; border-radius: 10px; padding: 12px; margin-bottom: 8px;">
                <div class="flex-between">
                    <div><b>{trade.get('name', 'N/A')}</b> ({trade.get('trade_type', 'N/A')}) - {status}</div>
                    <div>🎯 Smart: {trade.get('smart_score', 0)} | ⚖️ RR: {trade.get('rr', 0)}</div>
                </div>
                <div style="font-size: 12px; color: #8b949e;">📅 {trade.get('date_recorded', 'N/A')}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("لا توجد صفقات مسجلة بعد")


# ================== 🏁 MAIN ==================
def main():
    # تحميل البيانات
    if st.session_state.all_results is None:
        get_fresh_data()
    
    # حالة السوق
    market = get_egx30_status()
    st.markdown(f"""
    <div class="market-status">
        <span style="color: {market['color']}; font-weight: bold;">📊 المؤشر العام:</span>
        <span>{market['status']}</span>
        <span style="margin-right: 20px;">💰 {market['price']:,.0f}</span>
        <span style="margin-right: 20px;">📈 {market['change']:+.2f}%</span>
        <span>📊 RSI: {market['rsi']:.0f}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # الشريط الجانبي
    render_sidebar()
    
    # عرض الصفحة المطلوبة
    if st.session_state.page == 'home':
        show_home()
    elif st.session_state.page == 'top10':
        show_top10()
    elif st.session_state.page == 'correction':
        show_correction()
    elif st.session_state.page == 'rapid':
        show_rapid()
    elif st.session_state.page == 'analyze':
        show_analyze()
    elif st.session_state.page == 'performance':
        show_performance()
    
    # الشريط السفلي
    st.markdown(f"""
    <div class="footer">
        <div class="flex-between">
            <span>🎯 نمط التداول: {st.session_state.mode}</span>
            <span>📂 قطاع: {st.session_state.sector_filter}</span>
            <span>🕐 آخر تحديث: {st.session_state.last_update or 'لم يتم'}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
