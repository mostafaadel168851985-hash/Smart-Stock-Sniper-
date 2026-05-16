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

if is_mobile:
    st.session_state.mobile_view = True
else:
    st.session_state.mobile_view = False

st.set_page_config(page_title="🎯 EGX Sniper Ultimate v2.0", layout="wide", page_icon="🎯")

# ================== 📁 PERFORMANCE TRACKING (محسن) ==================
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

def load_outcomes():
    if os.path.exists(OUTCOMES_FILE):
        try:
            with open(OUTCOMES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_outcomes(outcomes):
    try:
        with open(OUTCOMES_FILE, 'w', encoding='utf-8') as f:
            json.dump(outcomes, f, ensure_ascii=False, indent=2)
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
    
    closed_trades = [t for t in trades if t.get('status') in ['hit_target', 'stopped_out'] and t.get('days_open') is not None]
    avg_holding_days = sum(t.get('days_open', 0) for t in closed_trades) / len(closed_trades) if closed_trades else 0
    
    trades_with_entry = [t for t in trades if t.get('entry_hit', False)]
    entry_accuracy = (len(trades_with_entry) / total * 100) if total > 0 else 0
    
    top10_trades = [t for t in trades if t.get('trade_type') == 'top10']
    gold_trades = [t for t in trades if t.get('trade_type') == 'gold']
    
    top10_closed = [t for t in top10_trades if t.get('status') in ['hit_target', 'stopped_out']]
    gold_closed = [t for t in gold_trades if t.get('status') in ['hit_target', 'stopped_out']]
    
    top10_success = (len([t for t in top10_closed if t.get('status') == 'hit_target']) / len(top10_closed) * 100) if top10_closed else 0
    gold_success = (len([t for t in gold_closed if t.get('status') == 'hit_target']) / len(gold_closed) * 100) if gold_closed else 0
    
    top10_return = sum(t.get('profit_pct', 0) for t in top10_trades if t.get('profit_pct') is not None)
    gold_return = sum(t.get('profit_pct', 0) for t in gold_trades if t.get('profit_pct') is not None)
    
    current_streak = 0
    max_streak = 0
    for t in trades:
        if t.get('status') == 'hit_target':
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        elif t.get('status') == 'stopped_out':
            current_streak = 0
    
    mfe_values = [t.get('max_price', 0) - t.get('entry_price', 0) for t in trades if t.get('max_price') and t.get('entry_price')]
    mae_values = [t.get('entry_price', 0) - t.get('min_price', 0) for t in trades if t.get('min_price') and t.get('entry_price')]
    avg_mfe = sum(mfe_values) / len(mfe_values) if mfe_values else 0
    avg_mae = sum(mae_values) / len(mae_values) if mae_values else 0
    
    return {
        'total': total, 'hit_target': hit_target, 'stopped_out': stopped_out, 'still_open': still_open,
        'success_rate': round(success_rate, 1), 'avg_rr': round(avg_rr, 2),
        'total_return': round(total_return, 1), 'avg_return': round(avg_return, 1),
        'top10_count': len(top10_trades), 'gold_count': len(gold_trades),
        'top10_success': round(top10_success, 1), 'gold_success': round(gold_success, 1),
        'top10_return': round(top10_return, 1), 'gold_return': round(gold_return, 1),
        'avg_holding_days': round(avg_holding_days, 1), 'entry_accuracy': round(entry_accuracy, 1),
        'current_win_streak': current_streak, 'max_win_streak': max_streak,
        'avg_mfe': round(avg_mfe, 2), 'avg_mae': round(avg_mae, 2)
    }


# ================== 📈 EGX30 MARKET ANALYSIS (Dynamic Weighting) ==================
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
                    volume = d[5] if d[5] else 0
                    avg_volume = d[6] if d[6] else 1
                    volume_ratio = volume / avg_volume if avg_volume > 0 else 1
                    
                    score = 0
                    if price and sma200 and price > sma200: score += 1
                    if price and sma50 and price > sma50: score += 1
                    if rsi and 40 < rsi < 70: score += 1
                    if change and change > -0.5: score += 1
                    if volume_ratio and volume_ratio > 1.2: score += 1
                    
                    if score >= 4:
                        status = "🟢 سوق صاعد قوي - مناسب للتداول"
                        color = "#00FF00"
                        market_multiplier = 1.2
                        trend_weight = 2
                        volume_weight = 1
                    elif score >= 3:
                        status = "🟢 سوق صاعد - مناسب للتداول"
                        color = "#00FF00"
                        market_multiplier = 1.0
                        trend_weight = 2
                        volume_weight = 1
                    elif score >= 2:
                        status = "🟡 سوق متذبذب - تداول بحذر"
                        color = "#FFA500"
                        market_multiplier = 0.7
                        trend_weight = 1.5
                        volume_weight = 1.5
                    else:
                        status = "🔴 سوق هابط - ركز على صائد التصحيحات فقط"
                        color = "#FF4444"
                        market_multiplier = 0.5
                        trend_weight = 1
                        volume_weight = 2
                    
                    return {
                        "status": status,
                        "color": color,
                        "market_multiplier": market_multiplier,
                        "trend_weight": trend_weight,
                        "volume_weight": volume_weight,
                        "rsi": rsi if rsi else 50,
                        "change": change if change else 0,
                        "price": price if price else 10000,
                        "volume_ratio": volume_ratio
                    }
        except:
            time.sleep(1)
            continue
    
    return {
        "status": "🟡 سوق متذبذب (افتراضي)",
        "color": "#FFA500",
        "market_multiplier": 0.7,
        "trend_weight": 1.5,
        "volume_weight": 1.5,
        "rsi": 50,
        "change": 0,
        "price": 10000,
        "volume_ratio": 1
    }


# ================== 🔥 SMART SCORE PRO (مع Dynamic Weighting) ==================
def smart_score_pro(res, market_weights=None):
    if market_weights is None:
        market_weights = {'trend_weight': 1.5, 'volume_weight': 1.5}
    
    score = 0
    
    # اتجاهات (وزن متغير حسب السوق)
    trend_weight = market_weights.get('trend_weight', 1.5)
    if res.get('t_short') == "صاعد": score += 15 * (trend_weight / 1.5)
    if res.get('t_med') == "صاعد": score += 15 * (trend_weight / 1.5)
    if res.get('t_long') == "صاعد": score += 5 * (trend_weight / 1.5)
    
    # سيولة (وزن متغير حسب السوق)
    volume_weight = market_weights.get('volume_weight', 1.5)
    ratio = res.get('ratio', 0)
    if ratio > 2.5: score += 20 * (volume_weight / 1.5)
    elif ratio > 1.8: score += 15 * (volume_weight / 1.5)
    elif ratio > 1.2: score += 8 * (volume_weight / 1.5)
    elif ratio > 0.9: score += 4 * (volume_weight / 1.5)
    
    # RSI - نطاق أوسع
    rsi = res.get('rsi', 50)
    if 45 < rsi < 60:
        score += 15
    elif 40 < rsi <= 45 or 60 <= rsi < 68:
        score += 12
    elif 35 <= rsi <= 40 or 68 <= rsi < 75:
        score += 8
    elif 28 <= rsi < 35:
        score += 5
    
    # RR Ratio
    rr = res.get('rr', 0)
    if rr >= 2.5: score += 15
    elif rr >= 2: score += 12
    elif rr >= 1.5: score += 8
    elif rr >= 1.2: score += 4
    
    # التغير - نطاق أوسع
    chg = res.get('chg', 0)
    if chg > 1.5: score += 15
    elif chg > 0.5: score += 12
    elif chg > -1: score += 8
    elif chg > -2.5: score += 5
    elif chg > -5: score += 2
    
    # المسافة من SMA50 (مقياس التصحيح الحقيقي)
    dist_sma50 = res.get('dist_sma50', 0)
    if -8 <= dist_sma50 <= -2:
        score += 12
    elif -12 <= dist_sma50 < -8:
        score += 8
    elif -2 < dist_sma50 <= 1:
        score += 4
    
    # الزخم - هل بدأ يستعيد EMA20؟
    if res.get('above_sma20', False):
        score += 8
    
    return min(100, int(score))


# ================== 🎯 ULTRA CONFIDENCE SCORE (7 طبقات) ==================
def calculate_technical_score(stock):
    """التحليل الفني المتقدم"""
    score = 0
    
    # 1. الاتجاهات المتعددة (30 نقطة)
    trend_score = 0
    if stock.get('t_long') == "صاعد":
        trend_score += 15
    if stock.get('t_med') == "صاعد":
        trend_score += 10
    if stock.get('t_short') == "صاعد":
        trend_score += 5
    score += trend_score
    
    # 2. RSI الأمثل (15 نقطة)
    rsi = stock.get('rsi', 50)
    if 45 <= rsi <= 55:
        score += 15
    elif 40 <= rsi <= 60:
        score += 10
    elif 35 <= rsi <= 65:
        score += 5
    
    # 3. RR Ratio (15 نقطة)
    rr = stock.get('rr', 0)
    if rr >= 3:
        score += 15
    elif rr >= 2.5:
        score += 12
    elif rr >= 2:
        score += 9
    elif rr >= 1.5:
        score += 5
    
    # 4. المسافة من SMA50 (10 نقاط)
    dist = stock.get('dist_sma50', 0)
    if -5 <= dist <= -2:
        score += 10
    elif -8 <= dist <= -1:
        score += 7
    
    # 5. الزخم (10 نقاط)
    chg = stock.get('chg', 0)
    if 0.5 <= chg <= 2:
        score += 10
    elif 0.2 <= chg < 0.5:
        score += 7
    elif -0.5 < chg < 0.2:
        score += 5
    
    # 6. SMA20 (10 نقاط)
    if stock.get('above_sma20', False):
        score += 10
    
    # 7. مستويات الدعم والمقاومة (10 نقاط)
    p = stock.get('p', 0)
    s1 = stock.get('s1', p * 0.97)
    if p <= s1 * 1.02:
        score += 10
    elif p <= s1 * 1.05:
        score += 5
    
    return min(100, score)

def calculate_liquidity_score(stock):
    """تحليل السيولة"""
    ratio = stock.get('ratio', 0)
    estimated_value = stock.get('estimated_value', 0)
    
    score = 0
    
    if estimated_value >= 10000000:
        score += 35
    elif estimated_value >= 5000000:
        score += 25
    elif estimated_value >= 2000000:
        score += 15
    
    if 1.5 <= ratio <= 3:
        score += 35
    elif 1.0 <= ratio < 1.5 or 3 < ratio <= 4:
        score += 20
    elif ratio >= 0.7:
        score += 10
    
    return min(100, score)

def calculate_momentum_score(stock):
    """تحليل الزخم"""
    chg = stock.get('chg', 0)
    rsi = stock.get('rsi', 50)
    ratio = stock.get('ratio', 0)
    
    score = 0
    
    if chg > 1:
        score += 35
    elif chg > 0.5:
        score += 25
    elif chg > 0:
        score += 15
    
    if 50 <= rsi <= 65:
        score += 35
    elif 45 <= rsi < 50:
        score += 25
    
    if ratio > 2:
        score += 30
    elif ratio > 1.5:
        score += 20
    
    return min(100, score)

def calculate_trend_score(stock, market_status):
    """تحليل الاتجاه العام"""
    score = 0
    
    if stock.get('t_long') == "صاعد":
        score += 40
    if stock.get('t_med') == "صاعد":
        score += 30
    
    if "صاعد" in market_status.get('status', ''):
        score += 30
    elif "متذبذب" in market_status.get('status', ''):
        score += 15
    
    return min(100, score)

def get_ultra_confidence(stock, market_status):
    """نظام الثقة فائق الدقة - 7 طبقات"""
    
    scores = {
        "technical": calculate_technical_score(stock),
        "liquidity": calculate_liquidity_score(stock),
        "momentum": calculate_momentum_score(stock),
        "trend": calculate_trend_score(stock, market_status),
    }
    
    weights = {
        "technical": 30,
        "liquidity": 25,
        "momentum": 25,
        "trend": 20,
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
    
    if final_score >= 85 and len(weak_layers) == 0:
        advice = "🔥🔥 فرصة ذهبية مؤكدة - دخول قوي"
        color = "#00FF00"
        emoji = "🔥🔥"
        risk_level = "منخفض"
    elif final_score >= 75 and len(weak_layers) <= 1:
        advice = "🔥 فرصة ممتازة - دخول"
        color = "#ADFF2F"
        emoji = "🔥"
        risk_level = "منخفض-متوسط"
    elif final_score >= 65 and len(weak_layers) <= 2:
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


# ================== 🎯 CORRECTION HUNTER (المحسن بالكامل من الكود الجديد) ==================
def is_correction_hunter(an):
    """الكشف عن الأسهم التي تصحح ثم تستعد للانطلاق - نسخة محسنة"""
    if an is None:
        return False, [], 0
    
    p = an.get('p', 0)
    rsi = an.get('rsi', 50)
    sma200 = an.get('sma200', 0)
    sma50 = an.get('sma50', 0)
    ratio = an.get('ratio', 0)
    change_pct = an.get('chg', 0)
    t_long = an.get('t_long', 'هابط')
    t_short = an.get('t_short', 'هابط')
    rr = an.get('rr', 0)
    dist_sma50 = an.get('dist_sma50', 0)
    
    reasons = []
    score = 0
    max_score = 10
    
    # 1. الاتجاه العام صاعد (أهم شرط) - 3 نقاط
    if t_long == "صاعد" or (sma200 and p > sma200):
        score += 3
        reasons.append(f"📈 الاتجاه العام صاعد (فوق EMA200)")
    else:
        return False, ["الاتجاه العام هابط - غير مناسب"], 0
    
    # 2. السهم في منطقة تصحيح (RSI بين 28 و 55) - 3 نقاط (نطاق أوسع)
    if 28 <= rsi <= 55:
        score += 3
        if rsi < 35:
            reasons.append(f"🔻 RSI منخفض جداً ({rsi:.0f}) - تشبع بيع ممتاز")
        elif rsi < 40:
            reasons.append(f"🔻 RSI منخفض ({rsi:.0f}) - منطقة تصحيح جيدة")
        else:
            reasons.append(f"📊 RSI في منطقة محايدة ({rsi:.0f}) - بداية انتعاش محتمل")
    elif 55 < rsi <= 60:
        score += 1
        reasons.append(f"⚠️ RSI بدأ يصعد ({rsi:.0f}) - قد يكون متأخراً قليلاً")
    else:
        return False, [f"RSI مرتفع ({rsi:.0f}) - فاتك التصحيح"], 0
    
    # 3. بداية ارتداد (تغير إيجابي أو استقرار) - 2 نقاط
    if change_pct > 0:
        score += 2
        reasons.append(f"📈 تغير إيجابي ({change_pct:+.2f}%) - بداية ارتداد")
    elif change_pct > -1:
        score += 1
        reasons.append(f"⚖️ تغير طفيف ({change_pct:+.2f}%) - استقرار")
    
    # 4. سيولة جيدة - 1 نقطة
    if ratio > 1.2:
        score += 1
        reasons.append(f"💧 سيولة ممتازة ({ratio:.1f}x)")
    elif ratio > 0.7:
        reasons.append(f"💧 سيولة جيدة ({ratio:.1f}x)")
    
    # 5. السعر قرب من المتوسط 50 (دعم إضافي) - 1 نقطة
    if sma50 and abs(dist_sma50) < 3:
        score += 1
        reasons.append(f"📍 قرب من EMA50 (دعم إضافي)")
    
    # 6. نسبة مخاطرة/عائد جيدة - 1 نقطة
    if rr >= 1.5:
        score += 1
        reasons.append(f"⚖️ RR جيد ({rr})")
    
    # حساب نسبة القوة
    strength_percent = int((score / max_score) * 100)
    
    if score >= 6:
        reasons.append(f"✅ فرصة قوية - درجة {score}/{max_score}")
        return True, reasons, strength_percent
    elif score >= 4:
        reasons.append(f"⚠️ فرصة متوسطة - درجة {score}/{max_score} - يحتاج متابعة")
        return True, reasons, strength_percent
    else:
        return False, [f"درجة منخفضة ({score}/{max_score})"], strength_percent


# ================== 🔻 SUPPORT & BOUNCE DETECTION (من الكود الجديد) ==================
def is_near_support_with_bounce(an, mode="near"):
    if an is None:
        return False, [], "عادي", 0
    
    s1 = an.get('s1', 0) if an.get('s1') is not None else 0
    s2 = an.get('s2', 0) if an.get('s2') is not None else 0
    p = an.get('p', 0) if an.get('p') is not None else 0
    change_pct = an.get('chg', 0) if an.get('chg') is not None else 0
    rsi = an.get('rsi', 50) if an.get('rsi') is not None else 50
    ratio = an.get('ratio', 0) if an.get('ratio') is not None else 0
    sma20 = an.get('sma20', p) if an.get('sma20') is not None else p
    
    if s1 == 0 and s2 == 0:
        return False, [], "عادي", 0
    
    nearest_support = s1 if s1 > 0 else s2
    distance_to_support = (p - nearest_support) / nearest_support * 100 if nearest_support > 0 else 999
    
    reasons = []
    level = "عادي"
    bounce_score = 0
    
    if 0 <= distance_to_support < 0.5:
        level = "عند الدعم"
        reasons.append(f"📍 عند الدعم ({distance_to_support:.2f}% فوقه)")
    elif 0.5 <= distance_to_support < 1.0:
        level = "قريب جداً"
        reasons.append(f"📍 قريب جداً من الدعم ({distance_to_support:.2f}% فوقه)")
    elif 1.0 <= distance_to_support < 1.5:
        level = "قريب نسبياً"
        reasons.append(f"📍 قريب نسبياً من الدعم ({distance_to_support:.2f}% فوقه)")
    else:
        if mode == "near":
            return False, [], "عادي", 0
    
    if p < nearest_support:
        reasons.append("❌ كسر الدعم - خطر")
        return False, ["كسر الدعم"], "مكسور", 0
    
    if mode == "bounce":
        if 0.1 < change_pct < 4:
            bounce_score += 1
            reasons.append(f"📈 تغير إيجابي معتدل ({change_pct:+.2f}%)")
        elif change_pct >= 4:
            reasons.append(f"⚠️ تغير كبير ({change_pct:+.1f}%) - احترس من القمة")
            return False, ["تغير كبير - قد يكون قمة"], level, bounce_score
        elif change_pct <= 0:
            return False, ["تغير سلبي - لم يرتد"], level, bounce_score
        
        if rsi > 40:
            bounce_score += 1
            reasons.append(f"📊 RSI بدأ بالتعافي ({rsi:.0f})")
        
        if ratio > 1.5:
            bounce_score += 1
            reasons.append(f"💧 سيولة ممتازة ({ratio:.1f}x)")
        elif ratio > 1.2:
            bounce_score += 1
            reasons.append(f"💧 سيولة جيدة ({ratio:.1f}x)")
        
        if p > sma20:
            bounce_score += 1
            reasons.append(f"📈 السعر فوق SMA20 - بداية تكون قاع")
        
        if bounce_score < 3:
            return False, [f"نقاط الارتداد منخفضة ({bounce_score}/5)"], level, bounce_score
    
    return True, reasons, level, bounce_score


# ================== ⚡ RAPID BREAKOUT (من الكود القديم - محسن) ==================
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
    max_score = 8
    
    # RSI - نطاق أوسع
    if 52 <= rsi <= 75:
        score += 2
        reasons.append(f"⚡ زخم قوي (RSI: {rsi:.0f})")
    elif 45 <= rsi < 52:
        score += 1
        reasons.append(f"📈 زخم إيجابي (RSI: {rsi:.0f})")
    else:
        return {"is_breakout": False, "reasons": reasons, "strength": 0, "label": "", "color": "#555", "target_1": 0, "target_2": 0, "stop_loss_rapid": 0}
    
    # السيولة - نسب أكثر مرونة
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
        return {"is_breakout": False, "reasons": reasons, "strength": 0, "label": "", "color": "#555", "target_1": 0, "target_2": 0, "stop_loss_rapid": 0}
    
    # قرب من المقاومة
    if p >= r1 * 0.98:
        score += 2
        reasons.append(f"🎯 على وشك اختراق R1 ({r1:.2f})")
    elif p >= r1 * 0.95:
        score += 1
        reasons.append(f"📍 قريب من المقاومة R1")
    else:
        return {"is_breakout": False, "reasons": reasons, "strength": 0, "label": "", "color": "#555", "target_1": 0, "target_2": 0, "stop_loss_rapid": 0}
    
    # الاتجاهات
    if t_short == "صاعد" and t_med == "صاعد":
        score += 1.5
        reasons.append("📊 الاتجاهات صاعدة")
    
    # التغير
    if change > 1.2:
        score += 0.5
        reasons.append(f"🟢 شمعة قوية (+{change:.2f}%)")
    elif change > 0.3:
        score += 0.5
        reasons.append(f"🟢 شمعة إيجابية (+{change:.2f}%)")
    
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
        return {"is_breakout": False, "reasons": reasons, "strength": 0, "label": "", "color": "#555", "target_1": 0, "target_2": 0, "stop_loss_rapid": 0}
    
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


# ================== 📂 SECTOR FILTER (متقدم) ==================
SECTOR_MAPPING = {
    "🏦 البنوك": ["CIEB", "COMI", "AAIB", "QNBA", "BID", "CAE", "NBK", "IB", "ALEXBANK"],
    "🏗️ العقارات": ["TMGH", "OCDI", "PHDC", "HELI", "MNHD", "DSC", "TALAAT", "MUSTAFA"],
    "🍔 الأغذية": ["BFR", "EFID", "JUFO", "ORWE", "EDFO", "BIF", "ISFP"],
    "📡 الاتصالات": ["ETEL", "OTMT", "TE", "EGS", "NILE"],
    "🏭 الصناعة": ["EFIC", "SKPC", "EGCH", "ABUK", "MICH", "ASCM", "IRON"],
    "🛒 التجارة": ["RAYA", "SWDY", "ELSE", "MENA", "CAPI"],
    "🔧 خدمات": ["EKH", "DOMT", "UPAC", "OIH", "NOIH", "EZZ"],
}

def get_stock_sector(name):
    """تصنيف السهم حسب القطاع"""
    name_upper = name.upper()
    
    small_caps = ["BIF", "EDFO", "ISFP", "NILE", "EGS", "CAPI", "MENA", "DOMT", "UPAC"]
    
    for sector, symbols in SECTOR_MAPPING.items():
        for sym in symbols:
            if sym in name_upper or name_upper.startswith(sym):
                return sector
    
    if name_upper in small_caps or any(sc in name_upper for sc in small_caps):
        return "🔬 أسهم صغيرة (خبراء)"
    
    return "📌 أخرى"

def filter_by_sector(results, sector):
    """تصفية النتائج حسب القطاع"""
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
            elif sector == "🔬 أسهم صغيرة (خبراء)" and stock_sector == "🔬 أسهم صغيرة (خبراء)":
                filtered.append(an)
            elif sector == "📌 أخرى" and stock_sector == "📌 أخرى":
                filtered.append(an)
    return filtered

def render_sector_filter():
    """عرض فلتر القطاع في الشريط الجانبي"""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📂 فلتر القطاع")
    
    sectors = ["🌍 الكل", "🏆 EGX30 (قيادي)", "🏦 البنوك", "🏗️ العقارات", "🍔 الأغذية", "📡 الاتصالات", "🏭 الصناعة", "🛒 التجارة", "🔧 خدمات", "🔬 أسهم صغيرة (خبراء)", "📌 أخرى"]
    
    selected = st.sidebar.selectbox("القطاع", sectors, index=sectors.index(st.session_state.sector_filter) if st.session_state.sector_filter in sectors else 0)
    
    if selected != st.session_state.sector_filter:
        st.session_state.sector_filter = selected
        st.rerun()


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
        st.error(f"⚠️ فشل الاتصال بـ TradingView: {e}")
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
    except Exception as e:
        print(f"API Error: {e}")
        return []

def analyze_stock(d_row, market_weights=None):
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
        
        if avg_v and avg_v > 0:
            ratio = v / avg_v
        else:
            ratio = 0
        
        estimated_value = p * v
        
        # حساب المسافة من SMA50
        dist_sma50 = ((p - sma50) / sma50) * 100 if sma50 and sma50 > 0 else 0
        
        # هل السعر أعلى من SMA20؟
        above_sma20 = p > sma20 if sma20 else False
        
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
            'ratio': ratio, 'rsi': rsi_val, 'rr': rr, 'chg': chg or 0,
            'dist_sma50': dist_sma50, 'above_sma20': above_sma20
        }
        smart_score = smart_score_pro(temp_res, market_weights)
        
        # حساب قوة التنفيذ
        execution_strength = 0
        entry_proximity = abs(p - entry_price) / entry_price
        if entry_proximity < 0.005:
            execution_strength += 25
        elif entry_proximity < 0.01:
            execution_strength += 15
        
        if ratio > 2 and p > sma20 and p > sma50:
            execution_strength += 25
        elif ratio > 1.5 and p > sma20:
            execution_strength += 15
        
        if (target - stop_loss) / entry_price > 0.1:
            execution_strength += 20
        elif (target - stop_loss) / entry_price > 0.05:
            execution_strength += 10
        
        if t_short == "صاعد" and t_med == "صاعد":
            execution_strength += 15
        elif t_short == "صاعد":
            execution_strength += 8
        
        execution_strength = min(100, execution_strength)
        
        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg or 0, "ratio": ratio,
            "t_short": t_short, "t_med": t_med, "t_long": t_long,
            "dist_sma50": dist_sma50, "above_sma20": above_sma20,
            "s1": s1, "s2": s2, "r1": r1, "r2": r2, "pp": pp,
            "sma20": sma20, "sma50": sma50, "sma200": sma200,
            "volume": v, "avg_volume": avg_v, "estimated_value": estimated_value,
            "entry_range": f"{entry_min:.2f} - {entry_max:.2f}", "entry_price": entry_price,
            "stop_loss": stop_loss, "target": target,
            "rr": rr, "risk_pct": risk_pct, "target_pct": target_pct,
            "smart_score": smart_score, "execution_strength": execution_strength
        }
    except Exception as e:
        print(f"Analysis Error: {e}")
        return None

def preprocess_all_data(raw_data, market_weights=None):
    results = []
    for r in raw_data:
        an = analyze_stock(r, market_weights)
        if an:
            results.append(an)
    return results

def get_top_ranked(results, limit=10):
    if not results:
        return []
    
    valid_results = [r for r in results if r is not None]
    
    sorted_results = sorted(
        valid_results,
        key=lambda x: (
            x.get('smart_score', 0) * 0.5 +
            x.get('execution_strength', 0) * 0.3 +
            x.get('rr', 0) * 10
        ),
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
            market_status = get_egx30_status()
            market_weights = {
                'trend_weight': market_status.get('trend_weight', 1.5),
                'volume_weight': market_status.get('volume_weight', 1.5)
            }
            st.session_state.market_data = raw_data
            st.session_state.all_results = preprocess_all_data(raw_data, market_weights)
            st.session_state.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return True
        return False


# ================== 📈 TRADINGVIEW CHART ==================
def render_tradingview_chart(symbol, height=450, theme='dark', interval='D'):
    full_symbol = f"EGX:{symbol}" if not symbol.startswith("EGX:") else symbol
    
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
            "interval": "{interval}",
            "timezone": "Africa/Cairo",
            "theme": "{theme}",
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
    message = f"""📊 *EGX Sniper Ultimate - تحليل سهم {res['name']}*

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
تم التحليل بواسطة EGX Sniper Ultimate"""
    
    encoded_msg = urllib.parse.quote(message)
    return f"https://wa.me/?text={encoded_msg}"


# ================== 📥 EXPORT TO EXCEL ==================
def export_to_excel(data, filename="egx_sniper_results.xlsx"):
    if not data:
        return None
    
    df_data = []
    for item in data:
        if isinstance(item, dict) and 'stock' in item:
            an = item['stock']
        else:
            an = item
        
        if an:
            df_data.append({
                "السهم": an.get('name', 'N/A'),
                "الوصف": an.get('desc', 'N/A'),
                "السعر": an.get('p', 0),
                "التغير %": an.get('chg', 0),
                "RSI": an.get('rsi', 0),
                "السيولة": an.get('ratio', 0),
                "Smart Score": an.get('smart_score', 0),
                "RR": an.get('rr', 0),
                "الهدف": an.get('target', 0),
                "وقف الخسارة": an.get('stop_loss', 0),
                "الاتجاه قصير": an.get('t_short', 'N/A'),
                "الاتجاه متوسط": an.get('t_med', 'N/A'),
                "الاتجاه طويل": an.get('t_long', 'N/A'),
                "القطاع": get_stock_sector(an.get('name', ''))
            })
    
    df = pd.DataFrame(df_data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='الفرص', index=False)
    
    return output.getvalue()


# ================== 🎨 STYLES ==================
st.markdown("""
<style>
.stButton>button { width: 100%; border-radius: 12px; height: 3em; font-weight: bold; margin-bottom: 10px; }
.stock-header { font-size: 24px; font-weight: bold; color: #58a6ff; border-bottom: 2px solid #30363d; padding-bottom: 10px; }
.score-tag { float: right; background: #238636; color: white; padding: 2px 15px; border-radius: 10px; font-size: 14px; }
.entry-card { background: #0d1117; border: 1px solid #3fb950; border-radius: 12px; padding: 15px; margin: 10px 0; }
.rapid-card { background: linear-gradient(135deg, #1a0a0a, #0d0a0a); border-radius: 12px; padding: 15px; margin-bottom: 15px; border-right: 4px solid #FF6666; }
.correction-card { background: linear-gradient(135deg, #0d1f0d, #0a150a); border-radius: 12px; padding: 15px; margin-bottom: 15px; border-right: 4px solid #2E7D32; }
.support-card { background: linear-gradient(135deg, #1a1a2e, #16213e); border-radius: 12px; padding: 15px; margin-bottom: 15px; border-right: 4px solid #ff8f00; }
.quality-badge { padding: 5px 10px; border-radius: 10px; text-align: center; font-weight: bold; }
.quality-excellent { background: linear-gradient(135deg, #1f4f2b, #2e7d32); color: white; }
.quality-good { background: linear-gradient(135deg, #1f3a4f, #1565c0); color: white; }
.whatsapp-btn { background-color: #25D366; color: white; border-radius: 12px; padding: 10px; text-align: center; text-decoration: none; display: block; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


# ================== UI RENDERER ==================
def render_stock_ui(res, is_top10=False, is_gold=False):
    if res is None:
        st.warning("بيانات السهم غير متوفرة")
        return
    
    market_status = get_egx30_status()
    ultra_conf = get_ultra_confidence(res, market_status)
    
    st.markdown(f"""
    <div class='stock-header'>
        {res.get('name', 'N/A')} - {res.get('desc', 'N/A')}
        <span class='score-tag'>Smart: {res.get('smart_score', 0)}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # نظام الثقة فائق الدقة
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, #1a1a2e, #16213e); border-radius: 12px; padding: 12px; margin: 10px 0; border-right: 4px solid {ultra_conf["color"]};'>
        <div style='display: flex; justify-content: space-between; align-items: center;'>
            <div>
                <span style='font-size: 18px; font-weight: bold;'>{ultra_conf["emoji"]} نظام الثقة فائق الدقة</span>
                <div style='font-size: 12px; color: #888;'>4 طبقات تحليل متقدمة</div>
            </div>
            <div style='text-align: center;'>
                <span style='font-size: 32px; font-weight: bold; color: {ultra_conf["color"]};'>{ultra_conf["score"]}%</span>
                <div style='font-size: 12px;'>مستوى خطر: {ultra_conf["risk_level"]}</div>
            </div>
        </div>
        <div style='margin-top: 8px;'><span style='color: {ultra_conf["color"]};'>{ultra_conf["advice"]}</span></div>
    </div>
    """, unsafe_allow_html=True)
    
    # عرض تفاصيل الطبقات
    with st.expander("📊 تفاصيل طبقات التحليل"):
        cols = st.columns(4)
        layers = list(ultra_conf['layers'].items())
        for i, (layer, score) in enumerate(layers):
            col = cols[i % 4]
            color = "#00FF00" if score >= 70 else "#FFD700" if score >= 55 else "#FF4444"
            col.markdown(f"""
            <div style='text-align: center; padding: 5px;'>
                <div style='font-size: 11px; color: #888;'>{layer}</div>
                <div style='font-size: 18px; font-weight: bold; color: {color};'>{score}%</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("### 📊 خلاصة")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("السعر", f"{res.get('p', 0):.2f}", f"{res.get('chg', 0):+.2f}%")
    with col2:
        st.metric("Smart Score", f"{res.get('smart_score', 0)}/100")
    with col3:
        st.metric("RR Ratio", f"{res.get('rr', 0)}")
    with col4:
        st.metric("RSI", f"{res.get('rsi', 0):.0f}")
    
    ratio = res.get('ratio', 0)
    if ratio > 2.5:
        vol_text = f"🚀 ممتازة جداً ({ratio:.1f}x)"
    elif ratio > 1.8:
        vol_text = f"⚡ قوية ({ratio:.1f}x)"
    elif ratio > 1.2:
        vol_text = f"🙂 جيدة ({ratio:.1f}x)"
    else:
        vol_text = f"❄️ ضعيفة ({ratio:.1f}x)"
    st.metric("السيولة", vol_text)
    
    st.markdown("---")
    
    whatsapp_url = share_on_whatsapp(res)
    st.markdown(f"""
    <a href="{whatsapp_url}" target="_blank" class="whatsapp-btn" style="margin-bottom: 15px;">
        📱 مشاركة التحليل عبر واتساب
    </a>
    """, unsafe_allow_html=True)
    
    with st.expander("📊 التحليل الفني", expanded=True):
        st.markdown("### 📈 شارت السهم")
        render_tradingview_chart(res.get('name', 'EGX30'), height=450)
        
        t_short_c = "🟢" if res.get('t_short') == "صاعد" else "🔴"
        t_med_c = "🟢" if res.get('t_med') == "صاعد" else "🔴"
        t_long_c = "🟢" if res.get('t_long') == "صاعد" else "🔴"
        
        st.markdown(f"""
        <div style='background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:10px;margin:10px 0;'>
            <b>📌 الاتجاهات:</b><br>
            {t_short_c} قصير المدى (EMA20): {res.get('t_short', 'هابط')}<br>
            {t_med_c} متوسط المدى (EMA50): {res.get('t_med', 'هابط')}<br>
            {t_long_c} طويل المدى (EMA200): {res.get('t_long', 'هابط')}<br>
            📏 المسافة من SMA50: {res.get('dist_sma50', 0):+.1f}%
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class='entry-card'>
            🎯 <b>نطاق الدخول:</b> {res.get('entry_range', 'N/A')}<br>
            🛑 <b>وقف الخسارة:</b> {res.get('stop_loss', 0):.2f} <span style='color:#f85149'>(-{res.get('risk_pct', 0):.1f}%)</span><br>
            🏁 <b>المستهدف:</b> {res.get('target', 0):.2f} <span style='color:#58a6ff'>(+{res.get('target_pct', 0):.1f}%)</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🏛️ مستويات الدعم والمقاومة")
        st.markdown(f"""
        | المستوى | السعر | الدلالة |
        |---------|-------|---------|
        | 🔴 **مقاومة ثانية R2** | {res.get('r2', 0):.2f} | مقاومة قوية |
        | 🔴 **مقاومة أولى R1** | {res.get('r1', 0):.2f} | مقاومة أولى |
        | 🟡 **نقطة الارتكاز PP** | {res.get('pp', 0):.2f} | المحور |
        | 🟢 **دعم أول S1** | {res.get('s1', 0):.2f} | دعم أول |
        | 🟢 **دعم ثاني S2** | {res.get('s2', 0):.2f} | دعم قوي |
        """)
    
    with st.expander("💰 إدارة المخاطر وخطة الدخول", expanded=False):
        deal_size = st.number_input("💰 ميزانية الصفقة (ج)", value=10000, step=1000, key=f"deal_{res.get('name', 'stock')}")
        entry_price = res.get('entry_price', 0)
        
        if deal_size > 0 and entry_price > 0:
            shares_deal = int(deal_size / entry_price)
            profit_val = (res.get('target', 0) - entry_price) * shares_deal
            loss_val = (entry_price - res.get('stop_loss', 0)) * shares_deal
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("📦 عدد الأسهم", f"{shares_deal:,}")
                st.metric("💰 قيمة الصفقة", f"{deal_size:,.0f} ج")
            with col2:
                st.metric("🟢 الربح المتوقع", f"{profit_val:,.0f} ج", delta=f"+{res.get('target_pct', 0):.1f}%")
                st.metric("🔴 الخسارة المحتملة", f"{loss_val:,.0f} ج", delta=f"-{res.get('risk_pct', 0):.1f}%")
            
            st.markdown("### 🏹 خطة الدخول المتكاملة (3 مستويات)")
            
            range_size = entry_price - res.get('stop_loss', 0)
            entry_level_1 = entry_price
            entry_level_2 = max(entry_price - (range_size * 0.5), res.get('stop_loss', 0) * 1.02)
            entry_level_3 = entry_price + (res.get('target', 0) - entry_price) * 0.3
            
            if res.get('rr', 0) >= 2.5:
                weights = [0.6, 0.25, 0.15]
            elif res.get('rr', 0) >= 1.8:
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


# ================== SESSION STATE & NAVIGATION ==================
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

def render_mode_selector():
    with st.sidebar.expander("🧠 نمط التداول", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🛡️ محافظ", use_container_width=True): 
                st.session_state.mode = "🛡️ محافظ"
        with col2:
            if st.button("⚖️ متوازن", use_container_width=True): 
                st.session_state.mode = "⚖️ متوازن"
        with col3:
            if st.button("🚀 هجومي", use_container_width=True): 
                st.session_state.mode = "🚀 هجومي"
    
    mode = st.session_state.mode
    color = "#238636" if "محافظ" in mode else "#f85149" if "هجومي" in mode else "#d29922"
    icon = "🛡️" if "محافظ" in mode else "🚀" if "هجومي" in mode else "⚖️"
    st.sidebar.markdown(f"""
    <div style="background:{color}; padding:8px; border-radius:10px; text-align:center; font-weight:bold; margin:10px 0; color:white;">
        🎯 {icon} {mode}
    </div>
    """, unsafe_allow_html=True)


# ================== MAIN APP ==================
def main():
    if st.session_state.all_results is None:
        get_fresh_data()
    
    market_status = get_egx30_status()
    
    # الشريط الجانبي
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/000000/stock.png", width=50)
        st.title("🎯 EGX Sniper")
        st.caption(f"آخر تحديث: {st.session_state.last_update or 'لم يتم بعد'}")
        
        st.markdown(f"""
        <div style="background: #0d1117; border-radius: 10px; padding: 10px; margin-bottom: 10px; text-align: center;">
            <span style="color: {market_status['color']}; font-weight: bold;">📊 المؤشر العام</span><br>
            <span>{market_status['status']}</span>
        </div>
        """, unsafe_allow_html=True)
        
        render_mode_selector()
        render_sector_filter()
        
        st.markdown("---")
        st.markdown("### 🎯 القائمة الرئيسية")
        
        if st.button("🏠 الرئيسية", use_container_width=True):
            st.session_state.page = 'home'
            st.rerun()
        
        st.markdown("### 🔍 أدوات التحليل")
        
        if st.button("🏆 أفضل 10 فرص", use_container_width=True):
            st.session_state.page = 'top10'
            st.rerun()
        
        if st.button("🎯 صائد التصحيحات", use_container_width=True):
            st.session_state.page = 'correction'
            st.rerun()
        
        if st.button("⚡ قناص الاختراق", use_container_width=True):
            st.session_state.page = 'rapid'
            st.rerun()
        
        if st.button("🔻 دعم وارتداد", use_container_width=True):
            st.session_state.page = 'support'
            st.rerun()
        
        if st.button("🔍 تحليل سهم", use_container_width=True):
            st.session_state.page = 'analyze'
            st.rerun()
        
        st.markdown("---")
        st.markdown("### ⚙️ الإدارة")
        
        if st.button("📊 تقييم الأداء", use_container_width=True):
            st.session_state.page = 'performance'
            st.rerun()
        
        if st.button("🔄 تحديث البيانات", use_container_width=True):
            get_fresh_data()
            st.success("✅ تم تحديث البيانات!")
            st.rerun()
        
        if st.button("🗑️ مسح بيانات التقييم", use_container_width=True):
            if os.path.exists(TRADES_FILE):
                os.remove(TRADES_FILE)
            if os.path.exists(OUTCOMES_FILE):
                os.remove(OUTCOMES_FILE)
            st.success("✅ تم المسح!")
            st.rerun()
    
    # ================== الصفحات ==================
    if st.session_state.page == 'home':
        st.title("🎯 EGX Sniper Ultimate v2.0")
        st.markdown("""
        <div style="background: #0d1117; border-radius: 10px; padding: 15px; margin-bottom: 20px;">
            <b>🚀 نظام تحليل أسهم البورصة المصرية فائق الدقة</b><br>
            • <b>4 طبقات تحليل</b> (فني، سيولة، زخم، اتجاه)<br>
            • <b>صائد التصحيحات</b> - اكتشف الأسهم القوية التي تصحح قبل الانطلاق<br>
            • <b>قناص الاختراق</b> - فرص الاختراق خلال جلسة أو جلستين<br>
            • <b>الدعم والارتداد</b> - نظام Bounce Score بـ 5 عوامل<br>
            • <b>فلتر القطاع</b> - ركز على القطاع الذي تفضله
        </div>
        """, unsafe_allow_html=True)
        
        filtered_results = filter_by_sector(st.session_state.all_results, st.session_state.sector_filter)
        
        if filtered_results:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📊 إجمالي الأسهم", len(filtered_results))
            with col2:
                # حساب فرص التصحيح
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
        
        st.markdown("---")
        st.markdown("### 📈 أحدث فرص السوق")
        
        # عرض فرق التصحيح والاختراق في الصفحة الرئيسية
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
                    
                    st.markdown(f"""
                    <div class='correction-card'>
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
                st.info("لا توجد فرص تصحيح حالياً.")
        
        with tab2:
            rapid_opportunities = get_rapid_breakouts(filtered_results)
            if rapid_opportunities:
                for item in rapid_opportunities[:5]:
                    an = item['stock']
                    analysis = item['analysis']
                    
                    st.markdown(f"""
                    <div class='rapid-card' style='border-right-color: {analysis["color"]};'>
                        <div style='display: flex; justify-content: space-between; align-items: center;'>
                            <h3 style='margin: 0; color: #FF9999;'>⚡ {an['name']} - {an['desc']}</h3>
                            <span style='background: {analysis["color"]}; padding: 5px 15px; border-radius: 20px; color: #1a1a1a; font-weight: bold;'>
                                {analysis['label']} | {analysis['strength']}%
                            </span>
                        </div>
                        <div style='height: 6px; background: #333; margin: 10px 0;'>
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
                st.info("لا توجد فرص اختراق حالياً.")
    
    # ================== صفحة أفضل 10 ==================
    elif st.session_state.page == 'top10':
        st.title("🏆 أفضل 10 فرص")
        
        filtered_results = filter_by_sector(st.session_state.all_results, st.session_state.sector_filter)
        top_results = get_top_ranked(filtered_results, limit=10)
        
        for i, an in enumerate(top_results, 1):
            if an:
                with st.expander(f"#{i} - {an['name']} | Smart: {an['smart_score']} | RR: {an['rr']} | RSI: {an['rsi']:.0f}"):
                    render_stock_ui(an, is_top10=True)
                    if st.button(f"💾 تسجيل الصفقة", key=f"rec_top_{an['name']}"):
                        record_trade(an, "top10")
                        st.success("✅ تم تسجيل الصفقة!")
    
    # ================== صفحة صائد التصحيحات ==================
    elif st.session_state.page == 'correction':
        st.title("🎯 صائد التصحيحات (Correction Hunter)")
        st.markdown("""
        <div style="background: rgba(46,125,50,0.15); border-right: 4px solid #2E7D32; padding: 10px; border-radius: 8px; margin-bottom: 20px;">
            🎯 <b>الأسهم القوية التي تصحح (قبل الارتداد)</b><br>
            • اتجاه عام صاعد | • RSI بين 28-55 | • تصحيح صحي | • سيولة مقبولة
        </div>
        """, unsafe_allow_html=True)
        
        filtered_results = filter_by_sector(st.session_state.all_results, st.session_state.sector_filter)
        
        corrections = []
        for an in filtered_results:
            if an:
                is_corr, reasons, strength = is_correction_hunter(an)
                if is_corr:
                    corrections.append({'stock': an, 'reasons': reasons, 'strength': strength})
        
        if corrections:
            corrections.sort(key=lambda x: x['strength'], reverse=True)
            st.markdown(f"**🎯 عدد فرص التصحيح: {len(corrections)}**")
            
            excel_data = export_to_excel(corrections)
            if excel_data:
                st.download_button(
                    label="📥 تحميل النتائج كـ Excel",
                    data=excel_data,
                    file_name=f"correction_hunter_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            
            for item in corrections:
                an = item['stock']
                reasons = item['reasons']
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
                
                st.markdown(f"""
                <div class='correction-card'>
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
                        ✅ {', '.join(reasons[:5])}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"📊 تحليل {an['name']} بالتفصيل", key=f"corr_{an['name']}"):
                    record_trade(an, "صائد تصحيحات")
                    render_stock_ui(an)
        else:
            st.info("ℹ️ لا توجد فرص تصحيح حالياً.")
    
    # ================== صفحة قناص الاختراق ==================
    elif st.session_state.page == 'rapid':
        st.title("⚡ قناص الاختراق السريع")
        st.markdown("""
        <div style="background: rgba(255,102,102,0.15); border-right: 4px solid #FF6666; padding: 10px; border-radius: 8px; margin-bottom: 20px;">
            🚀 <b>فرص خلال جلسة أو جلستين</b><br>
            • RSI بين 45-75 | • سيولة استثنائية > 1.5x | • قرب اختراق المقاومة | • وقف خسارة ضيق
        </div>
        """, unsafe_allow_html=True)
        
        filtered_results = filter_by_sector(st.session_state.all_results, st.session_state.sector_filter)
        rapid_opportunities = get_rapid_breakouts(filtered_results)
        
        if rapid_opportunities:
            st.markdown(f"**⚡ عدد فرص الاختراق السريع: {len(rapid_opportunities)}**")
            
            excel_data = export_to_excel(rapid_opportunities)
            if excel_data:
                st.download_button(
                    label="📥 تحميل النتائج كـ Excel",
                    data=excel_data,
                    file_name=f"rapid_breakout_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            
            for item in rapid_opportunities:
                an = item['stock']
                analysis = item['analysis']
                
                st.markdown(f"""
                <div class='rapid-card' style='border-right-color: {analysis["color"]};'>
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
                        ✅ {', '.join(analysis['reasons'])}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"📊 تحليل {an['name']} بالتفصيل", key=f"rapid_{an['name']}"):
                    record_trade(an, "اختراق سريع")
                    render_stock_ui(an)
        else:
            st.info("ℹ️ لا توجد فرص اختراق سريع حالياً.")
    
    # ================== صفحة دعم وارتداد ==================
    elif st.session_state.page == 'support':
        st.title("🔻 فرص الدعم والارتداد")
        st.markdown("""
        <div style="background: rgba(255,143,0,0.15); border-right: 4px solid #ff8f00; padding: 10px; border-radius: 8px; margin-bottom: 20px;">
            📌 <b>الأسهم القريبة من الدعم مع احتمالية ارتداد</b><br>
            • نظام Bounce Score بـ 5 عوامل | • يتطلب 3+ نقاط للدخول
        </div>
        """, unsafe_allow_html=True)
        
        filtered_results = filter_by_sector(st.session_state.all_results, st.session_state.sector_filter)
        
        bounce_stocks = []
        for an in filtered_results:
            if an:
                is_bounce, reasons, level, bounce_score = is_near_support_with_bounce(an, mode="bounce")
                if is_bounce:
                    bounce_stocks.append({'stock': an, 'reasons': reasons, 'level': level, 'bounce_score': bounce_score})
        
        if bounce_stocks:
            bounce_stocks.sort(key=lambda x: x['bounce_score'], reverse=True)
            st.markdown(f"**📈 عدد الأسهم ذات الارتداد: {len(bounce_stocks)}**")
            
            for item in bounce_stocks:
                an = item['stock']
                reasons = item['reasons']
                level = item['level']
                bounce_score = item['bounce_score']
                
                if bounce_score >= 4:
                    badge = "🔥 ارتداد قوي جداً"
                    badge_color = "#4caf50"
                elif bounce_score >= 3:
                    badge = "✅ ارتداد جيد"
                    badge_color = "#ff9800"
                else:
                    badge = "⚠️ ارتداد ضعيف"
                    badge_color = "#f44336"
                
                st.markdown(f"""
                <div class='support-card'>
                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                        <h3 style='margin: 0; color: #ff8f00;'>🔻 {an['name']} - {an['desc']}</h3>
                        <span style='background: {badge_color}; padding: 5px 15px; border-radius: 20px; color: white; font-weight: bold;'>
                            {badge} ({bounce_score}/5)
                        </span>
                    </div>
                    <div style='display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 10px 0;'>
                        <div>💰 {an['p']:.2f} ج</div>
                        <div>📊 RSI: {an['rsi']:.0f}</div>
                        <div>💧 سيولة: {an['ratio']:.1f}x</div>
                        <div>📈 تغير: {an['chg']:+.2f}%</div>
                    </div>
                    <div style='background: rgba(255,143,0,0.1); border-radius: 8px; padding: 8px;'>
                        ✅ {', '.join(reasons[:4])}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"📊 تحليل {an['name']} بالتفصيل", key=f"support_{an['name']}"):
                    record_trade(an, "دعم وارتداد")
                    render_stock_ui(an)
        else:
            st.info("ℹ️ لا توجد فرص ارتداد حالياً.")
    
    # ================== صفحة تحليل سهم ==================
    elif st.session_state.page == 'analyze':
        st.title("🔍 تحليل سهم")
        sym = st.text_input("🔎 أدخل رمز السهم", placeholder="مثال: COMI, TMGH, ETEL").upper().strip()
        
        if sym:
            with st.spinner("🔍 جاري البحث عن السهم..."):
                data = fetch_single_stock(sym)
                
                if not data:
                    st.error("❌ السهم غير موجود")
                    if st.session_state.all_results:
                        symbols = [r.get('name') for r in st.session_state.all_results[:30] if r]
                        if symbols:
                            st.info(f"💡 أمثلة: {', '.join(symbols[:15])}")
                else:
                    market_status = get_egx30_status()
                    market_weights = {
                        'trend_weight': market_status.get('trend_weight', 1.5),
                        'volume_weight': market_status.get('volume_weight', 1.5)
                    }
                    res = analyze_stock(data[0], market_weights)
                    if res:
                        render_stock_ui(res)
                        if st.button(f"💾 تسجيل الصفقة", key=f"rec_analyze_{sym}"):
                            record_trade(res, "تحليل فردي")
                            st.success("✅ تم تسجيل الصفقة!")
                    else:
                        st.warning("⚠️ تحليل السهم فشل")
    
    # ================== صفحة تقييم الأداء ==================
    elif st.session_state.page == 'performance':
        st.title("📊 تقييم الأداء")
        
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
        col2.metric("💰 إجمالي العائد %", f"{stats['total_return']}%")
        col3.metric("⚖️ متوسط RR", stats['avg_rr'])
        
        col1, col2, col3 = st.columns(3)
        col1.metric("📅 متوسط أيام الاحتفاظ", f"{stats['avg_holding_days']} يوم")
        col2.metric("🎯 دقة الدخول", f"{stats['entry_accuracy']}%")
        col3.metric("🔥 السلسلة الحالية", stats['current_win_streak'])
        
        st.markdown(f"""
        <div style='background:#161b22;border:1px solid #30363d;border-radius:10px;padding:15px;margin:15px 0;'>
            <b>💎 الفرص الذهبية:</b> {stats['gold_count']} صفقة | نسبة نجاح: {stats['gold_success']}% | إجمالي العائد: {stats['gold_return']}%
        </div>
        """, unsafe_allow_html=True)
        
        if trades:
            st.markdown("### 📋 آخر الصفقات")
            for trade in trades[-15:][::-1]:
                status = "🟢 هدف" if trade.get('status') == 'hit_target' else "🔴 وقف" if trade.get('status') == 'stopped_out' else "🟡 مفتوح"
                st.markdown(f"- {trade.get('name')} ({trade.get('trade_type')}) - {status} | دخول: {trade.get('entry_price', 0):.2f} | RR: {trade.get('rr', 0)}")


if __name__ == "__main__":
    main()
