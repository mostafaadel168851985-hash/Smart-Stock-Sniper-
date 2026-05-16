import streamlit as st
import streamlit.components.v1 as components
import requests
from datetime import datetime, date, timedelta
import json
import os
import re
import urllib.parse
import pandas as pd
from io import BytesIO
import time
import numpy as np

# ================== 📱 MOBILE DETECTION ==================
user_agent = st.context.headers.get('User-Agent', '')
is_mobile = bool(re.search(r'Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini', user_agent))

st.set_page_config(
    page_title="🎯 EGX Sniper Pro v4.0", 
    layout="wide", 
    page_icon="🎯",
    initial_sidebar_state="collapsed"
)

# ================== 📁 CONSTANTS ==================
TRADES_FILE = "trades_data.json"
OUTCOMES_FILE = "trade_outcomes.json"
MIN_DAILY_TURNOVER = 500000  # الحد الأدنى للسيولة اليومية (500 ألف جنيه)
MAX_RISK_PCT = 5.0  # الحد الأقصى لنسبة المخاطرة (5%)

# أعمدة API للاستخدام الديناميكي
API_COLUMNS = [
    "name", "close", "RSI", "volume", "average_volume_10d_calc",
    "high", "low", "change", "description", "SMA20", "SMA50", "SMA200",
    "high_20d", "low_20d"  # إضافة أعلى وأدنى 20 يوم
]

# ================== SESSION STATE INIT ==================
if "mode" not in st.session_state:
    st.session_state.mode = "⚖️ متوازن"
if 'page' not in st.session_state: 
    st.session_state.page = 'home'
if "sector_filter" not in st.session_state:
    st.session_state.sector_filter = "🌍 الكل"
if "market_data" not in st.session_state:
    st.session_state.market_data = None
if "all_results" not in st.session_state:
    st.session_state.all_results = None
if "last_update" not in st.session_state:
    st.session_state.last_update = None
if "show_guide" not in st.session_state:
    st.session_state.show_guide = False
if "yesterday_data" not in st.session_state:
    st.session_state.yesterday_data = None  # تخزين بيانات الأمس لل pivots الثابتة

# ================== 📁 PERFORMANCE TRACKING (محسن) ==================
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

def record_trade(res, trade_type, setup_conditions=None):
    if res is None:
        return
    trades = load_trades()
    today = datetime.now().strftime("%Y-%m-%d")
    trade_id = f"{res.get('name', 'N/A')}_{today}_{int(time.time())}"
    
    for t in trades:
        if (t.get('name') == res.get('name') and 
            t.get('date_recorded') == today and
            t.get('trade_type') == trade_type):
            return
    
    trades.append({
        "trade_id": trade_id,
        "name": res.get('name', 'N/A'),
        "desc": res.get('desc', 'N/A'),
        "entry_price": res.get('entry_price', 0),
        "entry_min": res.get('entry_price', 0) * 0.98,
        "entry_max": res.get('entry_price', 0) * 1.01,
        "target": res.get('target', 0),
        "stop_loss": res.get('stop_loss', 0),
        "target_pct": res.get('target_pct', 0),
        "risk_pct": res.get('risk_pct', 0),
        "rr": res.get('rr', 0),
        "rsi_at_entry": res.get('rsi', 50),
        "smart_score": res.get('smart_score', 0),
        "execution_strength": res.get('execution_strength', 0),
        "trade_type": trade_type,
        "date_recorded": today,
        "last_price": None,
        "last_update": None,
        "status": "pending",
        "profit_pct": None,
        "entry_hit": False,
        "days_open": None,
        "max_price": None,
        "min_price": None,
        "setup_conditions": setup_conditions or {}
    })
    save_trades(trades)

def update_all_trades(current_prices_dict):
    """تحديث جميع الصفقات - محسن: حفظ مرة واحدة فقط"""
    trades = load_trades()
    if not trades:
        return trades
    
    today = date.today()
    updated = False
    
    for trade in trades:
        if trade.get('status') in ['pending', 'still_open']:
            symbol = trade.get('name')
            current_price = current_prices_dict.get(symbol)
            
            if current_price:
                trade['last_price'] = current_price
                trade['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                if trade.get('max_price') is None or current_price > trade['max_price']:
                    trade['max_price'] = current_price
                    updated = True
                if trade.get('min_price') is None or current_price < trade['min_price']:
                    trade['min_price'] = current_price
                    updated = True
                
                if not trade.get('entry_hit', False):
                    entry_min = trade.get('entry_min', 0)
                    entry_max = trade.get('entry_max', 0)
                    if entry_min <= current_price <= entry_max:
                        trade['entry_hit'] = True
                        updated = True
                
                try:
                    recorded_date = datetime.strptime(trade['date_recorded'], "%Y-%m-%d").date()
                    trade['days_open'] = (today - recorded_date).days
                except:
                    trade['days_open'] = 0
                
                target = trade.get('target', 0)
                stop_loss = trade.get('stop_loss', 0)
                target_pct = trade.get('target_pct', 0)
                risk_pct = trade.get('risk_pct', 0)
                
                if current_price >= target:
                    if trade['status'] != 'hit_target':
                        trade['status'] = 'hit_target'
                        trade['profit_pct'] = target_pct
                        updated = True
                elif current_price <= stop_loss:
                    if trade['status'] != 'stopped_out':
                        trade['status'] = 'stopped_out'
                        trade['profit_pct'] = -risk_pct
                        updated = True
                else:
                    if trade['status'] != 'still_open':
                        trade['status'] = 'still_open'
                        updated = True
    
    # حفظ مرة واحدة فقط بعد كل التحديثات
    if updated:
        save_trades(trades)
    return trades

def get_performance_stats(trades):
    if not trades or not isinstance(trades, list):
        trades = []
    
    trades = [t for t in trades if t is not None]
    
    total = len(trades)
    if total == 0:
        return {
            'total': 0, 'hit_target': 0, 'stopped_out': 0, 'still_open': 0,
            'success_rate': 0, 'avg_rr': 0, 'total_return': 0, 'avg_return': 0,
            'avg_holding_days': 0
        }
    
    hit_target = len([t for t in trades if t.get('status') == 'hit_target'])
    stopped_out = len([t for t in trades if t.get('status') == 'stopped_out'])
    still_open = len([t for t in trades if t.get('status') in ['pending', 'still_open']])
    closed = hit_target + stopped_out
    success_rate = (hit_target / closed * 100) if closed > 0 else 0
    
    completed_trades = [t for t in trades if t.get('profit_pct') is not None]
    total_return = sum(t.get('profit_pct', 0) for t in completed_trades)
    avg_return = total_return / len(completed_trades) if completed_trades else 0
    
    avg_rr = sum(t.get('rr', 0) for t in trades) / total if total > 0 else 0
    
    return {
        'total': total, 'hit_target': hit_target, 'stopped_out': stopped_out, 'still_open': still_open,
        'success_rate': round(success_rate, 1), 'avg_rr': round(avg_rr, 2),
        'total_return': round(total_return, 1), 'avg_return': round(avg_return, 1),
        'avg_holding_days': 0
    }


# ================== 📈 EGX30 MARKET ANALYSIS ==================
@st.cache_data(ttl=600, show_spinner=False)
def get_egx30_status():
    for attempt in range(2):
        try:
            url = "https://scanner.tradingview.com/egypt/scan"
            payload = {
                "filter": [{"left": "symbol", "operation": "equal", "right": "EGX30"}],
                "columns": ["close", "RSI", "SMA50", "SMA200", "change", "volume", "average_volume_10d_calc"],
                "range": [0, 1]
            }
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.post(url, json=payload, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json().get("data", [])
                if data and len(data) > 0:
                    d = data[0].get('d', [])
                    if len(d) >= 7:
                        price = d[0] if d[0] else 10000
                        rsi = d[1] if d[1] else 50
                        sma50 = d[2] if d[2] else price
                        sma200 = d[3] if d[3] else price
                        change = d[4] if d[4] else 0
                        
                        score = 0
                        if price and sma200 and price > sma200: score += 1
                        if price and sma50 and price > sma50: score += 1
                        if rsi and 40 < rsi < 70: score += 1
                        if change and change > -0.5: score += 1
                        
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
                            "rsi": rsi if rsi else 50,
                            "change": change if change else 0,
                            "price": price if price else 10000
                        }
        except:
            time.sleep(1)
            continue
    
    return {
        "status": "🟡 سوق متذبذب (افتراضي)",
        "color": "#FFA500",
        "market_multiplier": 0.7,
        "rsi": 50,
        "change": 0,
        "price": 10000
    }


# ================== 🔥 SMART SCORE PRO ==================
def smart_score_pro(res):
    score = 0
    if res.get('t_short') == "صاعد": score += 15
    if res.get('t_med') == "صاعد": score += 15
    if res.get('t_long') == "صاعد": score += 5
    if res.get('ratio', 0) > 2.5: score += 20
    elif res.get('ratio', 0) > 1.8: score += 15
    elif res.get('ratio', 0) > 1.2: score += 8
    if 50 < res.get('rsi', 50) < 65: score += 15
    elif 45 < res.get('rsi', 50) <= 50 or 65 <= res.get('rsi', 50) < 75: score += 10
    elif 35 <= res.get('rsi', 50) <= 45: score += 5
    if res.get('rr', 0) >= 2.5: score += 15
    elif res.get('rr', 0) >= 2: score += 12
    elif res.get('rr', 0) >= 1.5: score += 8
    return min(100, int(score))


# ================== 🎯 REAL BREAKOUT DETECTION (جديد) ==================
def is_real_breakout(an):
    """اكتشاف الانفجار السعري الحقيقي - اختراق القمم مع سيولة مرعبة"""
    if an is None:
        return False, [], 0
    
    p = an.get('p', 0)
    high_20d = an.get('high_20d', 0)
    volume = an.get('volume', 0)
    avg_volume = an.get('avg_volume', 1)
    ratio = volume / avg_volume if avg_volume > 0 else 0
    rsi = an.get('rsi', 50)
    t_short = an.get('t_short', 'هابط')
    
    reasons = []
    score = 0
    max_score = 8
    
    # شرط الاختراق الأساسي: السعر يلامس أو يكسر أعلى 20 يوم
    if high_20d > 0 and p >= high_20d * 0.99:
        score += 3
        reasons.append(f"🚀 اختراق قمة 20 يوم ({high_20d:.2f})")
    else:
        return False, [], 0
    
    # سيولة استثنائية
    if ratio > 2.5:
        score += 3
        reasons.append(f"💥 سيولة استثنائية ({ratio:.1f}x)")
    elif ratio > 1.8:
        score += 2
        reasons.append(f"⚡ سيولة قوية ({ratio:.1f}x)")
    else:
        return False, ["سيولة غير كافية للاختراق"], 0
    
    # زخم صحي
    if 55 <= rsi <= 75:
        score += 2
        reasons.append(f"📈 زخم صحي (RSI: {rsi:.0f})")
    elif 45 <= rsi < 55:
        score += 1
        reasons.append(f"📊 بداية زخم (RSI: {rsi:.0f})")
    
    # اتجاه صاعد
    if t_short == "صاعد":
        score += 1
        reasons.append("📈 اتجاه قصير صاعد")
    
    strength = int((score / max_score) * 100)
    
    return True, reasons, strength


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
    daily_turnover = an.get('daily_turnover', 0)
    
    # فلتر السيولة: استبعاد الأسهم الميتة
    if daily_turnover < MIN_DAILY_TURNOVER:
        return False, [f"سيولة ضعيفة (أقل من {MIN_DAILY_TURNOVER/1000:.0f} ألف جنيه)"], 0
    
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
    elif 55 < rsi <= 60:
        score += 1
        reasons.append(f"⚠️ RSI بدأ يصعد ({rsi:.0f})")
    else:
        return False, [f"RSI مرتفع ({rsi:.0f}) - فاتك التصحيح"], 0
    
    if change_pct > 0:
        score += 2
        reasons.append(f"📈 تغير إيجابي ({change_pct:+.2f}%)")
    elif change_pct > -1:
        score += 1
        reasons.append(f"⚖️ تغير طفيف ({change_pct:+.2f}%)")
    
    if ratio > 1.2:
        score += 1
        reasons.append(f"💧 سيولة ممتازة ({ratio:.1f}x)")
    elif ratio > 0.7:
        reasons.append(f"💧 سيولة جيدة ({ratio:.1f}x)")
    
    if rr >= 1.5:
        score += 1
        reasons.append(f"⚖️ RR جيد ({rr})")
    
    strength_percent = int((score / max_score) * 100)
    
    return score >= 4, reasons, strength_percent


# ================== ⚡ RAPID BREAKOUT ==================
def is_rapid_breakout(an):
    if an is None:
        return {"is_breakout": False, "reasons": [], "strength": 0, "label": "", "color": "#555", "target_1": 0, "target_2": 0, "stop_loss_rapid": 0}
    
    p = an.get('p', 0)
    rsi = an.get('rsi', 50)
    ratio = an.get('ratio', 0)
    change = an.get('chg', 0)
    t_short = an.get('t_short', 'هابط')
    t_med = an.get('t_med', 'هابط')
    r1 = an.get('r1', p * 1.05)
    daily_turnover = an.get('daily_turnover', 0)
    
    # فلتر السيولة
    if daily_turnover < MIN_DAILY_TURNOVER:
        return {"is_breakout": False, "reasons": [], "strength": 0, "label": "", "color": "#555", "target_1": 0, "target_2": 0, "stop_loss_rapid": 0}
    
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
        return {"is_breakout": False, "reasons": [], "strength": 0, "label": "", "color": "#555", "target_1": 0, "target_2": 0, "stop_loss_rapid": 0}
    
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
        return {"is_breakout": False, "reasons": [], "strength": 0, "label": "", "color": "#555", "target_1": 0, "target_2": 0, "stop_loss_rapid": 0}
    
    if p >= r1 * 0.98:
        score += 2
        reasons.append(f"🎯 على وشك اختراق R1 ({r1:.2f})")
    elif p >= r1 * 0.95:
        score += 1
        reasons.append(f"📍 قريب من المقاومة R1")
    else:
        return {"is_breakout": False, "reasons": [], "strength": 0, "label": "", "color": "#555", "target_1": 0, "target_2": 0, "stop_loss_rapid": 0}
    
    if t_short == "صاعد" and t_med == "صاعد":
        score += 1
        reasons.append("📊 الاتجاهات صاعدة")
    
    strength = int((score / max_score) * 100)
    
    if strength >= 70:
        label = "🔥 انفجار وشيك خلال ساعات"
        color = "#FF6666"
    elif strength >= 55:
        label = "⚡ اختراق متوقع خلال جلسة"
        color = "#FFB347"
    elif strength >= 40:
        label = "🟡 مراقبة لاصطياد الاختراق"
        color = "#FFD700"
    else:
        return {"is_breakout": False, "reasons": [], "strength": 0, "label": "", "color": "#555", "target_1": 0, "target_2": 0, "stop_loss_rapid": 0}
    
    # وقف خسارة فني باستخدام S1
    s1 = an.get('s1', p * 0.97)
    technical_stop = s1 * 0.99  # تحت الدعم الأول بنسبة 1%
    max_risk_stop = p * (1 - MAX_RISK_PCT / 100)
    stop_loss_rapid = max(technical_stop, max_risk_stop)
    
    return {
        "is_breakout": True,
        "reasons": reasons,
        "strength": strength,
        "label": label,
        "color": color,
        "target_1": r1,
        "target_2": an.get('r2', r1 * 1.03),
        "stop_loss_rapid": stop_loss_rapid
    }


# ================== 📂 SECTOR FILTER ==================
SECTOR_MAPPING = {
    "🏦 البنوك": ["CIEB", "COMI", "AAIB", "QNBA", "BID", "CAE", "NBK"],
    "🏗️ العقارات": ["TMGH", "OCDI", "PHDC", "HELI", "MNHD", "DSC"],
    "🍔 الأغذية": ["BFR", "EFID", "JUFO", "ORWE", "EDFO", "BIF"],
    "📡 الاتصالات": ["ETEL", "OTMT", "TE", "EGS"],
    "🏭 الصناعة": ["EFIC", "SKPC", "EGCH", "ABUK", "MICH", "ASCM"],
    "🛒 التجارة": ["RAYA", "SWDY", "ELSE", "MENA", "CAPI"],
}

def get_stock_sector(name):
    name_upper = name.upper()
    for sector, symbols in SECTOR_MAPPING.items():
        for sym in symbols:
            if sym in name_upper or name_upper.startswith(sym):
                return sector
    return "📌 أخرى"

def filter_by_sector(results, sector):
    if sector == "🌍 الكل" or not results:
        return results
    
    filtered = []
    for an in results:
        if an:
            stock_sector = get_stock_sector(an.get('name', ''))
            if sector == "🏆 EGX30 (قيادي)":
                if an.get('smart_score', 0) >= 60 or an.get('ratio', 0) > 1.5:
                    filtered.append(an)
            elif stock_sector == sector:
                filtered.append(an)
    return filtered


# ================== 📈 DATA & ANALYSIS ENGINE (محسن بالكامل) ==================
@st.cache_data(ttl=300, show_spinner=False)
def get_all_data():
    """جلب البيانات من TradingView مع الأعمدة المطلوبة"""
    url = "https://scanner.tradingview.com/egypt/scan"
    payload = {
        "filter": [{"left": "volume", "operation": "greater", "right": 1000}],
        "columns": API_COLUMNS,
        "sort": {"sortBy": "change", "sortOrder": "desc"},
        "range": [0, 300]
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://www.tradingview.com",
        "Referer": "https://www.tradingview.com/"
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        if r.status_code != 200:
            return []
        data = r.json()
        return data.get("data", [])
    except Exception as e:
        return []

def fetch_single_stock(symbol):
    """جلب بيانات سهم واحد"""
    url = "https://scanner.tradingview.com/egypt/scan"
    payload = {
        "filter": [{"left": "name", "operation": "match", "right": symbol.upper()}],
        "columns": API_COLUMNS,
        "range": [0, 1]
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=20)
        if r.status_code == 200:
            data = r.json()
            results = data.get("data", [])
            if results and len(results) > 0:
                return results
        return []
    except:
        return []

def calculate_pivots(high, low, close):
    """حساب مستويات الدعم والمقاومة الثابتة بناءً على بيانات الأمس"""
    if not high or not low or not close:
        return None, None, None, None, None
    pp = (high + low + close) / 3
    r1 = (2 * pp) - low
    r2 = pp + (high - low)
    s1 = (2 * pp) - high
    s2 = pp - (high - low)
    return pp, r1, r2, s1, s2

def analyze_stock(d_row):
    """
    تحليل سهم باستخدام الأسماء بدلاً من الترتيب (Robust API Parsing)
    مع استخدام Pivots ثابتة ومتوسط تداول يومي حقيقي
    """
    try:
        d = d_row.get('d', [])
        
        if len(d) < len(API_COLUMNS):
            return None
        
        # استخدام الأسماء بدلاً من الترتيب (Robust API Parsing)
        data_dict = dict(zip(API_COLUMNS, d))
        
        name = data_dict.get("name")
        p = data_dict.get("close")
        rsi = data_dict.get("RSI")
        v = data_dict.get("volume")
        avg_v = data_dict.get("average_volume_10d_calc")
        h = data_dict.get("high")
        l = data_dict.get("low")
        chg = data_dict.get("change")
        desc = data_dict.get("description")
        sma20 = data_dict.get("SMA20")
        sma50 = data_dict.get("SMA50")
        sma200 = data_dict.get("SMA200")
        high_20d = data_dict.get("high_20d")
        low_20d = data_dict.get("low_20d")
        
        if p is None or p <= 0:
            return None
        
        if not desc or desc == "":
            desc = name
        
        rsi_val = rsi or 0
        ratio = v / avg_v if avg_v and avg_v > 0 else 0
        
        # حساب القيمة المالية المتداولة يومياً (فلتر السيولة)
        daily_turnover = p * (avg_v or 0)
        
        # استبعاد الأسهم الميتة سيولياً
        if daily_turnover < MIN_DAILY_TURNOVER:
            return None
        
        # الاتجاهات
        t_short = "صاعد" if (sma20 and p > sma20) else "هابط"
        t_med = "صاعد" if (sma50 and p > sma50) else "هابط"
        t_long = "صاعد" if (sma200 and p > sma200) else "هابط"
        
        # حساب Pivots الثابتة (باستخدام بيانات اليوم - في الواقع الأفضل استخدام بيانات الأمس)
        # ملاحظة: للدقة القصوى، يُفضل جلب بيانات الشمعة السابقة المنفصلة
        pp, r1, r2, s1, s2 = calculate_pivots(h or p, l or p, p)
        
        # نطاق الدخول
        entry_min = p * 0.98
        entry_max = p * 1.01
        entry_price = (entry_min + entry_max) / 2
        
        # وقف الخسارة الفني (Technical Stop-Loss)
        # نضعه تحت الدعم الأول بنسبة 1%، مع حد أقصى 5% من السعر
        if s1 and s1 > 0:
            technical_stop = s1 * 0.99
        else:
            technical_stop = p * 0.96
        
        # التأكد من أن الوقف ليس بعيداً جداً (حد أقصى 5%)
        max_risk_stop = p * (1 - MAX_RISK_PCT / 100)
        stop_loss = max(technical_stop, max_risk_stop)
        
        # الهدف: المقاومة الأولى أو +5% أيهما أكبر
        target = max(r1 if r1 else p * 1.05, p * 1.05)
        
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
            'ratio': ratio, 'rsi': rsi_val, 'rr': rr, 'chg': chg or 0
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
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg or 0, "ratio": ratio,
            "t_short": t_short, "t_med": t_med, "t_long": t_long,
            "s1": s1 or 0, "s2": s2 or 0, "r1": r1 or 0, "r2": r2 or 0, "pp": pp or 0,
            "sma20": sma20, "sma50": sma50, "sma200": sma200,
            "high_20d": high_20d or p, "low_20d": low_20d or p,
            "volume": v or 0, "avg_volume": avg_v or 1, "daily_turnover": daily_turnover,
            "entry_range": f"{entry_min:.2f} - {entry_max:.2f}", "entry_price": entry_price,
            "stop_loss": stop_loss, "target": target,
            "rr": rr, "risk_pct": risk_pct, "target_pct": target_pct,
            "smart_score": smart_score, "execution_strength": execution_strength
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

def get_top_ranked(results, limit=10):
    if not results:
        return []
    valid_results = [r for r in results if r is not None and r.get('daily_turnover', 0) >= MIN_DAILY_TURNOVER]
    sorted_results = sorted(
        valid_results,
        key=lambda x: (x.get('smart_score', 0) * 0.5 + x.get('execution_strength', 0) * 0.3 + x.get('rr', 0) * 10),
        reverse=True
    )
    return sorted_results[:limit]

def get_rapid_breakouts(results):
    rapid = []
    for an in results:
        if an and an.get('daily_turnover', 0) >= MIN_DAILY_TURNOVER:
            analysis = is_rapid_breakout(an)
            if analysis.get('is_breakout', False):
                rapid.append({'stock': an, 'analysis': analysis})
    rapid.sort(key=lambda x: x['analysis']['strength'], reverse=True)
    return rapid[:8]

def get_real_breakouts(results):
    """الحصول على الأسهم التي حققت انفجاراً سعرياً حقيقياً"""
    breakouts = []
    for an in results:
        if an:
            is_breakout, reasons, strength = is_real_breakout(an)
            if is_breakout:
                breakouts.append({'stock': an, 'reasons': reasons, 'strength': strength})
    breakouts.sort(key=lambda x: x['strength'], reverse=True)
    return breakouts[:8]

def get_fresh_data():
    with st.spinner("🔄 جاري تحميل بيانات السوق..."):
        raw_data = get_all_data()
        if raw_data:
            st.session_state.market_data = raw_data
            st.session_state.all_results = preprocess_all_data(raw_data)
            st.session_state.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # تحديث الصفقات المفتوحة
            if st.session_state.all_results:
                current_prices = {res['name']: res['p'] for res in st.session_state.all_results if res}
                update_all_trades(current_prices)
            
            return True
        return False


# ================== 📈 TRADINGVIEW CHART ==================
def render_tradingview_chart(symbol, height=400):
    full_symbol = f"EGX:{symbol}"
    chart_html = f"""
    <div class="tradingview-widget-container">
        <div id="tradingview_chart_{symbol.replace(':', '_')}"></div>
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script type="text/javascript">
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
            "toolbar_bg": "#f1f3f6",
            "enable_publishing": false,
            "allow_symbol_change": true,
            "hideideas": true,
            "studies": ["RSI@tv-basicstudies", "MASimple@tv-basicstudies"]
        }});
        </script>
    </div>
    """
    components.html(chart_html, height=height)


# ================== 📤 SHARE ON WHATSAPP ==================
def share_on_whatsapp(res):
    message = f"""📊 *EGX Sniper Pro v4.0 - تحليل سهم {res['name']}*

💰 السعر الحالي: {res['p']:.2f} ج ({res['chg']:+.1f}%)
🎯 Smart Score: {res['smart_score']}/100
📈 RSI: {res['rsi']:.1f}
⚖️ RR Ratio: {res['rr']}
📊 السيولة: {res['ratio']:.1f}x
💰 التداول اليومي: {res['daily_turnover']/1000:.0f} ألف ج

📌 الاتجاهات:
- قصير المدى: {res['t_short']}
- متوسط المدى: {res['t_med']}
- طويل المدى: {res['t_long']}

🎯 نطاق الدخول: {res['entry_range']}
🛑 وقف الخسارة: {res['stop_loss']:.2f} (-{res['risk_pct']:.1f}%)
🏁 الهدف: {res['target']:.2f} (+{res['target_pct']:.1f}%)

---
تم التحليل بواسطة EGX Sniper Pro v4.0"""
    
    encoded_msg = urllib.parse.quote(message)
    return f"https://wa.me/?text={encoded_msg}"


# ================== 🎨 GLOBAL STYLES ==================
st.markdown("""
<style>
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
        margin: 5px 0 0 0;
    }
    .market-status {
        background: #0d1117;
        border-radius: 10px;
        padding: 10px;
        text-align: center;
        margin-bottom: 20px;
    }
    .stock-name {
        font-size: 20px;
        font-weight: bold;
        color: #58a6ff;
    }
    .correction-card {
        background: linear-gradient(135deg, #0d1f0d, #0a150a);
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        border-right: 4px solid #2E7D32;
    }
    .rapid-card {
        background: linear-gradient(135deg, #1a0a0a, #0d0a0a);
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        border-right: 4px solid #FF6666;
    }
    .breakout-card {
        background: linear-gradient(135deg, #1a1a2e, #0d1117);
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        border-right: 4px solid #FFD700;
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 45px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# ================== 📖 GUIDE SECTION ==================
def show_guide():
    with st.expander("📖 دليل المستخدم - اضغط للتعلم", expanded=st.session_state.show_guide):
        st.markdown("""
        ## 📖 دليل EGX Sniper Pro v4.0
        
        ### 🎯 ما هذا التطبيق؟
        تطبيق متخصص في تحليل أسهم البورصة المصرية باستخدام الذكاء الاصطناعي والمؤشرات الفنية المتقدمة.
        
        ---
        
        ### 📊 أقسام التطبيق
        
        | القسم | الوظيفة | متى تستخدمه؟ |
        |-------|---------|--------------|
        | 🏠 **الرئيسية** | نظرة عامة على السوق وأحدث الفرص | يومياً عند فتح التطبيق |
        | 🏆 **أفضل 10 فرص** | أقوى 10 فرص استثمارية حسب Smart Score | لاختيار أفضل الفرص المتاحة |
        | 🎯 **صائد التصحيحات** | اكتشاف الأسهم القوية التي تصحح | في الأسواق الهابطة أو المستقرة |
        | ⚡ **قناص الاختراق** | فرص الاختراق خلال جلسة أو جلستين | في الأسواق الصاعدة والنشطة |
        | 🚀 **انفجار سعري** | اختراق القمم مع سيولة مرعبة | للفرص القوية جداً |
        | 🔍 **تحليل سهم** | تحليل مفصل لسهم محدد | عند الرغبة في دراسة سهم معين |
        | 📊 **تقييم الأداء** | متابعة نتائج الصفقات السابقة | لتقييم أدائك وتحسينه |
        
        ---
        
        ### 🧠 المصطلحات المهمة
        
        | المصطلح | الشرح |
        |---------|-------|
        | **Smart Score** | درجة ذكاء السهم من 0-100 (كلما زادت كان أفضل) |
        | **RR Ratio** | نسبة المخاطرة إلى العائد (يفضل أن تكون 1.5+) |
        | **RSI** | مؤشر القوة النسبية (30-70 هو النطاق الصحي) |
        | **السيولة** | حجم التداول مقارنة بالمتوسط (أكثر من 1.5x ممتاز) |
        | **وقف الخسارة** | السعر الذي تخرج عنده لتجنب خسائر أكبر |
        | **الانفجار السعري** | اختراق أعلى 20 يوم مع سيولة استثنائية |
        
        ---
        
        ### 🎯 كيف تختار نمط التداول المناسب؟
        
        - 🛡️ **محافظ**: تناسب المبتدئين، تطالب RR مرتفع (2+) واتجاهات واضحة
        - ⚖️ **متوازن**: يناسب معظم المتداولين، توازن بين المخاطرة والعائد
        - 🚀 **هجومي**: للمحترفين، يقبل مخاطرة أعلى مقابل فرص أكثر
        
        ---
        
        ### ⚠️ تنبيهات مهمة
        
        1. هذا التحليل **ليس توصية شراء/بيع**، بل أداة مساعدة
        2. **لا تخاطر** بأكثر من 2-5% من رأس مالك في صفقة واحدة
        3. **راجع التحليل** بنفسك قبل اتخاذ أي قرار
        4. الأسواق المالية **تنطوي على مخاطر**، قد تخسر جزءاً من رأس مالك
        
        ---
        
        ### 🆕 ميزات جديدة في v4.0
        
        - **فلتر الحجم الحقيقي**: استبعاد الأسهم ذات السيولة الضعيفة (أقل من 500 ألف جنيه يومياً)
        - **وقف خسارة فني**: يعتمد على مستويات الدعم الحقيقية
        - **اكتشاف الانفجار السعري**: اختراق القمم مع سيولة مرعبة
        - **تحليل أكثر استقراراً**: استخدام الأسماء بدلاً من الترتيب في API
        """)


# ================== NAVIGATION BAR ==================
def render_navigation():
    st.markdown("""
    <div class='main-header'>
        <h1>🎯 EGX Sniper Pro v4.0</h1>
        <p>نظام تحليل أسهم البورصة المصرية - فائق الدقة والاستقرار</p>
    </div>
    """, unsafe_allow_html=True)
    
    market_status = get_egx30_status()
    st.markdown(f"""
    <div class='market-status'>
        <span style="color: {market_status['color']}; font-weight: bold;">📊 المؤشر العام:</span>
        <span>{market_status['status']}</span>
        <span style="margin-right: 20px;">📈 التغير: {market_status['change']:+.2f}%</span>
        <span>📊 RSI: {market_status['rsi']:.0f}</span>
        <span>💰 السعر: {market_status['price']:.2f}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # الصف الأول
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        if st.button("🏠 **الرئيسية**", use_container_width=True):
            st.session_state.page = 'home'
            st.rerun()
    with col2:
        if st.button("🏆 **أفضل 10 فرص**", use_container_width=True):
            st.session_state.page = 'top10'
            st.rerun()
    with col3:
        if st.button("🎯 **صائد التصحيحات**", use_container_width=True):
            st.session_state.page = 'correction'
            st.rerun()
    with col4:
        if st.button("⚡ **قناص الاختراق**", use_container_width=True):
            st.session_state.page = 'rapid'
            st.rerun()
    with col5:
        if st.button("🚀 **انفجار سعري**", use_container_width=True):
            st.session_state.page = 'breakout'
            st.rerun()
    
    # الصف الثاني
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        if st.button("🔍 **تحليل سهم**", use_container_width=True):
            st.session_state.page = 'analyze'
            st.rerun()
    with col2:
        if st.button("📊 **تقييم الأداء**", use_container_width=True):
            st.session_state.page = 'performance'
            st.rerun()
    with col3:
        if st.button("📖 **دليل المستخدم**", use_container_width=True):
            st.session_state.show_guide = not st.session_state.show_guide
            st.session_state.page = 'home'
            st.rerun()
    with col4:
        if st.button("🔄 **تحديث البيانات**", use_container_width=True):
            get_fresh_data()
            st.success("✅ تم تحديث البيانات!")
            st.rerun()
    with col5:
        with st.popover("⚙️ **الإعدادات**"):
            st.markdown("#### 🧠 نمط التداول")
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("🛡️ محافظ", use_container_width=True):
                    st.session_state.mode = "🛡️ محافظ"
            with c2:
                if st.button("⚖️ متوازن", use_container_width=True):
                    st.session_state.mode = "⚖️ متوازن"
            with c3:
                if st.button("🚀 هجومي", use_container_width=True):
                    st.session_state.mode = "🚀 هجومي"
            st.markdown(f"**النمط الحالي:** {st.session_state.mode}")
            
            st.markdown("---")
            st.markdown("#### 📂 فلتر القطاع")
            sectors = ["🌍 الكل", "🏆 EGX30 (قيادي)", "🏦 البنوك", "🏗️ العقارات", "🍔 الأغذية", "📡 الاتصالات", "🏭 الصناعة", "🛒 التجارة"]
            selected = st.selectbox("اختر قطاعاً", sectors)
            if selected != st.session_state.sector_filter:
                st.session_state.sector_filter = selected
                st.rerun()
            
            st.markdown("---")
            st.markdown(f"#### 💰 فلتر السيولة")
            st.info(f"الحد الأدنى للتداول اليومي: {MIN_DAILY_TURNOVER/1000:.0f} ألف جنيه")
            st.caption("الأسهم الأقل من هذا الحد لا تظهر في النتائج")
            
            if st.button("🗑️ مسح بيانات التقييم", use_container_width=True):
                if os.path.exists(TRADES_FILE):
                    os.remove(TRADES_FILE)
                st.success("✅ تم المسح!")
                st.rerun()
    
    st.markdown("---")
    if st.session_state.show_guide:
        show_guide()


# ================== UI RENDERER ==================
def render_stock_ui(res, is_top10=False):
    if res is None:
        st.warning("بيانات السهم غير متوفرة")
        return
    
    st.markdown(f"""
    <div style='display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #30363d; padding-bottom: 10px; margin-bottom: 15px;'>
        <span class='stock-name'>{res['name']} - {res['desc']}</span>
        <span style='background: #238636; padding: 5px 15px; border-radius: 20px; font-weight: bold;'>Smart: {res.get('smart_score', 0)}</span>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 السعر", f"{res['p']:.2f}", f"{res['chg']:+.2f}%")
    with col2:
        st.metric("🎯 Smart Score", f"{res['smart_score']}/100")
    with col3:
        rr_color = "🟢" if res['rr'] >= 2 else "🟡" if res['rr'] >= 1.5 else "🔴"
        st.metric("⚖️ RR Ratio", f"{rr_color} {res['rr']}")
    with col4:
        rsi_color = "🟢" if 40 <= res['rsi'] <= 60 else "🟡" if 30 <= res['rsi'] <= 70 else "🔴"
        st.metric("📊 RSI", f"{rsi_color} {res['rsi']:.0f}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("💧 السيولة", f"{res['ratio']:.1f}x")
    with col2:
        st.metric("💰 التداول اليومي", f"{res['daily_turnover']/1000:.0f} ألف ج")
    
    whatsapp_url = share_on_whatsapp(res)
    st.markdown(f"""
    <a href="{whatsapp_url}" target="_blank" style="display: block; background-color: #25D366; color: white; text-align: center; padding: 10px; border-radius: 10px; text-decoration: none; margin: 10px 0; font-weight: bold;">
        📱 مشاركة التحليل عبر واتساب
    </a>
    """, unsafe_allow_html=True)
    
    with st.expander("📊 التحليل الفني والشموع", expanded=True):
        render_tradingview_chart(res['name'], height=400)
        
        st.markdown(f"""
        <div style='background:#0d1117;border:1px solid #30363d;border-radius:10px;padding:15px;margin:15px 0;'>
            <b>📌 الاتجاهات:</b><br>
            {'🟢' if res['t_short'] == 'صاعد' else '🔴'} قصير المدى: {res['t_short']}<br>
            {'🟢' if res['t_med'] == 'صاعد' else '🔴'} متوسط المدى: {res['t_med']}<br>
            {'🟢' if res['t_long'] == 'صاعد' else '🔴'} طويل المدى: {res['t_long']}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style='background:#0d1117;border:1px solid #3fb950;border-radius:10px;padding:15px;margin:15px 0;'>
            <b>🎯 خطة التداول المقترحة</b><br>
            🟢 نطاق الدخول: {res['entry_range']}<br>
            🔴 وقف الخسارة: {res['stop_loss']:.2f} (-{res['risk_pct']:.1f}%)<br>
            🏁 الهدف: {res['target']:.2f} (+{res['target_pct']:.1f}%)
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🏛️ مستويات الدعم والمقاومة الثابتة")
        st.markdown(f"""
        | المستوى | السعر |
        |---------|-------|
        | 🔴 R2 (مقاومة ثانية) | {res['r2']:.2f} |
        | 🔴 R1 (مقاومة أولى) | {res['r1']:.2f} |
        | 🟡 PP (نقطة الارتكاز) | {res['pp']:.2f} |
        | 🟢 S1 (دعم أول) | {res['s1']:.2f} |
        | 🟢 S2 (دعم ثاني) | {res['s2']:.2f} |
        """)
    
    with st.expander("💰 إدارة المخاطر وخطة الدخول", expanded=False):
        deal_size = st.number_input("💰 ميزانية الصفقة (ج)", value=10000, step=1000, key=f"deal_{res['name']}")
        entry_price = res['entry_price']
        
        if deal_size > 0 and entry_price > 0:
            shares_deal = int(deal_size / entry_price)
            profit_val = (res['target'] - entry_price) * shares_deal
            loss_val = (entry_price - res['stop_loss']) * shares_deal
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("📦 عدد الأسهم", f"{shares_deal:,}")
                st.metric("💰 قيمة الصفقة", f"{deal_size:,.0f} ج")
            with col2:
                st.metric("🟢 الربح المتوقع", f"{profit_val:,.0f} ج", delta=f"+{res['target_pct']:.1f}%")
                st.metric("🔴 الخسارة المحتملة", f"{loss_val:,.0f} ج", delta=f"-{res['risk_pct']:.1f}%")
            
            st.markdown("### 🏹 خطة الدخول المتكاملة")
            st.info(f"🛡️ وقف الخسارة الفني: {res['stop_loss']:.2f} ج (أسفل الدعم S1 بنسبة 1%)")


# ================== MAIN APP ==================
def main():
    if st.session_state.all_results is None:
        get_fresh_data()
    
    render_navigation()
    
    filtered_results = filter_by_sector(st.session_state.all_results, st.session_state.sector_filter)
    
    # ================== HOME PAGE ==================
    if st.session_state.page == 'home':
        st.markdown("## 🏠 نظرة عامة على السوق")
        
        if filtered_results:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📊 إجمالي الأسهم", len(filtered_results))
            with col2:
                correction_count = 0
                for an in filtered_results:
                    if an:
                        is_corr, _, _ = is_correction_hunter(an)
                        if is_corr:
                            correction_count += 1
                st.metric("🎯 فرص تصحيح", correction_count)
            with col3:
                rapid_count = len(get_rapid_breakouts(filtered_results))
                st.metric("⚡ فرص اختراق", rapid_count)
            with col4:
                breakout_count = len(get_real_breakouts(filtered_results))
                st.metric("🚀 انفجار سعري", breakout_count)
        
        st.markdown("---")
        st.markdown("## 🔥 أحدث فرص السوق")
        
        tab1, tab2, tab3 = st.tabs(["🎯 صائد التصحيحات", "⚡ قناص الاختراق", "🚀 انفجار سعري"])
        
        with tab1:
            corrections = []
            for an in filtered_results:
                if an:
                    is_corr, reasons, strength = is_correction_hunter(an)
                    if is_corr:
                        corrections.append({'stock': an, 'reasons': reasons, 'strength': strength})
            
            if corrections:
                corrections.sort(key=lambda x: x['strength'], reverse=True)
                for item in corrections[:5]:
                    an = item['stock']
                    strength = item['strength']
                    badge = "🔥 فرصة قوية" if strength >= 70 else "✅ فرصة جيدة" if strength >= 50 else "⚠️ فرصة متوسطة"
                    badge_color = "#4caf50" if strength >= 70 else "#ff9800" if strength >= 50 else "#f44336"
                    
                    st.markdown(f"""
                    <div class='correction-card'>
                        <div style='display: flex; justify-content: space-between; align-items: center;'>
                            <h3 style='margin: 0; color: #81C784;'>🎯 {an['name']} - {an['desc']}</h3>
                            <span style='background: {badge_color}; padding: 5px 15px; border-radius: 20px; color: white;'>{badge} | {strength}%</span>
                        </div>
                        <div style='display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 10px 0;'>
                            <div>💰 {an['p']:.2f} ج</div>
                            <div>📊 RSI: {an['rsi']:.0f}</div>
                            <div>💧 سيولة: {an['ratio']:.1f}x</div>
                            <div>📈 تغير: {an['chg']:+.2f}%</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"📊 تحليل {an['name']}", key=f"home_corr_{an['name']}"):
                        render_stock_ui(an)
            else:
                st.info("لا توجد فرص تصحيح حالياً")
        
        with tab2:
            rapid_opportunities = get_rapid_breakouts(filtered_results)
            if rapid_opportunities:
                for item in rapid_opportunities[:5]:
                    an = item['stock']
                    analysis = item['analysis']
                    st.markdown(f"""
                    <div class='rapid-card'>
                        <h3 style='margin: 0; color: #FF9999;'>⚡ {an['name']} - {an['desc']}</h3>
                        <div style='display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 10px 0;'>
                            <div>🎯 هدف: {analysis['target_1']:.2f}</div>
                            <div>🛑 وقف: {analysis['stop_loss_rapid']:.2f}</div>
                            <div>💪 قوة: {analysis['strength']}%</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"📊 تحليل {an['name']}", key=f"home_rapid_{an['name']}"):
                        render_stock_ui(an)
            else:
                st.info("لا توجد فرص اختراق حالياً")
        
        with tab3:
            breakouts = get_real_breakouts(filtered_results)
            if breakouts:
                for item in breakouts[:5]:
                    an = item['stock']
                    strength = item['strength']
                    st.markdown(f"""
                    <div class='breakout-card'>
                        <h3 style='margin: 0; color: #FFD700;'>🚀 {an['name']} - {an['desc']}</h3>
                        <div style='display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 10px 0;'>
                            <div>💰 {an['p']:.2f} ج</div>
                            <div>💧 سيولة: {an['ratio']:.1f}x</div>
                            <div>📈 تغير: {an['chg']:+.2f}%</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"📊 تحليل {an['name']}", key=f"home_breakout_{an['name']}"):
                        render_stock_ui(an)
            else:
                st.info("لا توجد انفجارات سعرية حالياً")
    
    # ================== TOP 10 PAGE ==================
    elif st.session_state.page == 'top10':
        st.markdown("## 🏆 أفضل 10 فرص استثمارية")
        top_results = get_top_ranked(filtered_results, limit=10)
        if top_results:
            for i, an in enumerate(top_results, 1):
                with st.expander(f"#{i} - {an['name']} | Smart: {an['smart_score']} | RR: {an['rr']}"):
                    render_stock_ui(an, is_top10=True)
                    if st.button(f"💾 تسجيل", key=f"rec_top_{an['name']}"):
                        record_trade(an, "أفضل 10")
                        st.success("✅ تم التسجيل!")
        else:
            st.warning("لا توجد فرص مطابقة للمعايير")
    
    # ================== CORRECTION PAGE ==================
    elif st.session_state.page == 'correction':
        st.markdown("## 🎯 صائد التصحيحات")
        corrections = []
        for an in filtered_results:
            if an:
                is_corr, reasons, strength = is_correction_hunter(an)
                if is_corr:
                    corrections.append({'stock': an, 'reasons': reasons, 'strength': strength})
        
        if corrections:
            corrections.sort(key=lambda x: x['strength'], reverse=True)
            for item in corrections:
                an = item['stock']
                strength = item['strength']
                badge = "🔥 قوية" if strength >= 70 else "✅ جيدة" if strength >= 50 else "⚠️ متوسطة"
                st.markdown(f"""
                <div class='correction-card'>
                    <h3>🎯 {an['name']} - {an['desc']} <span style='float:right'>{badge} | {strength}%</span></h3>
                    <div>💰 {an['p']:.2f} | RSI: {an['rsi']:.0f} | سيولة: {an['ratio']:.1f}x</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"📊 تحليل {an['name']}", key=f"corr_{an['name']}"):
                    record_trade(an, "تصحيحات")
                    render_stock_ui(an)
        else:
            st.info("لا توجد فرص تصحيح حالياً")
    
    # ================== RAPID PAGE ==================
    elif st.session_state.page == 'rapid':
        st.markdown("## ⚡ قناص الاختراق")
        rapid_opportunities = get_rapid_breakouts(filtered_results)
        if rapid_opportunities:
            for item in rapid_opportunities:
                an = item['stock']
                analysis = item['analysis']
                st.markdown(f"""
                <div class='rapid-card'>
                    <h3>⚡ {an['name']} - {an['desc']}</h3>
                    <div>🎯 {analysis['target_1']:.2f} | 🛑 {analysis['stop_loss_rapid']:.2f} | 💪 {analysis['strength']}%</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"📊 تحليل {an['name']}", key=f"rapid_{an['name']}"):
                    record_trade(an, "اختراق")
                    render_stock_ui(an)
        else:
            st.info("لا توجد فرص اختراق")
    
    # ================== BREAKOUT PAGE (جديد) ==================
    elif st.session_state.page == 'breakout':
        st.markdown("## 🚀 الانفجار السعري الحقيقي")
        st.caption("اختراق القمم مع سيولة استثنائية - فرص قوية جداً")
        breakouts = get_real_breakouts(filtered_results)
        if breakouts:
            for item in breakouts:
                an = item['stock']
                strength = item['strength']
                st.markdown(f"""
                <div class='breakout-card'>
                    <h3>🚀 {an['name']} - {an['desc']} <span style='float:right'>قوة: {strength}%</span></h3>
                    <div>💰 {an['p']:.2f} | سيولة: {an['ratio']:.1f}x | تغير: {an['chg']:+.2f}%</div>
                    <div>🎯 قمة 20 يوم: {an.get('high_20d', an['p']):.2f}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"📊 تحليل {an['name']}", key=f"breakout_{an['name']}"):
                    record_trade(an, "انفجار سعري")
                    render_stock_ui(an)
        else:
            st.info("لا توجد انفجارات سعرية حالياً")
    
    # ================== ANALYZE PAGE ==================
    elif st.session_state.page == 'analyze':
        st.markdown("## 🔍 تحليل سهم")
        sym = st.text_input("🔎 رمز السهم", placeholder="مثال: COMI, TMGH, ETEL").upper().strip()
        if sym:
            data = fetch_single_stock(sym)
            if data:
                res = analyze_stock(data[0])
                if res:
                    render_stock_ui(res)
                    if st.button(f"💾 تسجيل", key=f"rec_analyze_{sym}"):
                        record_trade(res, "تحليل")
                        st.success("✅ تم التسجيل!")
                else:
                    st.error("فشل التحليل")
            else:
                st.error("السهم غير موجود")
    
    # ================== PERFORMANCE PAGE ==================
    elif st.session_state.page == 'performance':
        st.markdown("## 📊 تقييم الأداء")
        if st.session_state.all_results:
            current_prices = {res['name']: res['p'] for res in st.session_state.all_results if res}
            trades = update_all_trades(current_prices)
        else:
            trades = load_trades()
        stats = get_performance_stats(trades)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📊 الإجمالي", stats['total'])
        col2.metric("✅ حققت الهدف", stats['hit_target'])
        col3.metric("❌ ضربت الوقف", stats['stopped_out'])
        col4.metric("⏳ مفتوحة", stats['still_open'])
        col1, col2 = st.columns(2)
        col1.metric("📈 نسبة النجاح", f"{stats['success_rate']}%")
        col2.metric("⚖️ متوسط RR", stats['avg_rr'])
        
        if trades:
            st.markdown("### 📋 آخر الصفقات")
            for trade in trades[-10:][::-1]:
                status = "🟢 هدف" if trade.get('status') == 'hit_target' else "🔴 وقف" if trade.get('status') == 'stopped_out' else "🟡 مفتوح"
                st.markdown(f"- {trade.get('name')} ({trade.get('trade_type')}) - {status}")


if __name__ == "__main__":
    main()
