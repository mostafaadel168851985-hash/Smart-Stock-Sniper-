import streamlit as st
import streamlit.components.v1 as components
import requests
from datetime import datetime, date
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
                if isinstance(data, list):
                    return data
                return []
        except:
            return []
    return []

def save_trades(trades):
    try:
        with open(TRADES_FILE, 'w', encoding='utf-8') as f:
            json.dump(trades, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving trades: {e}")

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
        "min_price": None
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


# ================== 🔥 SMART ADDITIONS ==================
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

def is_fake_breakout(res):
    if res.get('rsi', 50) > 75 and res.get('rr', 0) < 1.3:
        return True
    if res.get('ratio', 0) < 1.1 and res.get('rsi', 50) > 60:
        return True
    return False

def smart_decision(res):
    assert 'smart_score' in res, "smart_score missing from stock data"
    score = res['smart_score']
    fake = is_fake_breakout(res)
    if fake:
        return "❌ فخ سيولة", "danger"
    elif score >= 70:
        return "🔥 فرصة قوية جداً", "strong"
    elif score >= 50:
        return "✅ فرصة جيدة", "good"
    elif score >= 30:
        return "⚠️ تحت المراقبة", "watch"
    else:
        return "❄️ ضعيف", "weak"

def expected_success_rate(res):
    score = 0
    trends = [res.get('t_short', 'هابط'), res.get('t_med', 'هابط'), res.get('t_long', 'هابط')]
    if all(t == "صاعد" for t in trends):
        score += 30
    elif trends.count("صاعد") >= 2:
        score += 20
    elif trends.count("صاعد") == 1:
        score += 10
    
    ratio = res.get('ratio', 0)
    if ratio > 2:
        score += 25
    elif ratio > 1.5:
        score += 15
    elif ratio > 1:
        score += 8
    elif ratio == 0:
        score -= 5
    
    risk_range = res.get('target_pct', 0) - abs(res.get('risk_pct', 0))
    if risk_range > 5:
        score += 15
    elif risk_range > 3:
        score += 10
    elif risk_range > 1:
        score += 5
    
    if res.get('rr', 0) >= 2:
        score += 10
    elif res.get('rr', 0) >= 1.5:
        score += 5
    
    success_rate = min(85, max(0, score))
    if success_rate >= 70: level = "🔥 ممتازة"
    elif success_rate >= 55: level = "✅ جيدة"
    elif success_rate >= 40: level = "⚠️ متوسطة"
    else: level = "❌ ضعيفة"
    return success_rate, level

def calculate_trailing_stop(entry_price, current_price, highest_price, rr):
    if current_price <= entry_price:
        return entry_price * 0.97
    profit_pct = (current_price - entry_price) / entry_price * 100
    if highest_price > entry_price:
        return highest_price * 0.95
    elif profit_pct >= 5 and rr >= 1.5:
        new_stop = entry_price + (profit_pct / 2) / 100 * entry_price
        return round(min(new_stop, current_price * 0.98), 2)
    elif profit_pct >= 3:
        return round(entry_price, 2)
    else:
        return round(entry_price * 0.97, 2)

def calculate_stochastic_rsi(rsi):
    if rsi <= 20: return {"k": 90, "d": 85, "signal": "🟢 تشبع بيع - فرصة انعكاس (تقديري)"}
    elif rsi <= 35: return {"k": 70, "d": 65, "signal": "🟡 منطقة شراء محتملة (تقديري)"}
    elif rsi <= 65: return {"k": 50, "d": 50, "signal": "⚪ منطقة حيادية"}
    elif rsi <= 80: return {"k": 30, "d": 35, "signal": "🟠 منطقة بيع محتملة (تقديري)"}
    else: return {"k": 10, "d": 15, "signal": "🔴 تشبع شراء - خطر (تقديري)"}

def calculate_roc(current_price, previous_price):
    if previous_price and previous_price > 0:
        return ((current_price - previous_price) / previous_price) * 100
    return 0

# ================== 🆕 SUPPORT & BOUNCE DETECTION ==================
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
    r1 = an.get('r1', p * 1.03) if an.get('r1') is not None else p * 1.03
    
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
        
        rsi_recovery = max(0, rsi - 30)
        if rsi_recovery > 10:
            bounce_score += 1
            reasons.append(f"🔄 RSI تعافى بقوة من التشبع ({rsi_recovery:.0f} نقطة)")
        
        if bounce_score < 3:
            return False, [f"نقاط الارتداد منخفضة ({bounce_score}/5)"], level, bounce_score
    
    elif mode == "momentum":
        momentum_score = 0
        
        if rsi > 45 and p > sma20:
            momentum_score += 1
            reasons.append(f"📈 زخم إيجابي (RSI {rsi:.0f}، السعر فوق SMA20)")
        
        if ratio > 1.2:
            momentum_score += 1
            reasons.append(f"💧 سيولة جيدة ({ratio:.1f}x)")
        
        if 0 < change_pct < 4:
            momentum_score += 1
            reasons.append(f"📊 تغير إيجابي معتدل ({change_pct:+.2f}%)")
        
        if rsi < 40:
            momentum_score += 1
            reasons.append(f"🎯 RSI منخفض ({rsi:.0f}) - احتمال انعكاس")
        
        if momentum_score < 2:
            return False, [], "عادي", 0
    
    if rsi < 35:
        reasons.append(f"🟢 RSI منخفض جداً ({rsi:.0f}) - تشبع بيع ممتاز")
    elif rsi < 45:
        reasons.append(f"📊 RSI منخفض ({rsi:.0f}) - فرصة جيدة")
    
    potential_gain = (r1 - p) / p * 100 if r1 > p else 0
    if potential_gain > 3:
        reasons.append(f"🎯 هدف محتمل: {r1:.2f} (+{potential_gain:.1f}%)")
    
    return True, reasons, level, bounce_score

def get_support_quality_rating(res, level, mode="near", bounce_score=0):
    rr = res.get('rr', 0) if res.get('rr') is not None else 0
    ratio = res.get('ratio', 0) if res.get('ratio') is not None else 0
    rsi = res.get('rsi', 50) if res.get('rsi') is not None else 50
    
    if mode == "bounce":
        if bounce_score >= 4 and level == "عند الدعم" and rr >= 1.5 and ratio > 1.2 and 40 < rsi < 55:
            return "🔥 ممتاز - فرصة ذهبية للشراء"
        elif bounce_score >= 3 and rr >= 1.3:
            return "✅ جيد - مناسب للدخول"
        else:
            return "📌 للمتابعة - يحتاج تأكيد إضافي"
    elif mode == "momentum":
        if rsi < 45 and ratio > 1.2 and rr >= 1.5:
            return "🔥 ممتاز - زخم قوي جداً"
        elif rsi < 55 and ratio > 0.8:
            return "✅ جيد - يستحق المراقبة"
        else:
            return "📌 للمتابعة"
    else:
        if level == "عند الدعم" and rsi < 40 and ratio > 1:
            return "🔥 ممتاز - سهم عند الدعم مع تشبع بيع"
        elif level == "قريب جداً" and rsi < 45:
            return "✅ جيد - قريب من الدعم مع مؤشرات إيجابية"
        else:
            return "📌 للمتابعة"

# ================== 🆕 QUALITY RATING ==================
def get_quality_rating(res, section_type):
    if section_type == "breakout":
        if res.get('ratio', 0) > 3.5 and res.get('rsi', 50) < 65:
            return "🔥 ممتاز - اختراق قوي جداً"
        elif res.get('ratio', 0) > 2.5 and res.get('rsi', 50) < 70:
            return "✅ جيد - اختراق موثوق"
        else:
            return "⚠️ عادي - يحتاج متابعة"
    
    elif section_type == "scalp":
        if res.get('ratio', 0) > 2.5 and res.get('rr', 0) >= 1.8 and 45 < res.get('rsi', 50) < 60:
            return "🔥 ممتاز - مضاربة مثالية"
        elif res.get('ratio', 0) > 1.8 and res.get('rr', 0) >= 1.5:
            return "✅ جيد - مضاربة مناسبة"
        else:
            return "⚠️ عادي - يحتاج تركيز"
    
    elif section_type == "gold":
        if res.get('rr', 0) >= 2.2 and res.get('ratio', 0) > 2:
            return "🔥 ذهبي ممتاز - فرصة نادرة"
        else:
            return "✅ ذهبي - فرصة قوية"
    
    elif section_type == "top10":
        if res.get('smart_score', 0) >= 85:
            return "🏆 الأفضل اليوم"
        elif res.get('smart_score', 0) >= 75:
            return "⭐ ممتاز"
        elif res.get('smart_score', 0) >= 65:
            return "✅ جيد"
        else:
            return "📌 للمتابعة"
    
    elif section_type == "watchlist":
        if res.get('rr', 0) >= 1.8 and res.get('ratio', 0) > 1.8:
            return "🔥 واعد - قريب من الاختراق"
        elif res.get('rr', 0) >= 1.5:
            return "✅ جيد - يستحق المتابعة"
        else:
            return "📌 عادي"
    
    return "📌 عادي"

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
            "studies": [
                "RSI@tv-basicstudies",
                "MASimple@tv-basicstudies",
                "PivotPointsHighLow@tv-basicstudies"
            ]
        }});
        </script>
    </div>
    """
    components.html(chart_html, height=height)


# ================== 📤 SHARE ON WHATSAPP ==================
def share_on_whatsapp(res):
    smart_text, _ = smart_decision(res)
    
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

🤖 التقييم: {smart_text}

---
تم التحليل بواسطة EGX Sniper Pro"""
    
    encoded_msg = urllib.parse.quote(message)
    return f"https://wa.me/?text={encoded_msg}"


# ================== 🆕 IMMINENT BREAKOUT DETECTION ==================
def is_imminent_breakout(an):
    if an is None or not an.get('r1'):
        return False, []
    
    reasons = []
    distance_to_r1 = (an['r1'] - an['p']) / an['p'] * 100
    
    if 0 < distance_to_r1 < 2:
        reasons.append(f"🎯 قرب من المقاومة R1 ({distance_to_r1:.1f}%)")
    else:
        return False, []
    
    if 50 < an.get('rsi', 50) < 65:
        reasons.append(f"📈 RSI صحي ({an['rsi']:.0f})")
    else:
        return False, []
    
    if an.get('ratio', 0) > 1.5:
        reasons.append(f"💧 سيولة جيدة ({an['ratio']:.1f}x)")
    else:
        return False, []
    
    if an.get('t_short') == "صاعد":
        reasons.append("📊 اتجاه قصير صاعد")
    else:
        return False, []
    
    return True, reasons


# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="EGX Sniper Pro v17.5", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-size: 18px !important; font-weight: bold !important; margin-bottom: 10px; }
    .stock-header { font-size: 26px !important; font-weight: bold; color: #58a6ff; border-bottom: 2px solid #30363d; padding-bottom: 10px; }
    .score-tag { float: left; background: #238636; color: white; padding: 2px 15px; border-radius: 10px; font-size: 18px; margin-top: 5px; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 10px; padding: 10px !important; }
    .trend-pill { padding: 4px 12px; border-radius: 15px; font-size: 13px; font-weight: bold; margin: 2px; display: inline-block; border: 1px solid #30363d; }
    .trend-up { background-color: rgba(63, 185, 80, 0.15); color: #3fb950; border-color: #3fb950; }
    .trend-down { background-color: rgba(248, 81, 73, 0.15); color: #f85149; border-color: #f85149; }
    .signal-pill { padding: 8px 20px; border-radius: 20px; font-weight: bold; display: inline-block; margin: 10px 0; font-size: 16px; }
    .buy-strong { background: #238636; color: white; }
    .buy-caution { background: rgba(240, 139, 55, 0.2); color: #f08b37; border: 1px solid #f08b37; }
    .wait { background: #161b22; color: #8b949e; border: 1px solid #30363d; }
    .entry-card-new { background-color: #0d1117; border: 1px solid #3fb950; border-radius: 12px; padding: 15px; text-align: center; margin-bottom: 15px; border-top: 4px solid #3fb950; }
    .target-box { border: 2px solid #58a6ff; border-radius: 12px; padding: 15px; text-align: center; background: #0d1117; margin-top: 10px; font-size: 18px; }
    .plan-container { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-top: 15px; border-right: 5px solid #238636; }
    .investor-card { background-color: #161b22; border: 1px solid #d29922; border-radius: 12px; padding: 15px; margin-bottom: 15px; border-top: 4px solid #d29922; }
    .investor-title { color: #d29922; font-weight: bold; font-size: 18px; margin-bottom: 10px; display: block; border-bottom: 1px solid #30363d; padding-bottom: 5px; }
    .level-box { display: flex; justify-content: space-between; padding: 3px 0; border-bottom: 1px solid #21262d; }
    .sup-text { color: #3fb950; font-weight: bold; }
    .res-text { color: #f85149; font-weight: bold; }
    .alert-success { background-color: rgba(63, 185, 80, 0.2); border-right: 4px solid #3fb950; padding: 10px; border-radius: 8px; margin: 10px 0; }
    .alert-danger { background-color: rgba(248, 81, 73, 0.2); border-right: 4px solid #f85149; padding: 10px; border-radius: 8px; margin: 10px 0; }
    .buy-signal { background-color: #238636; padding: 10px; border-radius: 10px; text-align: center; margin-bottom: 10px; }
    .watch-signal { background-color: #d29922; padding: 10px; border-radius: 10px; text-align: center; margin-bottom: 10px; }
    .avoid-signal { background-color: #f85149; padding: 10px; border-radius: 10px; text-align: center; margin-bottom: 10px; }
    .premium-badge { background: linear-gradient(135deg, #d4af37, #ffd700); color: #1a1a2e; padding: 5px 15px; border-radius: 20px; font-weight: bold; display: inline-block; margin-bottom: 10px; }
    .real-breakout { background: linear-gradient(135deg, #00c853, #69f0ae); color: #1a1a2e; padding: 5px 15px; border-radius: 20px; font-weight: bold; display: inline-block; margin-bottom: 10px; }
    .whatsapp-btn { background-color: #25D366; color: white; border: none; border-radius: 12px; padding: 10px; font-size: 16px; font-weight: bold; cursor: pointer; width: 100%; text-align: center; text-decoration: none; display: inline-block; }
    .whatsapp-btn:hover { background-color: #128C7E; }
    .quality-badge { padding: 5px 10px; border-radius: 10px; margin-bottom: 10px; text-align: center; font-weight: bold; }
    .quality-excellent { background: linear-gradient(135deg, #1f4f2b, #2e7d32); color: white; }
    .quality-good { background: linear-gradient(135deg, #1f3a4f, #1565c0); color: white; }
    .quality-normal { background: linear-gradient(135deg, #4a4a4a, #616161); color: white; }
    .imminent-badge { background: linear-gradient(135deg, #ff8f00, #ff6f00); color: white; padding: 5px 10px; border-radius: 10px; margin-bottom: 10px; text-align: center; font-weight: bold; }
    .support-badge-at { background: linear-gradient(135deg, #00c853, #69f0ae); color: #1a1a2e; padding: 5px 10px; border-radius: 10px; margin-bottom: 10px; text-align: center; font-weight: bold; }
    .support-badge-near { background: linear-gradient(135deg, #ff8f00, #ff6f00); color: white; padding: 5px 10px; border-radius: 10px; margin-bottom: 10px; text-align: center; font-weight: bold; }
    .bounce-badge { background: linear-gradient(135deg, #2196f3, #00bcd4); color: white; padding: 5px 10px; border-radius: 10px; margin-bottom: 10px; text-align: center; font-weight: bold; }
    .momentum-badge { background: linear-gradient(135deg, #9c27b0, #e040fb); color: white; padding: 5px 10px; border-radius: 10px; margin-bottom: 10px; text-align: center; font-weight: bold; }
    .warning-box { background-color: rgba(248, 81, 73, 0.15); border-right: 4px solid #f85149; padding: 10px; border-radius: 8px; margin: 10px 0; }
    .success-box { background-color: rgba(63, 185, 80, 0.15); border-right: 4px solid #3fb950; padding: 10px; border-radius: 8px; margin: 10px 0; }
    .info-box { background-color: rgba(88, 166, 255, 0.15); border-right: 4px solid #58a6ff; padding: 10px; border-radius: 8px; margin: 10px 0; }
    </style>
    """, unsafe_allow_html=True)

# ================== HELPERS ==================
def get_rr_rating(rr):
    if rr < 1: return "❌ ضعيف", "RR سيء - مخاطرة أعلى من العائد"
    elif rr < 1.5: return "⚠️ متوسط", "مضاربة سريعة فقط"
    elif rr < 2: return "✅ جيد", "صفقة كويسة"
    else: return "🔥 ممتاز", "فرصة قوية جداً"

def get_volume_rating(ratio):
    if ratio == 0: return "❓ غير معروف", "لا توجد بيانات سيولة كافية"
    elif ratio < 1: return "❄️ ضعيفة", "مفيش سيولة كفاية"
    elif ratio < 1.5: return "🙂 عادية", "سيولة طبيعية"
    elif ratio < 2: return "⚡ نشطة", "في اهتمام بالسهم"
    else: return "🚀 قوية", "سيولة عالية واختراق محتمل"

def get_rsi_signal(rsi):
    if rsi < 30: return "🟢 تشبع بيع (فرصة انعكاس)", "oversold"
    elif rsi < 50: return "🟡 ضعيف", "weak"
    elif rsi < 65: return "🟢 زخم صحي", "good"
    elif rsi < 75: return "⚠️ قرب تشبع شراء", "caution"
    else: return "🔴 تشبع شراء خطر", "overbought"

# ================== 🛡️ CLASSIFY STOCK ==================
def classify_stock(res):
    if res is None:
        return "weak"
    
    rr = res.get('rr', 0) if res.get('rr') is not None else 0
    ratio = res.get('ratio', 0) if res.get('ratio') is not None else 0
    t_short = res.get('t_short', 'هابط') if res.get('t_short') is not None else 'هابط'
    t_med = res.get('t_med', 'هابط') if res.get('t_med') is not None else 'هابط'
    rsi = res.get('rsi', 50) if res.get('rsi') is not None else 50
    smart_score = res.get('smart_score', 0) if res.get('smart_score') is not None else 0
    change_pct = res.get('chg', 0) if res.get('chg') is not None else 0
    mode = st.session_state.mode if hasattr(st.session_state, 'mode') else "⚖️ متوازن"
    
    if change_pct > 3 and ratio < 1.5:
        return "weak"
    
    if "محافظ" in mode:
        rr_min = 1.5
        rr_gold = 2.0
    elif "هجومي" in mode:
        rr_min = 1.0
        rr_gold = 1.8
    else:
        rr_min = 1.3
        rr_gold = 2.0
    
    if ratio == 0:
        return "watchlist"
    
    if (rr >= rr_gold and 
        t_short == "صاعد" and 
        t_med == "صاعد" and 
        45 < rsi < 60 and 
        ratio > 1.5 and
        smart_score >= 70):
        return "gold"
    
    if ratio > 2.5 and t_short == "صاعد" and rsi < 70:
        return "breakout"
    
    if ratio > 1.8 and rr >= 1.3 and rsi < 75:
        return "scalp"
    
    if rr >= rr_min and ratio > 1.2:
        return "watchlist"
    
    return "weak"

def check_gold_rarity(results):
    if not results:
        return 0, 0, "لا توجد بيانات"
    
    gold_count = 0
    for an in results:
        if an is not None and classify_stock(an) == "gold":
            gold_count += 1
    
    total = len([r for r in results if r is not None])
    gold_percentage = (gold_count / total * 100) if total > 0 else 0
    
    if gold_count == 0:
        rarity_status = "❄️ نادر جداً (لا توجد فرص ذهبية)"
    elif gold_count <= 3:
        rarity_status = "✅ ممتاز - نادر كما يجب"
    elif gold_count <= 6:
        rarity_status = "⚠️ متوسط - قد يكون الفلتر قاسي قليلاً"
    else:
        rarity_status = "🔴 كثير - الفلتر ضعيف ويحتاج تشديد"
    
    return gold_count, gold_percentage, rarity_status

def get_confidence_score(res):
    if res is None:
        return 0
    smart = res.get('smart_score', 0) if res.get('smart_score') is not None else 0
    exec_strength = res.get('execution_strength', 0) if res.get('execution_strength') is not None else 0
    return int((smart + exec_strength) / 2)

def get_momentum_score(res):
    if res is None:
        return 50
    sma20 = res.get('sma20', res.get('p', 0))
    p = res.get('p', 0) if res.get('p') is not None else 0
    if sma20 and sma20 > 0:
        momentum = (p - sma20) / sma20
        if momentum > 0.05: return 80
        elif momentum > 0.02: return 60
        elif momentum > 0: return 40
        elif momentum > -0.02: return 20
        else: return 10
    return 50

def is_perfect_setup(res):
    if res is None:
        return False
    return (res.get('t_short') == "صاعد" and
            res.get('t_med') == "صاعد" and
            res.get('ratio', 0) > 2 and
            45 < res.get('rsi', 50) < 60 and
            res.get('rr', 0) >= 2)

def is_real_breakout(res):
    if res is None:
        return False
    return (res.get('ratio', 0) > 2.5 and 
            res.get('t_short') == "صاعد" and 
            res.get('t_med') == "صاعد" and
            40 < res.get('rsi', 50) < 70)

# ================== SESSION STATE ==================
if "mode" not in st.session_state:
    st.session_state.mode = "⚖️ متوازن"
if 'page' not in st.session_state: 
    st.session_state.page = 'home'

if "market_data" not in st.session_state:
    st.session_state.market_data = None
if "all_results" not in st.session_state:
    st.session_state.all_results = None

def render_mode_selector():
    with st.expander("🧠 اختر نوع التداول", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🛡️ محافظ"): st.session_state.mode = "🛡️ محافظ (محترف)"
        with col2:
            if st.button("⚖️ متوازن"): st.session_state.mode = "⚖️ متوازن"
        with col3:
            if st.button("🚀 هجومي"): st.session_state.mode = "🚀 هجومي"
    mode = st.session_state.mode
    color = "#238636" if "محافظ" in mode else "#f85149" if "هجومي" in mode else "#d29922"
    icon = "🛡️" if "محافظ" in mode else "🚀" if "هجومي" in mode else "⚖️"
    st.markdown(f"""
    <div style="background:{color}; padding:10px; border-radius:10px; text-align:center; font-weight:bold; margin-top:10px; color:white; margin-bottom: 20px;">
        🎯 النمط الحالي: {icon} {mode}
    </div>
    """, unsafe_allow_html=True)

# ================== DATA & ANALYSIS ENGINE ==================
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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Origin": "https://www.tradingview.com",
        "Referer": "https://www.tradingview.com/"
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if r.status_code != 200:
            st.error(f"⚠️ خطأ في API: Status {r.status_code}")
            return []
        
        data = r.json()
        return data.get("data", [])
    except Exception as e:
        st.error(f"⚠️ فشل الاتصال بـ TradingView: {e}")
        return []

def fetch_single_stock(symbol):
    url = "https://scanner.tradingview.com/egypt/scan"
    cols = ["name","close","RSI","volume","average_volume_10d_calc","high","low","change","description","SMA20","SMA50","SMA200"]
    
    payload1 = {
        "filter": [{"left": "name", "operation": "equal", "right": symbol.upper()}],
        "columns": cols,
        "range": [0, 1]
    }
    
    payload2 = {
        "filter": [{"left": "name", "operation": "match", "right": symbol.upper()}],
        "columns": cols,
        "range": [0, 1]
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        r1 = requests.post(url, json=payload1, headers=headers, timeout=20)
        if r1.status_code == 200:
            data = r1.json()
            results = data.get("data", [])
            if results and len(results) > 0:
                return results
        
        r2 = requests.post(url, json=payload2, headers=headers, timeout=20)
        if r2.status_code == 200:
            data = r2.json()
            results = data.get("data", [])
            if results and len(results) > 0:
                return results
        
        return []
    except Exception as e:
        print(f"API Error: {e}")
        return []

def analyze_stock(d_row):
    try:
        d = d_row.get('d', [])
        
        if len(d) != 12:
            return None
        
        name, p, rsi, v, avg_v, h, l, chg, desc, sma20, sma50, sma200 = d
        if p is None: return None
        
        if not desc or desc == "":
            desc = name
        
        rsi_val = rsi or 0
        
        if avg_v and avg_v > 0:
            ratio = v / avg_v
        else:
            ratio = 0
        
        t_short = "صاعد" if (sma20 and p > sma20) else "هابط"
        t_med = "صاعد" if (sma50 and p > sma50) else "هابط"
        t_long = "صاعد" if (sma200 and p > sma200) else "هابط"
        entry_min = p * 0.98
        entry_max = p * 1.01
        entry_price = (entry_min + entry_max) / 2
        pp = (p + (h or p) + (l or p)) / 3
        s1, r1 = (2 * pp) - (h or p), (2 * pp) - (l or p)
        s2, r2 = pp - ((h or p) - (l or p)), pp + ((h or p) - (l or p))
        stop_loss = min(s2, entry_price * 0.97)
        target = max(r1, entry_price * 1.05)
        profit_ps = target - entry_price
        loss_ps = entry_price - stop_loss
        if loss_ps <= 0: return None
        rr = round(profit_ps / loss_ps, 2)
        
        if rr >= 2 and t_short == "صاعد" and t_med == "صاعد" and rsi_val < 70:
            signal, sig_cls = "شراء قوي 🔥", "buy-strong"
        elif ratio > 2 and t_short == "صاعد" and rsi_val < 75:
            signal, sig_cls = "اختراق قوي 🚀", "buy-strong"
        elif ratio > 1.5 and rr >= 1.2 and rsi_val < 75:
            signal, sig_cls = "فرصة مضاربية ⚡", "buy-caution"
        elif rr >= 1.2 and rsi_val < 70:
            signal, sig_cls = "شراء حذر ⚠️", "buy-caution"
        else:
            signal, sig_cls = "انتظار ⏳", "wait"
        
        temp_res = {
            't_short': t_short, 't_med': t_med, 't_long': t_long,
            'ratio': ratio, 'rsi': rsi_val, 'rr': rr
        }
        smart_score = smart_score_pro(temp_res)
        
        execution_strength = 0
        entry_proximity = abs(p - entry_price) / entry_price
        if entry_proximity < 0.005:
            execution_strength += 25
        elif entry_proximity < 0.01:
            execution_strength += 15
        elif entry_proximity < 0.02:
            execution_strength += 8
        
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
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "signal": signal, "sig_cls": sig_cls, "t_short": t_short, "t_med": t_med, "t_long": t_long,
            "s1": s1, "s2": s2, "r1": r1, "r2": r2, "pp": pp, "sma20": sma20, "sma50": sma50,
            "entry_range": f"{entry_min:.2f} - {entry_max:.2f}", "entry_price": entry_price,
            "stop_loss": stop_loss, "target": target, "rr": rr, "risk_pct": (loss_ps/entry_price)*100, 
            "target_pct": (profit_ps/entry_price)*100, "score": int((min(ratio, 2) if ratio > 0 else 0) * 20 + (rsi_val / 2 if rsi_val else 25)),
            "smart_score": smart_score,
            "execution_strength": execution_strength
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

def get_fresh_data():
    with st.spinner("🔄 جاري تحميل بيانات السوق..."):
        raw_data = get_all_data()
        if raw_data:
            st.session_state.market_data = raw_data
            st.session_state.all_results = preprocess_all_data(raw_data)
            return True
        return False

# ================== UI RENDERER ==================
def render_stock_ui(res, is_top10=False, is_gold=False):
    if res is None:
        st.warning("بيانات السهم غير متوفرة")
        return
    
    st.markdown(f"""
    <div class='stock-header'>
        {res.get('name', 'N/A')} - {res.get('desc', 'N/A')}
        <span class='score-tag'>Score: {res.get('score', 0)}</span>
    </div>
    """, unsafe_allow_html=True)
    
    if is_top10:
        quality = get_quality_rating(res, "top10")
        if "الأفضل" in quality:
            st.markdown(f'<div class="quality-badge quality-excellent">🏆 {quality}</div>', unsafe_allow_html=True)
        elif "ممتاز" in quality:
            st.markdown(f'<div class="quality-badge quality-good">⭐ {quality}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="quality-badge quality-normal">📌 {quality}</div>', unsafe_allow_html=True)
    elif is_gold:
        quality = get_quality_rating(res, "gold")
        if "ممتاز" in quality:
            st.markdown(f'<div class="quality-badge quality-excellent">💎 {quality}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="quality-badge quality-good">💎 {quality}</div>', unsafe_allow_html=True)
    
    if is_real_breakout(res):
        st.markdown('<div class="real-breakout">✅ اختراق حقيقي - سيولة عالية واتجاه قوي</div>', unsafe_allow_html=True)
    
    if is_perfect_setup(res):
        st.markdown('<div class="premium-badge">💎 PERFECT SETUP - فرصة مثالية</div>', unsafe_allow_html=True)
    
    ratio = res.get('ratio', 0) if res.get('ratio') is not None else 0
    if ratio > 2.5:
        st.warning("🚨 اختراق قوي جداً - سيولة استثنائية")
    elif ratio > 3:
        st.error("🔥 اختراق خرافي - انتباه شديد")
    
    st.markdown("### 📊 خلاصة")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("السعر", f"{res.get('p', 0):.2f}", f"{res.get('chg', 0):.1f}%")
    with c2:
        st.metric("Smart", f"{res.get('smart_score', 0)}/100")
    with c3:
        st.metric("RR", res.get('rr', 0))
    with c4:
        st.metric("RSI", f"{res.get('rsi', 0):.0f}")
    
    smart_score = res.get('smart_score', 0) if res.get('smart_score') is not None else 0
    rr = res.get('rr', 0) if res.get('rr') is not None else 0
    rsi = res.get('rsi', 50) if res.get('rsi') is not None else 50
    
    if smart_score >= 70 and rr >= 1.5 and 45 < rsi < 65:
        st.success("🟢 إشارة شراء قوية")
    elif smart_score >= 50 and rr >= 1.2:
        st.warning("🟡 إشارة مراقبة")
    else:
        st.error("🔴 إشارة تجنب")
    
    st.markdown("---")
    
    whatsapp_url = share_on_whatsapp(res)
    st.markdown(f"""
    <div style="margin-bottom: 15px;">
        <a href="{whatsapp_url}" target="_blank" class="whatsapp-btn" style="display: block; text-align: center; background-color: #25D366; color: white; padding: 10px; border-radius: 12px; text-decoration: none; font-weight: bold;">
            📱 مشاركة التحليل عبر واتساب
        </a>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("📊 التحليل الفني", expanded=True):
        st.markdown("### 📈 شارت السهم (بيانات حية من السوق)")
        render_tradingview_chart(res.get('name', 'EGX30'), height=450)
        
        t_short_c = "trend-up" if res.get('t_short') == "صاعد" else "trend-down"
        t_med_c = "trend-up" if res.get('t_med') == "صاعد" else "trend-down"
        t_long_c = "trend-up" if res.get('t_long') == "صاعد" else "trend-down"
        st.markdown(f"""
        <div style='margin-bottom: 15px;'>
            <span class='trend-pill {t_short_c}'>قصير: {res.get('t_short', 'هابط')}</span>
            <span class='trend-pill {t_med_c}'>متوسط: {res.get('t_med', 'هابط')}</span>
            <span class='trend-pill {t_long_c}'>طويل: {res.get('t_long', 'هابط')}</span>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"<span class='signal-pill {res.get('sig_cls', 'wait')}'>{res.get('signal', 'انتظار')}</span>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            vol_label, vol_desc = get_volume_rating(ratio)
            st.metric("نشاط السيولة", f"{ratio:.1f}x", vol_label)
            st.caption(f"📊 {vol_desc}")
        with col2:
            rr_label, rr_desc = get_rr_rating(rr)
            st.metric("R/R Ratio", f"{rr}", rr_label)
            st.caption(f"🧠 {rr_desc}")
        
        rsi_label, _ = get_rsi_signal(rsi)
        st.metric("RSI", f"{rsi:.1f}", rsi_label)
        
        roc = calculate_roc(res.get('p', 0), res.get('sma20', res.get('p', 0)))
        roc_color = "🟢" if roc > 0 else "🔴"
        st.metric("ROC (معدل التغير)", f"{roc_color} {roc:+.1f}%")
        
        st.markdown("### 🏛️ مستويات الدعم والمقاومة (للمستثمر طويل الأجل)")
        st.markdown(f"""
        | المستوى | السعر | الدلالة |
        |---------|-------|---------|
        | 🔴 **مقاومة ثانية R2** | {res.get('r2', 0):.2f} | مقاومة قوية |
        | 🔴 **مقاومة أولى R1** | {res.get('r1', 0):.2f} | مقاومة أولى |
        | 🟡 **نقطة الارتكاز PP** | {res.get('pp', 0):.2f} | المحور |
        | 🟢 **دعم أول S1** | {res.get('s1', 0):.2f} | دعم أول |
        | 🟢 **دعم ثاني S2** | {res.get('s2', 0):.2f} | دعم قوي |
        """)
        
        st.markdown(f"""
        <div class='entry-card-new'>
            🎯 <b>نطاق الدخول (مضاربة/سوينج):</b> {res.get('entry_range', 'N/A')}<br>
            🛑 <b>وقف الخسارة:</b> {res.get('stop_loss', 0):.2f} <span style='color:#f85149'>(-{res.get('risk_pct', 0):.1f}%)</span><br>
            🏁 <b>المستهدف:</b> {res.get('target', 0):.2f} <span style='color:#58a6ff'>(+{res.get('target_pct', 0):.1f}%)</span>
        </div>
        """, unsafe_allow_html=True)
    
    with st.expander("💰 إدارة المخاطر وخطة الدخول", expanded=False):
        deal_size = st.number_input("💰 ميزانية الصفقة (ج)", value=10000, step=1000, key=f"deal_{res.get('name', 'stock')}")
        entry_price = res.get('entry_price', 0)
        
        if deal_size > 0 and entry_price > 0:
            shares_deal = int(deal_size / entry_price)
            actual_value = shares_deal * entry_price
            profit_val = (res.get('target', 0) - entry_price) * shares_deal
            loss_val = (entry_price - res.get('stop_loss', 0)) * shares_deal
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("📦 عدد الأسهم", f"{shares_deal:,}")
                st.metric("💰 قيمة الصفقة", f"{actual_value:,.0f} ج")
            with col2:
                st.metric("🟢 الربح المتوقع", f"{profit_val:,.0f} ج", delta=f"+{res.get('target_pct', 0):.1f}%")
                st.metric("🔴 الخسارة المحتملة", f"{loss_val:,.0f} ج", delta=f"-{res.get('risk_pct', 0):.1f}%")
            
            st.markdown("### 🏹 خطة الدخول")
            
            range_size = res.get('entry_price', 0) - res.get('stop_loss', 0)
            
            entry_level_1 = res.get('entry_price', 0)
            entry_level_2 = max(res.get('entry_price', 0) - (range_size * 0.5), res.get('stop_loss', 0) * 1.02)
            entry_level_3 = res.get('entry_price', 0) + (res.get('target', 0) - res.get('entry_price', 0)) * 0.3
            
            if res.get('rr', 0) >= 2:
                weights = [0.6, 0.25, 0.15]
            elif res.get('rr', 0) >= 1.5:
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
            <div style='background:#0d1117;border:1px solid #30363d;border-radius:10px;padding:15px;margin:10px 0;'>
                <b>📌 المستوى الأول - الدخول الأساسي</b><br>
                🟢 السعر: <b>{entry_level_1:.2f}</b> ج<br>
                📦 الكمية: <b>{shares_1:,}</b> سهم | 💰 المبلغ: <b>{amount_1:,.0f}</b> ج ({weights[0]*100:.0f}% من الميزانية)<br>
                <small>🔹 يتم التنفيذ عند وصول السعر للنطاق</small>
            </div>
            
            <div style='background:#0d1117;border:1px solid #30363d;border-radius:10px;padding:15px;margin:10px 0;'>
                <b>📌 المستوى الثاني - تعزيز الدعم</b><br>
                🟡 السعر: <b>{entry_level_2:.2f}</b> ج<br>
                📦 الكمية: <b>{shares_2:,}</b> سهم | 💰 المبلغ: <b>{amount_2:,.0f}</b> ج ({weights[1]*100:.0f}% من الميزانية)<br>
                <small>🔹 يتم التنفيذ إذا هبط السعر للدعم دون كسر الوقف</small>
            </div>
            
            <div style='background:#0d1117;border:1px solid #30363d;border-radius:10px;padding:15px;margin:10px 0;'>
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
        
        st.markdown("---")
        st.markdown("### 🎯 وقف الخسارة المتحرك")
        current_price_trail = st.number_input("السعر الحالي", value=res.get('p', 0), key=f"trail_price_{res.get('name', 'stock')}")
        highest_price_trail = st.number_input("أعلى سعر تم الوصول إليه", value=res.get('p', 0), key=f"highest_{res.get('name', 'stock')}")
        trailing_stop = calculate_trailing_stop(res.get('entry_price', 0), current_price_trail, highest_price_trail, res.get('rr', 0))
        st.info(f"🛡️ **وقف الخسارة المتحرك المقترح:** {trailing_stop:.2f} ج (الأصلي: {res.get('stop_loss', 0):.2f} ج)")
        
        st.warning("⚠️ **تذكير:** هذه الخطة استرشادية. القرار النهائي يعتمد على تحليلك الشخصي وظروف السوق.")
    
    with st.expander("🧠 تحليل الوضع الحالي", expanded=False):
        col1, col2 = st.columns(2)
        buy_price = col1.number_input("سعر الشراء", value=res.get('p', 0), key=f"buy_{res.get('name', 'stock')}")
        qty = col2.number_input("الكمية", value=100, step=1, key=f"qty_{res.get('name', 'stock')}")
        
        if qty > 0 and buy_price > 0:
            current_price = res.get('p', 0)
            pnl = (current_price - buy_price) * qty
            pnl_pct = ((current_price - buy_price) / buy_price) * 100
            
            if pnl > 0:
                st.success(f"🟢 كسبان: {pnl:,.0f} ج (+{pnl_pct:.2f}%)")
                if pnl_pct >= 3:
                    st.info(f"💡 حرك الوقف لنقطة الدخول: {buy_price:.2f}")
            elif pnl < 0:
                st.error(f"🔴 خسران: {pnl:,.0f} ج ({pnl_pct:.2f}%)")
            else:
                st.info("⚖️ على التعادل")
            
            if current_price >= res.get('target', 0):
                st.success("🎉 تم تحقيق الهدف!")
            elif current_price <= res.get('stop_loss', 0):
                st.error("⚠️ كسر وقف الخسارة!")
            
            trend_score = (1 if res.get('t_short') == "صاعد" else 0) + (1 if res.get('t_med') == "صاعد" else 0) + (1 if res.get('ratio', 0) > 1.5 else 0)
            if trend_score >= 2:
                st.success(f"✅ استمر طالما السعر فوق {res.get('stop_loss', 0):.2f}")
            else:
                st.warning("⚠️ اتجاه ضعيف - فكر في تأمين الأرباح")
    
    with st.expander("📈 مؤشرات متقدمة", expanded=False):
        stoch = calculate_stochastic_rsi(rsi)
        st.markdown(f"""
        <div style='background:#161b22;border:1px solid #30363d;border-radius:10px;padding:15px;margin-bottom:15px;'>
            <b>🔄 Stochastic RSI</b><br>
            📈 K={stoch['k']:.1f} | D={stoch['d']:.1f}<br>
            🧠 {stoch['signal']}
        </div>
        """, unsafe_allow_html=True)
        
        success_rate, success_level = expected_success_rate(res)
        st.markdown(f"""
        <div style='background:#161b22;border:1px solid #d29922;border-radius:10px;padding:15px;margin-bottom:15px;'>
            <b>📈 نسبة النجاح المتوقعة</b><br>
            🎯 <b>{success_rate}%</b> - {success_level}
        </div>
        """, unsafe_allow_html=True)
        
        smart_text, _ = smart_decision(res)
        st.markdown(f"""
        <div style='background:#161b22;border:1px solid #30363d;border-radius:10px;padding:15px;'>
            🤖 <b>Smart Score:</b> {res.get('smart_score', 0)}/100<br>
            ⚡ <b>قوة التنفيذ:</b> {res.get('execution_strength', 0)}/100<br>
            📊 <b>الثقة:</b> {get_confidence_score(res)}/100<br>
            🚀 <b>Momentum:</b> {get_momentum_score(res)}/100<br>
            🎯 {smart_text}
        </div>
        """, unsafe_allow_html=True)


# ================== NAVIGATION ==================
if st.session_state.market_data is None:
    get_fresh_data()

if st.session_state.page == 'home':
    st.title("🏹 EGX Sniper Pro v17.5")
    
    render_mode_selector()
    
    st.markdown("### 🎯 ابدأ هنا")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔍 أفضل 10 فرص اليوم", use_container_width=True):
            st.session_state.page = 'top10'
            st.rerun()
        st.caption("أقوى الفرص بناءً على Smart Score")
    with col2:
        if st.button("📊 تحليل سهم", use_container_width=True):
            st.session_state.page = 'analyze'
            st.rerun()
        st.caption("أدخل رمز السهم للتحليل المفصل")
    
    with st.expander("🛠️ أدوات متقدمة", expanded=False):
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            if st.button("💎 الفرص الذهبية"):
                st.session_state.page = 'gold'
                st.rerun()
        with col2:
            if st.button("🚀 الاختراقات"):
                st.session_state.page = 'breakout'
                st.rerun()
        with col3:
            if st.button("⚡ مضاربات سريعة"):
                st.session_state.page = 'scalp'
                st.rerun()
        with col4:
            if st.button("🔭 كشاف السوق"):
                st.session_state.page = 'scanner'
                st.rerun()
        with col5:
            if st.button("⚡ اختراقات وشيكة"):
                st.session_state.page = 'imminent'
                st.rerun()
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            if st.button("🔻 دعم وارتداد"):
                st.session_state.page = 'support_bounce'
                st.rerun()
    
    with st.expander("⚙️ إدارة التطبيق", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📊 تقييم الأداء"):
                st.session_state.page = 'performance'
                st.rerun()
        with col2:
            if st.button("📖 دليل المؤشرات"):
                st.session_state.page = 'guide'
                st.rerun()
        with col3:
            if st.button("🔄 تحديث البيانات"):
                get_fresh_data()
                st.success("✅ تم تحديث البيانات!")
                st.rerun()
        with col1:
            if st.button("🧮 حاسبة المتوسط"):
                st.session_state.page = 'avg'
                st.rerun()
    
    with st.expander("⚠️ أدوات خطيرة", expanded=False):
        if st.button("🗑️ إعادة ضبط جميع بيانات التقييم", use_container_width=True):
            if os.path.exists(TRADES_FILE):
                os.remove(TRADES_FILE)
                st.success("✅ تم مسح جميع بيانات التقييم! سيتم البدء من جديد")
                st.rerun()
            else:
                st.info("لا توجد بيانات للمسح")
    
    if st.session_state.all_results:
        gold_count, gold_percentage, rarity_status = check_gold_rarity(st.session_state.all_results)
        st.markdown("---")
        st.markdown(f"### 💎 إحصائية الفرص الذهبية")
        col1, col2, col3 = st.columns(3)
        col1.metric("عدد الفرص الذهبية", gold_count)
        col2.metric("نسبة الذهب من السوق", f"{gold_percentage:.1f}%")
        col3.markdown(f"**الحالة:** {rarity_status}")

# ================== 🆕 صفحة دعم وارتداد (مُصَححة - بدون تكرار) ==================
elif st.session_state.page == 'support_bounce':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    render_mode_selector()
    
    st.title("🔻 فرص الدعم والارتداد - مع فلاتر الجودة v17.5")
    st.markdown("""
    <div class='info-box'>
    📌 <b>تم الإصلاح في v17.5:</b><br>
    • <b>✓ لا تكرار:</b> الأسهم التي تظهر في "مؤكد الارتداد" لا تظهر في "قريبة من الدعم"<br>
    • <b>نظام Bounce Score:</b> 5 عوامل (مطلوب 3+ نقاط للدخول)<br>
    • <b>مسافة دعم موسعة:</b> 1.5% (3 مستويات) مناسبة للسوق المصري
    </div>
    """, unsafe_allow_html=True)
    
    if not st.session_state.all_results:
        st.error("⚠️ لا توجد بيانات. اضغط على 'تحديث البيانات' في الصفحة الرئيسية.")
        st.stop()
    
    tab1, tab2, tab3 = st.tabs(["📏 قريبة من الدعم (مراقبة)", "📈 مؤكد الارتداد (دخول)", "⚡ زخم إيجابي عند الدعم"])
    
    # ================== التبويب 1: قريبة من الدعم (بدون تكرار) ==================
    with tab1:
        st.markdown("### 📏 الأسهم القريبة من الدعم - مراقبة فقط")
        st.markdown("""
        <div class='warning-box'>
        ⚠️ <b>تنبيه مهم:</b> هذه الأسهم <b>لم تثبت الارتداد بعد</b> (نقاط أقل من 3/5).
        <br>✅ انتظر حتى تظهر في التبويب "مؤكد الارتداد" قبل الدخول.
        <br>📌 <b>ملاحظة:</b> الأسهم التي ظهرت في تبويب "مؤكد الارتداد" لا تظهر هنا.
        </div>
        """, unsafe_allow_html=True)
        
        # ✅ الخطوة 1: تحديد الأسهم التي حققت ارتداداً (لنستبعدها من التبويب 1)
        bounce_symbols = set()
        for an in st.session_state.all_results:
            if an:
                is_bounce, _, _, bounce_score = is_near_support_with_bounce(an, mode="bounce")
                if is_bounce and bounce_score >= 3:
                    bounce_symbols.add(an.get('name'))
        
        # ✅ الخطوة 2: جلب الأسهم القريبة من الدعم مع استبعاد أسهم الارتداد
        support_stocks = []
        for an in st.session_state.all_results:
            if an and an.get('name') not in bounce_symbols:
                is_support, reasons, level, _ = is_near_support_with_bounce(an, mode="near")
                if is_support:
                    quality_rating = get_support_quality_rating(an, level, mode="near")
                    support_stocks.append({
                        'stock': an, 
                        'reasons': reasons, 
                        'level': level,
                        'quality': quality_rating
                    })
        
        excellent_count = len([s for s in support_stocks if "ممتاز" in s['quality']])
        good_count = len([s for s in support_stocks if "جيد" in s['quality']])
        normal_count = len([s for s in support_stocks if "عادي" in s['quality'] or "للمتابعة" in s['quality']])
        
        st.markdown("---")
        col_filter1, col_ex1, col_go1, col_no1 = st.columns([2, 1, 1, 1])
        with col_filter1:
            filter_option = st.radio(
                "🔍 فلتر الجودة:",
                ["📋 الكل", "🔥 ممتاز", "✅ جيد", "📌 للمتابعة"],
                key="filter_support"
            )
        with col_ex1:
            st.metric("🔥 ممتاز", excellent_count)
        with col_go1:
            st.metric("✅ جيد", good_count)
        with col_no1:
            st.metric("📌 للمتابعة", normal_count)
        
        st.markdown("---")
        
        filtered_stocks = support_stocks
        if filter_option == "🔥 ممتاز":
            filtered_stocks = [s for s in support_stocks if "ممتاز" in s['quality']]
        elif filter_option == "✅ جيد":
            filtered_stocks = [s for s in support_stocks if "جيد" in s['quality']]
        elif filter_option == "📌 للمتابعة":
            filtered_stocks = [s for s in support_stocks if "عادي" in s['quality'] or "للمتابعة" in s['quality']]
        
        if filtered_stocks:
            st.markdown(f"**عدد الأسهم القريبة من الدعم: {len(filtered_stocks)}**")
            for item in filtered_stocks:
                an = item['stock']
                reasons = item['reasons']
                level = item['level']
                quality = item['quality']
                
                if level == "عند الدعم":
                    badge_color = "support-badge-at"
                    badge_text = "📍 عند الدعم (0-0.5%)"
                elif level == "قريب جداً":
                    badge_color = "support-badge-near"
                    badge_text = "📏 قريب جداً (0.5-1.0%)"
                else:
                    badge_color = "support-badge-near"
                    badge_text = "📏 قريب نسبياً (1.0-1.5%)"
                
                if "ممتاز" in quality:
                    quality_class = "quality-excellent"
                elif "جيد" in quality:
                    quality_class = "quality-good"
                else:
                    quality_class = "quality-normal"
                
                st.markdown(f"""
                <div style='background:#0d1117;border:2px solid #ff8f00;border-radius:12px;padding:15px;margin-bottom:15px;'>
                    <div style='display:flex;justify-content:space-between;align-items:center;'>
                        <h3 style='color:#ff8f00;margin:0'>🔻 {an['name']} - {an['desc']}</h3>
                        <span class='{badge_color}'>{badge_text}</span>
                    </div>
                    <div class='quality-badge {quality_class}' style='margin-top:10px;'>⭐ {quality}</div>
                    <div style='margin-top:10px;'>
                        <b>📊 المعطيات:</b><br>
                        • السعر: {an['p']:.2f} ج | الدعم S1: {an['s1']:.2f} ج<br>
                        • RSI: {an['rsi']:.1f} | السيولة: {an['ratio']:.1f}x<br>
                        • التغير: {an['chg']:+.2f}% | Smart Score: {an['smart_score']}/100
                    </div>
                    <div style='margin-top:10px;'>
                        <b>📌 حالة الاقتراب من الدعم:</b>
                        {"".join([f'<div style="color:#ff8f00;">{r}</div>' for r in reasons[:4]])}
                    </div>
                    <div class='warning-box' style='margin-top:10px;'>
                        ⚠️ <b>مراقبة فقط</b> - لم يثبت الارتداد بعد
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"📊 تحليل {an['name']} بالتفصيل", key=f"support_{an['name']}"):
                    render_stock_ui(an)
        else:
            st.info("لا توجد أسهم قريبة من الدعم (غير المرتدة) تطابق الفلتر المختار.")
    
    # ================== التبويب 2: مؤكد الارتداد ==================
    with tab2:
        st.markdown("### 📈 الأسهم التي حققت ارتداداً حقيقياً - صالحة للدخول")
        st.markdown("""
        <div class='success-box'>
        ✅ <b>ارتداد حقيقي محتمل</b> - السهم حقق 3+ نقاط من 5 في نظام التقييم.
        <br>🎯 مناسب للدخول مع وقف خسارة أسفل الدعم مباشرة.
        <br>⚠️ <b>تنبيه:</b> يتم استبعاد الأسهم التي ارتفعت أكثر من 4% (فاتك القطار).
        </div>
        """, unsafe_allow_html=True)
        
        bounce_stocks = []
        for an in st.session_state.all_results:
            if an:
                is_bounce, reasons, level, bounce_score = is_near_support_with_bounce(an, mode="bounce")
                if is_bounce and bounce_score >= 3:
                    quality_rating = get_support_quality_rating(an, level, mode="bounce", bounce_score=bounce_score)
                    bounce_stocks.append({
                        'stock': an, 
                        'reasons': reasons, 
                        'level': level,
                        'quality': quality_rating,
                        'bounce_score': bounce_score
                    })
        
        excellent_count = len([s for s in bounce_stocks if "ممتاز" in s['quality']])
        good_count = len([s for s in bounce_stocks if "جيد" in s['quality']])
        normal_count = len([s for s in bounce_stocks if "للمتابعة" in s['quality']])
        
        st.markdown("---")
        col_filter2, col_ex2, col_go2, col_no2 = st.columns([2, 1, 1, 1])
        with col_filter2:
            filter_option = st.radio(
                "🔍 فلتر الجودة:",
                ["📋 الكل", "🔥 ممتاز", "✅ جيد", "📌 للمتابعة"],
                key="filter_bounce"
            )
        with col_ex2:
            st.metric("🔥 ممتاز", excellent_count)
        with col_go2:
            st.metric("✅ جيد", good_count)
        with col_no2:
            st.metric("📌 للمتابعة", normal_count)
        
        st.markdown("---")
        
        filtered_stocks = bounce_stocks
        if filter_option == "🔥 ممتاز":
            filtered_stocks = [s for s in bounce_stocks if "ممتاز" in s['quality']]
        elif filter_option == "✅ جيد":
            filtered_stocks = [s for s in bounce_stocks if "جيد" in s['quality']]
        elif filter_option == "📌 للمتابعة":
            filtered_stocks = [s for s in bounce_stocks if "للمتابعة" in s['quality']]
        
        if filtered_stocks:
            st.markdown(f"**عدد الأسهم ذات الارتداد الحقيقي: {len(filtered_stocks)}**")
            for item in filtered_stocks:
                an = item['stock']
                reasons = item['reasons']
                quality = item['quality']
                bounce_score = item['bounce_score']
                
                nearest_support = an['s1'] if an['s1'] > 0 else an['s2']
                risk_percent = (an['p'] - nearest_support) / an['p'] * 100 if nearest_support > 0 else 0
                
                if "ممتاز" in quality:
                    quality_class = "quality-excellent"
                elif "جيد" in quality:
                    quality_class = "quality-good"
                else:
                    quality_class = "quality-normal"
                
                st.markdown(f"""
                <div style='background:#0d1117;border:2px solid #3fb950;border-radius:12px;padding:15px;margin-bottom:15px;'>
                    <div style='display:flex;justify-content:space-between;align-items:center;'>
                        <h3 style='color:#3fb950;margin:0'>📈 {an['name']} - {an['desc']}</h3>
                        <span class='bounce-badge'>✅ ارتداد حقيقي ({bounce_score}/5)</span>
                    </div>
                    <div class='quality-badge {quality_class}' style='margin-top:10px;'>⭐ {quality}</div>
                    <div style='margin-top:10px;'>
                        <b>📊 المعطيات:</b><br>
                        • السعر: {an['p']:.2f} ج | الدعم S1: {an['s1']:.2f} ج<br>
                        • RSI: {an['rsi']:.1f} | السيولة: {an['ratio']:.1f}x<br>
                        • التغير: {an['chg']:+.2f}% | وقف الخسارة المقترح: {nearest_support * 0.99:.2f}
                    </div>
                    <div style='margin-top:10px;'>
                        <b>✅ نقاط قوة الارتداد:</b>
                        {"".join([f'<div style="color:#3fb950;">{r}</div>' for r in reasons[:5]])}
                    </div>
                    <div class='success-box' style='margin-top:10px;'>
                        ✅ <b>مناسب للدخول</b> - وقف خسارة أسفل {nearest_support:.2f} (مخاطرة {risk_percent:.2f}%)
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"📊 تحليل {an['name']} بالتفصيل والدخول", key=f"bounce_{an['name']}"):
                    record_trade(an, "bounce")
                    render_stock_ui(an)
        else:
            st.info("لا توجد أسهم بارتداد حقيقي تطابق الفلتر المختار حالياً.")
    
    # ================== التبويب 3: زخم إيجابي ==================
    with tab3:
        st.markdown("### ⚡ زخم إيجابي عند الدعم - فرصة وشيكة")
        st.markdown("""
        <div class='info-box'>
        🟣 <b>زخم إيجابي</b> - المؤشرات الفنية إيجابية رغم أن السعر لم يرتد بشكل واضح.
        <br>🎯 مناسب للمتابعة عن كثب، قد يتحول إلى تبويب "مؤكد الارتداد" قريباً.
        </div>
        """, unsafe_allow_html=True)
        
        momentum_stocks = []
        for an in st.session_state.all_results:
            if an:
                is_momentum, reasons, level, _ = is_near_support_with_bounce(an, mode="momentum")
                if is_momentum:
                    quality_rating = get_support_quality_rating(an, level, mode="momentum")
                    momentum_stocks.append({
                        'stock': an, 
                        'reasons': reasons, 
                        'level': level,
                        'quality': quality_rating
                    })
        
        excellent_count = len([s for s in momentum_stocks if "ممتاز" in s['quality']])
        good_count = len([s for s in momentum_stocks if "جيد" in s['quality']])
        normal_count = len([s for s in momentum_stocks if "للمتابعة" in s['quality']])
        
        st.markdown("---")
        col_filter3, col_ex3, col_go3, col_no3 = st.columns([2, 1, 1, 1])
        with col_filter3:
            filter_option = st.radio(
                "🔍 فلتر الجودة:",
                ["📋 الكل", "🔥 ممتاز", "✅ جيد", "📌 للمتابعة"],
                key="filter_momentum"
            )
        with col_ex3:
            st.metric("🔥 ممتاز", excellent_count)
        with col_go3:
            st.metric("✅ جيد", good_count)
        with col_no3:
            st.metric("📌 للمتابعة", normal_count)
        
        st.markdown("---")
        
        filtered_stocks = momentum_stocks
        if filter_option == "🔥 ممتاز":
            filtered_stocks = [s for s in momentum_stocks if "ممتاز" in s['quality']]
        elif filter_option == "✅ جيد":
            filtered_stocks = [s for s in momentum_stocks if "جيد" in s['quality']]
        elif filter_option == "📌 للمتابعة":
            filtered_stocks = [s for s in momentum_stocks if "للمتابعة" in s['quality']]
        
        if filtered_stocks:
            st.markdown(f"**عدد الأسهم ذات الزخم الإيجابي: {len(filtered_stocks)}**")
            for item in filtered_stocks:
                an = item['stock']
                reasons = item['reasons']
                quality = item['quality']
                
                if "ممتاز" in quality:
                    quality_class = "quality-excellent"
                elif "جيد" in quality:
                    quality_class = "quality-good"
                else:
                    quality_class = "quality-normal"
                
                st.markdown(f"""
                <div style='background:#0d1117;border:2px solid #9c27b0;border-radius:12px;padding:15px;margin-bottom:15px;'>
                    <div style='display:flex;justify-content:space-between;align-items:center;'>
                        <h3 style='color:#9c27b0;margin:0'>⚡ {an['name']} - {an['desc']}</h3>
                        <span class='momentum-badge'>⚡ زخم إيجابي</span>
                    </div>
                    <div class='quality-badge {quality_class}' style='margin-top:10px;'>⭐ {quality}</div>
                    <div style='margin-top:10px;'>
                        <b>📊 المعطيات:</b><br>
                        • السعر: {an['p']:.2f} ج | الدعم S1: {an['s1']:.2f} ج<br>
                        • RSI: {an['rsi']:.1f} | السيولة: {an['ratio']:.1f}x<br>
                        • التغير: {an['chg']:+.2f}% | Smart Score: {an['smart_score']}/100
                    </div>
                    <div style='margin-top:10px;'>
                        <b>🟣 مؤشرات الزخم الإيجابي:</b>
                        {"".join([f'<div style="color:#9c27b0;">{r}</div>' for r in reasons[:4]])}
                    </div>
                    <div class='info-box' style='margin-top:10px;'>
                        🟣 <b>مراقبة عن كثب</b> - قد يتحول لفرصة دخول خلال الجلسة
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"📊 تحليل {an['name']} بالتفصيل", key=f"momentum_{an['name']}"):
                    record_trade(an, "support")
                    render_stock_ui(an)
        else:
            st.info("لا توجد أسهم بزخم إيجابي تطابق الفلتر المختار حالياً.")

# ================== باقي الصفحات ==================
elif st.session_state.page == 'avg':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    st.title("🧮 حاسبة متوسط السعر")
    c1, c2 = st.columns(2)
    p1 = c1.number_input("سعر الشراء الأول", value=0.0, format="%.2f")
    q1 = c2.number_input("عدد الأسهم", value=0, step=1)
    p2 = c1.number_input("سعر التعزيز", value=0.0, format="%.2f")
    q2 = c2.number_input("عدد الأسهم (تعزيز)", value=0, step=1)
    if (q1 + q2) > 0:
        avg = ((p1 * q1) + (p2 * q2)) / (q1 + q2)
        st.success(f"📊 متوسط السعر الجديد: {avg:.2f}")

elif st.session_state.page == 'imminent':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    st.title("⚡ اختراقات وشيكة")
    st.markdown("الأسهم اللي على وشك الاختراق (قربت من المقاومة + زخم صحي + سيولة)")
    
    if not st.session_state.all_results:
        st.error("⚠️ لا توجد بيانات. اضغط على 'تحديث البيانات' في الصفحة الرئيسية.")
        st.stop()
    
    imminent_stocks = []
    for an in st.session_state.all_results:
        if an:
            is_imminent, reasons = is_imminent_breakout(an)
            if is_imminent:
                imminent_stocks.append({'stock': an, 'reasons': reasons})
    
    if imminent_stocks:
        st.markdown(f"### 🎯 عدد الأسهم على وشك الاختراق: {len(imminent_stocks)}")
        for item in imminent_stocks:
            an = item['stock']
            reasons = item['reasons']
            
            st.markdown(f"""
            <div style='background:#0d1117;border:2px solid #ff8f00;border-radius:12px;padding:15px;margin-bottom:15px;'>
                <div style='display:flex;justify-content:space-between;align-items:center;'>
                    <h3 style='color:#ff8f00;margin:0'>⚡ {an['name']} - {an['desc']}</h3>
                    <span class='imminent-badge'>على وشك الاختراق</span>
                </div>
                <div style='margin-top:10px;'>
                    <b>📊 المعطيات:</b><br>
                    • السعر: {an['p']:.2f} ج | المقاومة R1: {an['r1']:.2f} ج ({(an['r1']-an['p'])/an['p']*100:.1f}% متبقي)<br>
                    • RSI: {an['rsi']:.1f} | السيولة: {an['ratio']:.1f}x<br>
                    • الاتجاه: {an['t_short']} | Smart Score: {an['smart_score']}/100
                </div>
                <div style='margin-top:10px;'>
                    <b>✅ أسباب الوشك على الاختراق:</b>
                    {"".join([f'<div style="color:#ff8f00;">{r}</div>' for r in reasons])}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"📊 تحليل {an['name']} بالتفصيل", key=f"analyze_{an['name']}"):
                render_stock_ui(an)
    else:
        st.info("لا توجد أسهم على وشك الاختراق حالياً.")

elif st.session_state.page == 'guide':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    st.title("📖 دليل المؤشرات الفنية")
    st.markdown("""
    <div class='info-box'>
    📌 <b>نظام تقييم الارتداد (Bounce Score):</b><br>
    • 5 عوامل (تغير السعر، تعافي RSI، السيولة، الهيكل السعري، تعافي RSI من القاع)<br>
    • 3+ نقاط = ارتداد حقيقي مناسب للدخول<br>
    • أقل من 3 نقاط = ضعيف - مراقبة فقط<br>
    • تغير > 4% = ممنوع - فاتك القطار
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("📊 مؤشر القوة النسبية (RSI)"):
        st.markdown("""
        ### ما هو RSI؟
        **RSI** هو مؤشر يقيس سرعة وتغير حركة السعر. قيمته تتراوح بين 0 و 100.
        
        ### دلالات RSI:
        | القيمة | الدلالة | التصرف المتوقع |
        |--------|---------|----------------|
        | **فوق 70** | 🔴 **تشبع شراء** | السهم ممكن ينزل (بيع/جني أرباح) |
        | **تحت 30** | 🟢 **تشبع بيع** | السهم ممكن يصعد (فرصة شراء) |
        | **بين 40 و 60** | 🟡 **منطقة محايدة** | استنى تأكيد إضافي |
        """)
    
    with st.expander("🎯 Smart Score"):
        st.markdown("""
        ### دلالات Smart Score:
        | الدرجة | التقييم | التصرف |
        |--------|---------|--------|
        | **70-100** | 🔥 فرصة قوية جداً | مناسب للدخول |
        | **50-69** | ✅ فرصة جيدة | دخول بحذر |
        | **30-49** | ⚠️ تحت المراقبة | استنى تأكيد |
        | **0-29** | ❄️ ضعيف | تجنب |
        """)
    
    st.info("💡 **تذكير:** هذه المؤشرات هي أدوات مساعدة، وليست قرارات نهائية.")

elif st.session_state.page == 'performance':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    st.title("📊 تقييم أداء التطبيق")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 تحديث البيانات", use_container_width=True):
            with st.spinner("جاري تحديث البيانات..."):
                if st.session_state.all_results:
                    current_prices = {res['name']: res['p'] for res in st.session_state.all_results if res}
                    trades = update_all_trades(current_prices)
                    st.success("تم تحديث البيانات بنجاح!")
                    st.rerun()
                else:
                    st.error("لا توجد بيانات محدثة")
    
    with col2:
        if st.button("🗑️ مسح جميع بيانات التقييم", use_container_width=True):
            if os.path.exists(TRADES_FILE):
                os.remove(TRADES_FILE)
                st.success("✅ تم مسح جميع بيانات التقييم! سيتم البدء من جديد")
                st.rerun()
            else:
                st.info("لا توجد بيانات للمسح")
    
    trades = load_trades()
    stats = get_performance_stats(trades)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📊 إجمالي الصفقات", stats['total'])
    col2.metric("✅ حققت الهدف", stats['hit_target'])
    col3.metric("❌ كسرت الوقف", stats['stopped_out'])
    col4.metric("⏳ لا تزال مفتوحة", stats['still_open'])
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📈 نسبة النجاح", f"{stats['success_rate']}%")
    col2.metric("💰 إجمالي العائد %", f"{stats['total_return']}%")
    col3.metric("📊 متوسط العائد %", f"{stats['avg_return']}%")
    col4.metric("⚖️ متوسط RR", stats['avg_rr'])
    
    col1, col2, col3 = st.columns(3)
    col1.metric("📅 متوسط أيام الاحتفاظ", f"{stats['avg_holding_days']} يوم")
    col2.metric("🎯 دقة الدخول", f"{stats['entry_accuracy']}%")
    col3.metric("🏆 أفضل 10 (نسبة نجاح)", f"{stats['top10_success']}%")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("🔥 السلسلة الحالية", stats['current_win_streak'])
    col2.metric("🏆 أطول سلسلة", stats['max_win_streak'])
    col3.metric("📈 متوسط MFE", f"{stats['avg_mfe']:.2f} ج")
    
    st.markdown(f"""
    <div style='background:#161b22;border:1px solid #30363d;border-radius:10px;padding:15px;margin:15px 0;'>
        <b>💎 الفرص الذهبية:</b> {stats['gold_count']} صفقة | نسبة نجاح: {stats['gold_success']}% | إجمالي العائد: {stats['gold_return']}%
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 📋 تفاصيل الصفقات")
    
    filter_option = st.radio(
        "🔍 اختر الفلتر:",
        ["📋 كل الصفقات", "✅ الناجحة فقط (حققت الهدف)", "❌ الفاشلة فقط (كسرت الوقف)", "⏳ المفتوحة فقط"],
        horizontal=True
    )
    
    if filter_option == "✅ الناجحة فقط (حققت الهدف)":
        filtered_trades = [t for t in trades if t.get('status') == 'hit_target']
    elif filter_option == "❌ الفاشلة فقط (كسرت الوقف)":
        filtered_trades = [t for t in trades if t.get('status') == 'stopped_out']
    elif filter_option == "⏳ المفتوحة فقط":
        filtered_trades = [t for t in trades if t.get('status') in ['pending', 'still_open']]
    else:
        filtered_trades = trades
    
    if filtered_trades:
        st.markdown(f"**عدد الصفقات: {len(filtered_trades)}**")
        for trade in reversed(filtered_trades[-30:]):
            if trade.get('status') == 'hit_target':
                status_color = "🟢"
                status_text = "حققت الهدف"
            elif trade.get('status') == 'stopped_out':
                status_color = "🔴"
                status_text = "كسرت الوقف"
            else:
                status_color = "🟡"
                status_text = "لا تزال مفتوحة"
            
            entry_hit_mark = "✅" if trade.get('entry_hit', False) else "❌"
            profit_text = f" | {'🟢' if trade.get('profit_pct', 0) > 0 else '🔴'} {trade.get('profit_pct', 0):+.1f}%" if trade.get('profit_pct') is not None else ""
            mfe_text = f" | 📈 MFE: {trade.get('max_price', 0) - trade.get('entry_price', 0):+.2f}" if trade.get('max_price') and trade.get('entry_price') else ""
            
            st.markdown(f"""
            <div style='background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:10px;margin:5px 0;'>
                <b>{trade.get('name', 'N/A')}</b> ({trade.get('trade_type', 'N/A')}) - {status_color} {status_text}{profit_text}{mfe_text}<br>
                📅 التسجيل: {trade.get('date_recorded', 'N/A')} | {entry_hit_mark} دخول في النطاق<br>
                🎯 الهدف: {trade.get('target', 0):.2f} | 🛑 الوقف: {trade.get('stop_loss', 0):.2f}<br>
                📊 RR: {trade.get('rr', 0)} | RSI: {trade.get('rsi_at_entry', 0):.1f}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("لا توجد صفقات تطابق الفلتر المختار.")

elif st.session_state.page == 'top10':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    render_mode_selector()
    
    if not st.session_state.all_results:
        st.error("⚠️ لا توجد بيانات. اضغط على 'تحديث البيانات' في الصفحة الرئيسية.")
        st.stop()
    
    top_results = get_top_ranked(st.session_state.all_results, limit=10)
    
    for an in top_results:
        if an:
            record_trade(an, "top10")
    
    st.markdown("## 🏆 أقوى 10 فرص حسب Smart Score")
    for i, an in enumerate(top_results, 1):
        if an:
            with st.expander(f"#{i} - {an['name']} | Smart: {an['smart_score']} | RR: {an['rr']} | ثقة: {get_confidence_score(an)}"):
                render_stock_ui(an, is_top10=True)

elif st.session_state.page in ['gold', 'scanner', 'breakout', 'scalp']:
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    render_mode_selector()
    
    if not st.session_state.all_results:
        st.error("⚠️ لا توجد بيانات. اضغط على 'تحديث البيانات' في الصفحة الرئيسية.")
        st.stop()
    
    if st.session_state.page == 'gold':
        found = False
        for an in st.session_state.all_results:
            if an and classify_stock(an) == "gold":
                record_trade(an, "gold")
                quality = get_quality_rating(an, "gold")
                if "ممتاز" in quality:
                    quality_display = f'<div class="quality-badge quality-excellent">💎 {quality}</div>'
                else:
                    quality_display = f'<div class="quality-badge quality-good">💎 {quality}</div>'
                
                with st.expander(f"✨ ذهبي: {an['name']} (RR: {an['rr']} | RSI: {an['rsi']:.1f} | ثقة: {get_confidence_score(an)}%)"): 
                    st.markdown(quality_display, unsafe_allow_html=True)
                    render_stock_ui(an, is_gold=True)
                    found = True
        if not found: st.info("لا توجد فرص ذهبية حالياً.")
    
    elif st.session_state.page == 'scanner':
        results = [an for an in st.session_state.all_results if an and classify_stock(an) == "watchlist"]
        results.sort(key=lambda x: (x.get('smart_score', 0), x.get('rr', 0)), reverse=True)
        for an in results[:15]:
            quality = get_quality_rating(an, "watchlist")
            if "واعد" in quality:
                quality_display = f'<div class="quality-badge quality-excellent">🔥 {quality}</div>'
            elif "جيد" in quality:
                quality_display = f'<div class="quality-badge quality-good">✅ {quality}</div>'
            else:
                quality_display = f'<div class="quality-badge quality-normal">📌 {quality}</div>'
            
            with st.expander(f"{an['name']} | {an['signal']} | ثقة: {get_confidence_score(an)}%"):
                st.markdown(quality_display, unsafe_allow_html=True)
                render_stock_ui(an)
    
    elif st.session_state.page == 'breakout':
        for an in st.session_state.all_results:
            if an and classify_stock(an) == "breakout":
                quality = get_quality_rating(an, "breakout")
                if "ممتاز" in quality:
                    quality_display = f'<div class="quality-badge quality-excellent">🚀 {quality}</div>'
                elif "جيد" in quality:
                    quality_display = f'<div class="quality-badge quality-good">🚀 {quality}</div>'
                else:
                    quality_display = f'<div class="quality-badge quality-normal">🚀 {quality}</div>'
                
                with st.expander(f"🚀 اختراق: {an['name']} (RSI: {an['rsi']:.1f} | ثقة: {get_confidence_score(an)}%)"):
                    st.markdown(quality_display, unsafe_allow_html=True)
                    render_stock_ui(an)
    
    elif st.session_state.page == 'scalp':
        found = False
        for an in st.session_state.all_results:
            if an and classify_stock(an) == "scalp":
                quality = get_quality_rating(an, "scalp")
                if "ممتاز" in quality:
                    quality_display = f'<div class="quality-badge quality-excellent">⚡ {quality}</div>'
                elif "جيد" in quality:
                    quality_display = f'<div class="quality-badge quality-good">⚡ {quality}</div>'
                else:
                    quality_display = f'<div class="quality-badge quality-normal">⚡ {quality}</div>'
                
                with st.expander(f"⚡ مضاربة: {an['name']} (RSI: {an['rsi']:.1f} | ثقة: {get_confidence_score(an)}%)"):
                    st.markdown(quality_display, unsafe_allow_html=True)
                    render_stock_ui(an)
                    found = True
        if not found: st.info("لا توجد مضاربات سريعة حالياً.")

elif st.session_state.page == 'analyze':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    render_mode_selector()
    
    if not st.session_state.all_results:
        st.error("⚠️ لا توجد بيانات. اضغط على 'تحديث البيانات' في الصفحة الرئيسية.")
        st.stop()
    
    sym = st.text_input("رمز السهم").upper().strip()
    if sym:
        with st.spinner("🔍 جاري البحث عن السهم..."):
            data = fetch_single_stock(sym)
            
            if not data:
                st.error("❌ السهم غير موجود في البيانات الحالية")
                symbols = [x['name'] for x in st.session_state.all_results if x]
                similar = [s for s in symbols if sym[:2] in s or s[:2] in sym][:5]
                if similar:
                    st.info(f"💡 هل تقصد: {', '.join(similar)}")
            else:
                res = analyze_stock(data[0])
                if res:
                    render_stock_ui(res)
                else:
                    st.warning("⚠️ تم جلب البيانات لكن التحليل فشل")
