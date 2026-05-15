import streamlit as st
import streamlit.components.v1 as components
import requests
from datetime import datetime
import json
import os
import re
import urllib.parse
import time

st.set_page_config(page_title="🎯 قناص EGX - المتكامل", layout="wide", page_icon="🎯")

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
    except:
        pass

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

# ================== 📈 EGX30 MARKET ANALYSIS (مُحسّن) ==================
@st.cache_data(ttl=600, show_spinner=False)
def get_egx30_status():
    """تحليل المؤشر العام - مع إعادة محاولة وتجاوز الأخطاء"""
    
    # محاولة 1: عبر الـ scanner العادي
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
    
    # محاولة 2: EGX100 كبديل
    try:
        url = "https://scanner.tradingview.com/egypt/scan"
        payload = {
            "filter": [{"left": "symbol", "operation": "equal", "right": "EGX100"}],
            "columns": ["close", "RSI", "change"],
            "range": [0, 1]
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json().get("data", [])
            if data and len(data) > 0:
                d = data[0].get('d', [])
                if len(d) >= 3:
                    change = d[2] if d[2] else 0
                    return {
                        "status": "🟡 سوق متذبذب (تقديري)",
                        "color": "#FFA500",
                        "market_multiplier": 0.7,
                        "rsi": 50,
                        "change": change,
                        "price": 10000
                    }
    except:
        pass
    
    # القيم الافتراضية الآمنة
    return {
        "status": "🟡 سوق متذبذب (افتراضي - تعذر التحليل)",
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
    
    rsi = res.get('rsi', 50)
    if 50 < rsi < 60:
        score += 15
    elif 45 < rsi <= 50 or 60 <= rsi < 65:
        score += 10
    elif 40 <= rsi <= 45:
        score += 5
    elif 30 <= rsi < 40:
        score += 3
    
    rr = res.get('rr', 0)
    if rr >= 2.5: score += 15
    elif rr >= 2: score += 12
    elif rr >= 1.5: score += 8
    elif rr >= 1.2: score += 4
    
    chg = res.get('chg', 0)
    if chg > 1.5: score += 15
    elif chg > 0.5: score += 10
    elif chg > 0: score += 5
    elif chg > -1: score += 2
    
    return min(100, int(score))

# ================== 🎯 CONFIDENCE SCORE ==================
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

# ================== ⚡ RAPID BREAKOUT HUNTER ==================
def is_rapid_breakout(an):
    if an is None:
        return False, [], 0
    
    p = an.get('p', 0)
    rsi = an.get('rsi', 50)
    ratio = an.get('ratio', 0)
    change = an.get('chg', 0)
    t_short = an.get('t_short', 'هابط')
    t_med = an.get('t_med', 'هابط')
    r1 = an.get('r1', p * 1.05)
    volume = an.get('volume', 0)
    avg_volume = an.get('avg_volume', 1)
    
    reasons = []
    score = 0
    max_score = 7
    
    if 55 <= rsi <= 70:
        score += 2
        reasons.append(f"⚡ زخم قوي جداً (RSI: {rsi:.0f})")
    elif 50 <= rsi < 55:
        score += 1
        reasons.append(f"📈 زخم إيجابي (RSI: {rsi:.0f})")
    else:
        return False, [], 0
    
    if ratio > 2.5:
        score += 2
        reasons.append(f"💥 سيولة استثنائية ({ratio:.1f}x)")
    elif ratio > 1.8:
        score += 1
        reasons.append(f"🚀 سيولة قوية ({ratio:.1f}x)")
    else:
        return False, [], 0
    
    if p >= r1 * 0.99:
        score += 2
        reasons.append(f"🎯 على وشك اختراق R1 ({r1:.2f})")
    elif p >= r1 * 0.97:
        score += 1
        reasons.append(f"📍 قريب من المقاومة R1")
    else:
        return False, [], 0
    
    if t_short == "صاعد" and t_med == "صاعد":
        score += 1
        reasons.append("📊 الاتجاهات صاعدة")
    
    if change > 1.5:
        score += 1
        reasons.append(f"🟢 شمعة قوية (+{change:.2f}%)")
    elif change > 0.5:
        score += 0.5
        reasons.append(f"🟢 شمعة إيجابية (+{change:.2f}%)")
    
    strength = int((score / max_score) * 100)
    
    if strength >= 70:
        label = "🔥 انفجار وشيك خلال ساعات"
        color = "#FF4444"
    elif strength >= 55:
        label = "⚡ اختراق متوقع خلال جلسة"
        color = "#FFA500"
    elif strength >= 40:
        label = "🟡 مراقبة لاصطياد الاختراق"
        color = "#FFD700"
    else:
        return False, [], 0
    
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

# ================== 🎯 CORRECTION HUNTER ==================
def is_correction(an, market_multiplier=1.0):
    if an is None:
        return False, [], 0
    
    p = an.get('p', 0)
    rsi = an.get('rsi', 50)
    sma200 = an.get('sma200', 0)
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
    
    if t_long == "صاعد" or (sma200 and p > sma200 * 0.98):
        score += 3
        reasons.append("📈 الاتجاه العام صاعد")
    else:
        return False, [], 0
    
    if 30 <= rsi <= 50:
        score += 2
        reasons.append(f"📊 RSI في تصحيح ({rsi:.0f})")
    elif 50 < rsi <= 55:
        score += 1
        reasons.append(f"📊 RSI بدأ يخرج من التصحيح ({rsi:.0f})")
    else:
        return False, [], 0
    
    if change > 0.2:
        score += 2
        reasons.append(f"📈 بداية ارتداد ({change:+.2f}%)")
    elif change > 0:
        score += 1
        reasons.append(f"📈 بداية ارتداد ({change:+.2f}%)")
    
    volume_ratio = volume / avg_volume if avg_volume > 0 else 0
    if volume_ratio > 1.5:
        score += 1
        reasons.append(f"💧 سيولة ممتازة ({volume_ratio:.1f}x)")
    elif volume_ratio > 1.0:
        score += 0.5
        reasons.append(f"💧 سيولة جيدة ({volume_ratio:.1f}x)")
    else:
        return False, [], 0
    
    if rr >= 1.8:
        score += 1
        reasons.append(f"⚖️ RR ممتاز ({rr})")
    elif rr >= 1.3:
        score += 0.5
        reasons.append(f"⚖️ RR جيد ({rr})")
    
    s1 = an.get('s1', p * 0.97)
    if p <= s1 * 1.02:
        score += 1
        reasons.append("🎯 السعر عند دعم قوي")
    
    adjusted_score = score * market_multiplier
    strength = int((adjusted_score / max_score) * 100)
    
    if strength >= 65:
        label = "🔥 فرصة تصحيح ممتازة"
        color = "#00FF00"
    elif strength >= 50:
        label = "✅ فرصة تصحيح جيدة"
        color = "#ADFF2F"
    elif strength >= 35:
        label = "🟡 فرصة تصحيح محتملة"
        color = "#FFA500"
    else:
        label = "❌ فرصة تصحيح ضعيفة"
        color = "#FF4444"
    
    return {
        "is_correction": score >= 3,
        "reasons": reasons,
        "strength": strength,
        "label": label,
        "color": color
    }

# ================== 📂 SECTOR FILTER ==================
SECTORS = {
    "🏦 البنوك": ["CIEB", "COMI", "AAIB", "QNBA", "ALEX"],
    "🏗️ العقارات": ["TMGH", "OCDI", "PHDC", "HELI", "DEGC"],
    "🍔 الأغذية": ["BFR", "EFID", "JUFO", "ORWE"],
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
    payload = {"filter": [], "columns": cols, "range": [0, 300]}
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
        
        ratio = v / avg_v if avg_v and avg_v > 0 else 0
        estimated_value = p * v
        
        t_short = "صاعد" if (sma20 and p > sma20) else "هابط"
        t_med = "صاعد" if (sma50 and p > sma50) else "هابط"
        t_long = "صاعد" if (sma200 and p > sma200) else "هابط"
        
        high = h if h else p
        low = l if l else p
        pp = (p + high + low) / 3
        r1 = (2 * pp) - low
        r2 = pp + (high - low)
        s1 = (2 * pp) - high
        s2 = pp - (high - low)
        
        entry_min = p * 0.98
        entry_max = p * 1.01
        entry_price = (entry_min + entry_max) / 2
        
        stop_loss = min(s2 * 0.98, entry_price * 0.96) if s2 > 0 else entry_price * 0.96
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
    except:
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
    valid = [r for r in valid if r.get('estimated_value', 0) >= 2000000]
    sorted_results = sorted(valid, key=lambda x: x.get('smart_score', 0), reverse=True)
    return sorted_results[:10]

def get_rapid_breakouts(results):
    rapid = []
    for r in results:
        if r and r.get('estimated_value', 0) >= 2000000:
            analysis = is_rapid_breakout(r)
            if analysis and analysis.get('is_breakout'):
                rapid.append({
                    'stock': r,
                    'analysis': analysis
                })
    rapid.sort(key=lambda x: x['analysis']['strength'], reverse=True)
    return rapid[:8]

def get_fresh_data():
    with st.spinner("🔄 جاري تحليل جميع الأسهم..."):
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
.entry-card { background: #0d1117; border: 1px solid #3fb950; border-radius: 10px; padding: 12px; margin: 10px 0; }
.rapid-card { background: linear-gradient(135deg, #2a0a0a, #1a0a0a); border-radius: 12px; padding: 15px; margin-bottom: 15px; border-right: 4px solid #FF4444; }
.correction-card { background: linear-gradient(135deg, #1a1a2e, #16213e); border-radius: 12px; padding: 15px; margin-bottom: 15px; }
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

# ================== 📄 RENDER STOCK CARD ==================
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
    with col1: st.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:+.2f}%")
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
    
    with st.expander("📈 مؤشرات متقدمة", expanded=False):
        rsi = res['rsi']
        if rsi <= 20:
            stoch_signal = "🟢 تشبع بيع - فرصة انعكاس قوية"
        elif rsi <= 35:
            stoch_signal = "🟡 منطقة شراء محتملة"
        elif rsi <= 65:
            stoch_signal = "⚪ منطقة حيادية"
        elif rsi <= 80:
            stoch_signal = "🟠 منطقة بيع محتملة"
        else:
            stoch_signal = "🔴 تشبع شراء - خطر"
        
        st.markdown(f"""
        <div style='background:#0d1117;border:1px solid #30363d;border-radius:10px;padding:12px;margin-bottom:15px;'>
            <b>🔄 تحليل RSI</b><br>
            🧠 {stoch_signal}
        </div>
        """, unsafe_allow_html=True)
        
        success_rate = 50
        if res['smart_score'] >= 80 and res['rr'] >= 2 and 45 < res['rsi'] < 60:
            success_rate = 80
        elif res['smart_score'] >= 65 and res['rr'] >= 1.5:
            success_rate = 70
        elif res['smart_score'] >= 50:
            success_rate = 60
        else:
            success_rate = 45
        
        st.markdown(f"""
        <div style='background:#0d1117;border:1px solid #d29922;border-radius:10px;padding:12px;'>
            <b>📈 نسبة النجاح المتوقعة</b><br>
            🎯 <b>{success_rate}%</b>
        </div>
        """, unsafe_allow_html=True)
    
    msg = f"📊 تحليل سهم {res['name']}\n💰 السعر: {res['p']:.2f}\n🎯 الدخول: {res['entry_range']}\n🛑 الوقف: {res['stop_loss']:.2f}\n🏁 الهدف: {res['target']:.2f}\n⚖️ RR: {res['rr']}"
    encoded = urllib.parse.quote(msg)
    st.markdown(f"[📱 مشاركة عبر واتساب](https://wa.me/?text={encoded})")

# ================== MAIN APP ==================
def main():
    if st.session_state.all_results is None:
        get_fresh_data()
    
    market_status = get_egx30_status()
    
    if st.session_state.page == 'home':
        st.title("🎯 قناص EGX - المتكامل")
        st.caption("تحليل كل الأسهم | فرص سريعة | صائد تصحيحات | أفضل 10 فرص")
        
        st.markdown(f"""
        <div style="background: #0d1117; border-radius: 10px; padding: 10px; margin-bottom: 20px; text-align: center;">
            <span style="color: {market_status['color']}; font-weight: bold;">📊 المؤشر العام:</span>
            <span>{market_status['status']}</span>
        </div>
        """, unsafe_allow_html=True)
        
        render_mode_and_sector()
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⚡ قناص الاختراق السريع", use_container_width=True):
                st.session_state.page = 'rapid'
                st.rerun()
        with col2:
            if st.button("🎯 صائد التصحيحات", use_container_width=True):
                st.session_state.page = 'correction'
                st.rerun()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🏆 أفضل 10 فرص", use_container_width=True):
                st.session_state.page = 'top10'
                st.rerun()
        with col2:
            if st.button("🔍 تحليل سهم", use_container_width=True):
                st.session_state.page = 'analyze'
                st.rerun()
        with col3:
            if st.button("📊 تقييم الأداء", use_container_width=True):
                st.session_state.page = 'performance'
                st.rerun()
        
        with st.expander("⚙️ إدارة التطبيق", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 تحديث البيانات", use_container_width=True):
                    get_fresh_data()
                    st.rerun()
            with col2:
                if st.button("🗑️ مسح بيانات التقييم", use_container_width=True):
                    if os.path.exists(TRADES_FILE):
                        os.remove(TRADES_FILE)
                    st.success("✅ تم المسح!")
                    st.rerun()
        
        sector_filter = st.session_state.sector_filter
        filtered = filter_by_sector(st.session_state.all_results, sector_filter)
        if filtered:
            st.markdown(f"""
            <div style='background:#0d1117;border-radius:10px;padding:15px;margin-top:20px;'>
                <b>📊 إحصائية السوق</b><br>
                • القطاع: {sector_filter}<br>
                • إجمالي الأسهم: {len(filtered)}<br>
                • 🕐 آخر تحديث: {st.session_state.last_update}
            </div>
            """, unsafe_allow_html=True)
    
    elif st.session_state.page == 'rapid':
        if st.button("🏠 العودة للرئيسية"): 
            st.session_state.page = 'home'
            st.rerun()
        
        st.title("⚡ قناص الاختراق السريع")
        st.markdown("""
        <div style="background: rgba(255,68,68,0.15); border-right: 4px solid #FF4444; padding: 10px; border-radius: 8px; margin-bottom: 20px;">
            🚀 <b>فرص خلال جلسة أو جلستين</b><br>
            • RSI بين 55-70 | • سيولة استثنائية > 2.5x | • قرب اختراق المقاومة | • وقف خسارة ضيق
        </div>
        """, unsafe_allow_html=True)
        
        sector_filter = st.session_state.sector_filter
        filtered = filter_by_sector(st.session_state.all_results, sector_filter)
        rapid_opportunities = get_rapid_breakouts(filtered)
        
        if rapid_opportunities:
            st.markdown(f"**⚡ عدد فرص الاختراق السريع: {len(rapid_opportunities)}**")
            for item in rapid_opportunities:
                stock = item['stock']
                analysis = item['analysis']
                
                st.markdown(f"""
                <div class="rapid-card" style="border-right-color: {analysis['color']};">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h3 style="margin: 0;">⚡ {stock['name']} - {stock['desc']}</h3>
                        <span style="background: {analysis['color']}; padding: 5px 15px; border-radius: 20px;">
                            {analysis['label']} | {analysis['strength']}%
                        </span>
                    </div>
                    <div style="height: 6px; background: #333; margin: 10px 0;">
                        <div style="width: {analysis['strength']}%; background: {analysis['color']}; height: 6px;"></div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 10px 0;">
                        <div>💰 {stock['p']:.2f} ج</div>
                        <div>📊 RSI: {stock['rsi']:.0f}</div>
                        <div>💧 سيولة: {stock['ratio']:.1f}x</div>
                        <div>📈 تغير: {stock['chg']:+.2f}%</div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 10px 0;">
                        <div style="background: #1f4f2b; border-radius: 8px; padding: 8px; text-align: center;">
                            🎯 هدف أول<br><b>{analysis['target_1']:.2f}</b>
                        </div>
                        <div style="background: #1f3a4f; border-radius: 8px; padding: 8px; text-align: center;">
                            🎯 هدف ثاني<br><b>{analysis['target_2']:.2f}</b>
                        </div>
                        <div style="background: #4a1a1a; border-radius: 8px; padding: 8px; text-align: center;">
                            🛑 وقف ضيق<br><b>{analysis['stop_loss_rapid']:.2f}</b>
                        </div>
                    </div>
                    <div style="background: rgba(255,68,68,0.1); border-radius: 8px; padding: 8px;">
                        ✅ {', '.join(analysis['reasons'])}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                with st.expander(f"📊 التحليل الكامل لسهم {stock['name']}"):
                    render_stock_card(stock)
                
                if st.button(f"💾 تسجيل الصفقة", key=f"rec_rapid_{stock['name']}"):
                    record_trade(stock, "اختراق سريع")
                    st.success("✅ تم تسجيل الصفقة!")
                st.markdown("---")
        else:
            st.info("ℹ️ لا توجد فرص اختراق سريع حالياً.")
    
    elif st.session_state.page == 'correction':
        if st.button("🏠 العودة للرئيسية"): 
            st.session_state.page = 'home'
            st.rerun()
        
        st.title("🎯 صائد التصحيحات")
        
        sector_filter = st.session_state.sector_filter
        filtered = filter_by_sector(st.session_state.all_results, sector_filter)
        
        corrections = []
        for an in filtered:
            if an and an.get('estimated_value', 0) >= 2000000:
                corr = is_correction(an, market_status['market_multiplier'])
                if corr.get('is_correction'):
                    corrections.append({'stock': an, 'analysis': corr})
        
        if corrections:
            corrections.sort(key=lambda x: x['analysis']['strength'], reverse=True)
            st.markdown(f"**🎯 عدد فرص التصحيح: {len(corrections)}**")
            for item in corrections:
                stock = item['stock']
                analysis = item['analysis']
                
                st.markdown(f"""
                <div class="correction-card" style="border-right-color: {analysis['color']};">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h3 style="margin: 0;">🎯 {stock['name']} - {stock['desc']}</h3>
                        <span style="background: {analysis['color']}; padding: 5px 15px; border-radius: 20px;">
                            {analysis['label']} | {analysis['strength']}%
                        </span>
                    </div>
                    <div style="height: 6px; background: #333; margin: 10px 0;">
                        <div style="width: {analysis['strength']}%; background: {analysis['color']}; height: 6px;"></div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 10px 0;">
                        <div>💰 {stock['p']:.2f} ج</div>
                        <div>📊 RSI: {stock['rsi']:.0f}</div>
                        <div>💧 سيولة: {stock['ratio']:.1f}x</div>
                        <div>📈 تغير: {stock['chg']:+.2f}%</div>
                    </div>
                    <div style="background: rgba(233,30,99,0.1); border-radius: 8px; padding: 8px;">
                        ✅ {', '.join(analysis['reasons'])}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                with st.expander(f"📊 التحليل الكامل لسهم {stock['name']}"):
                    render_stock_card(stock)
                
                if st.button(f"💾 تسجيل الصفقة", key=f"rec_corr_{stock['name']}"):
                    record_trade(stock, "صائد تصحيحات")
                    st.success("✅ تم تسجيل الصفقة!")
                st.markdown("---")
        else:
            st.info("ℹ️ لا توجد فرص تصحيح حالياً.")
    
    elif st.session_state.page == 'top10':
        if st.button("🏠 العودة للرئيسية"): 
            st.session_state.page = 'home'
            st.rerun()
        
        st.title("🏆 أفضل 10 فرص")
        
        sector_filter = st.session_state.sector_filter
        filtered = filter_by_sector(st.session_state.all_results, sector_filter)
        top = get_top_10(filtered)
        
        if top:
            for i, an in enumerate(top, 1):
                with st.expander(f"#{i} - {an['name']} | Smart: {an['smart_score']} | RR: {an['rr']} | RSI: {an['rsi']:.0f}"):
                    render_stock_card(an, is_top10=True)
                    if st.button(f"💾 تسجيل الصفقة", key=f"rec_top_{an['name']}"):
                        record_trade(an, "أفضل 10")
                        st.success("✅ تم تسجيل الصفقة!")
        else:
            st.warning("⚠️ لا توجد فرص مطابقة للمعايير حالياً.")
    
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
                    st.success("✅ تم تسجيل الصفقة!")
            else:
                st.error(f"❌ السهم '{sym}' غير موجود")
                symbols = [r.get('name') for r in st.session_state.all_results[:30] if r]
                if symbols:
                    st.info(f"💡 أمثلة: {', '.join(symbols[:15])}")
    
    elif st.session_state.page == 'performance':
        if st.button("🏠 العودة للرئيسية"): 
            st.session_state.page = 'home'
            st.rerun()
        
        st.title("📊 تقييم الأداء")
        trades = load_trades()
        stats = get_performance_stats(trades)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📊 إجمالي", stats['total'])
        col2.metric("✅ هدف", stats['hit_target'])
        col3.metric("❌ وقف", stats['stopped_out'])
        col4.metric("⏳ مفتوح", stats['still_open'])
        
        col1, col2 = st.columns(2)
        col1.metric("📈 نسبة النجاح", f"{stats['success_rate']}%")
        col2.metric("⚖️ متوسط RR", stats['avg_rr'])
        
        if trades:
            st.markdown("### 📋 آخر الصفقات")
            for trade in trades[-10:][::-1]:
                status = "🟢 هدف" if trade.get('status') == 'hit_target' else "🔴 وقف" if trade.get('status') == 'stopped_out' else "🟡 مفتوح"
                st.markdown(f"- {trade.get('name')} ({trade.get('trade_type')}) - {status} | دخول: {trade.get('entry_price', 0):.2f}")

if __name__ == "__main__":
    main()
