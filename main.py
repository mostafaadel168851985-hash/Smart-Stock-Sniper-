import streamlit as st
import streamlit.components.v1 as components
import requests
from datetime import datetime, date, timedelta
import json
import os
import re
import urllib.parse
import time
import math

# ================== صفحة التطبيق ==================
st.set_page_config(
    page_title="🎯 EGX Sniper Pro Ultimate", 
    layout="wide", 
    page_icon="🎯"
)

# ================== كشف الجوال ==================
user_agent = st.context.headers.get('User-Agent', '')
is_mobile = bool(re.search(r'Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini', user_agent))

# ================== تهيئة Session State ==================
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

# ================== ملف تتبع الأداء ==================
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
        "entry_min": res.get('entry_price', 0) * 0.98,
        "entry_max": res.get('entry_price', 0) * 1.01,
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

# ================== تحليل مؤشر EGX30 ==================
@st.cache_data(ttl=600, show_spinner=False)
def get_egx30_status():
    for attempt in range(2):
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
                if data and len(data) > 0 and len(data[0].get('d', [])) >= 5:
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

# ================== تحليل حجم التداول بالجنيه ==================
def analyze_turnover(an):
    """تحليل حجم التداول بالجنيه المصري"""
    if an is None:
        return 0, "لا توجد بيانات", 0
    
    price = an.get('p', 0)
    volume = an.get('volume', 0)
    avg_volume = an.get('avg_volume', 1)
    
    # قيمة التداول اليومية بالجنيه
    daily_turnover = price * volume if volume else 0
    avg_turnover = price * avg_volume if avg_volume else 1
    
    # نسبة التداول مقارنة بالمتوسط
    ratio = daily_turnover / avg_turnover if avg_turnover > 0 else 0
    
    if daily_turnover >= 50000000:  # 50 مليون فأكثر
        rating = "🔥 سيولة ممتازة جداً"
        score = 3
    elif daily_turnover >= 20000000:  # 20-50 مليون
        rating = "✅ سيولة ممتازة"
        score = 2
    elif daily_turnover >= 5000000:  # 5-20 مليون
        rating = "👍 سيولة جيدة"
        score = 1
    elif daily_turnover >= 1000000:  # 1-5 مليون
        rating = "⚠️ سيولة متوسطة"
        score = 0
    else:
        rating = "❄️ سيولة ضعيفة"
        score = -1
    
    return daily_turnover, rating, score, ratio

# ================== تحليل نماذج الشموع اليابانية ==================
def analyze_candlestick_patterns(an):
    """تحليل نماذج الشموع اليابانية"""
    if an is None:
        return [], 0
    
    p = an.get('p', 0)
    open_price = an.get('open', p)  # إذا لم يتوفر، نفترض السعر الحالي
    high = an.get('high', p)
    low = an.get('low', p)
    prev_close = an.get('prev_close', p * 0.99)
    change_pct = an.get('chg', 0)
    
    patterns = []
    strength_score = 0
    
    # حساب حجم الشمعة
    candle_body = abs(p - open_price) if open_price else 0
    candle_range = (high - low) if high and low else 0
    
    # 1. نموذج المطرقة (Hammer) - انعكاس صاعد
    if candle_range > 0:
        lower_shadow = min(p, open_price) - low if open_price else p - low
        if lower_shadow > candle_body * 2 and change_pct > -3:
            patterns.append("🔨 مطرقة (Hammer) - انعكاس صاعد محتمل")
            strength_score += 2
    
    # 2. نموذج الشهاب (Shooting Star) - انعكاس هابط
    if candle_range > 0:
        upper_shadow = high - max(p, open_price) if open_price else high - p
        if upper_shadow > candle_body * 2 and change_pct > 1:
            patterns.append("⭐ شهاب (Shooting Star) - انعكاس هابط محتمل")
            strength_score -= 1
    
    # 3. نموذج الابتلاع الصاعد (Bullish Engulfing)
    if p > prev_close and prev_close > open_price and p > prev_close * 1.02:
        patterns.append("🟢 ابتلاع صاعد (Bullish Engulfing) - إشارة شراء قوية")
        strength_score += 3
    
    # 4. نموذج الابتلاع الهابط (Bearish Engulfing)
    if p < prev_close and open_price > prev_close and p < prev_close * 0.98:
        patterns.append("🔴 ابتلاع هابط (Bearish Engulfing) - إشارة بيع")
        strength_score -= 2
    
    # 5. نموذج الدوجي (Doji) - تردد
    if candle_range > 0 and candle_body < candle_range * 0.1:
        patterns.append("✚ دوجي (Doji) - تردد في السوق")
        # الدوجي عند الدعم يكون إيجابي، عند المقاومة سلبي
    
    # 6. شمعة ماروبوزو (Marubozu) - قوة اتجاه
    if candle_range > 0:
        upper_wick = high - max(p, open_price) if open_price else high - p
        lower_wick = min(p, open_price) - low if open_price else p - low
        if upper_wick < candle_range * 0.1 and lower_wick < candle_range * 0.1:
            if change_pct > 0:
                patterns.append("📈 ماروبوزو صاعد - قوة شرائية")
                strength_score += 2
            else:
                patterns.append("📉 ماروبوزو هابط - قوة بيعية")
                strength_score -= 1
    
    return patterns, strength_score

# ================== Smart Score المتقدم ==================
def smart_score_pro(res):
    score = 0
    
    # الاتجاهات (35 نقطة كحد أقصى)
    if res.get('t_short') == "صاعد": score += 15
    if res.get('t_med') == "صاعد": score += 15
    if res.get('t_long') == "صاعد": score += 5
    
    # السيولة (20 نقطة) - مع مراعاة التداول بالجنيه
    ratio = res.get('ratio', 0)
    if ratio > 2.5: score += 20
    elif ratio > 1.8: score += 15
    elif ratio > 1.2: score += 8
    
    # إضافة نقاط إضافية لحجم التداول بالجنيه
    turnover = res.get('daily_turnover', 0)
    if turnover >= 50000000:
        score += 5
    elif turnover >= 20000000:
        score += 3
    elif turnover >= 5000000:
        score += 1
    
    # RSI (15 نقطة)
    rsi = res.get('rsi', 50)
    if 50 < rsi < 60:
        score += 15
    elif 45 < rsi <= 50 or 60 <= rsi < 65:
        score += 10
    elif 40 <= rsi <= 45:
        score += 5
    elif 30 <= rsi < 40:
        score += 3
    
    # نسبة المخاطرة/العائد (15 نقطة)
    rr = res.get('rr', 0)
    if rr >= 2.5: score += 15
    elif rr >= 2: score += 12
    elif rr >= 1.5: score += 8
    elif rr >= 1.2: score += 4
    
    # التغير اليومي (15 نقطة)
    chg = res.get('chg', 0)
    if chg > 1.5: score += 15
    elif chg > 0.5: score += 10
    elif chg > 0: score += 5
    elif chg > -1: score += 2
    
    # نماذج الشموع
    candle_score = res.get('candle_strength', 0)
    if candle_score >= 2:
        score += 10
    elif candle_score >= 1:
        score += 5
    elif candle_score <= -1:
        score -= 5
    
    return min(100, int(score))

# ================== درجة الثقة ==================
def get_confidence(res):
    score = 0
    total = 7  # زدنا عدد العوامل
    
    p = res.get('p', 0)
    rsi = res.get('rsi', 50)
    ratio = res.get('ratio', 0)
    change = res.get('chg', 0)
    t_short = res.get('t_short', 'هابط')
    t_med = res.get('t_med', 'هابط')
    t_long = res.get('t_long', 'هابط')
    sma200 = res.get('sma200', p)
    r1 = res.get('r1', p * 1.05)
    turnover = res.get('daily_turnover', 0)
    
    if t_long == "صاعد" or (sma200 and p > sma200):
        score += 1
    
    if t_med == "صاعد" and t_short == "صاعد":
        score += 1
    
    if 45 < rsi < 65:
        score += 1
    
    if ratio > 1.8:
        score += 1
    elif ratio > 1.2:
        score += 0.5
    
    if r1 and r1 > p:
        dist = (r1 - p) / p * 100
        if dist < 2:
            score += 1
        elif dist < 3:
            score += 0.5
    
    if change > 0.3:
        score += 1
    elif change > 0:
        score += 0.5
    
    # إضافة عامل حجم التداول بالجنيه
    if turnover >= 20000000:
        score += 1
    elif turnover >= 5000000:
        score += 0.5
    
    percent = int((score / total) * 100)
    
    if percent >= 85:
        advice, color, emoji = "🔥 دخول الآن (فرصة ذهبية)", "#00FF00", "🔥"
    elif percent >= 65:
        advice, color, emoji = "✅ شراء حذر / مراقبة", "#ADFF2F", "✅"
    elif percent >= 40:
        advice, color, emoji = "🟡 انتظار (تجميع)", "#FFD700", "🟡"
    else:
        advice, color, emoji = "❌ تجنب السهم حالياً", "#FF6B6B", "❌"
    
    return {'score': percent, 'advice': advice, 'color': color, 'emoji': emoji}

# ================== صائد التصحيحات (المحسن) ==================
def is_correction_hunter(an, market_multiplier=1.0):
    if an is None:
        return False, [], 0, "", ""
    
    p = an.get('p', 0)
    rsi = an.get('rsi', 50)
    sma200 = an.get('sma200', 0)
    ratio = an.get('ratio', 0)
    change_pct = an.get('chg', 0)
    t_long = an.get('t_long', 'هابط')
    rr = an.get('rr', 0)
    turnover = an.get('daily_turnover', 0)
    candle_strength = an.get('candle_strength', 0)
    
    reasons = []
    score = 0
    max_score = 12  # زدنا العوامل
    
    # الشرط 1: الاتجاه العام صاعد (أهم شرط)
    if t_long == "صاعد" or (sma200 and p > sma200):
        score += 3
        reasons.append("📈 الاتجاه العام صاعد")
    else:
        return False, ["الاتجاه العام هابط - غير مناسب"], 0, "", ""
    
    # الشرط 2: RSI في منطقة التصحيح (28-55)
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
        reasons.append(f"⚠️ RSI بدأ يصعد ({rsi:.0f}) - قد يكون متأخراً قليلاً")
    else:
        return False, [f"RSI مرتفع ({rsi:.0f}) - فاتك التصحيح"], 0, "", ""
    
    # الشرط 3: بداية ارتداد
    if change_pct > 0:
        score += 2
        reasons.append(f"📈 تغير إيجابي ({change_pct:+.2f}%) - بداية ارتداد")
    elif change_pct > -1:
        score += 1
        reasons.append(f"⚖️ تغير طفيف ({change_pct:+.2f}%) - استقرار")
    
    # الشرط 4: سيولة جيدة (حجم التداول بالجنيه)
    if turnover >= 20000000:
        score += 2
        reasons.append(f"💰 سيولة ممتازة ({turnover/1000000:.0f}M ج)")
    elif turnover >= 5000000:
        score += 1
        reasons.append(f"💰 سيولة جيدة ({turnover/1000000:.1f}M ج)")
    elif ratio > 0.7:
        reasons.append(f"📊 سيولة مقبولة ({ratio:.1f}x)")
    
    # الشرط 5: نسبة مخاطرة/عائد جيدة
    if rr >= 1.5:
        score += 1
        reasons.append(f"⚖️ RR جيد ({rr})")
    
    # الشرط 6: نماذج شموع إيجابية
    if candle_strength >= 2:
        score += 1
        reasons.append("🕯️ نماذج شموع إيجابية")
    
    # تطبيق مضاعف السوق
    adjusted_score = score * market_multiplier
    strength = int((adjusted_score / max_score) * 100)
    strength = min(100, strength)
    
    if strength >= 70:
        label = "🔥 فرصة تصحيح ممتازة"
        color = "#2E7D32"
    elif strength >= 50:
        label = "✅ فرصة تصحيح جيدة"
        color = "#388E3C"
    elif strength >= 35:
        label = "🟡 فرصة تصحيح محتملة"
        color = "#F57C00"
    else:
        label = "❌ فرصة تصحيح ضعيفة"
        color = "#C62828"
    
    return score >= 4, reasons, strength, label, color

# ================== قناص الاختراق السريع ==================
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
    turnover = an.get('daily_turnover', 0)
    candle_strength = an.get('candle_strength', 0)
    
    reasons = []
    score = 0
    max_score = 8  # زدنا العوامل
    
    # RSI شرط (زخم)
    if 52 <= rsi <= 75:
        score += 2
        reasons.append(f"⚡ زخم قوي (RSI: {rsi:.0f})")
    elif 45 <= rsi < 52:
        score += 1
        reasons.append(f"📈 زخم إيجابي (RSI: {rsi:.0f})")
    else:
        return {"is_breakout": False, "reasons": [], "strength": 0, "label": "", "color": "#555", "target_1": 0, "target_2": 0, "stop_loss_rapid": 0}
    
    # السيولة شرط أساسي (حجم التداول بالجنيه)
    if turnover >= 30000000:
        score += 2
        reasons.append(f"💥 سيولة استثنائية ({turnover/1000000:.0f}M ج)")
    elif turnover >= 15000000:
        score += 1.5
        reasons.append(f"🚀 سيولة قوية ({turnover/1000000:.0f}M ج)")
    elif ratio > 1.5:
        score += 1
        reasons.append(f"📊 سيولة جيدة ({ratio:.1f}x)")
    else:
        return {"is_breakout": False, "reasons": [], "strength": 0, "label": "", "color": "#555", "target_1": 0, "target_2": 0, "stop_loss_rapid": 0}
    
    # القرب من المقاومة
    if p >= r1 * 0.98:
        score += 2
        reasons.append(f"🎯 على وشك اختراق R1 ({r1:.3f})")
    elif p >= r1 * 0.95:
        score += 1
        reasons.append(f"📍 قريب من المقاومة R1")
    else:
        return {"is_breakout": False, "reasons": [], "strength": 0, "label": "", "color": "#555", "target_1": 0, "target_2": 0, "stop_loss_rapid": 0}
    
    if t_short == "صاعد" and t_med == "صاعد":
        score += 1
        reasons.append("📊 الاتجاهات صاعدة")
    
    # نماذج شموع إيجابية
    if candle_strength >= 2:
        score += 1
        reasons.append("🕯️ نماذج شموع قوية")
    
    strength = int((score / max_score) * 100)
    strength = min(100, strength)
    
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

# ================== دعم وارتداد متقدم ==================
def is_support_with_bounce(an):
    if an is None:
        return False, [], 0, "عادي"
    
    s1 = an.get('s1', 0)
    s2 = an.get('s2', 0)
    p = an.get('p', 0)
    change_pct = an.get('chg', 0)
    rsi = an.get('rsi', 50)
    ratio = an.get('ratio', 0)
    sma20 = an.get('sma20', p)
    turnover = an.get('daily_turnover', 0)
    candle_strength = an.get('candle_strength', 0)
    
    if s1 == 0 and s2 == 0:
        return False, [], 0, "عادي"
    
    nearest_support = s1 if s1 > 0 else s2
    distance_to_support = (p - nearest_support) / nearest_support * 100 if nearest_support > 0 else 999
    
    # تحديد مستوى القرب من الدعم
    if 0 <= distance_to_support < 0.5:
        level = "عند الدعم"
    elif 0.5 <= distance_to_support < 1.0:
        level = "قريب جداً"
    elif 1.0 <= distance_to_support < 1.5:
        level = "قريب نسبياً"
    else:
        return False, [], 0, "عادي"
    
    reasons = []
    bounce_score = 0
    
    # كسر الدعم = خطر
    if p < nearest_support:
        return False, ["❌ كسر الدعم - خطر"], 0, "مكسور"
    
    # تغير السعر
    if 0.1 < change_pct < 4:
        bounce_score += 2
        reasons.append(f"📈 تغير إيجابي معتدل ({change_pct:+.3f}%)")
    elif change_pct >= 4:
        return False, ["⚠️ تغير كبير - احترس من القمة"], 0, level
    elif change_pct <= 0:
        return False, ["تغير سلبي - لم يرتد"], 0, level
    
    # تعافي RSI
    if rsi > 40:
        bounce_score += 1
        reasons.append(f"📊 RSI بدأ بالتعافي ({rsi:.0f})")
    
    # سيولة (حجم التداول بالجنيه)
    if turnover >= 20000000:
        bounce_score += 1
        reasons.append(f"💰 سيولة ممتازة ({turnover/1000000:.0f}M ج)")
    elif turnover >= 5000000:
        bounce_score += 1
        reasons.append(f"💰 سيولة جيدة ({turnover/1000000:.1f}M ج)")
    elif ratio > 1.0:
        bounce_score += 1
        reasons.append(f"📊 سيولة جيدة ({ratio:.1f}x)")
    
    # هيكل سعري
    if p > sma20:
        bounce_score += 1
        reasons.append(f"📈 السعر فوق SMA20 - بداية تكون قاع")
    
    # نماذج شموع إيجابية
    if candle_strength >= 2:
        bounce_score += 1
        reasons.append("🕯️ نماذج شموع إيجابية عند الدعم")
    
    # يحتاج 3+ نقاط للدخول
    is_valid = bounce_score >= 3
    
    if is_valid:
        reasons.append(f"✅ نقاط الارتداد: {bounce_score}/6 - مناسب للدخول")
    
    return is_valid, reasons, bounce_score, level

# ================== فلتر القطاع ==================
SECTORS = {
    "🏦 البنوك": ["CIEB", "COMI", "AAIB", "QNBA", "ALEX", "BID", "CAE", "NBK"],
    "🏗️ العقارات": ["TMGH", "OCDI", "PHDC", "HELI", "DEGC", "MNHD", "DSC"],
    "🍔 الأغذية": ["BFR", "EFID", "JUFO", "ORWE", "EDFO", "BIF"],
    "📡 الاتصالات": ["ETEL", "OTMT", "TE", "EMOB", "EGS"],
    "🏭 الصناعات": ["ESRS", "MFPC", "SKPC", "ABUK", "EFIC", "EGCH", "MICH"],
    "🛒 التجارة": ["RAYA", "SWDY", "AUTO", "ELSE", "MENA", "CAPI"]
}

def get_sector(name):
    name_upper = name.upper()
    for sector, symbols in SECTORS.items():
        for sym in symbols:
            if sym in name_upper or name_upper.startswith(sym):
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

# ================== تحميل البيانات وتحليل الأسهم ==================
@st.cache_data(ttl=300, show_spinner=False)
def get_all_data():
    url = "https://scanner.tradingview.com/egypt/scan"
    cols = ["name", "close", "RSI", "volume", "average_volume_10d_calc", "high", "low", "change", "description", "SMA20", "SMA50", "SMA200", "open"]
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
    except:
        return []

def fetch_single_stock(symbol):
    url = "https://scanner.tradingview.com/egypt/scan"
    cols = ["name", "close", "RSI", "volume", "average_volume_10d_calc", "high", "low", "change", "description", "SMA20", "SMA50", "SMA200", "open"]
    
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
        
        if len(d) < 12:
            return None
        
        # استخراج البيانات مع 3 أرقام عشرية للأسعار
        name = d[0] if d[0] else "N/A"
        p = round(d[1], 3) if d[1] else 0
        rsi = d[2] if d[2] else 50
        v = d[3] if d[3] else 0
        avg_v = d[4] if d[4] else 0
        h = round(d[5], 3) if d[5] else p
        l = round(d[6], 3) if d[6] else p
        chg = d[7] if d[7] else 0
        desc = d[8] if d[8] else name
        sma20 = round(d[9], 3) if d[9] else p
        sma50 = round(d[10], 3) if d[10] else p
        sma200 = round(d[11], 3) if d[11] else p
        open_price = round(d[12], 3) if len(d) > 12 and d[12] else p
        
        if p <= 0:
            return None
        
        rsi_val = rsi if rsi else 50
        ratio = v / avg_v if avg_v and avg_v > 0 else 0
        
        # حساب قيمة التداول بالجنيه
        daily_turnover = p * v if v else 0
        
        t_short = "صاعد" if (sma20 and p > sma20) else "هابط"
        t_med = "صاعد" if (sma50 and p > sma50) else "هابط"
        t_long = "صاعد" if (sma200 and p > sma200) else "هابط"
        
        high = h if h else p
        low = l if l else p
        pp = round((p + high + low) / 3, 3)
        r1 = round((2 * pp) - low, 3)
        r2 = round(pp + (high - low), 3)
        s1 = round((2 * pp) - high, 3)
        s2 = round(pp - (high - low), 3)
        
        entry_min = round(p * 0.98, 3)
        entry_max = round(p * 1.01, 3)
        entry_price = round((entry_min + entry_max) / 2, 3)
        
        stop_loss = round(min(s2 * 0.98, entry_price * 0.96) if s2 and s2 > 0 else entry_price * 0.96, 3)
        target = round(max(r1, entry_price * 1.05) if r1 and r1 > 0 else entry_price * 1.05, 3)
        
        profit_ps = target - entry_price
        loss_ps = entry_price - stop_loss
        
        if loss_ps <= 0:
            rr = 0
            risk_pct = 0
            target_pct = 0
        else:
            rr = round(profit_ps / loss_ps, 2)
            risk_pct = round((loss_ps / entry_price) * 100, 1)
            target_pct = round((profit_ps / entry_price) * 100, 1)
        
        # تحليل حجم التداول بالجنيه
        _, turnover_rating, turnover_score, turnover_ratio = analyze_turnover({
            'p': p, 'volume': v, 'avg_volume': avg_v
        })
        
        # تحليل نماذج الشموع
        candle_patterns, candle_strength = analyze_candlestick_patterns({
            'p': p, 'open': open_price, 'high': high, 'low': low,
            'chg': chg, 'prev_close': p * (1 - chg/100) if chg else p
        })
        
        temp_res = {
            't_short': t_short, 't_med': t_med, 't_long': t_long,
            'ratio': ratio, 'rsi': rsi_val, 'rr': rr, 'chg': chg or 0,
            'daily_turnover': daily_turnover, 'candle_strength': candle_strength
        }
        smart_score = smart_score_pro(temp_res)
        
        return {
            "name": name,
            "desc": desc,
            "p": p,
            "rsi": rsi_val,
            "chg": chg or 0,
            "ratio": ratio,
            "volume": v,
            "avg_volume": avg_v,
            "daily_turnover": daily_turnover,
            "turnover_rating": turnover_rating,
            "turnover_score": turnover_score,
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
            "open": open_price,
            "high": high,
            "low": low,
            "entry_range": f"{entry_min:.3f} - {entry_max:.3f}",
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "target": target,
            "rr": rr,
            "risk_pct": risk_pct,
            "target_pct": target_pct,
            "smart_score": smart_score,
            "candle_patterns": candle_patterns,
            "candle_strength": candle_strength
        }
    except Exception as e:
        print(f"Analysis error: {e}")
        return None

def preprocess(raw_data):
    results = []
    for r in raw_data:
        analyzed = analyze_stock(r)
        if analyzed:
            results.append(analyzed)
    return results

def get_top_10(results):
    valid = [r for r in results if r and r.get('smart_score', 0) >= 45]
    valid = [r for r in valid if r.get('daily_turnover', 0) >= 2000000]  # تداول 2 مليون على الأقل
    sorted_results = sorted(valid, key=lambda x: x.get('smart_score', 0), reverse=True)
    return sorted_results[:10]

def get_rapid_breakouts(results):
    rapid = []
    for r in results:
        if r and r.get('daily_turnover', 0) >= 2000000:
            analysis = is_rapid_breakout(r)
            if analysis.get('is_breakout', False):
                rapid.append({
                    'stock': r,
                    'analysis': analysis
                })
    rapid.sort(key=lambda x: x['analysis']['strength'], reverse=True)
    return rapid[:8]

def get_corrections(results, market_multiplier):
    corrections = []
    for r in results:
        if r and r.get('daily_turnover', 0) >= 2000000:
            is_corr, reasons, strength, label, color = is_correction_hunter(r, market_multiplier)
            if is_corr:
                corrections.append({
                    'stock': r,
                    'reasons': reasons,
                    'strength': strength,
                    'label': label,
                    'color': color
                })
    corrections.sort(key=lambda x: x['strength'], reverse=True)
    return corrections

def get_fresh_data():
    with st.spinner("🔄 جاري تحليل جميع الأسهم..."):
        raw = get_all_data()
        if raw:
            st.session_state.all_results = preprocess(raw)
            st.session_state.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return True
    return False

# ================== شارت TradingView ==================
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
            "hideideas": true,
            "studies": ["RSI@tv-basicstudies", "MASimple@tv-basicstudies"]
        }});
        </script>
    </div>
    """
    components.html(chart_html, height=height)

# ================== عرض بطاقة السهم ==================
def render_confidence_card(res):
    conf = get_confidence(res)
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, #1a1a2e, #16213e); border-radius: 12px; padding: 12px; margin: 10px 0; border-right: 4px solid {conf["color"]};'>
        <div style='display: flex; justify-content: space-between; align-items: center;'>
            <span style='font-size: 18px; font-weight: bold; color: #e0e0e0;'>{conf["emoji"]} قرار القناص</span>
            <span style='font-size: 28px; font-weight: bold; color: {conf["color"]};'>{conf["score"]}%</span>
        </div>
        <div style='margin-top: 5px;'><span style='color: {conf["color"]};'>{conf["advice"]}</span></div>
    </div>
    """, unsafe_allow_html=True)

def render_stock_card(res, is_top10=False):
    if res is None:
        st.warning("بيانات السهم غير متوفرة")
        return
    
    st.markdown(f"<div class='stock-header'>{res['name']} - {res['desc']}<span class='score-tag'>Smart: {res.get('smart_score', 0)}</span></div>", unsafe_allow_html=True)
    
    render_confidence_card(res)
    
    if is_top10:
        if res.get('smart_score', 0) >= 80:
            st.markdown('<div class="quality-excellent">🏆 فرصة ممتازة</div>', unsafe_allow_html=True)
        elif res.get('smart_score', 0) >= 65:
            st.markdown('<div class="quality-good">⭐ فرصة قوية</div>', unsafe_allow_html=True)
    
    # عرض نماذج الشموع إن وجدت
    if res.get('candle_patterns'):
        for pattern in res['candle_patterns'][:2]:
            st.info(f"🕯️ {pattern}")
    
    # عرض تحليل حجم التداول بالجنيه
    turnover = res.get('daily_turnover', 0)
    if turnover >= 50000000:
        st.success(f"💰 حجم التداول: {turnover/1000000:.0f} مليون جنيه - سيولة ممتازة جداً")
    elif turnover >= 20000000:
        st.success(f"💰 حجم التداول: {turnover/1000000:.0f} مليون جنيه - سيولة ممتازة")
    elif turnover >= 5000000:
        st.info(f"💰 حجم التداول: {turnover/1000000:.1f} مليون جنيه - سيولة جيدة")
    elif turnover >= 1000000:
        st.warning(f"💰 حجم التداول: {turnover/1000000:.1f} مليون جنيه - سيولة متوسطة")
    else:
        st.warning(f"💰 حجم التداول: {turnover:,.0f} جنيه - سيولة ضعيفة")
    
    ratio = res.get('ratio', 0)
    if ratio > 2.5:
        vol_text = f"🚀 ممتازة جداً ({ratio:.1f}x)"
    elif ratio > 1.8:
        vol_text = f"⚡ قوية ({ratio:.1f}x)"
    elif ratio > 1.2:
        vol_text = f"🙂 جيدة ({ratio:.1f}x)"
    else:
        vol_text = f"❄️ ضعيفة ({ratio:.1f}x)"
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: st.metric("السعر", f"{res['p']:.3f}", f"{res['chg']:+.2f}%")
    with col2: st.metric("Smart Score", f"{res['smart_score']}/100")
    with col3: st.metric("RR Ratio", f"{res['rr']}")
    with col4: st.metric("RSI", f"{res['rsi']:.0f}")
    with col5: st.metric("السيولة", vol_text)
    
    with st.expander("📊 التحليل الفني", expanded=True):
        render_chart(res['name'])
        
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
        <div class='entry-card'>
            🎯 <b>نطاق الدخول:</b> {res['entry_range']}<br>
            🛑 <b>وقف الخسارة:</b> {res['stop_loss']:.3f} <span style='color:#f85149'>(-{res['risk_pct']:.1f}%)</span><br>
            🏁 <b>المستهدف:</b> {res['target']:.3f} <span style='color:#58a6ff'>(+{res['target_pct']:.1f}%)</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🏛️ مستويات الدعم والمقاومة")
        st.markdown(f"""
        | المستوى | السعر | الدلالة |
        |---------|-------|---------|
        | 🔴 **مقاومة ثانية R2** | {res['r2']:.3f} | مقاومة قوية |
        | 🔴 **مقاومة أولى R1** | {res['r1']:.3f} | مقاومة أولى |
        | 🟡 **نقطة الارتكاز PP** | {res['pp']:.3f} | المحور |
        | 🟢 **دعم أول S1** | {res['s1']:.3f} | دعم أول |
        | 🟢 **دعم ثاني S2** | {res['s2']:.3f} | دعم قوي |
        """)
        
        # عرض نماذج الشموع بالتفصيل
        if res.get('candle_patterns'):
            st.markdown("### 🕯️ تحليل نماذج الشموع")
            for pattern in res['candle_patterns']:
                st.markdown(f"- {pattern}")
    
    with st.expander("💰 إدارة المخاطر وخطة الدخول", expanded=True):
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
                🟢 السعر: <b>{entry_level_1:.3f}</b> ج | 📦 الكمية: <b>{shares_1:,}</b> سهم
            </div>
            <div style='background:#0d1117;border:1px solid #d29922;border-radius:10px;padding:12px;margin:10px 0;'>
                <b>📌 المستوى الثاني - تعزيز الدعم</b><br>
                🟡 السعر: <b>{entry_level_2:.3f}</b> ج | 📦 الكمية: <b>{shares_2:,}</b> سهم
            </div>
            <div style='background:#0d1117;border:1px solid #58a6ff;border-radius:10px;padding:12px;margin:10px 0;'>
                <b>📌 المستوى الثالث - تأكيد الاختراق</b><br>
                🔵 السعر: <b>{entry_level_3:.3f}</b> ج | 📦 الكمية: <b>{shares_3:,}</b> سهم
            </div>
            """, unsafe_allow_html=True)
            
            total_shares = shares_1 + shares_2 + shares_3
            total_cost = (shares_1 * entry_level_1) + (shares_2 * entry_level_2) + (shares_3 * entry_level_3)
            if total_shares > 0:
                avg_price = total_cost / total_shares
                st.info(f"📊 **متوسط السعر بعد التنفيذ الكامل:** {avg_price:.3f} ج ({total_shares:,} سهم)")
    
    msg = f"📊 تحليل سهم {res['name']}\n💰 السعر: {res['p']:.3f}\n🎯 الدخول: {res['entry_range']}\n🛑 الوقف: {res['stop_loss']:.3f}\n🏁 الهدف: {res['target']:.3f}\n⚖️ RR: {res['rr']}"
    encoded = urllib.parse.quote(msg)
    st.markdown(f"[📱 مشاركة عبر واتساب](https://wa.me/?text={encoded})")

# ================== CSS Styles ==================
st.markdown("""
<style>
.stButton>button { width: 100%; border-radius: 10px; height: 45px; font-weight: bold; }
.stock-header { font-size: 22px; font-weight: bold; color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 8px; }
.score-tag { float: right; background: #238636; color: white; padding: 2px 12px; border-radius: 15px; font-size: 14px; }
.quality-excellent { background: #1f4f2b; color: white; padding: 5px; border-radius: 8px; text-align: center; }
.quality-good { background: #1f3a4f; color: white; padding: 5px; border-radius: 8px; text-align: center; }
.entry-card { background: #0d1117; border: 1px solid #3fb950; border-radius: 10px; padding: 12px; margin: 10px 0; }
.rapid-card { background: linear-gradient(135deg, #1a0a0a, #0d0a0a); border-radius: 12px; padding: 15px; margin-bottom: 15px; border-right: 4px solid #FF6666; }
.correction-card { background: linear-gradient(135deg, #0d1f0d, #0a150a); border-radius: 12px; padding: 15px; margin-bottom: 15px; border-right: 4px solid #2E7D32; }
.support-card { background: linear-gradient(135deg, #0d1117, #0a0c10); border-radius: 12px; padding: 15px; margin-bottom: 15px; border-right: 4px solid #2196f3; }
</style>
""", unsafe_allow_html=True)

# ================== واجهة المستخدم الرئيسية ==================
def main():
    if st.session_state.all_results is None:
        get_fresh_data()
    
    market_status = get_egx30_status()
    
    st.title("🎯 EGX Sniper Pro Ultimate")
    st.caption("النسخة المدمجة - أفضل أداء وأعلى دقة | تحليل كل الأسهم | فرص سريعة | صائد تصحيحات | دعم وارتداد | تحليل الشموع وحجم التداول")
    
    st.markdown(f"""
    <div style="background: #0d1117; border-radius: 10px; padding: 10px; margin-bottom: 20px; text-align: center;">
        <span style="color: {market_status['color']}; font-weight: bold;">📊 المؤشر العام:</span>
        <span>{market_status['status']}</span>
        <span style="margin-right: 15px;">📈 التغير: {market_status['change']:+.2f}%</span>
        <span>📊 RSI: {market_status['rsi']:.0f}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # شريط التنقل
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        if st.button("🏠 الرئيسية", use_container_width=True):
            st.session_state.page = 'home'
            st.rerun()
    with col2:
        if st.button("🏆 أفضل 10", use_container_width=True):
            st.session_state.page = 'top10'
            st.rerun()
    with col3:
        if st.button("🎯 التصحيحات", use_container_width=True):
            st.session_state.page = 'correction'
            st.rerun()
    with col4:
        if st.button("⚡ الاختراق", use_container_width=True):
            st.session_state.page = 'rapid'
            st.rerun()
    with col5:
        if st.button("🔻 دعم وارتداد", use_container_width=True):
            st.session_state.page = 'support'
            st.rerun()
    with col6:
        if st.button("🔍 تحليل سهم", use_container_width=True):
            st.session_state.page = 'analyze'
            st.rerun()
    
    # فلتر القطاع ونمط التداول
    with st.expander("⚙️ الإعدادات والفلترة", expanded=False):
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
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 تحديث البيانات", use_container_width=True):
                get_fresh_data()
                st.rerun()
        with col2:
            if st.button("📊 تقييم الأداء", use_container_width=True):
                st.session_state.page = 'performance'
                st.rerun()
    
    # الصفحات المختلفة
    if st.session_state.page == 'home':
        st.markdown("### 📊 أحدث فرص السوق")
        
        filtered = filter_by_sector(st.session_state.all_results, st.session_state.sector_filter)
        
        if filtered:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📊 إجمالي الأسهم", len(filtered))
            with col2:
                rapid_count = len(get_rapid_breakouts(filtered))
                st.metric("⚡ فرص اختراق", rapid_count)
            with col3:
                corrections = get_corrections(filtered, market_status['market_multiplier'])
                st.metric("🎯 فرص تصحيح", len(corrections))
            
            st.info(f"🕐 آخر تحديث: {st.session_state.last_update}")
            
            tab1, tab2 = st.tabs(["🎯 صائد التصحيحات", "⚡ قناص الاختراق"])
            
            with tab1:
                corrections = get_corrections(filtered, market_status['market_multiplier'])
                if corrections:
                    for item in corrections[:5]:
                        an = item['stock']
                        st.markdown(f"""
                        <div class="correction-card" style="border-right-color: {item['color']};">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <h3 style="margin: 0; color: #81C784;">🎯 {an['name']} - {an['desc']}</h3>
                                <span style="background: {item['color']}; padding: 5px 15px; border-radius: 20px; color: white; font-weight: bold;">
                                    {item['label']} | {item['strength']}%
                                </span>
                            </div>
                            <div style="height: 6px; background: #1a3a1a; margin: 10px 0;">
                                <div style="width: {item['strength']}%; background: {item['color']}; height: 6px; border-radius: 3px;"></div>
                            </div>
                            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 10px 0;">
                                <div>💰 {an['p']:.3f} ج</div>
                                <div>📊 RSI: {an['rsi']:.0f}</div>
                                <div>💧 سيولة: {an['ratio']:.1f}x</div>
                                <div>📈 تغير: {an['chg']:+.2f}%</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button(f"📊 تحليل {an['name']}", key=f"home_corr_{an['name']}"):
                            render_stock_card(an)
                else:
                    st.info("ℹ️ لا توجد فرص تصحيح حالياً.")
            
            with tab2:
                rapid_opportunities = get_rapid_breakouts(filtered)
                if rapid_opportunities:
                    for item in rapid_opportunities[:5]:
                        an = item['stock']
                        analysis = item['analysis']
                        st.markdown(f"""
                        <div class="rapid-card" style="border-right-color: {analysis['color']};">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <h3 style="margin: 0; color: #FF9999;">⚡ {an['name']} - {an['desc']}</h3>
                                <span style="background: {analysis['color']}; padding: 5px 15px; border-radius: 20px; color: #1a1a1a; font-weight: bold;">
                                    {analysis['label']} | {analysis['strength']}%
                                </span>
                            </div>
                            <div style="height: 6px; background: #333; margin: 10px 0;">
                                <div style="width: {analysis['strength']}%; background: {analysis['color']}; height: 6px; border-radius: 3px;"></div>
                            </div>
                            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 10px 0;">
                                <div>🎯 هدف أول: {analysis['target_1']:.3f}</div>
                                <div>🎯 هدف ثاني: {analysis['target_2']:.3f}</div>
                                <div>🛑 وقف: {analysis['stop_loss_rapid']:.3f}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button(f"📊 تحليل {an['name']}", key=f"home_rapid_{an['name']}"):
                            render_stock_card(an)
                else:
                    st.info("ℹ️ لا توجد فرص اختراق حالياً.")
    
    elif st.session_state.page == 'top10':
        if st.button("🏠 العودة للرئيسية"): 
            st.session_state.page = 'home'
            st.rerun()
        
        st.title("🏆 أفضل 10 فرص")
        
        filtered = filter_by_sector(st.session_state.all_results, st.session_state.sector_filter)
        top = get_top_10(filtered)
        
        if top:
            for i, an in enumerate(top, 1):
                with st.expander(f"#{i} - {an['name']} | Smart: {an['smart_score']} | RR: {an['rr']} | RSI: {an['rsi']:.0f} | تداول: {an.get('daily_turnover', 0)/1000000:.1f}M"):
                    render_stock_card(an, is_top10=True)
                    if st.button(f"💾 تسجيل الصفقة", key=f"rec_top_{an['name']}"):
                        record_trade(an, "أفضل 10")
                        st.success("✅ تم تسجيل الصفقة!")
        else:
            st.warning("⚠️ لا توجد فرص مطابقة للمعايير حالياً.")
    
    elif st.session_state.page == 'correction':
        if st.button("🏠 العودة للرئيسية"): 
            st.session_state.page = 'home'
            st.rerun()
        
        st.title("🎯 صائد التصحيحات")
        st.markdown("""
        <div style="background: rgba(46,125,50,0.15); border-right: 4px solid #2E7D32; padding: 10px; border-radius: 8px; margin-bottom: 20px;">
            🎯 <b>الأسهم القوية التي تصحح</b><br>
            • اتجاه عام صاعد | • RSI في التصحيح (28-55) | • بداية ارتداد | • سيولة جيدة (تداول > 5 مليون)
        </div>
        """, unsafe_allow_html=True)
        
        filtered = filter_by_sector(st.session_state.all_results, st.session_state.sector_filter)
        corrections = get_corrections(filtered, market_status['market_multiplier'])
        
        if corrections:
            st.markdown(f"**🎯 عدد فرص التصحيح: {len(corrections)}**")
            for item in corrections:
                an = item['stock']
                st.markdown(f"""
                <div class="correction-card" style="border-right-color: {item['color']};">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h3 style="margin: 0; color: #81C784;">🎯 {an['name']} - {an['desc']}</h3>
                        <span style="background: {item['color']}; padding: 5px 15px; border-radius: 20px; color: white; font-weight: bold;">
                            {item['label']} | {item['strength']}%
                        </span>
                    </div>
                    <div style="height: 6px; background: #1a3a1a; margin: 10px 0;">
                        <div style="width: {item['strength']}%; background: {item['color']}; height: 6px; border-radius: 3px;"></div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 10px 0;">
                        <div>💰 {an['p']:.3f} ج</div>
                        <div>📊 RSI: {an['rsi']:.0f}</div>
                        <div>💰 تداول: {an.get('daily_turnover', 0)/1000000:.1f}M</div>
                        <div>📈 تغير: {an['chg']:+.2f}%</div>
                    </div>
                    <div style="background: rgba(46,125,50,0.15); border-radius: 8px; padding: 8px;">
                        ✅ {', '.join(item['reasons'][:4])}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                with st.expander(f"📊 التحليل الكامل لسهم {an['name']}"):
                    render_stock_card(an)
                
                if st.button(f"💾 تسجيل الصفقة", key=f"rec_corr_{an['name']}"):
                    record_trade(an, "صائد تصحيحات")
                    st.success("✅ تم تسجيل الصفقة!")
                st.markdown("---")
        else:
            st.info("ℹ️ لا توجد فرص تصحيح حالياً.")
    
    elif st.session_state.page == 'rapid':
        if st.button("🏠 العودة للرئيسية"): 
            st.session_state.page = 'home'
            st.rerun()
        
        st.title("⚡ قناص الاختراق السريع")
        st.markdown("""
        <div style="background: rgba(255,102,102,0.15); border-right: 4px solid #FF6666; padding: 10px; border-radius: 8px; margin-bottom: 20px;">
            🚀 <b>فرص خلال جلسة أو جلستين</b><br>
            • RSI بين 45-75 | • سيولة استثنائية (تداول > 15 مليون) | • قرب اختراق المقاومة | • وقف خسارة ضيق
        </div>
        """, unsafe_allow_html=True)
        
        filtered = filter_by_sector(st.session_state.all_results, st.session_state.sector_filter)
        rapid_opportunities = get_rapid_breakouts(filtered)
        
        if rapid_opportunities:
            st.markdown(f"**⚡ عدد فرص الاختراق السريع: {len(rapid_opportunities)}**")
            for item in rapid_opportunities:
                an = item['stock']
                analysis = item['analysis']
                
                st.markdown(f"""
                <div class="rapid-card" style="border-right-color: {analysis['color']};">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h3 style="margin: 0; color: #FF9999;">⚡ {an['name']} - {an['desc']}</h3>
                        <span style="background: {analysis['color']}; padding: 5px 15px; border-radius: 20px; color: #1a1a1a; font-weight: bold;">
                            {analysis['label']} | {analysis['strength']}%
                        </span>
                    </div>
                    <div style="height: 6px; background: #333; margin: 10px 0;">
                        <div style="width: {analysis['strength']}%; background: {analysis['color']}; height: 6px; border-radius: 3px;"></div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 10px 0;">
                        <div>💰 {an['p']:.3f} ج</div>
                        <div>📊 RSI: {an['rsi']:.0f}</div>
                        <div>💰 تداول: {an.get('daily_turnover', 0)/1000000:.1f}M</div>
                        <div>📈 تغير: {an['chg']:+.2f}%</div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 10px 0;">
                        <div style="background: #1f4f2b; border-radius: 8px; padding: 8px; text-align: center; color: white;">
                            🎯 هدف أول<br><b>{analysis['target_1']:.3f}</b>
                        </div>
                        <div style="background: #1f3a4f; border-radius: 8px; padding: 8px; text-align: center; color: white;">
                            🎯 هدف ثاني<br><b>{analysis['target_2']:.3f}</b>
                        </div>
                        <div style="background: #4a1a1a; border-radius: 8px; padding: 8px; text-align: center; color: white;">
                            🛑 وقف ضيق<br><b>{analysis['stop_loss_rapid']:.3f}</b>
                        </div>
                    </div>
                    <div style="background: rgba(255,102,102,0.1); border-radius: 8px; padding: 8px;">
                        ✅ {', '.join(analysis['reasons'])}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                with st.expander(f"📊 التحليل الكامل لسهم {an['name']}"):
                    render_stock_card(an)
                
                if st.button(f"💾 تسجيل الصفقة", key=f"rec_rapid_{an['name']}"):
                    record_trade(an, "اختراق سريع")
                    st.success("✅ تم تسجيل الصفقة!")
                st.markdown("---")
        else:
            st.info("ℹ️ لا توجد فرص اختراق سريع حالياً.")
    
    elif st.session_state.page == 'support':
        if st.button("🏠 العودة للرئيسية"): 
            st.session_state.page = 'home'
            st.rerun()
        
        st.title("🔻 فرص الدعم والارتداد")
        st.markdown("""
        <div style="background: rgba(33,150,243,0.15); border-right: 4px solid #2196f3; padding: 10px; border-radius: 8px; margin-bottom: 20px;">
            🔻 <b>الأسهم القريبة من الدعم مع تأكيد ارتداد</b><br>
            • قرب من الدعم (اقل من 1.5%) | • بداية ارتداد إيجابي | • RSI يتعافى | • سيولة جيدة
        </div>
        """, unsafe_allow_html=True)
        
        filtered = filter_by_sector(st.session_state.all_results, st.session_state.sector_filter)
        
        support_stocks = []
        for an in filtered:
            if an and an.get('daily_turnover', 0) >= 2000000:
                is_valid, reasons, score, level = is_support_with_bounce(an)
                if is_valid:
                    support_stocks.append({'stock': an, 'reasons': reasons, 'score': score, 'level': level})
        
        if support_stocks:
            support_stocks.sort(key=lambda x: x['score'], reverse=True)
            st.markdown(f"**🔻 عدد فرص الدعم والارتداد: {len(support_stocks)}**")
            
            for item in support_stocks:
                an = item['stock']
                reasons = item['reasons']
                score = item['score']
                level = item['level']
                
                if level == "عند الدعم":
                    badge = "📍 عند الدعم"
                    badge_color = "#4caf50"
                elif level == "قريب جداً":
                    badge = "📏 قريب جداً"
                    badge_color = "#ff9800"
                else:
                    badge = "📏 قريب نسبياً"
                    badge_color = "#ff9800"
                
                if score >= 5:
                    quality = "🔥 فرصة ممتازة"
                    quality_color = "#4caf50"
                elif score >= 4:
                    quality = "✅ فرصة جيدة جداً"
                    quality_color = "#2196f3"
                else:
                    quality = "✅ فرصة جيدة"
                    quality_color = "#2196f3"
                
                st.markdown(f"""
                <div class="support-card" style="border-right-color: {badge_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                        <h3 style="margin: 0; color: #64b5f6;">🔻 {an['name']} - {an['desc']}</h3>
                        <span style="background: {badge_color}; padding: 5px 15px; border-radius: 20px; color: white; font-weight: bold;">
                            {badge} | نقاط: {score}/6
                        </span>
                    </div>
                    <div style="margin-top: 10px;">
                        <span style="background: {quality_color}; padding: 3px 12px; border-radius: 15px; color: white; font-size: 13px;">
                            {quality}
                        </span>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 10px 0;">
                        <div>💰 {an['p']:.3f} ج</div>
                        <div>📊 RSI: {an['rsi']:.0f}</div>
                        <div>💰 تداول: {an.get('daily_turnover', 0)/1000000:.1f}M</div>
                        <div>📈 تغير: {an['chg']:+.2f}%</div>
                    </div>
                    <div style="background: rgba(33,150,243,0.1); border-radius: 8px; padding: 8px;">
                        ✅ {', '.join(reasons[:5])}
                    </div>
                    <div style="margin-top: 10px; background: rgba(76,175,80,0.1); border-radius: 8px; padding: 8px;">
                        💡 <b>وقف الخسارة المقترح:</b> أسفل {an['s1']:.3f} مباشرة
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                with st.expander(f"📊 التحليل الكامل لسهم {an['name']}"):
                    render_stock_card(an)
                
                if st.button(f"💾 تسجيل الصفقة", key=f"rec_support_{an['name']}"):
                    record_trade(an, "دعم وارتداد")
                    st.success("✅ تم تسجيل الصفقة!")
                st.markdown("---")
        else:
            st.info("ℹ️ لا توجد فرص دعم وارتداد حالياً.")
    
    elif st.session_state.page == 'analyze':
        if st.button("🏠 العودة للرئيسية"): 
            st.session_state.page = 'home'
            st.rerun()
        
        st.title("🔍 تحليل سهم")
        sym = st.text_input("🔎 أدخل رمز السهم", placeholder="مثال: COMI, TMGH, ETEL").upper().strip()
        
        if sym:
            with st.spinner("🔍 جاري البحث عن السهم..."):
                data = fetch_single_stock(sym)
                
                if not data:
                    st.error(f"❌ السهم '{sym}' غير موجود")
                    if st.session_state.all_results:
                        symbols = [r.get('name') for r in st.session_state.all_results[:30] if r]
                        if symbols:
                            st.info(f"💡 أمثلة: {', '.join(symbols[:15])}")
                else:
                    res = analyze_stock(data[0])
                    if res:
                        render_stock_card(res)
                        if st.button(f"💾 تسجيل الصفقة", key=f"rec_analyze_{sym}"):
                            record_trade(res, "تحليل فردي")
                            st.success("✅ تم تسجيل الصفقة!")
                    else:
                        st.warning("⚠️ فشل تحليل السهم")
    
    elif st.session_state.page == 'performance':
        if st.button("🏠 العودة للرئيسية"): 
            st.session_state.page = 'home'
            st.rerun()
        
        st.title("📊 تقييم الأداء")
        trades = load_trades()
        stats = get_performance_stats(trades)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📊 إجمالي الصفقات", stats['total'])
        col2.metric("✅ حققت الهدف", stats['hit_target'])
        col3.metric("❌ ضربت الوقف", stats['stopped_out'])
        col4.metric("⏳ لا تزال مفتوحة", stats['still_open'])
        
        col1, col2 = st.columns(2)
        col1.metric("📈 نسبة النجاح", f"{stats['success_rate']}%")
        col2.metric("⚖️ متوسط RR", stats['avg_rr'])
        
        if trades:
            st.markdown("### 📋 آخر الصفقات")
            for trade in trades[-10:][::-1]:
                if trade.get('status') == 'hit_target':
                    status = "🟢 حققت الهدف"
                elif trade.get('status') == 'stopped_out':
                    status = "🔴 ضربت الوقف"
                else:
                    status = "🟡 لا تزال مفتوحة"
                
                profit_text = f" | {trade.get('profit_pct', 0):+.1f}%" if trade.get('profit_pct') else ""
                
                st.markdown(f"""
                <div style='background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:10px;margin:5px 0;'>
                    <b>{trade.get('name', 'N/A')}</b> ({trade.get('trade_type', 'N/A')}) - {status}{profit_text}<br>
                    📅 التسجيل: {trade.get('date_recorded', 'N/A')}<br>
                    🎯 الهدف: {trade.get('target', 0):.3f} | 🛑 الوقف: {trade.get('stop_loss', 0):.3f} | ⚖️ RR: {trade.get('rr', 0)}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("📭 لا توجد صفقات مسجلة بعد.")

if __name__ == "__main__":
    main()
