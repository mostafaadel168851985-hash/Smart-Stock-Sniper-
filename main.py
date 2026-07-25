import streamlit as st
import streamlit.components.v1 as components
import requests
from datetime import datetime
import json
import os
import urllib.parse
import time

# ================== إعدادات التطبيق ==================
st.set_page_config(
    page_title="🎯 EGX Sniper Pro Ultimate",
    layout="wide",
    page_icon="🎯"
)

# ================== CSS محسّن ==================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Tajawal', sans-serif;
}

.stButton>button {
    width: 100%;
    border-radius: 10px;
    height: 48px;
    font-weight: 700;
    font-size: 13px;
    border: 1px solid #30363d;
    background: #161b22;
    color: #c9d1d9;
    transition: all 0.2s;
}
.stButton>button:hover {
    background: #238636;
    color: white;
    border-color: #238636;
    transform: translateY(-1px);
}

.stock-header {
    font-size: 22px;
    font-weight: 800;
    color: #58a6ff;
    border-bottom: 2px solid #30363d;
    padding-bottom: 10px;
    margin-bottom: 15px;
}

.score-tag {
    float: right;
    background: linear-gradient(135deg, #238636, #2ea043);
    color: white;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 14px;
    font-weight: 700;
}

.opp-card {
    background: linear-gradient(135deg, #0d1117, #161b22);
    border-radius: 14px;
    padding: 18px;
    margin-bottom: 16px;
    border-right: 4px solid;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    transition: transform 0.2s;
}
.opp-card:hover {
    transform: translateX(-4px);
}

.metric-box {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 12px;
    text-align: center;
}

.entry-card {
    background: linear-gradient(135deg, #0d1f0d, #0a150a);
    border: 1px solid #238636;
    border-radius: 12px;
    padding: 16px;
    margin: 12px 0;
}

.risk-card {
    background: linear-gradient(135deg, #1a0a0a, #0d0a0a);
    border: 1px solid #f85149;
    border-radius: 12px;
    padding: 16px;
    margin: 12px 0;
}

.info-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
    margin: 2px;
}

.progress-bar {
    height: 8px;
    background: #21262d;
    border-radius: 4px;
    overflow: hidden;
    margin: 8px 0;
}
.progress-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.6s ease;
}

.reason-item {
    background: rgba(88, 166, 255, 0.08);
    border-right: 3px solid #58a6ff;
    padding: 6px 12px;
    margin: 4px 0;
    border-radius: 0 8px 8px 0;
    font-size: 13px;
}

.indicator-good { background: rgba(0, 200, 83, 0.15); color: #00c853; border: 1px solid #00c85344; }
.indicator-ok { background: rgba(255, 179, 0, 0.15); color: #ffb300; border: 1px solid #ffb30044; }
.indicator-bad { background: rgba(255, 82, 82, 0.15); color: #ff5252; border: 1px solid #ff525244; }

.market-banner {
    background: linear-gradient(90deg, #0d1117, #161b22);
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 14px;
    margin-bottom: 20px;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# ================== تهيئة Session State ==================
def init_session():
    defaults = {
        "mode": "⚖️ متوازن",
        "page": "home",
        "sector_filter": "🌍 الكل",
        "all_results": None,
        "last_update": None,
        "selected_stock": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

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
        "profit_pct": None
    })
    save_trades(trades)

def get_performance_stats(trades):
    trades = [t for t in trades if t is not None]
    total = len(trades)
    if total == 0:
        return {'total': 0, 'hit_target': 0, 'stopped_out': 0, 'still_open': 0, 'success_rate': 0, 'avg_rr': 0}
    hit_target = sum(1 for t in trades if t.get('status') == 'hit_target')
    stopped_out = sum(1 for t in trades if t.get('status') == 'stopped_out')
    still_open = sum(1 for t in trades if t.get('status') in ['pending', 'still_open'])
    closed = hit_target + stopped_out
    success_rate = (hit_target / closed * 100) if closed > 0 else 0
    avg_rr = sum(t.get('rr', 0) for t in trades) / total
    return {
        'total': total, 'hit_target': hit_target, 'stopped_out': stopped_out,
        'still_open': still_open, 'success_rate': round(success_rate, 1), 'avg_rr': round(avg_rr, 2)
    }

# ================== معايير نمط التداول ==================
def get_mode_thresholds(mode):
    modes = {
        "🛡️ محافظ": {
            "min_rr": 2.0, "rsi_low": 40, "rsi_high": 60,
            "min_turnover": 20_000_000, "min_smart_score": 65,
            "min_volatility": 1.0, "max_volatility": 4.0,
            "correction_rsi_max": 50, "breakout_rsi_max": 65,
            "early_rsi_max": 58
        },
        "⚖️ متوازن": {
            "min_rr": 1.5, "rsi_low": 35, "rsi_high": 70,
            "min_turnover": 5_000_000, "min_smart_score": 55,
            "min_volatility": 0.8, "max_volatility": 6.0,
            "correction_rsi_max": 55, "breakout_rsi_max": 72,
            "early_rsi_max": 65
        },
        "🚀 هجومي": {
            "min_rr": 1.2, "rsi_low": 30, "rsi_high": 75,
            "min_turnover": 1_000_000, "min_smart_score": 45,
            "min_volatility": 0.5, "max_volatility": 10.0,
            "correction_rsi_max": 60, "breakout_rsi_max": 78,
            "early_rsi_max": 72
        }
    }
    return modes.get(mode, modes["⚖️ متوازن"])

# ================== تحليل مؤشر EGX30 ==================
@st.cache_data(ttl=300, show_spinner=False)
def get_egx30_status():
    for attempt in range(3):
        try:
            url = "https://scanner.tradingview.com/egypt/scan"
            payload = {
                "filter": [{"left": "name", "operation": "match", "right": "EGX30"}],
                "columns": ["close", "RSI", "SMA50", "SMA200", "change", "ATR"],
                "range": [0, 2]
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Origin": "https://www.tradingview.com",
                "Referer": "https://www.tradingview.com/"
            }
            r = requests.post(url, json=payload, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json().get("data", [])
                for item in data:
                    d = item.get('d', [])
                    if len(d) >= 5 and d[0] is not None:
                        price = float(d[0])
                        rsi = float(d[1]) if d[1] is not None else 50
                        sma50 = float(d[2]) if d[2] is not None else price
                        sma200 = float(d[3]) if d[3] is not None else price
                        change = float(d[4]) if d[4] is not None else 0
                        atr = float(d[5]) if len(d) > 5 and d[5] is not None else price * 0.02
                        score = 0
                        if price > sma200: score += 1
                        if price > sma50: score += 1
                        if 40 < rsi < 70: score += 1
                        if change > -0.5: score += 1
                        if atr / price * 100 < 3: score += 1
                        if score >= 4:
                            status, color, mult = "🟢 سوق صاعد - مناسب للتداول", "#00C853", 1.0
                        elif score >= 3:
                            status, color, mult = "🟡 سوق متذبذب - تداول بحذر", "#FFB300", 0.75
                        else:
                            status, color, mult = "🔴 سوق هابط - ركز على التصحيحات فقط", "#FF5252", 0.5
                        return {"status": status, "color": color, "market_multiplier": mult,
                                "rsi": rsi, "change": change, "price": price, "atr": atr}
        except:
            time.sleep(1)
    return {"status": "🟡 سوق متذبذب (افتراضي)", "color": "#FFB300", "market_multiplier": 0.7,
            "rsi": 50, "change": 0, "price": 10000, "atr": 200}

# ================== فلتر القطاع ==================
SECTORS = {
    "🏦 البنوك": ["CIEB", "COMI", "AAIB", "QNBA", "ALEX", "BID", "CAE", "NBK", "CBKD", "SAIB"],
    "🏗️ العقارات": ["TMGH", "OCDI", "PHDC", "HELI", "DEGC", "MNHD", "DSC", "ELKA", "MEPA"],
    "🍔 الأغذية": ["BFR", "EFID", "JUFO", "ORWE", "EDFO", "BIF", "MCQE", "UEFM"],
    "📡 الاتصالات": ["ETEL", "OTMT", "TE", "EMOB", "EGS"],
    "🏭 الصناعات": ["ESRS", "MFPC", "SKPC", "ABUK", "EFIC", "EGCH", "MICH", "EGAL", "EFIH"],
    "🛒 التجارة": ["RAYA", "SWDY", "AUTO", "ELSE", "MENA", "CAPI", "AMER"],
    "⚡ الطاقة": ["EAST", "TAQA", "CEEB", "EPCO"],
    "💊 الصحة": ["PHAR", "MPCI", "ADCI", "SPIN"]
}

def get_sector(name):
    name_upper = str(name).upper()
    for sector, symbols in SECTORS.items():
        for sym in symbols:
            if sym in name_upper or name_upper.startswith(sym):
                return sector
    return "📌 أخرى"

def filter_by_sector(results, sector):
    if sector == "🌍 الكل" or not results:
        return results
    return [r for r in results if r and get_sector(r.get('name', '')) == sector]

# ================== تحميل البيانات من TradingView ==================
@st.cache_data(ttl=180, show_spinner=False)
def get_all_data():
    url = "https://scanner.tradingview.com/egypt/scan"
    cols = [
        "name", "close", "RSI", "volume", "average_volume_10d_calc",
        "high", "low", "change", "description",
        "SMA20", "SMA50", "SMA200", "open",
        "price_52_week_high", "price_52_week_low", "Perf.1M",
        "ATR", "MACD.macd", "MACD.signal", "Stoch.RSI.K",
        "market_cap_basic", "Perf.3M"
    ]
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
    for attempt in range(3):
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=30)
            if r.status_code == 200:
                return r.json().get("data", [])
            time.sleep(1)
        except:
            time.sleep(1)
    return []

@st.cache_data(ttl=180, show_spinner=False)
def fetch_single_stock(symbol):
    url = "https://scanner.tradingview.com/egypt/scan"
    cols = [
        "name", "close", "RSI", "volume", "average_volume_10d_calc",
        "high", "low", "change", "description",
        "SMA20", "SMA50", "SMA200", "open",
        "price_52_week_high", "price_52_week_low", "Perf.1M",
        "ATR", "MACD.macd", "MACD.signal", "Stoch.RSI.K",
        "market_cap_basic", "Perf.3M"
    ]
    payload = {
        "filter": [{"left": "name", "operation": "match", "right": symbol.upper()}],
        "columns": cols,
        "range": [0, 1]
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://www.tradingview.com",
        "Referer": "https://www.tradingview.com/"
    }
    for attempt in range(3):
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=20)
            if r.status_code == 200:
                results = r.json().get("data", [])
                if results:
                    return results
            time.sleep(1)
        except:
            time.sleep(1)
    return []

def safe_float(val, default=0.0):
    try:
        return float(val) if val is not None else default
    except:
        return default

# ================== محرك التحليل الفني ==================
def analyze_stock(d_row):
    try:
        d = d_row.get('d', [])
        if len(d) < 13:
            return None

        name = str(d[0]) if d[0] is not None else "N/A"
        p = safe_float(d[1])
        rsi = safe_float(d[2], 50)
        v = safe_float(d[3], 0)
        avg_v = safe_float(d[4], 0)
        h = safe_float(d[5], p)
        l = safe_float(d[6], p)
        chg = safe_float(d[7], 0)
        desc = str(d[8]) if d[8] is not None else name
        sma20 = safe_float(d[9], p)
        sma50 = safe_float(d[10], p)
        sma200 = safe_float(d[11], p)
        open_price = safe_float(d[12], p)
        high52 = safe_float(d[13], h)
        low52 = safe_float(d[14], l)
        perf_1m = safe_float(d[15], 0)
        atr = safe_float(d[16], p * 0.02)
        macd = safe_float(d[17], 0)
        macd_signal = safe_float(d[18], 0)
        stoch_k = safe_float(d[19], 50)
        market_cap = safe_float(d[20], 0)
        perf_3m = safe_float(d[21], 0)

        if p <= 0 or v <= 0:
            return None

        ratio = v / avg_v if avg_v > 0 else 0
        daily_turnover = p * v
        volatility = ((h - l) / p) * 100 if p > 0 and h > l else 0.5

        t_short = "صاعد" if p > sma20 else "هابط"
        t_med = "صاعد" if p > sma50 else "هابط"
        t_long = "صاعد" if p > sma200 else "هابط"

        pp = (p + h + l) / 3
        r1 = (2 * pp) - l
        r2 = pp + (h - l)
        s1 = (2 * pp) - h
        s2 = pp - (h - l)

        entry_price = p
        atr_mult = 2.0
        stop_loss = max(s1, p - (atr * atr_mult)) if s1 > 0 else p * 0.96
        target = max(r1, p + (atr * 3)) if r1 > 0 else p * 1.06

        profit_ps = target - entry_price
        loss_ps = entry_price - stop_loss
        if loss_ps <= 0:
            rr = 0
            risk_pct = 0
            target_pct = 0
        else:
            rr = round(profit_ps / loss_ps, 2)
            risk_pct = round((loss_ps / entry_price) * 100, 2)
            target_pct = round((profit_ps / entry_price) * 100, 2)

        prev_close = p / (1 + chg / 100) if chg != -100 else p
        prev_open = prev_close

        candle_patterns, candle_strength = analyze_candlestick_patterns(
            p, open_price, h, l, prev_close, prev_open, chg
        )

        upside_to_52w = round((high52 - p) / p * 100, 2) if high52 > p else 0.0

        temp = {
            't_short': t_short, 't_med': t_med, 't_long': t_long,
            'ratio': ratio, 'rsi': rsi, 'rr': rr, 'chg': chg,
            'daily_turnover': daily_turnover, 'candle_strength': candle_strength,
            'volatility': volatility, 'macd': macd, 'macd_signal': macd_signal,
            'stoch_k': stoch_k, 'perf_1m': perf_1m, 'perf_3m': perf_3m
        }
        smart_score = smart_score_pro(temp)

        return {
            "name": name, "desc": desc, "p": round(p, 3), "rsi": round(rsi, 1),
            "chg": chg, "ratio": round(ratio, 2), "volume": int(v),
            "avg_volume": int(avg_v), "daily_turnover": int(daily_turnover),
            "t_short": t_short, "t_med": t_med, "t_long": t_long,
            "s1": round(s1, 3), "s2": round(s2, 3), "r1": round(r1, 3), "r2": round(r2, 3),
            "pp": round(pp, 3), "sma20": round(sma20, 3), "sma50": round(sma50, 3),
            "sma200": round(sma200, 3), "open": round(open_price, 3),
            "high": round(h, 3), "low": round(l, 3),
            "high52": round(high52, 3), "low52": round(low52, 3),
            "perf_1m": perf_1m, "perf_3m": perf_3m,
            "upside_to_52w_high": upside_to_52w, "volatility": round(volatility, 2),
            "atr": round(atr, 3), "macd": round(macd, 3), "macd_signal": round(macd_signal, 3),
            "stoch_k": round(stoch_k, 1), "market_cap": int(market_cap),
            "entry_price": round(entry_price, 3), "stop_loss": round(stop_loss, 3),
            "target": round(target, 3), "rr": rr,
            "risk_pct": risk_pct, "target_pct": target_pct,
            "smart_score": smart_score,
            "candle_patterns": candle_patterns, "candle_strength": candle_strength
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

# ================== نماذج الشموع ==================
def analyze_candlestick_patterns(p, open_p, high, low, prev_close, prev_open, chg):
    patterns = []
    strength = 0
    body = abs(p - open_p)
    range_val = high - low if high > low else 0.001
    upper_wick = high - max(p, open_p)
    lower_wick = min(p, open_p) - low
    prev_body = abs(prev_close - prev_open) if prev_open else 0.001

    if lower_wick > body * 2 and upper_wick < body * 0.5 and chg > -2:
        patterns.append("🔨 مطرقة - انعكاس صاعد محتمل")
        strength += 3

    if upper_wick > body * 2 and lower_wick < body * 0.5 and chg > 0.5:
        patterns.append("⭐ شهاب - انعكاس هابط محتمل")
        strength -= 2

    if (p > open_p and prev_close < prev_open and
        p > prev_open and open_p < prev_close and body > prev_body * 1.1):
        patterns.append("🟢 ابتلاع صاعد - قوة شرائية")
        strength += 4

    if (p < open_p and prev_close > prev_open and
        p < prev_open and open_p > prev_close and body > prev_body * 1.1):
        patterns.append("🔴 ابتلاع هابط - قوة بيعية")
        strength -= 3

    if range_val > 0 and body < range_val * 0.08:
        patterns.append("✚ دوجي - تردد/توازن في السوق")

    if range_val > 0 and upper_wick < range_val * 0.05 and lower_wick < range_val * 0.05:
        if chg > 0:
            patterns.append("📈 ماروبوزو صاعد - قوة اتجاه شرائي")
            strength += 3
        else:
            patterns.append("📉 ماروبوزو هابط - قوة اتجاه بيعي")
            strength -= 2

    if body < range_val * 0.3 and upper_wick > body and lower_wick > body:
        patterns.append("🔄 غزل - تردد قبل حركة كبيرة")

    return patterns, strength

# ================== Smart Score ==================
def smart_score_pro(res):
    score = 0

    trend_w = 0
    if res.get('t_long') == "صاعد": trend_w += 45
    if res.get('t_med') == "صاعد": trend_w += 35
    if res.get('t_short') == "صاعد": trend_w += 20
    score += (trend_w / 100) * 25

    ratio = res.get('ratio', 0)
    turnover = res.get('daily_turnover', 0)
    vol_score = 20
    if ratio > 3: vol_score = 100
    elif ratio > 2: vol_score = 85
    elif ratio > 1.5: vol_score = 70
    elif ratio > 1: vol_score = 50
    elif ratio > 0.7: vol_score = 35
    if turnover > 50_000_000: vol_score += 10
    elif turnover > 20_000_000: vol_score += 5
    score += (min(100, vol_score) / 100) * 20

    rsi = res.get('rsi', 50)
    if 45 <= rsi <= 60: rsi_score = 100
    elif 40 <= rsi <= 65: rsi_score = 80
    elif 35 <= rsi <= 70: rsi_score = 60
    elif 30 <= rsi <= 75: rsi_score = 40
    else: rsi_score = 20
    score += (rsi_score / 100) * 15

    rr = res.get('rr', 0)
    if rr >= 3: rr_score = 100
    elif rr >= 2.5: rr_score = 90
    elif rr >= 2: rr_score = 75
    elif rr >= 1.5: rr_score = 55
    elif rr >= 1.2: rr_score = 35
    else: rr_score = 15
    score += (rr_score / 100) * 15

    chg = res.get('chg', 0)
    if chg > 3: pa = 100
    elif chg > 1.5: pa = 80
    elif chg > 0.5: pa = 60
    elif chg > 0: pa = 40
    elif chg > -1: pa = 25
    else: pa = 10
    score += (pa / 100) * 10

    macd = res.get('macd', 0)
    macd_sig = res.get('macd_signal', 0)
    if macd > macd_sig and macd > 0: macd_score = 100
    elif macd > macd_sig: macd_score = 70
    elif macd > 0: macd_score = 40
    else: macd_score = 20
    score += (macd_score / 100) * 10

    cs = res.get('candle_strength', 0)
    if cs >= 3: score += 5
    elif cs >= 1: score += 2
    elif cs <= -2: score -= 4

    return min(100, max(0, int(score)))

# ================== نظام الثقة مع تقييم المؤشرات ==================
def get_indicator_rating(rsi, ratio, turnover, rr, volatility, thresholds):
    """تقييم كل مؤشر بشكل منفصل مع شرح"""
    ratings = {}

    # RSI
    if 45 <= rsi <= 60:
        ratings['rsi'] = ("🟢 ممتاز", f"RSI في المنطقة المثالية ({rsi:.0f}) - زخم متوازن")
    elif 40 <= rsi <= 65:
        ratings['rsi'] = ("🟡 جيد", f"RSI مقبول ({rsi:.0f}) - قريب من المثالي")
    elif 35 <= rsi <= 70:
        ratings['rsi'] = ("🟠 متوسط", f"RSI محايد ({rsi:.0f}) - يراقب")
    else:
        ratings['rsi'] = ("🔴 ضعيف", f"RSI بعيد عن المثالي ({rsi:.0f}) - تشبع أو ضعف")

    # Volume Ratio
    if ratio > 2.5:
        ratings['volume'] = ("🟢 ممتاز", f"سيولة استثنائية ({ratio:.1f}x المتوسط)")
    elif ratio > 1.8:
        ratings['volume'] = ("🟢 جيد جداً", f"سيولة قوية ({ratio:.1f}x المتوسط)")
    elif ratio > 1.2:
        ratings['volume'] = ("🟡 جيد", f"سيولة مقبولة ({ratio:.1f}x المتوسط)")
    else:
        ratings['volume'] = ("🔴 ضعيف", f"سيولة منخفضة ({ratio:.1f}x المتوسط)")

    # Turnover
    if turnover >= 50_000_000:
        ratings['turnover'] = ("🟢 ممتاز", f"تداول ضخم ({turnover/1_000_000:.0f}M جنيه)")
    elif turnover >= 20_000_000:
        ratings['turnover'] = ("🟢 جيد", f"تداول قوي ({turnover/1_000_000:.0f}M جنيه)")
    elif turnover >= 5_000_000:
        ratings['turnover'] = ("🟡 مقبول", f"تداول متوسط ({turnover/1_000_000:.1f}M جنيه)")
    else:
        ratings['turnover'] = ("🔴 ضعيف", f"تداول ضعيف ({turnover/1_000_000:.1f}M جنيه)")

    # RR
    if rr >= 2.5:
        ratings['rr'] = ("🟢 ممتاز", f"نسبة مخاطرة/عائد ممتازة ({rr})")
    elif rr >= 2:
        ratings['rr'] = ("🟢 جيد", f"نسبة مخاطرة/عائد جيدة ({rr})")
    elif rr >= 1.5:
        ratings['rr'] = ("🟡 مقبول", f"نسبة مخاطرة/عائد مقبولة ({rr})")
    else:
        ratings['rr'] = ("🔴 ضعيف", f"نسبة مخاطرة/عائد ضعيفة ({rr})")

    # Volatility
    if thresholds['min_volatility'] <= volatility <= thresholds['max_volatility']:
        ratings['volatility'] = ("🟢 مناسب", f"تقلب مناسب للتداول ({volatility:.1f}%)")
    elif volatility < thresholds['min_volatility']:
        ratings['volatility'] = ("🔴 منخفض", f"تقلب منخفض جداً ({volatility:.1f}%) - سهم ميت")
    else:
        ratings['volatility'] = ("🟠 مرتفع", f"تقلب مرتفع ({volatility:.1f}%) - حذر")

    return ratings

def get_confidence(res, thresholds):
    score = 0
    total = 9

    p = res.get('p', 0)
    rsi = res.get('rsi', 50)
    ratio = res.get('ratio', 0)
    change = res.get('chg', 0)
    t_short = res.get('t_short', 'هابط')
    t_med = res.get('t_med', 'هابط')
    t_long = res.get('t_long', 'هابط')
    turnover = res.get('daily_turnover', 0)
    candle_strength = res.get('candle_strength', 0)
    macd = res.get('macd', 0)
    macd_sig = res.get('macd_signal', 0)
    rr = res.get('rr', 0)

    checks = [
        t_long == "صاعد" or p > res.get('sma200', p),
        t_med == "صاعد" and t_short == "صاعد",
        thresholds['rsi_low'] < rsi < thresholds['rsi_high'],
        ratio > 1.2,
        turnover >= thresholds['min_turnover'],
        change > 0,
        macd > macd_sig,
        rr >= thresholds['min_rr'],
        candle_strength >= 1
    ]
    score = sum(checks)
    pct = int((score / total) * 100)

    if pct >= 80: return {"grade": "A+", "advice": "🔥 فرصة عالية الجودة", "color": "#00C853", "emoji": "🔥", "score": pct}
    elif pct >= 65: return {"grade": "A", "advice": "✅ فرصة جيدة", "color": "#69F0AE", "emoji": "✅", "score": pct}
    elif pct >= 50: return {"grade": "B", "advice": "🟡 فرصة متوسطة - تحتاج متابعة", "color": "#FFD600", "emoji": "🟡", "score": pct}
    elif pct >= 35: return {"grade": "C", "advice": "⚠️ فرصة ضعيفة - مؤشرات متضاربة", "color": "#FF9100", "emoji": "⚠️", "score": pct}
    else: return {"grade": "D", "advice": "❌ تجنب - معظم المؤشرات سلبية", "color": "#FF5252", "emoji": "❌", "score": pct}

# ================== كاشف الفرص (مُصلح بالكامل) ==================
def is_correction_hunter(an, thresholds, market_mult=1.0):
    if an is None: 
        return False, [], 0, "", ""

    p = an.get('p', 0)
    rsi = an.get('rsi', 50)
    sma200 = an.get('sma200', 0)
    chg = an.get('chg', 0)
    turnover = an.get('daily_turnover', 0)
    t_long = an.get('t_long', 'هابط')
    rr = an.get('rr', 0)
    candle = an.get('candle_strength', 0)
    volatility = an.get('volatility', 1.5)

    reasons = []
    score = 0
    max_s = 10

    if not (t_long == "صاعد" or (sma200 and p > sma200)):
        return False, ["❌ الاتجاه العام هابط - غير مناسب للتصحيح"], 0, "", ""

    score += 2
    reasons.append("📈 الاتجاه العام صاعد - السهم في ترند صاعد")

    if rsi <= thresholds['correction_rsi_max']:
        score += 3
        if rsi < 35:
            reasons.append(f"🔻 RSI منخفض جداً ({rsi:.0f}) - تشبع بيع ممتاز للدخول")
        elif rsi < 45:
            reasons.append(f"🔻 RSI منخفض ({rsi:.0f}) - منطقة تصحيح جيدة")
        else:
            reasons.append(f"📊 RSI في منطقة محايدة ({rsi:.0f}) - بداية تعافي")
    else:
        return False, [f"❌ RSI مرتفع ({rsi:.0f}) - السهم ليس في تصحيح"], 0, "", ""

    if chg > 0:
        score += 2
        reasons.append(f"📈 السعر يرتد (+{chg:.2f}%) - بداية ارتداد واضحة")
    elif chg > -1:
        score += 1
        reasons.append(f"⚖️ استقرار السعر ({chg:.2f}%) - توقف الهبوط")

    if turnover >= thresholds['min_turnover']:
        score += 1.5
        reasons.append(f"💰 سيولة كافية ({turnover/1_000_000:.1f}M جنيه) - سهل الدخول والخروج")

    if rr >= thresholds['min_rr']:
        score += 1
        reasons.append(f"⚖️ RR جيد ({rr}) - المكسب يستحق المخاطرة")

    if candle >= 2:
        score += 1
        reasons.append("🕯️ نماذج شموع إيجابية - إشارة انعكاس")

    if thresholds['min_volatility'] <= volatility <= thresholds['max_volatility']:
        score += 0.5
        reasons.append(f"📊 تقلب مناسب ({volatility:.1f}%) - حركة كافية للربح")

    adj = score * market_mult
    strength = min(100, int((adj / max_s) * 100))

    if strength >= 75: 
        label, color = "🔥🔥 فرصة تصحيح ممتازة جداً", "#1B5E20"
    elif strength >= 60: 
        label, color = "🔥 فرصة تصحيح ممتازة", "#2E7D32"
    elif strength >= 45: 
        label, color = "✅ فرصة تصحيح جيدة", "#388E3C"
    else: 
        label, color = "🟡 فرصة تصحيح محتملة", "#F57C00"

    return score >= 4, reasons, strength, label, color

def is_rapid_breakout(an, thresholds):
    if an is None:
        return {"is_breakout": False}

    p = an.get('p', 0)
    rsi = an.get('rsi', 50)
    r1 = an.get('r1', p * 1.05)
    turnover = an.get('daily_turnover', 0)
    chg = an.get('chg', 0)
    t_short = an.get('t_short', 'هابط')
    t_med = an.get('t_med', 'هابط')
    candle = an.get('candle_strength', 0)
    high = an.get('high', p)
    low = an.get('low', p)

    if not (thresholds['rsi_low'] <= rsi <= thresholds['breakout_rsi_max']):
        return {"is_breakout": False}
    if turnover < thresholds['min_turnover']:
        return {"is_breakout": False}

    reasons = []
    score = 0
    max_s = 10

    close_str = (p - low) / (high - low) * 100 if (high - low) > 0 else 50
    near_high = (high - p) / p * 100 if p > 0 else 0

    if 50 <= rsi <= thresholds['breakout_rsi_max']:
        score += 2
        reasons.append(f"⚡ زخم قوي (RSI: {rsi:.0f}) - السعر يتجه للاختراق")

    if turnover >= 20_000_000:
        score += 2.5
        reasons.append("💥 سيولة استثنائية - دعم قوي للاختراق")
    elif turnover >= thresholds['min_turnover']:
        score += 1.5
        reasons.append("📊 سيولة جيدة - كافية للاختراق")

    if p >= r1 * 0.995:
        score += 3
        reasons.append(f"🎯 السعر عند المقاومة ({r1:.3f}) - جاهز للاختراق")
    elif p >= r1 * 0.98:
        score += 2
        reasons.append(f"📍 السهم قريب جداً من المقاومة ({r1:.3f})")
    else:
        return {"is_breakout": False}

    if close_str >= 75:
        score += 2
        reasons.append(f"💪 إغلاق قوي ({close_str:.0f}%) - اختراق حقيقي وليس وهمي")
    elif close_str >= 60:
        score += 1
        reasons.append(f"📊 إغلاق جيد ({close_str:.0f}%)")

    if t_short == "صاعد" and t_med == "صاعد":
        score += 1
        reasons.append("📈 جميع الاتجاهات صاعدة - دعم قوي للاختراق")

    if candle >= 2:
        score += 1
        reasons.append("🕯️ نماذج شموع قوية تدعم الاختراق")

    strength = min(100, int((score / max_s) * 100))
    if strength < 40:
        return {"is_breakout": False}

    if strength >= 75:
        label, color = "🔥🔥 انفجار وشيك خلال ساعات", "#FF1744"
    elif strength >= 60:
        label, color = "🔥 اختراق قوي متوقع خلال الجلسة", "#FF5252"
    else:
        label, color = "⚡ مراقبة لاصطياد الاختراق", "#FFB300"

    return {
        "is_breakout": True, "reasons": reasons, "strength": strength,
        "label": label, "color": color,
        "target_1": r1, "target_2": an.get('r2', r1 * 1.03),
        "stop_loss_rapid": max(an.get('s1', p * 0.98), p - an.get('atr', p * 0.02) * 1.5)
    }

def is_support_with_bounce(an, thresholds):
    if an is None:
        return False, [], 0, "عادي"

    s1 = an.get('s1', 0)
    s2 = an.get('s2', 0)
    p = an.get('p', 0)
    chg = an.get('chg', 0)
    rsi = an.get('rsi', 50)
    turnover = an.get('daily_turnover', 0)
    sma20 = an.get('sma20', p)
    candle = an.get('candle_strength', 0)

    if s1 == 0 and s2 == 0:
        return False, [], 0, "عادي"

    ns = s1 if s1 > 0 else s2
    dist = (p - ns) / ns * 100 if ns > 0 else 999

    if dist < 0:
        return False, ["❌ كسر الدعم - خطر على السهم"], 0, "مكسور"
    if dist >= 1.5:
        return False, [], 0, "عادي"

    level = "عند الدعم" if dist < 0.5 else "قريب جداً" if dist < 1.0 else "قريب من الدعم"
    reasons = []
    score = 0
    max_s = 8

    if 0.1 < chg < 4:
        score += 2
        reasons.append(f"📈 ارتداد واضح (+{chg:.2f}%) - السعر يرتد من الدعم")
    elif 0 < chg <= 0.1:
        score += 1
        reasons.append(f"📈 بداية ارتداد (+{chg:.2f}%)")
    elif chg >= 4:
        return False, ["⚠️ ارتفاع كبير - احترس من القمة"], 0, level
    elif chg <= 0:
        return False, ["❌ السعر لم يرتد بعد - انتظر تأكيد"], 0, level

    if rsi > 40:
        score += 2
        reasons.append(f"📊 RSI يتعافى ({rsi:.0f}) - الزخم يتحسن")
    elif rsi > 35:
        score += 1
        reasons.append(f"📊 RSI قريب من التعافي ({rsi:.0f})")

    if turnover >= thresholds['min_turnover']:
        score += 1.5
        reasons.append(f"💰 سيولة كافية ({turnover/1_000_000:.1f}M جنيه)")

    if p > sma20:
        score += 1
        reasons.append("📈 السعر فوق SMA20 - بداية تكون قاع")

    if candle >= 2:
        score += 1
        reasons.append("🕯️ نماذج شموع إيجابية عند الدعم")

    is_valid = score >= 4
    if is_valid:
        reasons.append(f"✅ نقاط الارتداد: {score}/{max_s} - مناسب للدخول")

    return is_valid, reasons, score, level

def is_early_uptrend(an, thresholds, market_mult=1.0):
    if an is None:
        return False, [], 0, "", "", 0

    p = an.get('p', 0)
    high52 = an.get('high52', p)
    rsi = an.get('rsi', 50)
    chg = an.get('chg', 0)
    t_short = an.get('t_short', 'هابط')
    t_med = an.get('t_med', 'هابط')
    t_long = an.get('t_long', 'هابط')
    turnover = an.get('daily_turnover', 0)
    perf_1m = an.get('perf_1m', 0)
    candle = an.get('candle_strength', 0)
    macd = an.get('macd', 0)
    macd_sig = an.get('macd_signal', 0)

    if p <= 0 or high52 <= 0:
        return False, [], 0, "", "", 0

    upside = round((high52 - p) / p * 100, 2) if high52 > p else 0.0

    if upside < 20:
        return False, [f"❌ مساحة الصعود ضعيفة ({upside:.1f}%) - لا يوجد هدف حقيقي"], 0, "", "", upside

    reasons = []
    score = 0
    max_s = 12

    if upside >= 40:
        score += 3
        reasons.append(f"🚀 مساحة صعود ضخمة ({upside:.1f}%) - هدف كبير متاح")
    elif upside >= 30:
        score += 2.5
        reasons.append(f"📈 مساحة صعود كبيرة ({upside:.1f}%)")
    else:
        score += 2
        reasons.append(f"📈 مساحة صعود جيدة ({upside:.1f}%)")

    if t_short != "صاعد":
        return False, ["❌ السهم لم يخترق المتوسط القصير بعد - مبكر جداً"], 0, "", "", upside

    score += 2
    reasons.append("✅ السهم اخترق SMA20 - بداية اتجاه صاعد")

    if t_med == "صاعد" and t_long != "صاعد":
        score += 2
        reasons.append("🌱 بداية انعكاس حقيقي - المدى المتوسط تحول صاعد")
    elif t_med == "صاعد":
        score += 1
        reasons.append("📊 الاتجاه المتوسط صاعد - الموجة مستمرة")
    else:
        score += 0.5
        reasons.append("⏳ الاتجاه المتوسط لم يتأكد - إشارة مبكرة")

    if 40 <= rsi <= thresholds['early_rsi_max']:
        score += 2
        reasons.append(f"⚡ RSI مثالي ({rsi:.0f}) - زخم صاعد بدون تشبع")
    elif 35 <= rsi < 40:
        score += 1
        reasons.append(f"📊 RSI يتعافى ({rsi:.0f}) - بدأ يتحسن")
    else:
        return False, [f"❌ RSI غير مناسب ({rsi:.0f}) - خارج نطاق بداية الموجة"], 0, "", "", upside

    if chg > 1:
        score += 1.5
        reasons.append(f"📈 زخم إيجابي قوي (+{chg:.2f}%)")
    elif chg > 0:
        score += 1
        reasons.append(f"📈 زخم إيجابي (+{chg:.2f}%)")
    elif chg > -1:
        score += 0.5
        reasons.append(f"⚖️ استقرار السعر ({chg:.2f}%)")
    else:
        return False, ["❌ السهم لا يزال في زخم سلبي"], 0, "", "", upside

    if perf_1m > 0:
        score += 1
        reasons.append(f"📆 أداء الشهر إيجابي ({perf_1m:+.1f}%)")
    elif perf_1m > -10:
        score += 0.5
        reasons.append(f"📆 أداء الشهر مستقر ({perf_1m:+.1f}%)")

    if turnover >= thresholds['min_turnover']:
        score += 1.5
        reasons.append(f"💰 سيولة كافية ({turnover/1_000_000:.1f}M جنيه)")

    if macd > macd_sig:
        score += 1
        reasons.append("📊 MACD إيجابي - زخم صاعد")

    if candle >= 2:
        score += 1
        reasons.append("🕯️ نماذج شموع داعمة للانعكاس")

    adj = score * market_mult
    strength = min(100, int((adj / max_s) * 100))

    if strength >= 70:
        label, color = "🚀🚀 بداية موجة صاعدة قوية جداً", "#00C853"
    elif strength >= 55:
        label, color = "🚀 بداية موجة صاعدة واعدة", "#43A047"
    elif strength >= 40:
        label, color = "🌱 بداية موجة صاعدة محتملة", "#FDD835"
    else:
        label, color = "🟡 إشارة مبكرة - تحتاج تأكيد", "#FB8C00"

    return score >= 5, reasons, strength, label, color, upside

# ================== جامعات الفرص ==================
def get_top_10(results, thresholds):
    valid = [r for r in results if r and r.get('smart_score', 0) >= thresholds['min_smart_score']]
    valid = [r for r in valid if r.get('daily_turnover', 0) >= thresholds['min_turnover']]
    valid = [r for r in valid if thresholds['min_volatility'] <= r.get('volatility', 1.5) <= thresholds['max_volatility']]
    valid.sort(key=lambda x: x.get('smart_score', 0), reverse=True)
    return valid[:10]

def get_rapid_breakouts(results, thresholds):
    rapid = []
    for r in results:
        if r and r.get('daily_turnover', 0) >= thresholds['min_turnover']:
            a = is_rapid_breakout(r, thresholds)
            if a.get('is_breakout'):
                rapid.append({'stock': r, 'analysis': a})
    rapid.sort(key=lambda x: x['analysis']['strength'], reverse=True)
    return rapid[:8]

def get_corrections(results, thresholds, market_mult):
    corr = []
    for r in results:
        if r and r.get('daily_turnover', 0) >= thresholds['min_turnover']:
            ok, reasons, strength, label, color = is_correction_hunter(r, thresholds, market_mult)
            if ok:
                corr.append({'stock': r, 'reasons': reasons, 'strength': strength, 'label': label, 'color': color})
    corr.sort(key=lambda x: x['strength'], reverse=True)
    return corr

def get_support_stocks(results, thresholds):
    sup = []
    for r in results:
        if r and r.get('daily_turnover', 0) >= thresholds['min_turnover']:
            ok, reasons, score, level = is_support_with_bounce(r, thresholds)
            if ok:
                sup.append({'stock': r, 'reasons': reasons, 'score': score, 'level': level})
    sup.sort(key=lambda x: x['score'], reverse=True)
    return sup

def get_early_uptrend_stocks(results, thresholds, market_mult):
    picks = []
    for r in results:
        if r and r.get('daily_turnover', 0) >= thresholds['min_turnover']:
            ok, reasons, strength, label, color, upside = is_early_uptrend(r, thresholds, market_mult)
            if ok:
                picks.append({'stock': r, 'reasons': reasons, 'strength': strength, 'label': label, 'color': color, 'upside': upside})
    picks.sort(key=lambda x: x['strength'], reverse=True)
    return picks

def get_fresh_data():
    with st.spinner("🔄 جاري تحليل السوق..."):
        raw = get_all_data()
        if raw:
            st.session_state.all_results = preprocess(raw)
            st.session_state.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return True
    return False

# ================== مكونات الواجهة ==================
def render_chart(symbol, height=400):
    full = f"EGX:{symbol}"
    html = f"""
    <div class="tradingview-widget-container">
        <div id="tv_{symbol}"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>
        new TradingView.widget({{
            "container_id": "tv_{symbol}",
            "width": "100%", "height": {height},
            "symbol": "{full}", "interval": "D",
            "timezone": "Africa/Cairo", "theme": "dark",
            "style": "1", "locale": "ar", "hideideas": true,
            "studies": ["RSI@tv-basicstudies","MASimple@tv-basicstudies","MACD@tv-basicstudies"]
        }});
        </script>
    </div>
    """
    components.html(html, height=height)

def render_opportunity_card(item, card_type, thresholds):
    """بطاقة فرصة موحدة مع شرح واضح"""
    an = item['stock']

    if card_type == "correction":
        strength, label, color = item['strength'], item['label'], item['color']
        reasons = item['reasons']
        icon = "🎯"
        border_color = color
    elif card_type == "rapid":
        strength, label, color = item['analysis']['strength'], item['analysis']['label'], item['analysis']['color']
        reasons = item['analysis']['reasons']
        icon = "⚡"
        border_color = color
    elif card_type == "support":
        strength = min(item['score'] * 12, 100)
        label = f"نقاط: {item['score']}/8"
        color = "#2196f3"
        reasons = item['reasons']
        icon = "🔻"
        border_color = color
    elif card_type == "early":
        strength, label, color = item['strength'], item['label'], item['color']
        reasons = item['reasons']
        icon = "🚀"
        border_color = color
    else:
        strength, label, color, reasons, icon = 0, "", "#888", [], "📊"
        border_color = "#888"

    # تقييم المؤشرات
    ratings = get_indicator_rating(an['rsi'], an['ratio'], an['daily_turnover'], an['rr'], an['volatility'], thresholds)

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #0d1117, #161b22); border-radius: 14px; padding: 18px; margin-bottom: 16px; border-right: 4px solid {border_color}; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <h4 style="margin:0; color:#e0e0e0; font-size: 18px;">{icon} {an['name']} - {an['desc']}</h4>
            <span style="background: {color}22; color: {color}; padding: 5px 16px; border-radius: 20px; font-weight: 700; font-size: 13px; border: 1px solid {color}44;">
                {label}
            </span>
        </div>
        <div style="height: 6px; background: #21262d; margin: 12px 0; border-radius: 3px;">
            <div style="width: {min(strength, 100)}%; background: {color}; height: 6px; border-radius: 3px;"></div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; font-size: 14px; color: #8b949e; margin-bottom: 12px;">
            <div style="text-align:center; background:#0d1117; padding:8px; border-radius:8px; border:1px solid #30363d;">
                <div style="font-size:12px; color:#58a6ff;">السعر</div>
                <div style="font-weight:700; color:#e0e0e0;">{an['p']:.3f} ج</div>
            </div>
            <div style="text-align:center; background:#0d1117; padding:8px; border-radius:8px; border:1px solid #30363d;">
                <div style="font-size:12px; color:#58a6ff;">RSI</div>
                <div style="font-weight:700; color:#e0e0e0;">{an['rsi']:.0f}</div>
            </div>
            <div style="text-align:center; background:#0d1117; padding:8px; border-radius:8px; border:1px solid #30363d;">
                <div style="font-size:12px; color:#58a6ff;">التداول</div>
                <div style="font-weight:700; color:#e0e0e0;">{an['daily_turnover']/1_000_000:.1f}M</div>
            </div>
            <div style="text-align:center; background:#0d1117; padding:8px; border-radius:8px; border:1px solid #30363d;">
                <div style="font-size:12px; color:#58a6ff;">التغير</div>
                <div style="font-weight:700; color:{'#3fb950' if an['chg'] >= 0 else '#f85149'};">{an['chg']:+.2f}%</div>
            </div>
        </div>
        <div style="margin-bottom: 10px;">
            <div style="font-size: 12px; color: #8b949e; margin-bottom: 6px;">📊 <b>تقييم المؤشرات:</b></div>
            <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                <span class="info-badge" style="background: {ratings['rsi'][0][:2] == '🟢' and 'rgba(0,200,83,0.15)' or ratings['rsi'][0][:2] == '🟡' and 'rgba(255,179,0,0.15)' or 'rgba(255,82,82,0.15)'}; color: {ratings['rsi'][0][:2] == '🟢' and '#00c853' or ratings['rsi'][0][:2] == '🟡' and '#ffb300' or '#ff5252'}; border: 1px solid {ratings['rsi'][0][:2] == '🟢' and '#00c85344' or ratings['rsi'][0][:2] == '🟡' and '#ffb30044' or '#ff525244'};">{ratings['rsi'][0]} RSI</span>
                <span class="info-badge" style="background: {ratings['volume'][0][:2] == '🟢' and 'rgba(0,200,83,0.15)' or ratings['volume'][0][:2] == '🟡' and 'rgba(255,179,0,0.15)' or 'rgba(255,82,82,0.15)'}; color: {ratings['volume'][0][:2] == '🟢' and '#00c853' or ratings['volume'][0][:2] == '🟡' and '#ffb300' or '#ff5252'}; border: 1px solid {ratings['volume'][0][:2] == '🟢' and '#00c85344' or ratings['volume'][0][:2] == '🟡' and '#ffb30044' or '#ff525244'};">{ratings['volume'][0]} سيولة</span>
                <span class="info-badge" style="background: {ratings['rr'][0][:2] == '🟢' and 'rgba(0,200,83,0.15)' or ratings['rr'][0][:2] == '🟡' and 'rgba(255,179,0,0.15)' or 'rgba(255,82,82,0.15)'}; color: {ratings['rr'][0][:2] == '🟢' and '#00c853' or ratings['rr'][0][:2] == '🟡' and '#ffb300' or '#ff5252'}; border: 1px solid {ratings['rr'][0][:2] == '🟢' and '#00c85344' or ratings['rr'][0][:2] == '🟡' and '#ffb30044' or '#ff525244'};">{ratings['rr'][0]} RR</span>
                <span class="info-badge" style="background: {ratings['volatility'][0][:2] == '🟢' and 'rgba(0,200,83,0.15)' or ratings['volatility'][0][:2] == '🟡' and 'rgba(255,179,0,0.15)' or 'rgba(255,82,82,0.15)'}; color: {ratings['volatility'][0][:2] == '🟢' and '#00c853' or ratings['volatility'][0][:2] == '🟡' and '#ffb300' or '#ff5252'}; border: 1px solid {ratings['volatility'][0][:2] == '🟢' and '#00c85344' or ratings['volatility'][0][:2] == '🟡' and '#ffb30044' or '#ff525244'};">{ratings['volatility'][0]} تقلب</span>
            </div>
        </div>
        <div style="background: rgba(88, 166, 255, 0.05); border-radius: 8px; padding: 10px; border: 1px solid #30363d;">
            <div style="font-size: 12px; color: #58a6ff; margin-bottom: 6px;">💡 <b>ليه الفرصة دي كويسة؟</b></div>
            <div style="font-size: 13px; color: #c9d1d9; line-height: 1.8;">
                {'<br>'.join([f"• {r}" for r in reasons[:5]])}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button(f"📊 تحليل كامل لـ {an['name']}", key=f"btn_{card_type}_{an['name']}"):
        st.session_state.selected_stock = an
        st.session_state.page = 'detail'
        st.rerun()


def render_stock_detail(res, thresholds):
    if res is None:
        st.warning("بيانات غير متوفرة")
        return

    conf = get_confidence(res, thresholds)
    ratings = get_indicator_rating(res['rsi'], res['ratio'], res['daily_turnover'], res['rr'], res['volatility'], thresholds)

    st.markdown(f"""
    <div style="background: linear-gradient(90deg, #0d1117, #161b22); padding: 18px; border-radius: 14px; border-right: 5px solid {conf['color']}; margin-bottom: 18px;">
        <h2 style="margin:0; color:#58a6ff; font-size: 24px;">📈 {res['name']} - {res['desc']}</h2>
        <div style="display:flex; gap:12px; margin-top:10px; flex-wrap:wrap;">
            <span style="background:{conf['color']}22; color:{conf['color']}; padding:5px 14px; border-radius:20px; font-weight:700; border:1px solid {conf['color']}44;">{conf['emoji']} {conf['grade']} - {conf['advice']}</span>
            <span style="background:#23863622; color:#3fb950; padding:5px 14px; border-radius:20px; font-weight:700; border:1px solid #23863644;">Smart: {res['smart_score']}/100</span>
            <span style="background:#58a6ff22; color:#58a6ff; padding:5px 14px; border-radius:20px; font-weight:700; border:1px solid #58a6ff44;">RR: {res['rr']}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Metrics
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("السعر", f"{res['p']:.3f}", f"{res['chg']:+.2f}%")
    m2.metric("Smart Score", res['smart_score'])
    m3.metric("RR", res['rr'])
    m4.metric("RSI", f"{res['rsi']:.1f}")
    m5.metric("التداول", f"{res['daily_turnover']/1_000_000:.1f}M")
    m6.metric("التقلب", f"{res['volatility']:.1f}%")

    # Indicator Ratings
    st.markdown("### 📊 تقييم المؤشرات")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"<div style='background:#0d1117; border:1px solid #30363d; padding:12px; border-radius:10px; text-align:center;'><div style='font-size:24px;'>{ratings['rsi'][0][:2]}</div><div style='font-weight:700; color:{ratings['rsi'][0][:2] == '🟢' and '#00c853' or ratings['rsi'][0][:2] == '🟡' and '#ffb300' or '#ff5252'};'>RSI</div><div style='font-size:12px; color:#8b949e;'>{ratings['rsi'][1]}</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div style='background:#0d1117; border:1px solid #30363d; padding:12px; border-radius:10px; text-align:center;'><div style='font-size:24px;'>{ratings['volume'][0][:2]}</div><div style='font-weight:700; color:{ratings['volume'][0][:2] == '🟢' and '#00c853' or ratings['volume'][0][:2] == '🟡' and '#ffb300' or '#ff5252'};'>السيولة</div><div style='font-size:12px; color:#8b949e;'>{ratings['volume'][1]}</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div style='background:#0d1117; border:1px solid #30363d; padding:12px; border-radius:10px; text-align:center;'><div style='font-size:24px;'>{ratings['rr'][0][:2]}</div><div style='font-weight:700; color:{ratings['rr'][0][:2] == '🟢' and '#00c853' or ratings['rr'][0][:2] == '🟡' and '#ffb300' or '#ff5252'};'>RR Ratio</div><div style='font-size:12px; color:#8b949e;'>{ratings['rr'][1]}</div></div>", unsafe_allow_html=True)
    with c4:
        st.markdown(f"<div style='background:#0d1117; border:1px solid #30363d; padding:12px; border-radius:10px; text-align:center;'><div style='font-size:24px;'>{ratings['volatility'][0][:2]}</div><div style='font-weight:700; color:{ratings['volatility'][0][:2] == '🟢' and '#00c853' or ratings['volatility'][0][:2] == '🟡' and '#ffb300' or '#ff5252'};'>التقلب</div><div style='font-size:12px; color:#8b949e;'>{ratings['volatility'][1]}</div></div>", unsafe_allow_html=True)

    # Candle Patterns
    if res.get('candle_patterns'):
        st.markdown("### 🕯️ نماذج الشموع")
        cp = res['candle_patterns']
        cols = st.columns(min(len(cp), 4))
        for i, pat in enumerate(cp[:4]):
            is_bull = any(x in pat for x in ["صاعد", "شراء", "مطرقة"])
            is_bear = any(x in pat for x in ["هابط", "بيع"])
            color = "#00c853" if is_bull else "#ff5252" if is_bear else "#8b949e"
            bg = "rgba(0,200,83,0.1)" if is_bull else "rgba(255,82,82,0.1)" if is_bear else "rgba(139,148,158,0.1)"
            cols[i].markdown(f"<div style='background:{bg}; border:1px solid {color}44; padding:10px; border-radius:10px; text-align:center; font-size:13px; color:{color};'>{pat}</div>", unsafe_allow_html=True)

    # Chart
    if st.toggle("📊 إظهار الرسم البياني (TradingView)", key=f"chart_{res['name']}"):
        render_chart(res['name'])

    # Tabs
    tab1, tab2, tab3 = st.tabs(["📊 تحليل فني مفصل", "💰 إدارة المخاطر", "📋 بيانات السهم"])

    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### الاتجاهات والمؤشرات الفنية")
            st.markdown(f"""
            - {'🟢' if res['t_short']=='صاعد' else '🔴'} **قصير المدى (SMA20):** {res['t_short']}
            - {'🟢' if res['t_med']=='صاعد' else '🔴'} **متوسط المدى (SMA50):** {res['t_med']}
            - {'🟢' if res['t_long']=='صاعد' else '🔴'} **طويل المدى (SMA200):** {res['t_long']}
            - **MACD:** {res['macd']:.3f} | **Signal:** {res['macd_signal']:.3f} ({'🟢 إيجابي' if res['macd'] > res['macd_signal'] else '🔴 سلبي'})
            - **Stoch RSI:** {res['stoch_k']:.1f} ({'🟢 تشبع بيعي' if res['stoch_k'] < 20 else '🔴 تشبع شرائي' if res['stoch_k'] > 80 else '🟡 محايد'})
            - **ATR:** {res['atr']:.3f} (متوسط حركة اليوم)
            """)
        with c2:
            st.markdown("#### مستويات الدعم والمقاومة")
            st.markdown(f"""
            | المستوى | السعر | الدلالة |
            |---------|-------|---------|
            | 🔴 **مقاومة ثانية R2** | {res['r2']:.3f} | مقاومة قوية |
            | 🔴 **مقاومة أولى R1** | {res['r1']:.3f} | مقاومة أولى |
            | 🟡 **نقطة الارتكاز PP** | {res['pp']:.3f} | المحور |
            | 🟢 **دعم أول S1** | {res['s1']:.3f} | دعم أول |
            | 🟢 **دعم ثاني S2** | {res['s2']:.3f} | دعم قوي |
            """)

    with tab2:
        deal = st.number_input("💰 ميزانية الصفقة (جنيه)", value=10000, step=1000, key=f"deal_{res['name']}")
        if deal > 0 and res['entry_price'] > 0:
            shares = int(deal / res['entry_price'])
            profit = (res['target'] - res['entry_price']) * shares
            loss = (res['entry_price'] - res['stop_loss']) * shares

            c1, c2, c3 = st.columns(3)
            c1.metric("📦 عدد الأسهم", f"{shares:,}")
            c2.metric("🟢 الربح المتوقع", f"{profit:,.0f} ج", f"+{res['target_pct']:.1f}%")
            c3.metric("🔴 الخسارة المحتملة", f"{loss:,.0f} ج", f"-{res['risk_pct']:.1f}%")

            st.markdown(f"""
            <div style="background:#0d1117; border:1px solid #3fb950; border-radius:12px; padding:16px; margin:12px 0;">
                🎯 <b>سعر الدخول المقترح:</b> {res['entry_price']:.3f} ج<br>
                🛑 <b>وقف الخسارة (ATR-based):</b> {res['stop_loss']:.3f} ج <span style="color:#f85149">(-{res['risk_pct']:.1f}%)</span><br>
                🏁 <b>الهدف الأول:</b> {res['target']:.3f} ج <span style="color:#58a6ff">(+{res['target_pct']:.1f}%)</span><br>
                📊 <b>نسبة المخاطرة/العائد:</b> {res['rr']} ({'ممتازة' if res['rr'] >= 2 else 'جيدة' if res['rr'] >= 1.5 else 'مقبولة'})
            </div>
            """, unsafe_allow_html=True)

            st.markdown("#### 🏹 خطة دخول متدرجة")
            risk_range = res['entry_price'] - res['stop_loss']
            e1 = res['entry_price']
            e2 = max(res['entry_price'] - risk_range * 0.5, res['stop_loss'] * 1.02)
            e3 = res['entry_price'] + (res['target'] - res['entry_price']) * 0.3

            if res['rr'] >= 2.5:
                w1, w2, w3 = 0.6, 0.25, 0.15
            elif res['rr'] >= 1.8:
                w1, w2, w3 = 0.5, 0.3, 0.2
            else:
                w1, w2, w3 = 0.4, 0.35, 0.25

            s1 = int((deal * w1) / e1) if e1 > 0 else 0
            s2 = int((deal * w2) / e2) if e2 > 0 else 0
            s3 = int((deal * w3) / e3) if e3 > 0 else 0

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"<div style='background:#0d1117; border:1px solid #3fb950; border-radius:10px; padding:12px; text-align:center;'><b>🟢 الدخول الأساسي</b><br>السعر: {e1:.3f}<br>الكمية: {s1:,} سهم</div>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"<div style='background:#0d1117; border:1px solid #d29922; border-radius:10px; padding:12px; text-align:center;'><b>🟡 تعزيز الدعم</b><br>السعر: {e2:.3f}<br>الكمية: {s2:,} سهم</div>", unsafe_allow_html=True)
            with col3:
                st.markdown(f"<div style='background:#0d1117; border:1px solid #58a6ff; border-radius:10px; padding:12px; text-align:center;'><b>🔵 تأكيد الاختراق</b><br>السعر: {e3:.3f}<br>الكمية: {s3:,} سهم</div>", unsafe_allow_html=True)

            total_shares = s1 + s2 + s3
            total_cost = (s1 * e1) + (s2 * e2) + (s3 * e3)
            if total_shares > 0:
                avg = total_cost / total_shares
                st.info(f"📊 **متوسط السعر بعد التنفيذ:** {avg:.3f} ج ({total_shares:,} سهم)")

    with tab3:
        st.markdown(f"""
        - **القمة السنوية (52 أسبوع):** {res['high52']:.3f} ج (مساحة صعود: {res['upside_to_52w_high']:.1f}%)
        - **القاع السنوي (52 أسبوع):** {res['low52']:.3f} ج
        - **أداء الشهر الأخير:** {res['perf_1m']:+.2f}%
        - **أداء 3 شهور:** {res['perf_3m']:+.2f}%
        - **حجم التداول اليوم:** {res['volume']:,} سهم
        - **متوسط التداول (10 أيام):** {res['avg_volume']:,} سهم
        - **نسبة السيولة:** {res['ratio']:.2f}x المتوسط
        - **القيمة السوقية:** {res['market_cap']:,.0f}
        """)

    if st.button("💾 تسجيل الصفقة", key=f"rec_{res['name']}", use_container_width=True):
        record_trade(res, "تحليل فردي")
        st.success("✅ تم تسجيل الصفقة بنجاح!")

    msg = f"📊 {res['name']}\n💰 {res['p']:.3f}\n🎯 {res['entry_price']:.3f}\n🛑 {res['stop_loss']:.3f}\n🏁 {res['target']:.3f}\n⚖️ RR: {res['rr']}"
    st.markdown(f"[📱 مشاركة عبر واتساب](https://wa.me/?text={urllib.parse.quote(msg)})")

# ================== التطبيق الرئيسي ==================
def main():
    # Load data
    if st.session_state.all_results is None:
        get_fresh_data()

    market_status = get_egx30_status()
    thresholds = get_mode_thresholds(st.session_state.mode)

    # Header
    st.title("🎯 EGX Sniper Pro Ultimate")
    st.caption("📈 محلل EGX المتقدم - بيانات TradingView مباشرة")

    # Market Banner
    st.markdown(f"""
    <div style="background: linear-gradient(90deg, #0d1117, #161b22); border: 1px solid #30363d; border-radius: 12px; padding: 14px; margin-bottom: 20px; text-align: center;">
        <span style="color: {market_status['color']}; font-weight: 700; font-size: 16px;">📊 {market_status['status']}</span>
        <span style="margin: 0 15px; color: #8b949e;">|</span>
        <span>📈 التغير: <b>{market_status['change']:+.2f}%</b></span>
        <span style="margin: 0 15px; color: #8b949e;">|</span>
        <span>📊 RSI: <b>{market_status['rsi']:.0f}</b></span>
        <span style="margin: 0 15px; color: #8b949e;">|</span>
        <span>💰 EGX30: <b>{market_status['price']:,.0f}</b></span>
    </div>
    """, unsafe_allow_html=True)

    # Navigation Bar (old style with text)
    nav_cols = st.columns(7)
    nav_items = [
        ("🏠", "الرئيسية", "home"),
        ("🏆", "أفضل 10", "top10"),
        ("🎯", "التصحيحات", "correction"),
        ("⚡", "الاختراق", "rapid"),
        ("🔻", "دعم وارتداد", "support"),
        ("🚀", "بداية صعود", "early_uptrend"),
        ("🔍", "تحليل سهم", "analyze")
    ]
    for i, (icon, label, page_key) in enumerate(nav_items):
        with nav_cols[i]:
            if st.button(f"{icon} {label}", use_container_width=True, key=f"nav_{page_key}"):
                st.session_state.page = page_key
                st.rerun()

    # Settings Expander
    with st.expander("⚙️ الإعدادات والفلترة", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🛡️ محافظ", use_container_width=True):
                st.session_state.mode = "🛡️ محافظ"
                st.rerun()
        with c2:
            if st.button("⚖️ متوازن", use_container_width=True):
                st.session_state.mode = "⚖️ متوازن"
                st.rerun()
        with c3:
            if st.button("🚀 هجومي", use_container_width=True):
                st.session_state.mode = "🚀 هجومي"
                st.rerun()

        mode_color = {"🛡️ محافظ": "#00C853", "⚖️ متوازن": "#FFB300", "🚀 هجومي": "#FF5252"}[st.session_state.mode]
        st.markdown(f"<div style='background:{mode_color}33; color:{mode_color}; padding:8px; border-radius:8px; text-align:center; font-weight:700; margin:10px 0; border:1px solid {mode_color}44;'>النمط الحالي: {st.session_state.mode}</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 📂 فلتر القطاع")
        sectors = ["🌍 الكل"] + list(SECTORS.keys()) + ["📌 أخرى"]
        selected = st.selectbox("اختر قطاعاً", sectors, index=sectors.index(st.session_state.sector_filter) if st.session_state.sector_filter in sectors else 0)
        if selected != st.session_state.sector_filter:
            st.session_state.sector_filter = selected
            st.rerun()

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 تحديث البيانات", use_container_width=True):
                get_fresh_data()
                st.rerun()
        with c2:
            if st.button("📊 تقييم الأداء", use_container_width=True):
                st.session_state.page = 'performance'
                st.rerun()

    # Page routing
    page = st.session_state.page

    if page == 'detail' and st.session_state.selected_stock:
        if st.button("⬅️ العودة للقائمة", use_container_width=True):
            st.session_state.page = 'home'
            st.session_state.selected_stock = None
            st.rerun()
        render_stock_detail(st.session_state.selected_stock, thresholds)
        return

    filtered = filter_by_sector(st.session_state.all_results, st.session_state.sector_filter)

    if page == 'home':
        st.markdown("### 📊 لوحة فرص السوق")

        if filtered:
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("📊 إجمالي الأسهم", len(filtered))
            rapid_count = len(get_rapid_breakouts(filtered, thresholds))
            c2.metric("⚡ فرص اختراق", rapid_count)
            corrections = get_corrections(filtered, thresholds, market_status['market_multiplier'])
            c3.metric("🎯 فرص تصحيح", len(corrections))
            early_list = get_early_uptrend_stocks(filtered, thresholds, market_status['market_multiplier'])
            c4.metric("🚀 بداية صعود", len(early_list))
            support_list = get_support_stocks(filtered, thresholds)
            c5.metric("🔻 دعم وارتداد", len(support_list))

            st.caption(f"🕐 آخر تحديث: {st.session_state.last_update}")

            tab1, tab2, tab3, tab4 = st.tabs(["🎯 صائد التصحيحات", "⚡ قناص الاختراق", "🚀 بداية الصعود", "🔻 دعم وارتداد"])

            with tab1:
                if corrections:
                    for item in corrections[:6]:
                        render_opportunity_card(item, "correction", thresholds)
                else:
                    st.info("ℹ️ لا توجد فرص تصحيح حالياً في هذا النمط.")

            with tab2:
                rapid = get_rapid_breakouts(filtered, thresholds)
                if rapid:
                    for item in rapid[:6]:
                        render_opportunity_card(item, "rapid", thresholds)
                else:
                    st.info("ℹ️ لا توجد فرص اختراق حالياً في هذا النمط.")

            with tab3:
                if early_list:
                    for item in early_list[:6]:
                        render_opportunity_card(item, "early", thresholds)
                else:
                    st.info("ℹ️ لا توجد فرص بداية صعود حالياً في هذا النمط.")

            with tab4:
                if support_list:
                    for item in support_list[:6]:
                        render_opportunity_card(item, "support", thresholds)
                else:
                    st.info("ℹ️ لا توجد فرص دعم وارتداد حالياً في هذا النمط.")
        else:
            st.warning("⚠️ لا توجد بيانات. اضغط تحديث من الإعدادات.")

    elif page == 'top10':
        st.title("🏆 أفضل 10 فرص")
        top = get_top_10(filtered, thresholds)
        if top:
            for i, an in enumerate(top, 1):
                conf = get_confidence(an, thresholds)
                with st.container():
                    c1, c2, c3 = st.columns([1, 3, 1])
                    with c1:
                        st.markdown(f"<h1 style='text-align:center; color:#FFD600; margin:0;'>#{i}</h1>", unsafe_allow_html=True)
                    with c2:
                        st.markdown(f"**{an['name']}** - {an['desc']}")
                        st.progress(an['smart_score'] / 100, text=f"Smart Score: {an['smart_score']}/100")
                        st.caption(f"RR: {an['rr']} | RSI: {an['rsi']:.0f} | تداول: {an['daily_turnover']/1_000_000:.1f}M | تقلب: {an['volatility']:.1f}%")
                    with c3:
                        st.markdown(f"<div style='background:{conf['color']}22; color:{conf['color']}; padding:8px; border-radius:10px; text-align:center; font-weight:700; border:1px solid {conf['color']}44;'>{conf['grade']}</div>", unsafe_allow_html=True)
                        if st.button("تحليل", key=f"top_{an['name']}", use_container_width=True):
                            st.session_state.selected_stock = an
                            st.session_state.page = 'detail'
                            st.rerun()
                    st.divider()
        else:
            st.warning("⚠️ لا توجد فرص مطابقة للمعايير الحالية.")

    elif page == 'correction':
        st.title("🎯 صائد التصحيحات")
        st.markdown("""
        <div style="background: rgba(46,125,50,0.1); border-right: 4px solid #2E7D32; padding: 12px; border-radius: 8px; margin-bottom: 20px;">
            <b>🎯 الأسهم القوية التي تصحح</b><br>
            <small>• الاتجاه العام صاعد | • RSI في منطقة التصحيح | • بداية ارتداد | • سيولة كافية</small>
        </div>
        """, unsafe_allow_html=True)
        corrections = get_corrections(filtered, thresholds, market_status['market_multiplier'])
        if corrections:
            st.markdown(f"**🎯 عدد فرص التصحيح: {len(corrections)}**")
            for item in corrections:
                render_opportunity_card(item, "correction", thresholds)
        else:
            st.info("ℹ️ لا توجد فرص تصحيح حالياً.")

    elif page == 'rapid':
        st.title("⚡ قناص الاختراق السريع")
        st.markdown("""
        <div style="background: rgba(255,23,68,0.1); border-right: 4px solid #FF1744; padding: 12px; border-radius: 8px; margin-bottom: 20px;">
            <b>⚡ فرص اختراق المقاومة خلال جلسة أو جلستين</b><br>
            <small>• RSI بين 45-75 | • سيولة استثنائية | • قرب اختراق المقاومة | • إغلاق قوي</small>
        </div>
        """, unsafe_allow_html=True)
        rapid = get_rapid_breakouts(filtered, thresholds)
        if rapid:
            st.markdown(f"**⚡ عدد فرص الاختراق: {len(rapid)}**")
            for item in rapid:
                render_opportunity_card(item, "rapid", thresholds)
        else:
            st.info("ℹ️ لا توجد فرص اختراق حالياً.")

    elif page == 'support':
        st.title("🔻 فرص الدعم والارتداد")
        st.markdown("""
        <div style="background: rgba(33,150,243,0.1); border-right: 4px solid #2196f3; padding: 12px; border-radius: 8px; margin-bottom: 20px;">
            <b>🔻 الأسهم القريبة من الدعم مع تأكيد ارتداد</b><br>
            <small>• قرب من الدعم (< 1.5%) | • بداية ارتداد إيجابي | • RSI يتعافى | • سيولة جيدة</small>
        </div>
        """, unsafe_allow_html=True)
        support = get_support_stocks(filtered, thresholds)
        if support:
            st.markdown(f"**🔻 عدد فرص الدعم: {len(support)}**")
            for item in support:
                render_opportunity_card(item, "support", thresholds)
        else:
            st.info("ℹ️ لا توجد فرص دعم وارتداد حالياً.")

    elif page == 'early_uptrend':
        st.title("🚀 بداية الموجة الصاعدة")
        st.markdown("""
        <div style="background: rgba(0,200,83,0.1); border-right: 4px solid #00C853; padding: 12px; border-radius: 8px; margin-bottom: 20px;">
            <b>🚀 أسهم في بداية اتجاه صاعد حقيقي مع مساحة صعود ≥ 20%</b><br>
            <small>• مساحة صعود كافية | • اختراق SMA20 | • RSI في بداية الزخم | • زخم إيجابي</small>
        </div>
        """, unsafe_allow_html=True)
        early = get_early_uptrend_stocks(filtered, thresholds, market_status['market_multiplier'])
        if early:
            st.markdown(f"**🚀 عدد فرص بداية الصعود: {len(early)}**")
            for item in early:
                render_opportunity_card(item, "early", thresholds)
        else:
            st.info("ℹ️ لا توجد فرص بداية صعود حالياً.")

    elif page == 'analyze':
        st.title("🔍 تحليل سهم")
        sym = st.text_input("🔎 أدخل رمز السهم", placeholder="مثال: COMI, TMGH, ETEL, ESRS").upper().strip()
        if sym:
            with st.spinner("🔍 جاري البحث عن السهم..."):
                data = fetch_single_stock(sym)
                if data:
                    res = analyze_stock(data[0])
                    if res:
                        render_stock_detail(res, thresholds)
                    else:
                        st.error("⚠️ فشل تحليل السهم - قد يكون ذو سيولة ضعيفة جداً")
                else:
                    st.error(f"❌ السهم '{sym}' غير موجود في قاعدة البيانات")
                    if st.session_state.all_results:
                        syms = [r['name'] for r in st.session_state.all_results[:20] if r]
                        if syms:
                            st.info(f"💡 أمثلة: {', '.join(syms[:15])}")

    elif page == 'performance':
        st.title("📊 تقييم الأداء")
        trades = load_trades()
        stats = get_performance_stats(trades)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📊 إجمالي الصفقات", stats['total'])
        c2.metric("✅ حققت الهدف", stats['hit_target'])
        c3.metric("❌ ضربت الوقف", stats['stopped_out'])
        c4.metric("⏳ لا تزال مفتوحة", stats['still_open'])

        c1, c2 = st.columns(2)
        c1.metric("📈 نسبة النجاح", f"{stats['success_rate']}%")
        c2.metric("⚖️ متوسط RR", stats['avg_rr'])

        if trades:
            st.markdown("### 📋 آخر الصفقات المسجلة")
            for trade in trades[-15:][::-1]:
                status_color = {"hit_target": "#00C853", "stopped_out": "#FF5252"}.get(trade.get('status'), "#FFB300")
                status_text = {"hit_target": "🟢 حققت الهدف", "stopped_out": "🔴 ضربت الوقف"}.get(trade.get('status'), "🟡 لا تزال مفتوحة")
                st.markdown(f"""
                <div style='background:#0d1117; border:1px solid #30363d; border-radius:8px; padding:12px; margin:6px 0; border-right: 3px solid {status_color};'>
                    <b>{trade.get('name', 'N/A')}</b> <span style='color:#8b949e;'>({trade.get('trade_type', '')})</span> - <span style='color:{status_color};'>{status_text}</span><br>
                    <small>📅 {trade.get('date_recorded', '')} | 🎯 {trade.get('target', 0):.3f} | 🛑 {trade.get('stop_loss', 0):.3f} | ⚖️ RR: {trade.get('rr', 0)} | Smart: {trade.get('smart_score', 0)}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("📭 لا توجد صفقات مسجلة بعد. ابدأ بتسجيل صفقات من صفحات الفرص.")

if __name__ == "__main__":
    main()
