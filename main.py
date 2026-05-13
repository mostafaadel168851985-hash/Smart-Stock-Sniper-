import streamlit as st
import streamlit.components.v1 as components
import requests
from datetime import datetime, date
import json
import os
import re
import urllib.parse
import pandas as pd
from io import BytesIO

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
    except Exception as e:
        print(f"Error: {e}")

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


# ================== 🔥 SMART SCORE ==================
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


# ================== 🎯 ADVANCED CONFIDENCE SCORE (قرار القناص) ==================
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
    
    # 1. الاتجاه العام
    if t_long == "صاعد" or (sma200 and p > sma200):
        score += 1
    
    # 2. الزخم
    if t_med == "صاعد" and t_short == "صاعد":
        score += 1
    
    # 3. RSI في منطقة الانطلاق
    if 45 < rsi < 65:
        score += 1
    
    # 4. السيولة
    if ratio > 1.5:
        score += 1
    elif ratio > 1.2:
        score += 0.5
    
    # 5. قرب من المقاومة
    if r1 and r1 > p:
        dist = (r1 - p) / p * 100
        if dist < 2:
            score += 1
        elif dist < 3:
            score += 0.5
    
    # 6. الشمعة الصاعدة
    if change > 0.2:
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
    return conf["score"]


# ================== 🎯 CORRECTION HUNTER (صائد التصحيحات) ==================
def is_correction(an):
    if an is None:
        return False, [], 0
    
    p = an.get('p', 0)
    rsi = an.get('rsi', 50)
    sma200 = an.get('sma200', 0)
    ratio = an.get('ratio', 0)
    change = an.get('chg', 0)
    t_long = an.get('t_long', 'هابط')
    rr = an.get('rr', 0)
    
    reasons = []
    score = 0
    max_score = 7
    
    if t_long == "صاعد" or (sma200 and p > sma200):
        score += 3
        reasons.append("📈 الاتجاه العام صاعد (فوق EMA200)")
    else:
        return False, [], 0
    
    if 30 <= rsi <= 50:
        score += 2
        if rsi < 35:
            reasons.append(f"🔻 RSI منخفض جداً ({rsi:.0f}) - تشبع بيع ممتاز")
        else:
            reasons.append(f"📊 RSI في منطقة تصحيح ({rsi:.0f})")
    elif rsi < 30:
        score += 1
        reasons.append(f"🟢 RSI منخفض جداً ({rsi:.0f}) - تشبع بيع")
    else:
        return False, [], 0
    
    if change > 0:
        score += 1
        reasons.append(f"📈 بداية ارتداد ({change:+.2f}%)")
    
    if ratio > 1.2:
        score += 1
        reasons.append(f"💧 سيولة جيدة ({ratio:.1f}x)")
    
    if rr >= 1.5:
        score += 1
        reasons.append(f"⚖️ RR جيد ({rr})")
    
    strength = int((score / max_score) * 100)
    return score >= 4, reasons, strength


# ================== 🚀 BREAKOUT SCANNER (صائد الانفجارات) ==================
def is_breakout_candidate(an):
    """
    الكشف عن الأسهم على وشك الانفجار (اختراق وشيك)
    متوقع حركة 5%+ خلال أيام قليلة
    """
    if an is None:
        return False, [], 0
    
    p = an.get('p', 0)
    rsi = an.get('rsi', 50)
    ratio = an.get('ratio', 0)
    change = an.get('chg', 0)
    t_short = an.get('t_short', 'هابط')
    t_med = an.get('t_med', 'هابط')
    sma20 = an.get('sma20', p)
    r1 = an.get('r1', p * 1.05)
    
    reasons = []
    score = 0
    max_score = 10
    
    # 1. قرب من المقاومة R1 (أقل من 1.5%) - أهم شرط
    if r1 and r1 > p:
        dist_to_r1 = (r1 - p) / p * 100
        if dist_to_r1 < 0.5:
            score += 3
            reasons.append(f"🎯 عند المقاومة ({dist_to_r1:.1f}% - اختراق وشيك)")
        elif dist_to_r1 < 1.0:
            score += 2
            reasons.append(f"🎯 قريب جداً من المقاومة ({dist_to_r1:.1f}%)")
        elif dist_to_r1 < 1.5:
            score += 1
            reasons.append(f"🎯 قريب من المقاومة ({dist_to_r1:.1f}%)")
        else:
            return False, [], 0
    else:
        return False, [], 0
    
    # 2. RSI في منطقة الانطلاق (55-75) - زخم قوي
    if 55 <= rsi <= 75:
        score += 2
        if rsi < 65:
            reasons.append(f"📈 RSI صحي ({rsi:.0f}) - زخم قوي")
        else:
            reasons.append(f"⚡ RSI قوي ({rsi:.0f}) - يقترب من التشبع")
    elif 45 <= rsi < 55:
        score += 1
        reasons.append(f"📊 RSI متوسط ({rsi:.0f}) - يحتاج زخم أكثر")
    else:
        reasons.append(f"⚠️ RSI خارج المنطقة ({rsi:.0f})")
    
    # 3. سيولة عالية (أكبر من 1.8x)
    if ratio > 2.5:
        score += 2
        reasons.append(f"💧 سيولة استثنائية ({ratio:.1f}x)")
    elif ratio > 1.8:
        score += 1.5
        reasons.append(f"💧 سيولة عالية ({ratio:.1f}x)")
    elif ratio > 1.2:
        score += 1
        reasons.append(f"💧 سيولة جيدة ({ratio:.1f}x)")
    else:
        reasons.append(f"❄️ سيولة منخفضة ({ratio:.1f}x)")
    
    # 4. الاتجاه صاعد (قصير ومتوسط)
    if t_short == "صاعد" and t_med == "صاعد":
        score += 1.5
        reasons.append(f"📊 اتجاه صاعد في الأطر القصيرة والمتوسطة")
    elif t_short == "صاعد":
        score += 0.5
        reasons.append(f"📊 اتجاه قصير صاعد فقط")
    else:
        reasons.append(f"📉 اتجاه هابط - غير مناسب")
    
    # 5. السعر فوق EMA20 (زخم إيجابي)
    if p > sma20:
        score += 1
        reasons.append(f"📈 السعر فوق EMA20 (زخم إيجابي)")
    
    # 6. تغير إيجابي في آخر جلسة
    if change > 0.5:
        score += 0.5
        reasons.append(f"🟢 تغير إيجابي قوي ({change:+.2f}%)")
    elif change > 0:
        score += 0.25
        reasons.append(f"🟢 تغير إيجابي ({change:+.2f}%)")
    
    # حساب نسبة القوة (0-100%)
    strength = int((score / max_score) * 100)
    
    # توقع نسبة الانفجار المتوقعة
    if strength >= 80:
        expected_breakout = "🔥🔥 8-10% متوقع خلال 2-3 جلسات"
    elif strength >= 60:
        expected_breakout = "🚀 5-7% متوقع خلال 3-5 جلسات"
    elif strength >= 40:
        expected_breakout = "📈 3-5% متوقع خلال أسبوع"
    else:
        expected_breakout = "⚠️ حركة محدودة متوقعة"
    
    return score >= 5, reasons, strength, expected_breakout


# ================== 📂 SECTOR FILTER ==================
SECTORS = {
    "🏦 البنوك": ["CIEB", "COMI", "AAIB", "QNBA"],
    "🏗️ العقارات": ["TMGH", "OCDI", "PHDC", "HELI"],
    "🍔 الأغذية": ["BFR", "EFID", "JUFO"],
    "📡 الاتصالات": ["ETEL", "OTMT", "TE"],
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
    payload = {"filter": [{"left": "volume", "operation": "greater", "right": 1000}], "columns": cols, "range": [0, 300]}
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
        if p is None:
            return None
        desc = desc or name
        ratio = v / avg_v if avg_v and avg_v > 0 else 0
        t_short = "صاعد" if (sma20 and p > sma20) else "هابط"
        t_med = "صاعد" if (sma50 and p > sma50) else "هابط"
        t_long = "صاعد" if (sma200 and p > sma200) else "هابط"
        
        entry_min, entry_max = p * 0.98, p * 1.01
        entry_price = (entry_min + entry_max) / 2
        pp = (p + (h or p) + (l or p)) / 3
        s1, r1 = (2 * pp) - (h or p), (2 * pp) - (l or p)
        s2, r2 = pp - ((h or p) - (l or p)), pp + ((h or p) - (l or p))
        stop_loss = min(s2, entry_price * 0.97)
        target = max(r1, entry_price * 1.05)
        profit_ps = target - entry_price
        loss_ps = entry_price - stop_loss
        if loss_ps <= 0:
            return None
        rr = round(profit_ps / loss_ps, 2)
        
        temp_res = {'t_short': t_short, 't_med': t_med, 't_long': t_long, 'ratio': ratio, 'rsi': rsi or 0, 'rr': rr}
        smart_score = smart_score_pro(temp_res)
        
        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi or 0, "chg": chg or 0, "ratio": ratio,
            "t_short": t_short, "t_med": t_med, "t_long": t_long,
            "s1": s1, "s2": s2, "r1": r1, "r2": r2, "pp": pp, "sma20": sma20, "sma50": sma50, "sma200": sma200,
            "entry_range": f"{entry_min:.2f} - {entry_max:.2f}", "entry_price": entry_price,
            "stop_loss": stop_loss, "target": target, "rr": rr, 
            "risk_pct": (loss_ps/entry_price)*100, "target_pct": (profit_ps/entry_price)*100,
            "smart_score": smart_score,
        }
    except:
        return None

def preprocess(raw_data):
    return [analyze_stock(r) for r in raw_data if analyze_stock(r)]

def get_top_10(results):
    valid = [r for r in results if r]
    sorted_results = sorted(valid, key=lambda x: x.get('smart_score', 0), reverse=True)
    return sorted_results[:10]

def get_fresh_data():
    with st.spinner("🔄 جاري تحميل البيانات..."):
        raw = get_all_data()
        if raw:
            st.session_state.all_results = preprocess(raw)
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
st.set_page_config(page_title="🎯 قناص EGX", layout="wide", page_icon="🎯")
st.markdown("""
<style>
.stButton>button { width: 100%; border-radius: 10px; height: 45px; font-weight: bold; }
.stock-header { font-size: 22px; font-weight: bold; color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 8px; }
.score-tag { float: right; background: #238636; color: white; padding: 2px 12px; border-radius: 15px; font-size: 14px; }
.quality-excellent { background: #1f4f2b; color: white; padding: 5px; border-radius: 8px; text-align: center; }
.quality-good { background: #1f3a4f; color: white; padding: 5px; border-radius: 8px; text-align: center; }
.quality-normal { background: #4a4a4a; color: white; padding: 5px; border-radius: 8px; text-align: center; }
.warning-box { background: rgba(248,81,73,0.15); border-right: 4px solid #f85149; padding: 10px; border-radius: 8px; margin: 10px 0; }
.success-box { background: rgba(63,185,80,0.15); border-right: 4px solid #3fb950; padding: 10px; border-radius: 8px; margin: 10px 0; }
.info-box { background: rgba(88,166,255,0.15); border-right: 4px solid #58a6ff; padding: 10px; border-radius: 8px; margin: 10px 0; }
.entry-card { background: #0d1117; border: 1px solid #3fb950; border-radius: 10px; padding: 12px; margin: 10px 0; }
.breakout-card { background: linear-gradient(135deg, #0d1117, #1a1a2e); border: 2px solid #ff6f00; border-radius: 12px; padding: 15px; margin: 15px 0; }
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


def render_mode_and_sector():
    """عرض نمط التداول وفلتر القطاع في expander واحد"""
    with st.expander("🎯 نمط التداول وفلتر القطاع", expanded=False):
        # نمط التداول
        st.markdown("#### 🧠 نمط التداول")
        c1, c2, c3 = st.columns(3)
        if c1.button("🛡️ محافظ", use_container_width=True): 
            st.session_state.mode = "🛡️ محافظ"
        if c2.button("⚖️ متوازن", use_container_width=True): 
            st.session_state.mode = "⚖️ متوازن"
        if c3.button("🚀 هجومي", use_container_width=True): 
            st.session_state.mode = "🚀 هجومي"
        
        # عرض النمط الحالي
        color = "#238636" if "محافظ" in st.session_state.mode else "#f85149" if "هجومي" in st.session_state.mode else "#d29922"
        st.markdown(f"<div style='background:{color}; padding:5px; border-radius:8px; text-align:center; color:white; margin:10px 0;'>{st.session_state.mode}</div>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # فلتر القطاع
        st.markdown("#### 📂 فلتر القطاع")
        sectors = ["🌍 الكل", "🏦 البنوك", "🏗️ العقارات", "🍔 الأغذية", "📡 الاتصالات", "📌 أخرى"]
        selected = st.selectbox("اختر قطاعاً", sectors, index=0)
        if selected != st.session_state.sector_filter:
            st.session_state.sector_filter = selected
            st.rerun()


# ================== 📄 GUIDE SECTION ==================
def render_guide():
    st.markdown("""
    <div class='info-box'>
    📚 <b>دليل الأقسام - كيف يعمل كل قسم؟</b>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("🎯 قرار القناص - نظام التقييم المتقدم", expanded=True):
        st.markdown("""
        ### كيف يتم حساب "قرار القناص"؟
        
        النظام يجمع **6 مؤشرات فنية مختلفة** في تقييم واحد:
        
        | المؤشر | الشرط | لماذا؟ |
        |--------|-------|--------|
        | **الاتجاه العام** | السعر فوق EMA200 | يضمن أن السهم في ترند صاعد |
        | **الزخم** | EMA20 و EMA50 صاعدين | يؤكد قوة الحركة الحالية |
        | **RSI** | بين 45 و 65 | منطقة انطلاق صحية (غير مشبعة) |
        | **السيولة** | حجم > 1.5x المتوسط | تأكيد اهتمام المؤسسات |
        | **الاختراق** | قرب من المقاومة R1 (<2%) | السهم على وشك اختراق |
        | **الشمعة** | الشمعة الأخيرة صاعدة | تأكيد فوري للحركة |
        
        **النتائج:**
        - 🔥 **85-100%**: دخول الآن (جميع المؤشرات متوافقة)
        - ✅ **65-84%**: شراء حذر (معظم المؤشرات إيجابية)  
        - 🟡 **40-64%**: انتظار (بعض المؤشرات إيجابية)
        - ❌ **0-39%**: تجنب (المؤشرات سلبية)
        """)
    
    with st.expander("🎯 صائد التصحيحات - فرص الشراء من القاع", expanded=True):
        st.markdown("""
        ### كيف يختار "صائد التصحيحات" الأسهم؟
        
        هذا القسم يبحث عن **الأسهم القوية التي تصحح**:
        
        | الشرط | الدلالة |
        |--------|---------|
        | الاتجاه العام صاعد | السهم في ترند صاعد قوي |
        | RSI بين 30-50 | السهم في منطقة تصحيح (يرتاح بعد الصعود) |
        | تغير إيجابي | بداية ارتداد من القاع |
        | سيولة جيدة | حجم تداول > المتوسط |
        | RR >= 1.5 | نسبة مخاطرة/عائد جيدة |
        
        **لماذا هذه الفرصة مربحة؟**
        - الدخول في منطقة التصحيح = مخاطرة أقل
        - السهم القوي يعود للصعود بعد التصحيح
        """)
    
    with st.expander("🚀 صائد الانفجارات - فرص الاختراق الوشيك", expanded=True):
        st.markdown("""
        ### كيف يختار "صائد الانفجارات" الأسهم؟
        
        هذا القسم يبحث عن **الأسهم على وشك الاختراق**:
        
        | الشرط | الدلالة |
        |--------|---------|
        | قرب من المقاومة R1 | أقل من 1.5% (على وشك الاختراق) |
        | RSI بين 55-75 | زخم قوي غير مشبع |
        | سيولة عالية | أكبر من 1.8x المتوسط |
        | اتجاه صاعد | EMA20 و EMA50 صاعدين |
        | زخم إيجابي | السعر فوق EMA20 وتغير إيجابي |
        
        **التوقع:**
        - 🔥🔥 قوة 80%+: 8-10% خلال 2-3 جلسات
        - 🚀 قوة 60%+: 5-7% خلال 3-5 جلسات
        - 📈 قوة 40%+: 3-5% خلال أسبوع
        """)
    
    with st.expander("🏆 أفضل 10 فرص - أقوى الأسهم اليوم", expanded=True):
        st.markdown("""
        ### كيف يتم ترتيب أفضل 10 فرص؟
        
        يتم ترتيب **جميع الأسهم** تنازلياً حسب **Smart Score**:
        
        **ما هو Smart Score؟**
        
        درجة مركبة من **8 عوامل**:
        - الاتجاه قصير المدى (EMA20) - 15 نقطة
        - الاتجاه متوسط المدى (EMA50) - 15 نقطة
        - الاتجاه طويل المدى (EMA200) - 5 نقاط
        - سيولة عالية (ratio > 2) - 20 نقطة
        - سيولة جيدة (ratio > 1.5) - 10 نقاط
        - RSI صحي (50-65) - 20 نقطة
        - RR ممتاز (>=2) - 20 نقطة
        - RR جيد (>=1.5) - 10 نقاط
        
        **التصنيف:**
        - 70-100: 🔥 فرصة قوية جداً
        - 50-69: ✅ فرصة جيدة
        - 30-49: ⚠️ تحت المراقبة
        - 0-29: ❄️ ضعيف
        """)
    
    with st.expander("⚖️ RR Ratio - نسبة المخاطرة إلى العائد", expanded=True):
        st.markdown("""
        ### ما هو RR Ratio?
        
        **RR = (الهدف - سعر الدخول) / (سعر الدخول - وقف الخسارة)**
        
        | القيمة | المعنى |
        |--------|--------|
        | RR < 1 | ❌ سيء - المخاطرة أكبر من العائد |
        | RR = 1 | ⚠️ متوسط - المخاطرة = العائد |
        | RR = 1.5 | ✅ جيد - العائد أكبر 1.5 مرة من المخاطرة |
        | RR >= 2 | 🔥 ممتاز - العائد ضعف المخاطرة |
        """)
    
    st.info("💡 **تذكير:** كل هذه المؤشرات أدوات مساعدة. القرار النهائي يعتمد على تحليلك الشخصي وإدارة المخاطر.")


# ================== UI RENDERER (الكامل مع خطة الدخول) ==================
def render_stock_card(res, is_top10=False, is_gold=False):
    if res is None:
        st.warning("بيانات السهم غير متوفرة")
        return
    
    # عنوان السهم
    st.markdown(f"<div class='stock-header'>{res['name']} - {res['desc']}<span class='score-tag'>Smart: {res.get('smart_score', 0)}</span></div>", unsafe_allow_html=True)
    
    # كارت الثقة
    render_confidence_card(res)
    
    # تقييم الجودة
    if is_top10:
        if res.get('smart_score', 0) >= 85:
            st.markdown('<div class="quality-excellent">🏆 الأفضل اليوم</div>', unsafe_allow_html=True)
        elif res.get('smart_score', 0) >= 75:
            st.markdown('<div class="quality-good">⭐ ممتاز</div>', unsafe_allow_html=True)
        elif res.get('smart_score', 0) >= 65:
            st.markdown('<div class="quality-good">✅ جيد</div>', unsafe_allow_html=True)
    elif is_gold:
        st.markdown('<div class="quality-excellent">💎 فرصة ذهبية</div>', unsafe_allow_html=True)
    
    # عرض السيولة
    ratio = res.get('ratio', 0)
    if ratio > 2:
        vol_text = f"🚀 قوية جداً ({ratio:.1f}x)"
    elif ratio > 1.5:
        vol_text = f"⚡ قوية ({ratio:.1f}x)"
    elif ratio > 1:
        vol_text = f"🙂 عادية ({ratio:.1f}x)"
    elif ratio > 0.5:
        vol_text = f"❄️ ضعيفة ({ratio:.1f}x)"
    else:
        vol_text = f"❓ غير معروف ({ratio:.1f}x)"
    
    # المؤشرات الأساسية
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: st.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:+.2f}%")
    with col2: st.metric("Smart Score", f"{res['smart_score']}/100")
    with col3: st.metric("RR Ratio", f"{res['rr']}")
    with col4: st.metric("RSI", f"{res['rsi']:.0f}")
    with col5: st.metric("السيولة", vol_text)
    
    # التحليل الفني
    with st.expander("📊 التحليل الفني", expanded=True):
        render_chart(res['name'])
        
        # الاتجاهات
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
        
        # نطاق الدخول
        st.markdown(f"""
        <div class='entry-card'>
            🎯 <b>نطاق الدخول:</b> {res['entry_range']}<br>
            🛑 <b>وقف الخسارة:</b> {res['stop_loss']:.2f} <span style='color:#f85149'>(-{res['risk_pct']:.1f}%)</span><br>
            🏁 <b>المستهدف:</b> {res['target']:.2f} <span style='color:#58a6ff'>(+{res['target_pct']:.1f}%)</span>
        </div>
        """, unsafe_allow_html=True)
        
        # الدعم والمقاومة
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
    
    # إدارة المخاطر وخطة الدخول الكاملة
    with st.expander("💰 إدارة المخاطر وخطة الدخول", expanded=True):
        deal_size = st.number_input("💰 ميزانية الصفقة (ج)", value=10000, step=1000, key=f"deal_{res['name']}")
        entry_price = res['entry_price']
        
        if deal_size > 0 and entry_price > 0:
            # حساب أساسي
            shares_deal = int(deal_size / entry_price)
            actual_value = shares_deal * entry_price
            profit_val = (res['target'] - entry_price) * shares_deal
            loss_val = (entry_price - res['stop_loss']) * shares_deal
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("📦 عدد الأسهم", f"{shares_deal:,}")
                st.metric("💰 قيمة الصفقة", f"{actual_value:,.0f} ج")
            with col2:
                st.metric("🟢 الربح المتوقع", f"{profit_val:,.0f} ج", delta=f"+{res['target_pct']:.1f}%")
                st.metric("🔴 الخسارة المحتملة", f"{loss_val:,.0f} ج", delta=f"-{res['risk_pct']:.1f}%")
            
            # خطة الدخول المتكاملة (3 مستويات)
            st.markdown("### 🏹 خطة الدخول المتكاملة")
            
            range_size = entry_price - res['stop_loss']
            
            entry_level_1 = entry_price
            entry_level_2 = max(entry_price - (range_size * 0.5), res['stop_loss'] * 1.02)
            entry_level_3 = entry_price + (res['target'] - entry_price) * 0.3
            
            # توزيع الوزن حسب RR
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
            <div style='background:#0d1117;border:1px solid #3fb950;border-radius:10px;padding:12px;margin:10px 0;'>
                <b>📌 المستوى الأول - الدخول الأساسي</b><br>
                🟢 السعر: <b>{entry_level_1:.2f}</b> ج<br>
                📦 الكمية: <b>{shares_1:,}</b> سهم | 💰 المبلغ: <b>{amount_1:,.0f}</b> ج ({weights[0]*100:.0f}% من الميزانية)<br>
                <small>🔹 يتم التنفيذ عند وصول السعر للنطاق</small>
            </div>
            
            <div style='background:#0d1117;border:1px solid #d29922;border-radius:10px;padding:12px;margin:10px 0;'>
                <b>📌 المستوى الثاني - تعزيز الدعم</b><br>
                🟡 السعر: <b>{entry_level_2:.2f}</b> ج<br>
                📦 الكمية: <b>{shares_2:,}</b> سهم | 💰 المبلغ: <b>{amount_2:,.0f}</b> ج ({weights[1]*100:.0f}% من الميزانية)<br>
                <small>🔹 يتم التنفيذ إذا هبط السعر للدعم دون كسر الوقف</small>
            </div>
            
            <div style='background:#0d1117;border:1px solid #58a6ff;border-radius:10px;padding:12px;margin:10px 0;'>
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
        current_price_trail = st.number_input("السعر الحالي", value=res['p'], key=f"trail_{res['name']}")
        highest_price_trail = st.number_input("أعلى سعر تم الوصول إليه", value=res['p'], key=f"high_{res['name']}")
        
        # حساب الوقف المتحرك
        entry = res['entry_price']
        rr = res['rr']
        if current_price_trail <= entry:
            trailing = entry * 0.97
        else:
            profit_pct = (current_price_trail - entry) / entry * 100
            if highest_price_trail > entry:
                trailing = highest_price_trail * 0.95
            elif profit_pct >= 5 and rr >= 1.5:
                trailing = entry + (profit_pct / 2) / 100 * entry
                trailing = min(trailing, current_price_trail * 0.98)
            elif profit_pct >= 3:
                trailing = entry
            else:
                trailing = entry * 0.97
        
        st.info(f"🛡️ **وقف الخسارة المتحرك المقترح:** {trailing:.2f} ج (الأصلي: {res['stop_loss']:.2f} ج)")
        
        st.warning("⚠️ **تذكير:** هذه الخطة استرشادية. القرار النهائي يعتمد على تحليلك الشخصي وظروف السوق.")
    
    # تحليل الوضع الحالي
    with st.expander("🧠 تحليل الوضع الحالي", expanded=False):
        col1, col2 = st.columns(2)
        buy_price = col1.number_input("سعر الشراء", value=res['p'], key=f"buy_{res['name']}")
        qty = col2.number_input("الكمية", value=100, step=100, key=f"qty_{res['name']}")
        
        if qty > 0 and buy_price > 0:
            current = res['p']
            pnl = (current - buy_price) * qty
            pnl_pct = ((current - buy_price) / buy_price) * 100
            
            if pnl > 0:
                st.success(f"🟢 كسبان: {pnl:,.0f} ج (+{pnl_pct:.2f}%)")
                if pnl_pct >= 3:
                    st.info(f"💡 حرك الوقف لنقطة الدخول: {buy_price:.2f}")
            elif pnl < 0:
                st.error(f"🔴 خسران: {pnl:,.0f} ج ({pnl_pct:.2f}%)")
            else:
                st.info("⚖️ على التعادل")
            
            if current >= res['target']:
                st.success("🎉 تم تحقيق الهدف!")
            elif current <= res['stop_loss']:
                st.error("⚠️ كسر وقف الخسارة!")
            
            trend_score = (1 if res['t_short'] == "صاعد" else 0) + (1 if res['t_med'] == "صاعد" else 0) + (1 if res['ratio'] > 1.5 else 0)
            if trend_score >= 2:
                st.success(f"✅ استمر طالما السعر فوق {res['stop_loss']:.2f}")
            else:
                st.warning("⚠️ اتجاه ضعيف - فكر في تأمين الأرباح")
    
    # مؤشرات متقدمة
    with st.expander("📈 مؤشرات متقدمة", expanded=False):
        # Stochastic RSI
        rsi = res['rsi']
        if rsi <= 20:
            stoch_signal = "🟢 تشبع بيع - فرصة انعكاس"
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
            <b>🔄 Stochastic RSI</b><br>
            🧠 {stoch_signal}
        </div>
        """, unsafe_allow_html=True)
        
        # نسبة النجاح المتوقعة
        success_rate = 50
        if res['smart_score'] >= 70 and res['rr'] >= 1.5 and 45 < res['rsi'] < 65:
            success_rate = 75
        elif res['smart_score'] >= 50 and res['rr'] >= 1.2:
            success_rate = 60
        elif res['smart_score'] >= 30:
            success_rate = 45
        else:
            success_rate = 30
        
        st.markdown(f"""
        <div style='background:#0d1117;border:1px solid #d29922;border-radius:10px;padding:12px;margin-bottom:15px;'>
            <b>📈 نسبة النجاح المتوقعة</b><br>
            🎯 <b>{success_rate}%</b>
        </div>
        """, unsafe_allow_html=True)
        
        # معلومات إضافية
        st.markdown(f"""
        <div style='background:#0d1117;border:1px solid #30363d;border-radius:10px;padding:12px;'>
            🤖 <b>Smart Score:</b> {res['smart_score']}/100<br>
            📊 <b>الثقة:</b> {get_confidence(res)['score']}/100<br>
            🎯 {get_confidence(res)['advice']}
        </div>
        """, unsafe_allow_html=True)
    
    # مشاركة واتساب
    msg = f"📊 تحليل سهم {res['name']}\n💰 السعر: {res['p']:.2f} ج\n🎯 ثقة القناص: {get_confidence(res)['score']}%\n🎯 الدخول: {res['entry_range']}\n🛑 الوقف: {res['stop_loss']:.2f}\n🏁 الهدف: {res['target']:.2f}\n⚖️ RR: {res['rr']}\n💧 السيولة: {res['ratio']:.1f}x"
    encoded = urllib.parse.quote(msg)
    st.markdown(f"[📱 مشاركة عبر واتساب](https://wa.me/?text={encoded})")


# ================== PAGES ==================
if st.session_state.all_results is None:
    get_fresh_data()

if st.session_state.page == 'home':
    st.title("🎯 قناص EGX - الإصدار المتقدم")
    
    # نمط التداول وفلتر القطاع في expander واحد
    render_mode_and_sector()
    
    # الأزرار الرئيسية - الصف الأول
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🏆 أفضل 10 فرص", use_container_width=True):
            st.session_state.page = 'top10'
            st.rerun()
    with col2:
        if st.button("🎯 صائد التصحيحات", use_container_width=True):
            st.session_state.page = 'correction'
            st.rerun()
    with col3:
        if st.button("🚀 صائد الانفجارات", use_container_width=True):
            st.session_state.page = 'breakout'
            st.rerun()
    
    # الأزرار الرئيسية - الصف الثاني
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔍 تحليل سهم", use_container_width=True):
            st.session_state.page = 'analyze'
            st.rerun()
    with col2:
        if st.button("📊 تقييم الأداء", use_container_width=True):
            st.session_state.page = 'performance'
            st.rerun()
    with col3:
        if st.button("📖 دليل الأقسام", use_container_width=True):
            st.session_state.page = 'guide'
            st.rerun()
    
    # إدارة التطبيق
    with st.expander("⚙️ إدارة التطبيق", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 تحديث البيانات", use_container_width=True):
                get_fresh_data()
                st.success("✅ تم تحديث البيانات!")
                st.rerun()
        with col2:
            if st.button("🗑️ مسح بيانات التقييم", use_container_width=True):
                if os.path.exists(TRADES_FILE):
                    os.remove(TRADES_FILE)
                    st.success("✅ تم مسح البيانات!")
                    st.rerun()
    
    # إحصائيات
    sector_filter = st.session_state.sector_filter
    filtered = filter_by_sector(st.session_state.all_results, sector_filter)
    if filtered:
        gold_count = len([r for r in filtered if r.get('smart_score', 0) >= 70])
        st.markdown(f"""
        <div style='background:#0d1117;border-radius:10px;padding:15px;margin-top:20px;'>
            <b>📊 إحصائية السوق</b><br>
            • القطاع: {sector_filter}<br>
            • إجمالي الأسهم: {len(filtered)}<br>
            • 🔥 فرص قوية (Smart >= 70): {gold_count}
        </div>
        """, unsafe_allow_html=True)


# ================== أفضل 10 فرص ==================
elif st.session_state.page == 'top10':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    
    sector_filter = st.session_state.sector_filter
    filtered = filter_by_sector(st.session_state.all_results, sector_filter)
    top = get_top_10(filtered)
    
    st.markdown("## 🏆 أفضل 10 فرص")
    for i, an in enumerate(top, 1):
        if an:
            with st.expander(f"#{i} - {an['name']} | Smart: {an['smart_score']} | RR: {an['rr']}"):
                render_stock_card(an, is_top10=True)
                if st.button(f"💾 تسجيل الصفقة", key=f"rec_{an['name']}"):
                    record_trade(an, "top10")
                    st.success("تم تسجيل الصفقة!")


# ================== صائد التصحيحات ==================
elif st.session_state.page == 'correction':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    
    st.title("🎯 صائد التصحيحات")
    st.markdown("""
    <div class='info-box'>
    🎯 <b>كيف تم الاختيار؟</b><br>
    • الاتجاه العام صاعد | • RSI في التصحيح (30-50) | • بداية ارتداد | • سيولة جيدة | • RR جيد
    </div>
    """, unsafe_allow_html=True)
    
    sector_filter = st.session_state.sector_filter
    filtered = filter_by_sector(st.session_state.all_results, sector_filter)
    
    corrections = []
    for an in filtered:
        if an:
            is_corr, reasons, strength = is_correction(an)
            if is_corr:
                corrections.append({'stock': an, 'reasons': reasons, 'strength': strength})
    
    if corrections:
        corrections.sort(key=lambda x: x['strength'], reverse=True)
        st.markdown(f"**🎯 عدد فرص التصحيح: {len(corrections)}**")
        for item in corrections:
            an = item['stock']
            reasons = item['reasons']
            strength = item['strength']
            color = "#4caf50" if strength >= 70 else "#ff9800" if strength >= 50 else "#f44336"
            
            st.markdown(f"""
            <div style='background:#0d1117;border:2px solid #e91e63;border-radius:12px;padding:15px;margin-bottom:15px;'>
                <div style='display:flex;justify-content:space-between;'>
                    <h3>🎯 {an['name']} - {an['desc']}</h3>
                    <span style='background:{color}; padding:4px 12px; border-radius:20px;'>{strength}%</span>
                </div>
                <div style='height:6px; background:#333; margin:10px 0;'><div style='width:{strength}%; background:{color}; height:6px;'></div></div>
                <div>💰 {an['p']:.2f} ج | RSI: {an['rsi']:.1f} | سيولة: {an['ratio']:.1f}x | تغير: {an['chg']:+.2f}%</div>
                <div>✅ {', '.join(reasons)}</div>
            </div>
            """, unsafe_allow_html=True)
            
            render_stock_card(an)
    else:
        st.info("لا توجد فرص تصحيح حالياً")


# ================== 🚀 صائد الانفجارات (BREAKOUT SCANNER) ==================
elif st.session_state.page == 'breakout':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    
    st.title("🚀 صائد الانفجارات")
    st.markdown("""
    <div class='info-box'>
    🚀 <b>كيف تم الاختيار؟</b><br>
    • قرب من المقاومة R1 (أقل من 1.5%) | • RSI 55-75 (زخم قوي) | • سيولة عالية (>1.8x)<br>
    • اتجاه صاعد | • زخم إيجابي<br>
    📈 <b>متوقع:</b> حركة 5%+ خلال أيام قليلة
    </div>
    """, unsafe_allow_html=True)
    
    sector_filter = st.session_state.sector_filter
    filtered = filter_by_sector(st.session_state.all_results, sector_filter)
    
    breakout_stocks = []
    for an in filtered:
        if an:
            is_breakout, reasons, strength, expected = is_breakout_candidate(an)
            if is_breakout:
                breakout_stocks.append({
                    'stock': an, 
                    'reasons': reasons, 
                    'strength': strength,
                    'expected': expected
                })
    
    if breakout_stocks:
        breakout_stocks.sort(key=lambda x: x['strength'], reverse=True)
        st.markdown(f"**🚀 عدد فرص الانفجار: {len(breakout_stocks)}**")
        
        for item in breakout_stocks:
            an = item['stock']
            reasons = item['reasons']
            strength = item['strength']
            expected = item['expected']
            
            # تحديد اللون حسب القوة
            if strength >= 80:
                color = "#ff6f00"
                emoji = "🔥🔥"
            elif strength >= 60:
                color = "#ff9800"
                emoji = "🚀"
            elif strength >= 40:
                color = "#ffc107"
                emoji = "📈"
            else:
                color = "#ff9800"
                emoji = "⭐"
            
            st.markdown(f"""
            <div class='breakout-card'>
                <div style='display:flex;justify-content:space-between;align-items:center;'>
                    <h2 style='color:#ff6f00;margin:0'>{emoji} {an['name']} - {an['desc']}</h2>
                    <span style='background:{color}; padding:8px 16px; border-radius:25px; color:white; font-weight:bold;'>{strength}%</span>
                </div>
                <div style='height:8px; background:#333; margin:10px 0; border-radius:4px;'>
                    <div style='width:{strength}%; background:{color}; height:8px; border-radius:4px;'></div>
                </div>
                <div style='margin-top:15px;'>
                    <b>📊 المعطيات الفنية:</b><br>
                    • السعر: {an['p']:.2f} ج | المقاومة R1: {an['r1']:.2f} ج ({(an['r1']-an['p'])/an['p']*100:.2f}% متبقي)<br>
                    • RSI: {an['rsi']:.1f} | السيولة: {an['ratio']:.1f}x | التغير: {an['chg']:+.2f}%<br>
                    • Smart Score: {an['smart_score']}/100 | RR: {an['rr']}
                </div>
                <div style='margin-top:10px;'>
                    <b>✅ أسباب الفرصة:</b>
                    {"".join([f'<div style="color:#ff9800;">✓ {r}</div>' for r in reasons])}
                </div>
                <div class='success-box' style='margin-top:10px;'>
                    💡 <b>التوقع:</b> {expected}<br>
                    🎯 <b>الاستراتيجية:</b> اختراق R1 مع وقف خسارة أسفلها مباشرة
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            render_stock_card(an)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"📊 تحليل {an['name']} بالتفصيل", key=f"breakout_analyze_{an['name']}"):
                    render_stock_card(an)
            with col2:
                if st.button(f"💾 تسجيل الصفقة", key=f"breakout_rec_{an['name']}"):
                    record_trade(an, "breakout")
                    st.success("تم تسجيل الصفقة!")
    else:
        st.info("""
        🧐 لا توجد فرص انفجار حالياً.
        
        **لماذا؟**
        - قد تكون الأسهم بعيدة عن المقاومة
        - أو السيولة غير كافية للاختراق
        - أو الزخم ضعيف حالياً
        
        **نصيحة:** استمر في متابعة الأسهم القريبة من المقاومات القوية
        """)


# ================== تحليل سهم فردي ==================
elif st.session_state.page == 'analyze':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    st.title("🔍 تحليل سهم")
    sym = st.text_input("رمز السهم").upper().strip()
    if sym:
        data = [r for r in st.session_state.all_results if r and r.get('name') == sym]
        if data:
            render_stock_card(data[0])
        else:
            st.error("❌ السهم غير موجود")
            symbols = [r.get('name') for r in st.session_state.all_results[:20] if r]
            if symbols:
                st.info(f"💡 أمثلة: {', '.join(symbols[:10])}")


# ================== تقييم الأداء ==================
elif st.session_state.page == 'performance':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
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


# ================== دليل الأقسام ==================
elif st.session_state.page == 'guide':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    render_guide()
