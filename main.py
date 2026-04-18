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
    trades = load_trades()
    today = datetime.now().strftime("%Y-%m-%d")
    
    for t in trades:
        if (t.get('name') == res['name'] and 
            t.get('date_recorded') == today and
            t.get('trade_type') == trade_type):
            return
    
    trades.append({
        "name": res['name'],
        "desc": res['desc'],
        "entry_price": res['entry_price'],
        "entry_min": res['entry_price'] * 0.98,
        "entry_max": res['entry_price'] * 1.01,
        "target": res['target'],
        "stop_loss": res['stop_loss'],
        "target_pct": res['target_pct'],
        "risk_pct": res['risk_pct'],
        "rr": res['rr'],
        "rsi_at_entry": res['rsi'],
        "smart_score": res['smart_score'],
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

# ================== 🆕 QUALITY RATING ==================
def get_quality_rating(res, section_type):
    """تقييم جودة السهم داخل كل قسم"""
    
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
    """عرض شارت TradingView مع مؤشرات الدعم والمقاومة"""
    
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


# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="EGX Sniper Pro v16.0", layout="wide")

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

def classify_stock(res):
    rr = res.get('rr', 0)
    ratio = res.get('ratio', 0)
    t_short = res.get('t_short', 'هابط')
    t_med = res.get('t_med', 'هابط')
    rsi = res.get('rsi', 50)
    smart_score = res.get('smart_score', 0)
    change_pct = res.get('chg', 0)
    mode = st.session_state.mode
    
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
    gold_count = sum(1 for an in results if classify_stock(an) == "gold")
    total = len(results)
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
    return int((res.get('smart_score', 0) + res.get('execution_strength', 0)) / 2)

def get_momentum_score(res):
    sma20 = res.get('sma20', res.get('p', 0))
    if sma20 and sma20 > 0:
        momentum = (res['p'] - sma20) / sma20
        if momentum > 0.05: return 80
        elif momentum > 0.02: return 60
        elif momentum > 0: return 40
        elif momentum > -0.02: return 20
        else: return 10
    return 50

def is_perfect_setup(res):
    return (res.get('t_short') == "صاعد" and
            res.get('t_med') == "صاعد" and
            res.get('ratio', 0) > 2 and
            45 < res.get('rsi', 50) < 60 and
            res.get('rr', 0) >= 2)

def is_real_breakout(res):
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
        "filter": [{"left": "volume", "operation": "greater", "right": 5000}],
        "columns": cols,
        "sort": {"sortBy": "change", "sortOrder": "desc"},
        "range": [0, 150]
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
    sorted_results = sorted(
        results,
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
    # عنوان السهم
    st.markdown(f"""
    <div class='stock-header'>
        {res['name']} - {res['desc']}
        <span class='score-tag'>Score: {res['score']}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # ✅ تقييم الجودة حسب نوع القسم
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
    
    # اختراق حقيقي
    if is_real_breakout(res):
        st.markdown('<div class="real-breakout">✅ اختراق حقيقي - سيولة عالية واتجاه قوي</div>', unsafe_allow_html=True)
    
    # Perfect Setup Badge
    if is_perfect_setup(res):
        st.markdown('<div class="premium-badge">💎 PERFECT SETUP - فرصة مثالية</div>', unsafe_allow_html=True)
    
    # تنبيهات السيولة
    if res.get('ratio', 0) > 2.5:
        st.warning("🚨 اختراق قوي جداً - سيولة استثنائية")
    elif res.get('ratio', 0) > 3:
        st.error("🔥 اختراق خرافي - انتباه شديد")
    
    # ================== QUICK SUMMARY ==================
    st.markdown("### 📊 خلاصة")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
    with c2:
        st.metric("Smart", f"{res['smart_score']}/100")
    with c3:
        st.metric("RR", res['rr'])
    with c4:
        st.metric("RSI", f"{res['rsi']:.0f}")
    
    # إشارة سريعة
    if res['smart_score'] >= 70 and res['rr'] >= 1.5 and 45 < res['rsi'] < 65:
        st.success("🟢 إشارة شراء قوية")
    elif res['smart_score'] >= 50 and res['rr'] >= 1.2:
        st.warning("🟡 إشارة مراقبة")
    else:
        st.error("🔴 إشارة تجنب")
    
    st.markdown("---")
    
    # ================== 📤 زر مشاركة واتساب ==================
    whatsapp_url = share_on_whatsapp(res)
    st.markdown(f"""
    <div style="margin-bottom: 15px;">
        <a href="{whatsapp_url}" target="_blank" class="whatsapp-btn" style="display: block; text-align: center; background-color: #25D366; color: white; padding: 10px; border-radius: 12px; text-decoration: none; font-weight: bold;">
            📱 مشاركة التحليل عبر واتساب
        </a>
    </div>
    """, unsafe_allow_html=True)
    
    # ================== 📊 التحليل الفني ==================
    with st.expander("📊 التحليل الفني", expanded=True):
        # عرض شارت TradingView الحقيقي
        st.markdown("### 📈 شارت السهم (بيانات حية من السوق)")
        render_tradingview_chart(res['name'], height=450)
        
        # الاتجاهات
        t_short_c = "trend-up" if res['t_short'] == "صاعد" else "trend-down"
        t_med_c = "trend-up" if res['t_med'] == "صاعد" else "trend-down"
        t_long_c = "trend-up" if res['t_long'] == "صاعد" else "trend-down"
        st.markdown(f"""
        <div style='margin-bottom: 15px;'>
            <span class='trend-pill {t_short_c}'>قصير: {res['t_short']}</span>
            <span class='trend-pill {t_med_c}'>متوسط: {res['t_med']}</span>
            <span class='trend-pill {t_long_c}'>طويل: {res['t_long']}</span>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"<span class='signal-pill {res['sig_cls']}'>{res['signal']}</span>", unsafe_allow_html=True)
        
        # المؤشرات الأساسية
        col1, col2 = st.columns(2)
        with col1:
            vol_label, vol_desc = get_volume_rating(res['ratio'])
            st.metric("نشاط السيولة", f"{res['ratio']:.1f}x", vol_label)
            st.caption(f"📊 {vol_desc}")
        with col2:
            rr_label, rr_desc = get_rr_rating(res['rr'])
            st.metric("R/R Ratio", f"{res['rr']}", rr_label)
            st.caption(f"🧠 {rr_desc}")
        
        # RSI
        rsi_label, _ = get_rsi_signal(res['rsi'])
        st.metric("RSI", f"{res['rsi']:.1f}", rsi_label)
        
        # ROC
        roc = calculate_roc(res['p'], res.get('sma20', res['p']))
        roc_color = "🟢" if roc > 0 else "🔴"
        st.metric("ROC (معدل التغير)", f"{roc_color} {roc:+.1f}%")
        
        # ================== 🏛️ الدعم والمقاومة ==================
        st.markdown("### 🏛️ مستويات الدعم والمقاومة (للمستثمر طويل الأجل)")
        st.markdown(f"""
        | المستوى | السعر | الدلالة |
        |---------|-------|---------|
        | 🔴 **مقاومة ثانية R2** | {res['r2']:.2f} | مقاومة قوية |
        | 🔴 **مقاومة أولى R1** | {res['r1']:.2f} | مقاومة أولى |
        | 🟡 **نقطة الارتكاز PP** | {res['pp']:.2f} | المحور |
        | 🟢 **دعم أول S1** | {res['s1']:.2f} | دعم أول |
        | 🟢 **دعم ثاني S2** | {res['s2']:.2f} | دعم قوي |
        """)
        
        # ================== 🎯 نطاق الدخول ==================
        st.markdown(f"""
        <div class='entry-card-new'>
            🎯 <b>نطاق الدخول (مضاربة/سوينج):</b> {res['entry_range']}<br>
            🛑 <b>وقف الخسارة:</b> {res['stop_loss']:.2f} <span style='color:#f85149'>(-{res['risk_pct']:.1f}%)</span><br>
            🏁 <b>المستهدف:</b> {res['target']:.2f} <span style='color:#58a6ff'>(+{res['target_pct']:.1f}%)</span>
        </div>
        """, unsafe_allow_html=True)
    
    # ================== 💰 إدارة المخاطر وخطة الدخول ==================
    with st.expander("💰 إدارة المخاطر وخطة الدخول", expanded=False):
        
        # ميزانية الصفقة
        deal_size = st.number_input("💰 ميزانية الصفقة (ج)", value=10000, step=1000, key=f"deal_{res['name']}")
        
        if deal_size > 0 and res['entry_price'] > 0:
            shares_deal = int(deal_size / res['entry_price'])
            actual_value = shares_deal * res['entry_price']
            profit_val = (res['target'] - res['entry_price']) * shares_deal
            loss_val = (res['entry_price'] - res['stop_loss']) * shares_deal
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("📦 عدد الأسهم", f"{shares_deal:,}")
                st.metric("💰 قيمة الصفقة", f"{actual_value:,.0f} ج")
            with col2:
                st.metric("🟢 الربح المتوقع", f"{profit_val:,.0f} ج", delta=f"+{res['target_pct']:.1f}%")
                st.metric("🔴 الخسارة المحتملة", f"{loss_val:,.0f} ج", delta=f"-{res['risk_pct']:.1f}%")
            
            # خطة الدخول المتكاملة
            st.markdown("### 🏹 خطة الدخول")
            
            range_size = res['entry_price'] - res['stop_loss']
            
            entry_level_1 = res['entry_price']
            entry_level_2 = max(res['entry_price'] - (range_size * 0.5), res['stop_loss'] * 1.02)
            entry_level_3 = res['entry_price'] + (res['target'] - res['entry_price']) * 0.3
            
            if res['rr'] >= 2:
                weights = [0.6, 0.25, 0.15]
            elif res['rr'] >= 1.5:
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
        
        # وقف الخسارة المتحرك
        st.markdown("---")
        st.markdown("### 🎯 وقف الخسارة المتحرك")
        current_price_trail = st.number_input("السعر الحالي", value=res['p'], key=f"trail_price_{res['name']}")
        highest_price_trail = st.number_input("أعلى سعر تم الوصول إليه", value=res['p'], key=f"highest_{res['name']}")
        trailing_stop = calculate_trailing_stop(res['entry_price'], current_price_trail, highest_price_trail, res['rr'])
        st.info(f"🛡️ **وقف الخسارة المتحرك المقترح:** {trailing_stop:.2f} ج (الأصلي: {res['stop_loss']:.2f} ج)")
        
        st.warning("⚠️ **تذكير:** هذه الخطة استرشادية. القرار النهائي يعتمد على تحليلك الشخصي وظروف السوق.")
    
    # ================== 🧠 تحليل الوضع الحالي ==================
    with st.expander("🧠 تحليل الوضع الحالي", expanded=False):
        col1, col2 = st.columns(2)
        buy_price = col1.number_input("سعر الشراء", value=res['p'], key=f"buy_{res['name']}")
        qty = col2.number_input("الكمية", value=100, step=1, key=f"qty_{res['name']}")
        
        if qty > 0 and buy_price > 0:
            current_price = res['p']
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
            
            if current_price >= res['target']:
                st.success("🎉 تم تحقيق الهدف!")
            elif current_price <= res['stop_loss']:
                st.error("⚠️ كسر وقف الخسارة!")
            
            trend_score = (1 if res['t_short'] == "صاعد" else 0) + (1 if res['t_med'] == "صاعد" else 0) + (1 if res['ratio'] > 1.5 else 0)
            if trend_score >= 2:
                st.success(f"✅ استمر طالما السعر فوق {res['stop_loss']:.2f}")
            else:
                st.warning("⚠️ اتجاه ضعيف - فكر في تأمين الأرباح")
    
    # ================== 📈 مؤشرات متقدمة ==================
    with st.expander("📈 مؤشرات متقدمة", expanded=False):
        stoch = calculate_stochastic_rsi(res['rsi'])
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
            🤖 <b>Smart Score:</b> {res['smart_score']}/100<br>
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
    st.title("🏹 EGX Sniper Pro v16.0")
    
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
        col1, col2, col3, col4 = st.columns(4)
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
    
    # زر مسح البيانات
    with st.expander("⚠️ أدوات خطيرة", expanded=False):
        if st.button("🗑️ إعادة ضبط جميع البيانات (مسح التقييم)", use_container_width=True):
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

elif st.session_state.page == 'guide':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    st.title("📖 دليل المؤشرات الفنية")
    st.markdown("مرحباً بك في دليل المؤشرات! هنا شرح مبسط لكل مؤشر تستخدمه في التطبيق.")
    
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
        | **بين 30 و 40 أو 60 و 70** | ⚪ **ضعيف** | زخم السهم ضعيف |
        
        ### نصيحة:
        الأفضل للدخول في صفقة شراء عندما يكون RSI **بين 40 و 65** (زخم صحي).
        """)
    
    with st.expander("🎯 Smart Score"):
        st.markdown("""
        ### ما هو Smart Score؟
        **Smart Score** هو ابتكارنا الخاص في هذا التطبيق! هو درجة مركبة من 0 إلى 100 تقييم قوة السهم.
        
        ### كيفية حسابه:
        | العامل | الوزن |
        |--------|-------|
        | اتجاه قصير صاعد | +15 |
        | اتجاه متوسط صاعد | +15 |
        | اتجاه طويل صاعد | +5 |
        | سيولة عالية (ratio > 2) | +20 |
        | سيولة جيدة (ratio > 1.5) | +10 |
        | RSI في المنطقة الصحية (50-65) | +20 |
        | RR ممتاز (>= 2) | +20 |
        | RR جيد (>= 1.5) | +10 |
        
        ### دلالات Smart Score:
        | الدرجة | التقييم | التصرف |
        |--------|---------|--------|
        | **70-100** | 🔥 فرصة قوية جداً | مناسب للدخول |
        | **50-69** | ✅ فرصة جيدة | دخول بحذر |
        | **30-49** | ⚠️ تحت المراقبة | استنى تأكيد |
        | **0-29** | ❄️ ضعيف | تجنب |
        """)
    
    # دليل أقسام التطبيق
    with st.expander("🎯 دليل أقسام التطبيق - إزاي تختار الأسهم؟"):
        st.markdown("""
        ### 📊 شرح أقسام التطبيق

        ---

        #### 🏆 أفضل 10 فرص (Top 10)
        | المعيار | التفاصيل |
        |----------|----------|
        | **طريقة الاختيار** | ترتيب تنازلي حسب `Smart Score` (أعلى 10 أسهم في السوق كله) |
        | **المؤشرات المعتمدة** | Smart Score (الاتجاهات + السيولة + RSI + RR) |
        | **نوع الصفقات** | متنوعة (ذهب، اختراقات، مضاربات، مراقبة) |
        | **الهدف** | أفضل الفرص بغض النظر عن النوع |
        | **مناسب لـ** | أي متداول يبي يبدأ من هنا |

        > 💡 **نصيحة:** ابدأ من هنا كل يوم، هي الخلاصة الكاملة للسوق.

        ---

        #### 🔭 كشاف السوق (Scanner)
        | المعيار | التفاصيل |
        |----------|----------|
        | **طريقة الاختيار** | كل الأسهم اللي في `watchlist` (قائمة المراقبة) |
        | **المؤشرات المعتمدة** | RR >= حد معين (حسب نمط التداول) + سيولة > 1.2x |
        | **نوع الصفقات** | فرص متوسطة إلى جيدة (مش قوية جداً) |
        | **الهدف** | عرض فرص تستحق المتابعة |
        | **مناسب لـ** | اللي عايز يتابع فرص محتملة قبل ما تتحول لقوية |

        > 💡 **نصيحة:** استخدمه للتعرف على فرص جديدة قد تتحول لاختراقات لاحقاً.

        ---

        #### 🚀 الاختراقات (Breakout)
        | المعيار | التفاصيل |
        |----------|----------|
        | **طريقة الاختيار** | سيولة > 2.5x + اتجاه قصير صاعد + RSI < 70 |
        | **المؤشرات المعتمدة** | السيولة (الأهم) + الاتجاه + RSI |
        | **نوع الصفقات** | اختراق حقيقي بحجم تداول عالي |
        | **الهدف** | فرص الصعود السريع |
        | **مناسب لـ** | مضاربات سريعة (ساعات - أيام) |

        > 💡 **نصيحة:** أفضل قسم للمضاربات السريعة، السيولة العالية تؤكد الاختراق.

        ---

        #### ⚡ مضاربات سريعة (Scalp)
        | المعيار | التفاصيل |
        |----------|----------|
        | **طريقة الاختيار** | سيولة > 1.8x + RR >= 1.3 + RSI < 75 |
        | **المؤشرات المعتمدة** | السيولة + RR + RSI |
        | **نوع الصفقات** | صفقات قصيرة جداً (دقائق - ساعات) |
        | **الهدف** | ربح سريع 1-3% |
        | **مناسب لـ** | مضاربين خبرة (مش للمبتدئين) |

        > 💡 **نصيحة:** صفقات سريعة، لازم Stop Loss قريب وتكون جاهز للخروج بسرعة.

        ---

        #### 💎 الفرص الذهبية (Gold)
        | المعيار | التفاصيل |
        |----------|----------|
        | **طريقة الاختيار** | RR >= 2 + اتجاهين صاعدين + RSI 45-60 + سيولة > 1.5x + Smart Score >= 70 |
        | **المؤشرات المعتمدة** | كل شيء (أصعب فرصة تتحقق) |
        | **نوع الصفقات** | فرص نادرة وقوية جداً |
        | **الهدف** | أفضل فرصة ممكنة |
        | **مناسب لـ** | اللي عايز أنقى الفرص (عددها قليل جداً) |

        > 💡 **نصيحة:** دي "الكريمة" في التطبيق، نادرة لكن قوية جداً. لو ظهرت، ركز عليها.

        ---

        ### 🎯 جدول مقارنة سريع:

        | القسم | السيولة (Ratio) | RR | RSI | عدد الفرص | السرعة |
        |-------|-----------------|-----|-----|-----------|--------|
        | 🏆 أفضل 10 | أي | أي | أي | 10 | متنوعة |
        | 🔭 كشاف | > 1.2 | حسب النمط | أي | 15+ | بطيئة |
        | 🚀 اختراقات | > 2.5 | أي | < 70 | قليل | سريعة |
        | ⚡ مضاربات | > 1.8 | >= 1.3 | < 75 | متوسط | سريعة جداً |
        | 💎 ذهبي | > 1.5 | >= 2 | 45-60 | نادر جداً | متوسطة |

        ---

        ### 💡 إزاي تختار القسم المناسب ليك؟

        | لو عايز | استخدم |
        |---------|--------|
        | **تبدأ وتشوف أفضل حاجة** | 🏆 أفضل 10 فرص |
        | **تتابع فرص محتملة** | 🔭 كشاف السوق |
        | **مضاربات سريعة (ربح سريع)** | 🚀 اختراقات أو ⚡ مضاربات |
        | **أقوى وأندر الفرص** | 💎 الفرص الذهبية |

        ---

        ### 📌 تذكير مهم:
        > كل الأرقام اللي في الجدول (نسبة السيولة، RR، RSI) هي اللي التطبيق بيستخدمها عشان يحدد نوع الفرصة. اعتمد عليها في اختياراتك.
        """)
    
    st.info("💡 **تذكير:** هذه المؤشرات هي أدوات مساعدة، وليست قرارات نهائية. القرار النهائي يعتمد على تحليلك الشخصي وإدارة المخاطر الخاصة بك.")

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
    
    if stats['gold_count'] >= 5:
        if stats['gold_success'] > stats['top10_success']:
            st.success("💡 Insight: الفرص الذهبية تتفوق على أفضل 10 فرص!")
        elif stats['top10_success'] > stats['gold_success']:
            st.info("💡 Insight: أفضل 10 فرص تتفوق على الفرص الذهبية!")
    
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
                # ✅ إضافة تقييم الجودة للذهب
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
            # ✅ إضافة تقييم الجودة لكشاف السوق
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
                # ✅ إضافة تقييم الجودة للاختراقات
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
                # ✅ إضافة تقييم الجودة للمضاربات
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
            res = next((x for x in st.session_state.all_results if x['name'] == sym), None)
            
            if not res:
                st.error("❌ السهم غير موجود في البيانات الحالية")
                symbols = [x['name'] for x in st.session_state.all_results]
                similar = [s for s in symbols if sym[:2] in s or s[:2] in sym][:5]
                if similar:
                    st.info(f"💡 هل تقصد: {', '.join(similar)}")
            else:
                render_stock_ui(res)
