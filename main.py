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
    page_title="🎯 EGX Sniper Pro", 
    layout="wide", 
    page_icon="🎯",
    initial_sidebar_state="collapsed"  # تصغير الشريط الجانبي افتراضياً
)

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

# ================== 📁 PERFORMANCE TRACKING ==================
TRADES_FILE = "trades_data.json"
OUTCOMES_FILE = "trade_outcomes.json"

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

def update_all_trades(current_prices):
    trades = load_trades()
    today = date.today()
    updated = False
    
    for trade in trades:
        if trade.get('status') in ['pending', 'still_open']:
            symbol = trade.get('name')
            if symbol in current_prices:
                current_price = current_prices[symbol]
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
            'top10_count': 0, 'gold_count': 0,
            'top10_success': 0, 'gold_success': 0,
            'top10_return': 0, 'gold_return': 0,
            'avg_holding_days': 0, 'entry_accuracy': 0,
            'current_win_streak': 0, 'max_win_streak': 0,
            'avg_mfe': 0, 'avg_mae': 0
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
        'avg_holding_days': 0, 'entry_accuracy': 0,
        'current_win_streak': 0, 'max_win_streak': 0,
        'avg_mfe': 0, 'avg_mae': 0
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
                if data and len(data) > 0 and len(data[0].get('d', [])) >= 7:
                    d = data[0]['d']
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


# ================== 🔥 SMART SCORE ==================
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
    
    if score >= 6:
        return True, reasons, strength_percent
    elif score >= 4:
        return True, reasons, strength_percent
    else:
        return False, [f"درجة منخفضة ({score}/{max_score})"], strength_percent


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
    
    return {
        "is_breakout": True,
        "reasons": reasons,
        "strength": strength,
        "label": label,
        "color": color,
        "target_1": r1,
        "target_2": an.get('r2', r1 * 1.03),
        "stop_loss_rapid": max(an.get('s1', p * 0.98), p * 0.97)
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
            elif sector == "📌 أخرى" and stock_sector == "📌 أخرى":
                filtered.append(an)
    return filtered


# ================== 📈 DATA & ANALYSIS ENGINE ==================
@st.cache_data(ttl=300, show_spinner=False)
def get_all_data():
    url = "https://scanner.tradingview.com/egypt/scan"
    cols = ["name","close","RSI","volume","average_volume_10d_calc","high","low","change","description","SMA20","SMA50","SMA200"]
    payload = {
        "filter": [{"left": "volume", "operation": "greater", "right": 1000}],
        "columns": cols,
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
    url = "https://scanner.tradingview.com/egypt/scan"
    cols = ["name","close","RSI","volume","average_volume_10d_calc","high","low","change","description","SMA20","SMA50","SMA200"]
    
    payload = {
        "filter": [{"left": "name", "operation": "match", "right": symbol.upper()}],
        "columns": cols,
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

def analyze_stock(d_row):
    try:
        d = d_row.get('d', [])
        
        if len(d) != 12:
            return None
        
        name, p, rsi, v, avg_v, h, l, chg, desc, sma20, sma50, sma200 = d
        if p is None or p <= 0:
            return None
        
        if not desc or desc == "":
            desc = name
        
        rsi_val = rsi or 0
        ratio = v / avg_v if avg_v and avg_v > 0 else 0
        estimated_value = p * v
        
        # المسافة من SMA50
        dist_sma50 = ((p - sma50) / sma50) * 100 if sma50 and sma50 > 0 else 0
        
        t_short = "صاعد" if (sma20 and p > sma20) else "هابط"
        t_med = "صاعد" if (sma50 and p > sma50) else "هابط"
        t_long = "صاعد" if (sma200 and p > sma200) else "هابط"
        
        entry_min = p * 0.98
        entry_max = p * 1.01
        entry_price = (entry_min + entry_max) / 2
        pp = (p + (h or p) + (l or p)) / 3
        s1 = (2 * pp) - (h or p)
        r1 = (2 * pp) - (l or p)
        s2 = pp - ((h or p) - (l or p))
        r2 = pp + ((h or p) - (l or p))
        
        stop_loss = min(s2, entry_price * 0.97) if s2 > 0 else entry_price * 0.96
        target = max(r1, entry_price * 1.05) if r1 > 0 else entry_price * 1.05
        
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
            "dist_sma50": dist_sma50,
            "s1": s1, "s2": s2, "r1": r1, "r2": r2, "pp": pp,
            "sma20": sma20, "sma50": sma50, "sma200": sma200,
            "volume": v, "avg_volume": avg_v, "estimated_value": estimated_value,
            "entry_range": f"{entry_min:.2f} - {entry_max:.2f}", "entry_price": entry_price,
            "stop_loss": stop_loss, "target": target,
            "rr": rr, "risk_pct": risk_pct, "target_pct": target_pct,
            "smart_score": smart_score, "execution_strength": execution_strength
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

def get_top_ranked(results, limit=10):
    if not results:
        return []
    valid_results = [r for r in results if r is not None and r.get('estimated_value', 0) >= 2000000]
    sorted_results = sorted(
        valid_results,
        key=lambda x: (x.get('smart_score', 0) * 0.5 + x.get('execution_strength', 0) * 0.3 + x.get('rr', 0) * 10),
        reverse=True
    )
    return sorted_results[:limit]

def get_rapid_breakouts(results):
    rapid = []
    for an in results:
        if an and an.get('estimated_value', 0) >= 2000000:
            analysis = is_rapid_breakout(an)
            if analysis.get('is_breakout', False):
                rapid.append({'stock': an, 'analysis': analysis})
    rapid.sort(key=lambda x: x['analysis']['strength'], reverse=True)
    return rapid[:8]

def get_fresh_data():
    with st.spinner("🔄 جاري تحميل بيانات السوق..."):
        raw_data = get_all_data()
        if raw_data:
            st.session_state.market_data = raw_data
            st.session_state.all_results = preprocess_all_data(raw_data)
            st.session_state.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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


# ================== 🎨 GLOBAL STYLES ==================
st.markdown("""
<style>
    /* تنسيق عام */
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
    
    /* تنسيق الأزرار */
    .nav-btn {
        background-color: #0d1117;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 12px;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
        margin: 5px;
    }
    .nav-btn:hover {
        background-color: #1f242f;
        border-color: #58a6ff;
    }
    .nav-btn.active {
        background-color: #238636;
        border-color: #3fb950;
        color: white;
    }
    
    /* تنسيق البطاقات */
    .card {
        background: linear-gradient(135deg, #0d1117, #0a0c10);
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        border: 1px solid #30363d;
    }
    .card-title {
        font-size: 18px;
        font-weight: bold;
        color: #58a6ff;
        margin-bottom: 10px;
    }
    
    /* تنسيق المؤشرات */
    .market-status {
        background: #0d1117;
        border-radius: 10px;
        padding: 10px;
        text-align: center;
        margin-bottom: 20px;
    }
    
    /* تنسيق الشارت */
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 45px;
        font-weight: bold;
    }
    
    /* تنسيق الإكسباندر */
    .streamlit-expanderHeader {
        background-color: #0d1117;
        border-radius: 10px;
    }
    
    /* تنسيق النصوص */
    .stock-name {
        font-size: 20px;
        font-weight: bold;
        color: #58a6ff;
    }
    .stock-price {
        font-size: 24px;
        font-weight: bold;
    }
    
    /* تنسيق الدليل */
    .guide-section {
        background: #0d1117;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        border-right: 4px solid #58a6ff;
    }
    .guide-icon {
        font-size: 32px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)


# ================== 📖 GUIDE SECTION ==================
def show_guide():
    """عرض دليل المستخدم"""
    with st.expander("📖 دليل المستخدم - اضغط للتعلم", expanded=st.session_state.show_guide):
        st.markdown("""
        ## 📖 دليل EGX Sniper Pro
        
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
        
        ### 📞 الدعم والمساعدة
        
        - لمشكلة تقنية: أعد تشغيل التطبيق
        - لبيانات غير محدثة: اضغط على "تحديث البيانات"
        - لاستفسار: تواصل مع مطور التطبيق
        """)
        
        if st.button("🗑️ إغلاق الدليل", use_container_width=True):
            st.session_state.show_guide = False
            st.rerun()


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
    
    whatsapp_url = share_on_whatsapp(res)
    st.markdown(f"""
    <a href="{whatsapp_url}" target="_blank" style="display: block; background-color: #25D366; color: white; text-align: center; padding: 10px; border-radius: 10px; text-decoration: none; margin: 10px 0; font-weight: bold;">
        📱 مشاركة التحليل عبر واتساب
    </a>
    """, unsafe_allow_html=True)
    
    with st.expander("📊 التحليل الفني والشموع", expanded=True):
        st.markdown("### 📈 شارت السهم")
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
        
        st.markdown("### 🏛️ مستويات الدعم والمقاومة")
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
            
            st.markdown("### 🏹 خطة الدخول المتكاملة (3 مستويات)")
            
            range_size = entry_price - res['stop_loss']
            entry_level_1 = entry_price
            entry_level_2 = max(entry_price - (range_size * 0.5), res['stop_loss'] * 1.02)
            entry_level_3 = entry_price + (res['target'] - entry_price) * 0.3
            
            if res['rr'] >= 2.5:
                weights = [0.6, 0.25, 0.15]
            elif res['rr'] >= 1.8:
                weights = [0.5, 0.3, 0.2]
            else:
                weights = [0.4, 0.35, 0.25]
            
            shares_1 = int((deal_size * weights[0]) / entry_level_1) if entry_level_1 > 0 else 0
            shares_2 = int((deal_size * weights[1]) / entry_level_2) if entry_level_2 > 0 else 0
            shares_3 = int((deal_size * weights[2]) / entry_level_3) if entry_level_3 > 0 else 0
            
            st.markdown(f"""
            <div style='background:#0d1117;border:1px solid #3fb950;border-radius:10px;padding:12px;margin:10px 0;'>
                <b>📌 المستوى الأول - الدخول الأساسي</b><br>
                🟢 السعر: <b>{entry_level_1:.2f}</b> ج | 📦 الكمية: <b>{shares_1:,}</b> سهم
            </div>
            <div style='background:#0d1117;border:1px solid #d29922;border-radius:10px;padding:12px;margin:10px 0;'>
                <b>📌 المستوى الثاني - تعزيز الدعم</b><br>
                🟡 السعر: <b>{entry_level_2:.2f}</b> ج | 📦 الكمية: <b>{shares_2:,}</b> سهم
            </div>
            <div style='background:#0d1117;border:1px solid #58a6ff;border-radius:10px;padding:12px;margin:10px 0;'>
                <b>📌 المستوى الثالث - تأكيد الاختراق</b><br>
                🔵 السعر: <b>{entry_level_3:.2f}</b> ج | 📦 الكمية: <b>{shares_3:,}</b> سهم
            </div>
            """, unsafe_allow_html=True)
            
            total_shares = shares_1 + shares_2 + shares_3
            total_cost = (shares_1 * entry_level_1) + (shares_2 * entry_level_2) + (shares_3 * entry_level_3)
            if total_shares > 0:
                avg_price = total_cost / total_shares
                st.info(f"📊 **متوسط السعر بعد التنفيذ الكامل:** {avg_price:.2f} ج ({total_shares:,} سهم)")


# ================== NAVIGATION BAR ==================
def render_navigation():
    """شريط التنقل العلوي"""
    
    # الهيدر
    st.markdown("""
    <div class='main-header'>
        <h1>🎯 EGX Sniper Pro</h1>
        <p>نظام تحليل أسهم البورصة المصرية - فائق الدقة</p>
    </div>
    """, unsafe_allow_html=True)
    
    # حالة السوق
    market_status = get_egx30_status()
    st.markdown(f"""
    <div class='market-status'>
        <span style="color: {market_status['color']}; font-weight: bold;">📊 المؤشر العام:</span>
        <span>{market_status['status']}</span>
        <span style="margin-right: 20px;">📈 التغير: {market_status['change']:+.2f}%</span>
        <span>📊 RSI: {market_status['rsi']:.0f}</span>
        <span style="margin-right: 20px;">💰 السعر: {market_status['price']:.2f}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # شريط التنقل - صفوف من الأزرار
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("🏠 **الرئيسية**", use_container_width=True, help="نظرة عامة على السوق وأحدث الفرص"):
            st.session_state.page = 'home'
            st.rerun()
    
    with col2:
        if st.button("🏆 **أفضل 10 فرص**", use_container_width=True, help="أقوى 10 فرص استثمارية حسب Smart Score"):
            st.session_state.page = 'top10'
            st.rerun()
    
    with col3:
        if st.button("🎯 **صائد التصحيحات**", use_container_width=True, help="اكتشاف الأسهم القوية التي تصحح"):
            st.session_state.page = 'correction'
            st.rerun()
    
    with col4:
        if st.button("⚡ **قناص الاختراق**", use_container_width=True, help="فرص الاختراق خلال جلسة أو جلستين"):
            st.session_state.page = 'rapid'
            st.rerun()
    
    with col5:
        if st.button("🔍 **تحليل سهم**", use_container_width=True, help="تحليل مفصل لسهم محدد"):
            st.session_state.page = 'analyze'
            st.rerun()
    
    # الصف الثاني من الأزرار
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("📊 **تقييم الأداء**", use_container_width=True, help="متابعة نتائج الصفقات السابقة"):
            st.session_state.page = 'performance'
            st.rerun()
    
    with col2:
        if st.button("📖 **دليل المستخدم**", use_container_width=True, help="شرح التطبيق وكيفية استخدامه"):
            st.session_state.show_guide = not st.session_state.show_guide
            st.session_state.page = 'home'
            st.rerun()
    
    with col3:
        if st.button("🔄 **تحديث البيانات**", use_container_width=True, help="تحديث بيانات السوق"):
            get_fresh_data()
            st.success("✅ تم تحديث البيانات!")
            st.rerun()
    
    with col4:
        # إعدادات إضافية
        with st.popover("⚙️ **الإعدادات**"):
            st.markdown("### ⚙️ إعدادات التطبيق")
            
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
            sectors = ["🌍 الكل", "🏆 EGX30 (قيادي)", "🏦 البنوك", "🏗️ العقارات", "🍔 الأغذية", "📡 الاتصالات", "🏭 الصناعة", "🛒 التجارة", "📌 أخرى"]
            selected = st.selectbox("اختر قطاعاً", sectors, index=sectors.index(st.session_state.sector_filter) if st.session_state.sector_filter in sectors else 0)
            if selected != st.session_state.sector_filter:
                st.session_state.sector_filter = selected
                st.rerun()
            
            st.markdown("---")
            if st.button("🗑️ مسح بيانات التقييم", use_container_width=True):
                if os.path.exists(TRADES_FILE):
                    os.remove(TRADES_FILE)
                st.success("✅ تم مسح بيانات التقييم!")
                st.rerun()
    
    with col5:
        st.caption(f"🕐 آخر تحديث: {st.session_state.last_update or 'لم يتم بعد'}")
    
    st.markdown("---")
    
    # عرض الدليل إذا كان مطلوباً
    if st.session_state.show_guide:
        show_guide()


# ================== MAIN APP ==================
def main():
    # تحميل البيانات إذا لزم الأمر
    if st.session_state.all_results is None:
        get_fresh_data()
    
    # شريط التنقل
    render_navigation()
    
    # تطبيق فلتر القطاع
    filtered_results = filter_by_sector(st.session_state.all_results, st.session_state.sector_filter)
    
    # ================== HOME PAGE ==================
    if st.session_state.page == 'home':
        st.markdown("## 🏠 نظرة عامة على السوق")
        
        if filtered_results:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📊 إجمالي الأسهم", len(filtered_results))
            with col2:
                # فرص التصحيح
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
                top_count = len(get_top_ranked(filtered_results, 10))
                st.metric("🏆 أفضل 10 فرص", f"{top_count}/10")
        
        st.markdown("---")
        st.markdown("## 🔥 أحدث فرص السوق")
        
        tab1, tab2 = st.tabs(["🎯 صائد التصحيحات", "⚡ قناص الاختراق"])
        
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
                    
                    if strength >= 70:
                        badge = "🔥 فرصة قوية جداً"
                        badge_color = "#4caf50"
                    elif strength >= 50:
                        badge = "✅ فرصة جيدة"
                        badge_color = "#ff9800"
                    else:
                        badge = "⚠️ فرصة متوسطة"
                        badge_color = "#f44336"
                    
                    with st.container():
                        st.markdown(f"""
                        <div style='background: linear-gradient(135deg, #0d1f0d, #0a150a); border-radius: 12px; padding: 15px; margin-bottom: 15px; border-right: 4px solid {badge_color};'>
                            <div style='display: flex; justify-content: space-between; align-items: center;'>
                                <h3 style='margin: 0; color: #81C784;'>🎯 {an['name']} - {an['desc']}</h3>
                                <span style='background: {badge_color}; padding: 5px 15px; border-radius: 20px; color: white; font-weight: bold;'>
                                    {badge} | {strength}%
                                </span>
                            </div>
                            <div style='height: 6px; background: #1a3a1a; margin: 10px 0; border-radius: 3px;'>
                                <div style='width: {strength}%; background: {badge_color}; height: 6px; border-radius: 3px;'></div>
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
                st.info("ℹ️ لا توجد فرص تصحيح حالياً.")
        
        with tab2:
            rapid_opportunities = get_rapid_breakouts(filtered_results)
            if rapid_opportunities:
                for item in rapid_opportunities[:5]:
                    an = item['stock']
                    analysis = item['analysis']
                    
                    with st.container():
                        st.markdown(f"""
                        <div style='background: linear-gradient(135deg, #1a0a0a, #0d0a0a); border-radius: 12px; padding: 15px; margin-bottom: 15px; border-right: 4px solid {analysis["color"]};'>
                            <div style='display: flex; justify-content: space-between; align-items: center;'>
                                <h3 style='margin: 0; color: #FF9999;'>⚡ {an['name']} - {an['desc']}</h3>
                                <span style='background: {analysis["color"]}; padding: 5px 15px; border-radius: 20px; color: #1a1a1a; font-weight: bold;'>
                                    {analysis['label']} | {analysis['strength']}%
                                </span>
                            </div>
                            <div style='height: 6px; background: #333; margin: 10px 0; border-radius: 3px;'>
                                <div style='width: {analysis['strength']}%; background: {analysis["color"]}; height: 6px; border-radius: 3px;'></div>
                            </div>
                            <div style='display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 10px 0;'>
                                <div>🎯 هدف أول: {analysis['target_1']:.2f}</div>
                                <div>🎯 هدف ثاني: {analysis['target_2']:.2f}</div>
                                <div>🛑 وقف ضيق: {analysis['stop_loss_rapid']:.2f}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button(f"📊 تحليل {an['name']}", key=f"home_rapid_{an['name']}"):
                            render_stock_ui(an)
            else:
                st.info("ℹ️ لا توجد فرص اختراق حالياً.")
    
    # ================== TOP 10 PAGE ==================
    elif st.session_state.page == 'top10':
        st.markdown("## 🏆 أفضل 10 فرص استثمارية")
        st.caption("هذه هي أقوى 10 فرص حسب Smart Score وقوة التنفيذ")
        
        top_results = get_top_ranked(filtered_results, limit=10)
        
        if top_results:
            for i, an in enumerate(top_results, 1):
                with st.expander(f"#{i} - {an['name']} | Smart: {an['smart_score']} | RR: {an['rr']} | RSI: {an['rsi']:.0f}"):
                    render_stock_ui(an, is_top10=True)
                    if st.button(f"💾 تسجيل الصفقة", key=f"rec_top_{an['name']}"):
                        record_trade(an, "أفضل 10")
                        st.success("✅ تم تسجيل الصفقة!")
        else:
            st.warning("⚠️ لا توجد فرص مطابقة للمعايير حالياً (Smart Score ≥ 60 وسيولة كافية).")
    
    # ================== CORRECTION PAGE ==================
    elif st.session_state.page == 'correction':
        st.markdown("## 🎯 صائد التصحيحات (Correction Hunter)")
        st.markdown("""
        <div style="background: rgba(46,125,50,0.15); border-right: 4px solid #2E7D32; padding: 10px; border-radius: 8px; margin-bottom: 20px;">
            🎯 <b>ما هذا القسم؟</b><br>
            نكتشف الأسهم القوية التي في حالة تصحيح (نزول مؤقت) استعداداً للانطلاق مرة أخرى.<br>
            • <b>الاتجاه العام صاعد</b> (السهم قوي)<br>
            • <b>RSI منخفض (28-55)</b> (السهم صحح بما يكفي)<br>
            • <b>بداية ارتداد</b> (التغير إيجابي أو مستقر)
        </div>
        """, unsafe_allow_html=True)
        
        corrections = []
        for an in filtered_results:
            if an:
                is_corr, reasons, strength = is_correction_hunter(an)
                if is_corr:
                    corrections.append({'stock': an, 'reasons': reasons, 'strength': strength})
        
        if corrections:
            corrections.sort(key=lambda x: x['strength'], reverse=True)
            st.markdown(f"**🎯 عدد فرص التصحيح: {len(corrections)}**")
            
            for item in corrections:
                an = item['stock']
                reasons = item['reasons']
                strength = item['strength']
                
                if strength >= 70:
                    badge = "🔥 فرصة قوية جداً - مناسبة للدخول"
                    badge_color = "#4caf50"
                elif strength >= 50:
                    badge = "✅ فرصة جيدة - مراقبة عن كثب"
                    badge_color = "#ff9800"
                else:
                    badge = "⚠️ فرصة متوسطة - تحتاج تأكيد إضافي"
                    badge_color = "#f44336"
                
                with st.container():
                    st.markdown(f"""
                    <div style='background: linear-gradient(135deg, #0d1f0d, #0a150a); border-radius: 12px; padding: 15px; margin-bottom: 15px; border-right: 4px solid {badge_color};'>
                        <div style='display: flex; justify-content: space-between; align-items: center;'>
                            <h3 style='margin: 0; color: #81C784;'>🎯 {an['name']} - {an['desc']}</h3>
                            <span style='background: {badge_color}; padding: 5px 15px; border-radius: 20px; color: white; font-weight: bold;'>
                                {badge} | {strength}%
                            </span>
                        </div>
                        <div style='height: 6px; background: #1a3a1a; margin: 10px 0; border-radius: 3px;'>
                            <div style='width: {strength}%; background: {badge_color}; height: 6px; border-radius: 3px;'></div>
                        </div>
                        <div style='display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 10px 0;'>
                            <div>💰 {an['p']:.2f} ج</div>
                            <div>📊 RSI: {an['rsi']:.0f}</div>
                            <div>💧 سيولة: {an['ratio']:.1f}x</div>
                            <div>📈 تغير: {an['chg']:+.2f}%</div>
                        </div>
                        <div style='background: rgba(46,125,50,0.15); border-radius: 8px; padding: 8px;'>
                            ✅ <b>أسباب الفرصة:</b><br>
                            {', '.join(reasons[:5])}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"📊 تحليل {an['name']} بالتفصيل", key=f"corr_{an['name']}"):
                        record_trade(an, "صائد تصحيحات")
                        render_stock_ui(an)
        else:
            st.info("ℹ️ لا توجد فرص تصحيح حالياً. قد يكون السوق في اتجاه صاعد قوي دون تصحيح.")
    
    # ================== RAPID BREAKOUT PAGE ==================
    elif st.session_state.page == 'rapid':
        st.markdown("## ⚡ قناص الاختراق السريع")
        st.markdown("""
        <div style="background: rgba(255,102,102,0.15); border-right: 4px solid #FF6666; padding: 10px; border-radius: 8px; margin-bottom: 20px;">
            🚀 <b>ما هذا القسم؟</b><br>
            نكتشف الأسهم على وشك الاختراق خلال جلسة أو جلستين.<br>
            • <b>RSI صحي (45-75)</b> (زخم قوي بدون تشبع)<br>
            • <b>سيولة استثنائية (>1.5x)</b> (اهتمام كبير)<br>
            • <b>قرب اختراق المقاومة</b> (على وشك الانطلاق)
        </div>
        """, unsafe_allow_html=True)
        
        rapid_opportunities = get_rapid_breakouts(filtered_results)
        
        if rapid_opportunities:
            st.markdown(f"**⚡ عدد فرص الاختراق السريع: {len(rapid_opportunities)}**")
            
            for item in rapid_opportunities:
                an = item['stock']
                analysis = item['analysis']
                
                with st.container():
                    st.markdown(f"""
                    <div style='background: linear-gradient(135deg, #1a0a0a, #0d0a0a); border-radius: 12px; padding: 15px; margin-bottom: 15px; border-right: 4px solid {analysis["color"]};'>
                        <div style='display: flex; justify-content: space-between; align-items: center;'>
                            <h3 style='margin: 0; color: #FF9999;'>⚡ {an['name']} - {an['desc']}</h3>
                            <span style='background: {analysis["color"]}; padding: 5px 15px; border-radius: 20px; color: #1a1a1a; font-weight: bold;'>
                                {analysis['label']} | {analysis['strength']}%
                            </span>
                        </div>
                        <div style='height: 6px; background: #333; margin: 10px 0; border-radius: 3px;'>
                            <div style='width: {analysis['strength']}%; background: {analysis["color"]}; height: 6px; border-radius: 3px;'></div>
                        </div>
                        <div style='display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 10px 0;'>
                            <div>💰 {an['p']:.2f} ج</div>
                            <div>📊 RSI: {an['rsi']:.0f}</div>
                            <div>💧 سيولة: {an['ratio']:.1f}x</div>
                            <div>📈 تغير: {an['chg']:+.2f}%</div>
                        </div>
                        <div style='display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 10px 0;'>
                            <div style='background: #1f4f2b; border-radius: 8px; padding: 8px; text-align: center; color: white;'>
                                🎯 هدف أول<br><b>{analysis['target_1']:.2f}</b>
                            </div>
                            <div style='background: #1f3a4f; border-radius: 8px; padding: 8px; text-align: center; color: white;'>
                                🎯 هدف ثاني<br><b>{analysis['target_2']:.2f}</b>
                            </div>
                            <div style='background: #4a1a1a; border-radius: 8px; padding: 8px; text-align: center; color: white;'>
                                🛑 وقف ضيق<br><b>{analysis['stop_loss_rapid']:.2f}</b>
                            </div>
                        </div>
                        <div style='background: rgba(255,102,102,0.1); border-radius: 8px; padding: 8px;'>
                            ✅ <b>أسباب الاختراق:</b><br>
                            {', '.join(analysis['reasons'])}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"📊 تحليل {an['name']} بالتفصيل", key=f"rapid_{an['name']}"):
                        record_trade(an, "اختراق سريع")
                        render_stock_ui(an)
        else:
            st.info("ℹ️ لا توجد فرص اختراق حالياً. قد يكون السوق هادئاً أو في حالة تصحيح.")
    
    # ================== ANALYZE PAGE ==================
    elif st.session_state.page == 'analyze':
        st.markdown("## 🔍 تحليل سهم")
        st.caption("أدخل رمز السهم الذي تريد تحليله (مثال: COMI, TMGH, ETEL)")
        
        sym = st.text_input("🔎 رمز السهم", placeholder="مثال: COMI, TMGH, ETEL", key="analyze_sym").upper().strip()
        
        if sym:
            with st.spinner("🔍 جاري البحث عن السهم..."):
                data = fetch_single_stock(sym)
                
                if not data:
                    st.error(f"❌ السهم '{sym}' غير موجود في قاعدة البيانات")
                    if st.session_state.all_results:
                        symbols = [r.get('name') for r in st.session_state.all_results[:30] if r]
                        if symbols:
                            st.info(f"💡 أمثلة على رموز موجودة: {', '.join(symbols[:15])}")
                else:
                    res = analyze_stock(data[0])
                    if res:
                        render_stock_ui(res)
                        if st.button(f"💾 تسجيل الصفقة", key=f"rec_analyze_{sym}"):
                            record_trade(res, "تحليل فردي")
                            st.success("✅ تم تسجيل الصفقة!")
                    else:
                        st.warning("⚠️ فشل تحليل السهم، حاول مرة أخرى")
    
    # ================== PERFORMANCE PAGE ==================
    elif st.session_state.page == 'performance':
        st.markdown("## 📊 تقييم الأداء")
        st.caption("متابعة نتائج الصفقات السابقة وتحليل الأداء")
        
        # تحديث البيانات أولاً
        if st.session_state.all_results:
            current_prices = {res['name']: res['p'] for res in st.session_state.all_results if res}
            trades = update_all_trades(current_prices)
        else:
            trades = load_trades()
        
        stats = get_performance_stats(trades)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📊 إجمالي الصفقات", stats['total'])
        col2.metric("✅ حققت الهدف", stats['hit_target'])
        col3.metric("❌ ضربت الوقف", stats['stopped_out'])
        col4.metric("⏳ لا تزال مفتوحة", stats['still_open'])
        
        col1, col2, col3 = st.columns(3)
        col1.metric("📈 نسبة النجاح", f"{stats['success_rate']}%")
        col2.metric("💰 إجمالي العائد", f"{stats['total_return']}%")
        col3.metric("⚖️ متوسط RR", stats['avg_rr'])
        
        if trades:
            st.markdown("---")
            st.markdown("### 📋 آخر الصفقات")
            for trade in trades[-10:][::-1]:
                if trade.get('status') == 'hit_target':
                    status_icon = "🟢"
                    status_text = "حققت الهدف"
                elif trade.get('status') == 'stopped_out':
                    status_icon = "🔴"
                    status_text = "ضربت الوقف"
                else:
                    status_icon = "🟡"
                    status_text = "لا تزال مفتوحة"
                
                profit_text = f" | {trade.get('profit_pct', 0):+.1f}%" if trade.get('profit_pct') else ""
                
                st.markdown(f"""
                <div style='background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:10px;margin:5px 0;'>
                    <b>{status_icon} {trade.get('name', 'N/A')}</b> ({trade.get('trade_type', 'N/A')}) - {status_text}{profit_text}<br>
                    📅 تاريخ التسجيل: {trade.get('date_recorded', 'N/A')}<br>
                    🎯 الهدف: {trade.get('target', 0):.2f} | 🛑 الوقف: {trade.get('stop_loss', 0):.2f} | ⚖️ RR: {trade.get('rr', 0)}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("📭 لا توجد صفقات مسجلة بعد. استخدم زر 'تسجيل الصفقة' عند تحليل أي سهم.")


if __name__ == "__main__":
    main()
