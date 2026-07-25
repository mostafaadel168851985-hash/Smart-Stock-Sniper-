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
    page_icon="🎯",
    initial_sidebar_state="expanded"
)

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
                            status, color, mult = "🟢 سوق صاعد", "#00C853", 1.0
                        elif score >= 3:
                            status, color, mult = "🟡 سوق متذبذب", "#FFB300", 0.75
                        else:
                            status, color, mult = "🔴 سوق هابط", "#FF5252", 0.5
                        return {"status": status, "color": color, "market_multiplier": mult,
                                "rsi": rsi, "change": change, "price": price, "atr": atr}
        except:
            time.sleep(1)
    return {"status": "🟡 سوق متذبذب", "color": "#FFB300", "market_multiplier": 0.7,
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

# ================== محرك التحليل الفني ==================
def safe_float(val, default=0.0):
    try:
        return float(val) if val is not None else default
    except:
        return default

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

# ================== نماذج الشموع (محسنة) ==================
def analyze_candlestick_patterns(p, open_p, high, low, prev_close, prev_open, chg):
    patterns = []
    strength = 0
    body = abs(p - open_p)
    range_val = high - low if high > low else 0.001
    upper_wick = high - max(p, open_p)
    lower_wick = min(p, open_p) - low
    prev_body = abs(prev_close - prev_open) if prev_open else 0.001

    if lower_wick > body * 2 and upper_wick < body * 0.5 and chg > -2:
        patterns.append("🔨 مطرقة - انعكاس صاعد")
        strength += 3

    if upper_wick > body * 2 and lower_wick < body * 0.5 and chg > 0.5:
        patterns.append("⭐ شهاب - انعكاس هابط")
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
        patterns.append("✚ دوجي - تردد/توازن")

    if range_val > 0 and upper_wick < range_val * 0.05 and lower_wick < range_val * 0.05:
        if chg > 0:
            patterns.append("📈 ماروبوزو صاعد - قوة اتجاه")
            strength += 3
        else:
            patterns.append("📉 ماروبوزو هابط - ضعف")
            strength -= 2

    if body < range_val * 0.3 and upper_wick > body and lower_wick > body:
        patterns.append("🔄 غزل - تردد قبل حركة")

    return patterns, strength

# ================== Smart Score (محسن) ==================
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

# ================== نظام الثقة ==================
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

    if pct >= 80: return {"grade": "A+", "advice": "🔥 فرصة ممتازة", "color": "#00C853", "emoji": "🔥"}
    elif pct >= 65: return {"grade": "A", "advice": "✅ فرصة جيدة", "color": "#69F0AE", "emoji": "✅"}
    elif pct >= 50: return {"grade": "B", "advice": "🟡 فرصة متوسطة", "color": "#FFD600", "emoji": "🟡"}
    elif pct >= 35: return {"grade": "C", "advice": "⚠️ ضعيفة", "color": "#FF9100", "emoji": "⚠️"}
    else: return {"grade": "D", "advice": "❌ تجنب", "color": "#FF5252", "emoji": "❌"}

# ================== كاشف الفرص ==================
def is_correction_hunter(an, thresholds, market_mult=1.0):
    if an is None: return False, [], 0, "", ""
    p, rsi, sma200 = an.get('p', 0), an.get('rsi', 50), an.get('sma200', 0)
    chg, turnover, t_long = an.get('chg', 0), an.get('daily_turnover', 0), an.get('t_long', 'هابط')
    rr, candle = an.get('rr', 0), an.get('candle_strength', 0)
    volatility = an.get('volatility', 1.5)

    reasons, score = [], 0
    max_s = 10

    if not (t_long == "صاعد" or (sma200 and p > sma200)):
        return False, ["الاتجاه العام هابط"], 0, "", ""

    score += 2; reasons.append("📈 الاتجاه العام صاعد")

    if rsi <= thresholds['correction_rsi_max']:
        score += 3
        reasons.append(f"🔻 RSI تصحيحي ({rsi:.0f})")
    else:
        return False, [f"RSI مرتفع ({rsi:.0f})"], 0, "", ""

    if chg > 0: score += 2; reasons.append(f"📈 ارتداد (+{chg:.2f}%)")
    elif chg > -1: score += 1; reasons.append(f"⚖️ استقرار ({chg:.2f}%)")

    if turnover >= thresholds['min_turnover']:
        score += 1.5; reasons.append("💰 سيولة كافية")

    if rr >= thresholds['min_rr']: score += 1; reasons.append(f"⚖️ RR جيد ({rr})")
    if candle >= 2: score += 1; reasons.append("🕯️ شمعة داعمة")
    if thresholds['min_volatility'] <= volatility <= thresholds['max_volatility']:
        score += 0.5; reasons.append(f"📊 تقلب مناسب")

    adj = score * market_mult
    strength = min(100, int((adj / max_s) * 100))

    if strength >= 75: label, color = "🔥🔥 ممتازة جداً", "#1B5E20"
    elif strength >= 60: label, color = "🔥 ممتازة", "#2E7D32"
    elif strength >= 45: label, color = "✅ جيدة", "#388E3C"
    else: label, color = "🟡 محتملة", "#F57C00"

    return score >= 4, reasons, strength, label, color

def is_rapid_breakout(an, thresholds):
    if an is None:
        return {"is_breakout": False}
    p, rsi, r1 = an.get('p', 0), an.get('rsi', 50), an.get('r1', p * 1.05)
    turnover, chg = an.get('daily_turnover', 0), an.get('chg', 0)
    t_short, t_med = an.get('t_short', 'هابط'), an.get('t_med', 'هابط')
    candle = an.get('candle_strength', 0)
    high, low = an.get('high', p), an.get('low', p)

    if not (thresholds['rsi_low'] <= rsi <= thresholds['breakout_rsi_max']):
        return {"is_breakout": False}
    if turnover < thresholds['min_turnover']:
        return {"is_breakout": False}

    reasons, score = [], 0
    max_s = 10

    close_str = (p - low) / (high - low) * 100 if (high - low) > 0 else 50
    near_high = (high - p) / p * 100 if p > 0 else 0

    if 50 <= rsi <= thresholds['breakout_rsi_max']: score += 2; reasons.append(f"⚡ زخم ({rsi:.0f})")
    if turnover >= 20_000_000: score += 2.5; reasons.append("💥 سيولة قوية")
    elif turnover >= thresholds['min_turnover']: score += 1.5; reasons.append("📊 سيولة جيدة")

    if p >= r1 * 0.995: score += 3; reasons.append("🎯 عند المقاومة")
    elif p >= r1 * 0.98: score += 2; reasons.append("📍 قريب من المقاومة")
    else: return {"is_breakout": False}

    if close_str >= 75: score += 2; reasons.append(f"💪 إغلاق قوي ({close_str:.0f}%)")
    elif close_str >= 60: score += 1; reasons.append(f"📊 إغلاق جيد")

    if t_short == "صاعد" and t_med == "صاعد": score += 1; reasons.append("📈 اتجاهات صاعدة")
    if candle >= 2: score += 1; reasons.append("🕯️ شمعة قوية")

    strength = min(100, int((score / max_s) * 100))
    if strength < 40: return {"is_breakout": False}

    if strength >= 75: label, color = "🔥🔥 انفجار وشيك", "#FF1744"
    elif strength >= 60: label, color = "🔥 اختراق قوي", "#FF5252"
    else: label, color = "⚡ مراقبة", "#FFB300"

    return {
        "is_breakout": True, "reasons": reasons, "strength": strength,
        "label": label, "color": color,
        "target_1": r1, "target_2": an.get('r2', r1 * 1.03),
        "stop_loss_rapid": max(an.get('s1', p * 0.98), p - an.get('atr', p * 0.02) * 1.5)
    }

def is_support_with_bounce(an, thresholds):
    if an is None: return False, [], 0, "عادي"
    s1, s2, p = an.get('s1', 0), an.get('s2', 0), an.get('p', 0)
    chg, rsi = an.get('chg', 0), an.get('rsi', 50)
    turnover, sma20 = an.get('daily_turnover', 0), an.get('sma20', p)
    candle = an.get('candle_strength', 0)

    if s1 == 0 and s2 == 0: return False, [], 0, "عادي"
    ns = s1 if s1 > 0 else s2
    dist = (p - ns) / ns * 100 if ns > 0 else 999

    if dist < 0: return False, ["❌ كسر الدعم"], 0, "مكسور"
    if dist >= 1.5: return False, [], 0, "عادي"

    level = "عند الدعم" if dist < 0.5 else "قريب جداً" if dist < 1.0 else "قريب"
    reasons, score = [], 0
    max_s = 8

    if 0.1 < chg < 4: score += 2; reasons.append(f"📈 ارتداد (+{chg:.2f}%)")
    elif 0 < chg <= 0.1: score += 1; reasons.append(f"📈 بداية ارتداد")
    elif chg >= 4: return False, ["⚠️ قمة محتملة"], 0, level
    elif chg <= 0: return False, ["لم يرتد بعد"], 0, level

    if rsi > 40: score += 2; reasons.append(f"📊 RSI يتعافى ({rsi:.0f})")
    elif rsi > 35: score += 1; reasons.append(f"📊 RSI قريب من التعافي")

    if turnover >= thresholds['min_turnover']: score += 1.5; reasons.append("💰 سيولة كافية")
    if p > sma20: score += 1; reasons.append("📈 فوق SMA20")
    if candle >= 2: score += 1; reasons.append("🕯️ شمعة داعمة")

    is_valid = score >= 4
    if is_valid: reasons.append(f"✅ نقاط: {score}/{max_s}")
    return is_valid, reasons, score, level

def is_early_uptrend(an, thresholds, market_mult=1.0):
    if an is None: return False, [], 0, "", "", 0
    p, high52 = an.get('p', 0), an.get('high52', p)
    rsi, chg = an.get('rsi', 50), an.get('chg', 0)
    t_short, t_med, t_long = an.get('t_short', 'هابط'), an.get('t_med', 'هابط'), an.get('t_long', 'هابط')
    turnover, perf_1m = an.get('daily_turnover', 0), an.get('perf_1m', 0)
    candle, macd, macd_sig = an.get('candle_strength', 0), an.get('macd', 0), an.get('macd_signal', 0)

    if p <= 0 or high52 <= 0: return False, [], 0, "", "", 0
    upside = round((high52 - p) / p * 100, 2) if high52 > p else 0.0

    if upside < 20: return False, [f"مساحة صعود ضعيفة ({upside:.1f}%)"], 0, "", "", upside

    reasons, score = [], 0
    max_s = 12

    if upside >= 40: score += 3; reasons.append(f"🚀 مساحة ضخمة ({upside:.1f}%)")
    elif upside >= 30: score += 2.5; reasons.append(f"📈 مساحة كبيرة ({upside:.1f}%)")
    else: score += 2; reasons.append(f"📈 مساحة جيدة ({upside:.1f}%)")

    if t_short != "صاعد": return False, ["لم يخترق SMA20"], 0, "", "", upside
    score += 2; reasons.append("✅ اختراق SMA20")

    if t_med == "صاعد" and t_long != "صاعد": score += 2; reasons.append("🌱 بداية انعكاس")
    elif t_med == "صاعد": score += 1; reasons.append("📊 اتجاه متوسط صاعد")
    else: score += 0.5; reasons.append("⏳ متوسط لم يتأكد")

    if 40 <= rsi <= thresholds['early_rsi_max']: score += 2; reasons.append(f"⚡ RSI مثالي ({rsi:.0f})")
    elif 35 <= rsi < 40: score += 1; reasons.append(f"📊 RSI يتعافى")
    else: return False, [f"RSI غير مناسب ({rsi:.0f})"], 0, "", "", upside

    if chg > 1: score += 1.5; reasons.append(f"📈 زخم (+{chg:.2f}%)")
    elif chg > 0: score += 1; reasons.append(f"📈 زخم إيجابي")
    elif chg > -1: score += 0.5; reasons.append("⚖️ استقرار")
    else: return False, ["زخم سلبي"], 0, "", "", upside

    if perf_1m > 0: score += 1; reasons.append(f"📆 شهر إيجابي")
    elif perf_1m > -10: score += 0.5; reasons.append(f"📆 شهر مستقر")

    if turnover >= thresholds['min_turnover']: score += 1.5; reasons.append("💰 سيولة كافية")
    if macd > macd_sig: score += 1; reasons.append("📊 MACD إيجابي")
    if candle >= 2: score += 1; reasons.append("🕯️ شمعة داعمة")

    adj = score * market_mult
    strength = min(100, int((adj / max_s) * 100))

    if strength >= 70: label, color = "🚀🚀 قوية جداً", "#00C853"
    elif strength >= 55: label, color = "🚀 واعدة", "#43A047"
    elif strength >= 40: label, color = "🌱 محتملة", "#FDD835"
    else: label, color = "🟡 مبكرة", "#FB8C00"

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
def render_chart(symbol, height=380):
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

def render_opportunity_card(item, card_type):
    """بطاقة فرصة موحدة"""
    an = item['stock']

    if card_type == "correction":
        strength, label, color = item['strength'], item['label'], item['color']
        reasons = item['reasons']
        icon = "🎯"
    elif card_type == "rapid":
        strength, label, color = item['analysis']['strength'], item['analysis']['label'], item['analysis']['color']
        reasons = item['analysis']['reasons']
        icon = "⚡"
    elif card_type == "support":
        strength, label, color = item['score'] * 12, f"نقاط: {item['score']}/8", "#2196f3"
        reasons = item['reasons']
        icon = "🔻"
    elif card_type == "early":
        strength, label, color = item['strength'], item['label'], item['color']
        reasons = item['reasons']
        icon = "🚀"
    else:
        strength, label, color = 0, "", "#888"
        reasons = []
        icon = "📊"

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #0d1117, #161b22); border-radius: 12px; padding: 15px; margin-bottom: 12px; border-right: 4px solid {color};">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <h4 style="margin:0; color:#e0e0e0;">{icon} {an['name']} - {an['desc']}</h4>
            <span style="background: {color}22; color: {color}; padding: 4px 14px; border-radius: 20px; font-weight: bold; font-size: 13px;">
                {label}
            </span>
        </div>
        <div style="height: 5px; background: #21262d; margin: 10px 0; border-radius: 3px;">
            <div style="width: {min(strength, 100)}%; background: {color}; height: 5px; border-radius: 3px; transition: width 0.5s;"></div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; font-size: 13px; color: #8b949e;">
            <div>💰 {an['p']:.3f} ج</div>
            <div>📊 RSI: {an['rsi']:.0f}</div>
            <div>💧 تداول: {an['daily_turnover']/1_000_000:.1f}M</div>
            <div>📈 {an['chg']:+.2f}%</div>
        </div>
        <div style="margin-top: 8px; font-size: 12px; color: #58a6ff;">
            {' • '.join(reasons[:4])}
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("📊 تحليل كامل", key=f"btn_{card_type}_{an['name']}"):
        st.session_state.selected_stock = an
        st.session_state.page = 'detail'
        st.rerun()

def render_stock_detail(res, thresholds):
    if res is None:
        st.warning("بيانات غير متوفرة")
        return

    conf = get_confidence(res, thresholds)

    st.markdown(f"""
    <div style="background: linear-gradient(90deg, #0d1117, #161b22); padding: 15px; border-radius: 12px; border-right: 5px solid {conf['color']}; margin-bottom: 15px;">
        <h2 style="margin:0; color:#58a6ff;">📈 {res['name']} - {res['desc']}</h2>
        <div style="display:flex; gap:15px; margin-top:8px; flex-wrap:wrap;">
            <span style="background:{conf['color']}22; color:{conf['color']}; padding:4px 12px; border-radius:20px; font-weight:bold;">{conf['emoji']} {conf['grade']} - {conf['advice']}</span>
            <span style="background:#23863622; color:#3fb950; padding:4px 12px; border-radius:20px;">Smart: {res['smart_score']}/100</span>
            <span style="background:#58a6ff22; color:#58a6ff; padding:4px 12px; border-radius:20px;">RR: {res['rr']}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("السعر", f"{res['p']:.3f}", f"{res['chg']:+.2f}%")
    m2.metric("Smart Score", res['smart_score'])
    m3.metric("RR", res['rr'])
    m4.metric("RSI", f"{res['rsi']:.1f}")
    m5.metric("التداول", f"{res['daily_turnover']/1_000_000:.1f}M")
    m6.metric("التقلب", f"{res['volatility']:.1f}%")

    if res.get('candle_patterns'):
        cp = res['candle_patterns']
        cols = st.columns(min(len(cp), 4))
        for i, pat in enumerate(cp[:4]):
            icon = "🟢" if any(x in pat for x in ["صاعد", "شراء", "مطرقة"]) else "🔴" if any(x in pat for x in ["هابط", "بيع"]) else "⚪"
            cols[i].markdown(f"<div style='background:#0d1117; border:1px solid #30363d; padding:8px; border-radius:8px; text-align:center; font-size:13px;'>{icon} {pat}</div>", unsafe_allow_html=True)

    if st.toggle("📊 إظهار الرسم البياني", key=f"chart_{res['name']}"):
        render_chart(res['name'])

    tab1, tab2, tab3 = st.tabs(["📊 تحليل فني", "💰 إدارة المخاطر", "📋 بيانات"])

    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### الاتجاهات والمؤشرات")
            st.markdown(f"""
            - {'🟢' if res['t_short']=='صاعد' else '🔴'} قصير المدى (SMA20): {res['t_short']}
            - {'🟢' if res['t_med']=='صاعد' else '🔴'} متوسط المدى (SMA50): {res['t_med']}
            - {'🟢' if res['t_long']=='صاعد' else '🔴'} طويل المدى (SMA200): {res['t_long']}
            - 📊 MACD: {res['macd']:.3f} | Signal: {res['macd_signal']:.3f}
            - ⚡ Stoch RSI: {res['stoch_k']:.1f}
            - 📐 ATR: {res['atr']:.3f}
            """)
        with c2:
            st.markdown("#### مستويات الدعم والمقاومة")
            st.markdown(f"""
            | المستوى | السعر |
            |---------|-------|
            | 🔴 R2 | {res['r2']:.3f} |
            | 🔴 R1 | {res['r1']:.3f} |
            | 🟡 PP | {res['pp']:.3f} |
            | 🟢 S1 | {res['s1']:.3f} |
            | 🟢 S2 | {res['s2']:.3f} |
            """)

    with tab2:
        deal = st.number_input("💰 ميزانية الصفقة (ج)", value=10000, step=1000, key=f"deal_{res['name']}")
        if deal > 0 and res['entry_price'] > 0:
            shares = int(deal / res['entry_price'])
            profit = (res['target'] - res['entry_price']) * shares
            loss = (res['entry_price'] - res['stop_loss']) * shares

            c1, c2, c3 = st.columns(3)
            c1.metric("📦 الأسهم", f"{shares:,}")
            c2.metric("🟢 الربح", f"{profit:,.0f} ج", f"+{res['target_pct']:.1f}%")
            c3.metric("🔴 الخسارة", f"{loss:,.0f} ج", f"-{res['risk_pct']:.1f}%")

            st.markdown(f"""
            <div style="background:#0d1117; border:1px solid #3fb950; border-radius:10px; padding:12px; margin:10px 0;">
                🎯 <b>دخول:</b> {res['entry_price']:.3f} ج<br>
                🛑 <b>وقف (ATR-based):</b> {res['stop_loss']:.3f} ج <span style="color:#f85149">(-{res['risk_pct']:.1f}%)</span><br>
                🏁 <b>هدف:</b> {res['target']:.3f} ج <span style="color:#58a6ff">(+{res['target_pct']:.1f}%)</span>
            </div>
            """, unsafe_allow_html=True)

    with tab3:
        st.markdown(f"""
        - **القمة السنوية:** {res['high52']:.3f} (مساحة صعود: {res['upside_to_52w_high']:.1f}%)
        - **القاع السنوي:** {res['low52']:.3f}
        - **أداء شهر:** {res['perf_1m']:+.2f}%
        - **أداء 3 شهور:** {res['perf_3m']:+.2f}%
        - **حجم التداول:** {res['volume']:,} (متوسط: {res['avg_volume']:,})
        - **نسبة السيولة:** {res['ratio']:.2f}x
        - **القيمة السوقية:** {res['market_cap']:,.0f}
        """)

    if st.button("💾 تسجيل الصفقة", key=f"rec_{res['name']}"):
        record_trade(res, "تحليل فردي")
        st.success("✅ تم تسجيل الصفقة!")

    msg = f"📊 {res['name']}\n💰 {res['p']:.3f}\n🎯 {res['entry_price']:.3f}\n🛑 {res['stop_loss']:.3f}\n🏁 {res['target']:.3f}\n⚖️ RR: {res['rr']}"
    st.markdown(f"[📱 مشاركة واتساب](https://wa.me/?text={urllib.parse.quote(msg)})")

# ================== التطبيق الرئيسي ==================
def main():
    # Sidebar
    with st.sidebar:
        st.title("🎯 EGX Sniper")
        st.caption("Pro Ultimate - محلل EGX")

        st.markdown("---")
        st.markdown("### 🧠 نمط التداول")
        mode = st.radio("", ["🛡️ محافظ", "⚖️ متوازن", "🚀 هجومي"], 
                       index=["🛡️ محافظ", "⚖️ متوازن", "🚀 هجومي"].index(st.session_state.mode),
                       label_visibility="collapsed")
        if mode != st.session_state.mode:
            st.session_state.mode = mode
            st.rerun()

        thresholds = get_mode_thresholds(st.session_state.mode)
        mode_color = {"🛡️ محافظ": "#00C853", "⚖️ متوازن": "#FFB300", "🚀 هجومي": "#FF5252"}[st.session_state.mode]
        st.markdown(f"<div style='background:{mode_color}33; color:{mode_color}; padding:8px; border-radius:8px; text-align:center; font-weight:bold;'>{st.session_state.mode}</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📂 فلتر القطاع")
        sectors = ["🌍 الكل"] + list(SECTORS.keys()) + ["📌 أخرى"]
        sector = st.selectbox("", sectors, index=sectors.index(st.session_state.sector_filter) if st.session_state.sector_filter in sectors else 0, label_visibility="collapsed")
        if sector != st.session_state.sector_filter:
            st.session_state.sector_filter = sector
            st.rerun()

        st.markdown("---")
        if st.button("🔄 تحديث البيانات", use_container_width=True):
            get_fresh_data()
            st.rerun()

        if st.button("📊 تقييم الأداء", use_container_width=True):
            st.session_state.page = 'performance'
            st.rerun()

        st.markdown("---")
        st.caption("v3.0 - تحسين شامل")

    # Load data
    if st.session_state.all_results is None:
        get_fresh_data()

    market_status = get_egx30_status()
    thresholds = get_mode_thresholds(st.session_state.mode)

    # Header
    st.title("🎯 EGX Sniper Pro Ultimate")
    st.markdown(f"""
    <div style="background: #0d1117; border-radius: 10px; padding: 12px; margin-bottom: 20px; display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; border: 1px solid #30363d;">
        <span style="color: {market_status['color']}; font-weight: bold;">📊 {market_status['status']}</span>
        <span>📈 التغير: {market_status['change']:+.2f}%</span>
        <span>📊 RSI: {market_status['rsi']:.0f}</span>
        <span>💰 السعر: {market_status['price']:,.0f}</span>
    </div>
    """, unsafe_allow_html=True)

    # Navigation
    nav_cols = st.columns(7)
    pages = [
        ("🏠", "الرئيسية", "home"),
        ("🏆", "أفضل 10", "top10"),
        ("🎯", "تصحيحات", "correction"),
        ("⚡", "اختراق", "rapid"),
        ("🔻", "دعم", "support"),
        ("🚀", "صعود", "early_uptrend"),
        ("🔍", "تحليل", "analyze")
    ]
    for i, (icon, label, page_key) in enumerate(pages):
        with nav_cols[i]:
            if st.button(f"{icon}", use_container_width=True, help=label):
                st.session_state.page = page_key
                st.rerun()

    # Page routing
    page = st.session_state.page

    if page == 'detail' and st.session_state.selected_stock:
        if st.button("⬅️ رجوع"):
            st.session_state.page = 'home'
            st.session_state.selected_stock = None
            st.rerun()
        render_stock_detail(st.session_state.selected_stock, thresholds)
        return

    filtered = filter_by_sector(st.session_state.all_results, st.session_state.sector_filter)

    if page == 'home':
        st.markdown("### 📊 لوحة فرص السوق")

        if filtered:
            # Summary metrics
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("📊 الأسهم", len(filtered))
            rapid_count = len(get_rapid_breakouts(filtered, thresholds))
            c2.metric("⚡ اختراق", rapid_count)
            corrections = get_corrections(filtered, thresholds, market_status['market_multiplier'])
            c3.metric("🎯 تصحيح", len(corrections))
            early_list = get_early_uptrend_stocks(filtered, thresholds, market_status['market_multiplier'])
            c4.metric("🚀 صعود", len(early_list))
            support_list = get_support_stocks(filtered, thresholds)
            c5.metric("🔻 دعم", len(support_list))

            st.caption(f"🕐 آخر تحديث: {st.session_state.last_update}")

            # Opportunities tabs
            tab1, tab2, tab3, tab4 = st.tabs(["🎯 تصحيحات", "⚡ اختراق", "🚀 صعود", "🔻 دعم"])

            with tab1:
                if corrections:
                    for item in corrections[:6]:
                        render_opportunity_card(item, "correction")
                else:
                    st.info("لا توجد فرص تصحيح حالياً")

            with tab2:
                rapid = get_rapid_breakouts(filtered, thresholds)
                if rapid:
                    for item in rapid[:6]:
                        render_opportunity_card(item, "rapid")
                else:
                    st.info("لا توجد فرص اختراق حالياً")

            with tab3:
                if early_list:
                    for item in early_list[:6]:
                        render_opportunity_card(item, "early")
                else:
                    st.info("لا توجد فرص بداية صعود")

            with tab4:
                if support_list:
                    for item in support_list[:6]:
                        render_opportunity_card(item, "support")
                else:
                    st.info("لا توجد فرص دعم وارتداد")
        else:
            st.warning("⚠️ لا توجد بيانات. اضغط تحديث من الشريط الجانبي.")

    elif page == 'top10':
        st.title("🏆 أفضل 10 فرص")
        top = get_top_10(filtered, thresholds)
        if top:
            for i, an in enumerate(top, 1):
                conf = get_confidence(an, thresholds)
                with st.container():
                    c1, c2, c3 = st.columns([1, 3, 1])
                    with c1:
                        st.markdown(f"<h1 style='text-align:center; color:#FFD600;'>#{i}</h1>", unsafe_allow_html=True)
                    with c2:
                        st.markdown(f"**{an['name']}** - {an['desc']}")
                        st.progress(an['smart_score'] / 100, text=f"Smart Score: {an['smart_score']}")
                        st.caption(f"RR: {an['rr']} | RSI: {an['rsi']:.0f} | تداول: {an['daily_turnover']/1_000_000:.1f}M")
                    with c3:
                        st.markdown(f"<div style='background:{conf['color']}22; color:{conf['color']}; padding:6px; border-radius:8px; text-align:center; font-weight:bold;'>{conf['grade']}</div>", unsafe_allow_html=True)
                        if st.button("تحليل", key=f"top_{an['name']}"):
                            st.session_state.selected_stock = an
                            st.session_state.page = 'detail'
                            st.rerun()
                    st.divider()
        else:
            st.warning("لا توجد فرص مطابقة للمعايير")

    elif page == 'correction':
        st.title("🎯 صائد التصحيحات")
        st.info("الأسهم القوية التي تصحح في اتجاه صاعد")
        corrections = get_corrections(filtered, thresholds, market_status['market_multiplier'])
        if corrections:
            st.markdown(f"**عدد الفرص: {len(corrections)}**")
            for item in corrections:
                render_opportunity_card(item, "correction")
        else:
            st.info("لا توجد فرص حالياً")

    elif page == 'rapid':
        st.title("⚡ قناص الاختراق السريع")
        st.info("فرص اختراق المقاومة خلال جلسة أو جلستين")
        rapid = get_rapid_breakouts(filtered, thresholds)
        if rapid:
            st.markdown(f"**عدد الفرص: {len(rapid)}**")
            for item in rapid:
                render_opportunity_card(item, "rapid")
        else:
            st.info("لا توجد فرص حالياً")

    elif page == 'support':
        st.title("🔻 فرص الدعم والارتداد")
        st.info("أسهم قريبة من الدعم مع تأكيد ارتداد")
        support = get_support_stocks(filtered, thresholds)
        if support:
            st.markdown(f"**عدد الفرص: {len(support)}**")
            for item in support:
                render_opportunity_card(item, "support")
        else:
            st.info("لا توجد فرص حالياً")

    elif page == 'early_uptrend':
        st.title("🚀 بداية الموجة الصاعدة")
        st.info("أسهم في بداية اتجاه صاعد مع مساحة صعود ≥ 20%")
        early = get_early_uptrend_stocks(filtered, thresholds, market_status['market_multiplier'])
        if early:
            st.markdown(f"**عدد الفرص: {len(early)}**")
            for item in early:
                render_opportunity_card(item, "early")
        else:
            st.info("لا توجد فرص حالياً")

    elif page == 'analyze':
        st.title("🔍 تحليل سهم")
        sym = st.text_input("أدخل رمز السهم", placeholder="مثال: COMI, TMGH, ETEL").upper().strip()
        if sym:
            with st.spinner("جاري البحث..."):
                data = fetch_single_stock(sym)
                if data:
                    res = analyze_stock(data[0])
                    if res:
                        render_stock_detail(res, thresholds)
                    else:
                        st.error("فشل تحليل السهم - سيولة ضعيفة")
                else:
                    st.error(f"السهم {sym} غير موجود")
                    if st.session_state.all_results:
                        syms = [r['name'] for r in st.session_state.all_results[:20] if r]
                        st.info(f"أمثلة: {', '.join(syms)}")

    elif page == 'performance':
        st.title("📊 تقييم الأداء")
        trades = load_trades()
        stats = get_performance_stats(trades)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("إجمالي الصفقات", stats['total'])
        c2.metric("✅ الهدف", stats['hit_target'])
        c3.metric("❌ الوقف", stats['stopped_out'])
        c4.metric("⏳ مفتوحة", stats['still_open'])

        c1, c2 = st.columns(2)
        c1.metric("نسبة النجاح", f"{stats['success_rate']}%")
        c2.metric("متوسط RR", stats['avg_rr'])

        if trades:
            st.markdown("### آخر الصفقات")
            for trade in trades[-15:][::-1]:
                status_color = {"hit_target": "#00C853", "stopped_out": "#FF5252"}.get(trade.get('status'), "#FFB300")
                status_text = {"hit_target": "🟢 هدف", "stopped_out": "🔴 وقف"}.get(trade.get('status'), "🟡 مفتوحة")
                st.markdown(f"""
                <div style='background:#0d1117; border:1px solid #30363d; border-radius:8px; padding:10px; margin:5px 0; border-right: 3px solid {status_color};'>
                    <b>{trade.get('name', 'N/A')}</b> ({trade.get('trade_type', '')}) - {status_text}<br>
                    📅 {trade.get('date_recorded', '')} | 🎯 {trade.get('target', 0):.3f} | 🛑 {trade.get('stop_loss', 0):.3f} | ⚖️ {trade.get('rr', 0)}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("لا توجد صفقات مسجلة")

if __name__ == "__main__":
    main()
