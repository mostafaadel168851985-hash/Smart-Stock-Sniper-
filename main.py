import streamlit as st
import streamlit.components.v1 as components
import requests
from datetime import datetime
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
                return data if isinstance(data, list) else []
        except:
            return []
    return []

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
        "trade_type": trade_type,
        "date_recorded": today,
        "status": "pending"
    })
    save_trades(trades)

def save_trades(trades):
    try:
        with open(TRADES_FILE, 'w', encoding='utf-8') as f:
            json.dump(trades, f, ensure_ascii=False, indent=2)
    except:
        pass


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


# ================== 🎯 قرار القناص (6 مؤشرات) ==================
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
    
    # 3. RSI
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
        advice, emoji = "فرصة ذهبية - دخول الآن", "🔥"
    elif percent >= 65:
        advice, emoji = "فرصة جيدة - شراء حذر", "✅"
    elif percent >= 40:
        advice, emoji = "مراقبة - انتظار", "🟡"
    else:
        advice, emoji = "تجنب السهم حالياً", "❌"
    
    return {'score': percent, 'advice': advice, 'emoji': emoji}


# ================== 🚀 صائد الانفجارات (نسخة خفيفة) ==================
def is_breakout_candidate(an):
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
    
    # 1. قرب من المقاومة
    if r1 and r1 > p:
        dist = (r1 - p) / p * 100
        if dist < 0.5:
            score += 3
            reasons.append(f"📍 عند المقاومة ({dist:.1f}%)")
        elif dist < 1.0:
            score += 2
            reasons.append(f"📍 قريب جداً ({dist:.1f}%)")
        elif dist < 1.5:
            score += 1
            reasons.append(f"📍 قريب ({dist:.1f}%)")
        else:
            return False, [], 0
    else:
        return False, [], 0
    
    # 2. RSI
    if 55 <= rsi <= 75:
        score += 2
        reasons.append(f"📈 RSI قوي ({rsi:.0f})")
    elif 45 <= rsi < 55:
        score += 1
        reasons.append(f"📊 RSI متوسط ({rsi:.0f})")
    
    # 3. سيولة
    if ratio > 2.5:
        score += 2
        reasons.append(f"💧 سيولة استثنائية ({ratio:.1f}x)")
    elif ratio > 1.8:
        score += 1.5
        reasons.append(f"💧 سيولة عالية ({ratio:.1f}x)")
    elif ratio > 1.2:
        score += 1
        reasons.append(f"💧 سيولة جيدة ({ratio:.1f}x)")
    
    # 4. الاتجاه
    if t_short == "صاعد" and t_med == "صاعد":
        score += 1.5
        reasons.append(f"📊 اتجاه صاعد")
    
    # 5. السعر فوق EMA20
    if p > sma20:
        score += 0.5
        reasons.append(f"📈 فوق EMA20")
    
    # 6. تغير إيجابي
    if change > 0.5:
        score += 0.5
        reasons.append(f"🟢 تغير قوي ({change:+.1f}%)")
    elif change > 0:
        score += 0.25
    
    strength = int((score / max_score) * 100)
    
    if strength >= 80:
        expected = "🔥 8-10% خلال 2-3 جلسات"
    elif strength >= 60:
        expected = "🚀 5-7% خلال 3-5 جلسات"
    elif strength >= 40:
        expected = "📈 3-5% خلال أسبوع"
    else:
        expected = "⚠️ حركة محدودة"
    
    return score >= 5, reasons, strength, expected


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
            "s1": s1, "s2": s2, "r1": r1, "r2": r2, "pp": pp,
            "sma20": sma20, "sma50": sma50, "sma200": sma200,
            "entry_range": f"{entry_min:.2f} - {entry_max:.2f}",
            "entry_price": entry_price,
            "stop_loss": stop_loss, "target": target, "rr": rr,
            "risk_pct": (loss_ps/entry_price)*100,
            "target_pct": (profit_ps/entry_price)*100,
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
    with st.spinner("🔄 جاري التحميل..."):
        raw = get_all_data()
        if raw:
            st.session_state.all_results = preprocess(raw)
            return True
    return False


# ================== 🎨 STYLES ==================
st.set_page_config(page_title="🎯 قناص EGX", layout="wide", page_icon="🎯")
st.markdown("""
<style>
.stButton>button { width: 100%; border-radius: 10px; height: 45px; font-weight: bold; }
.stock-header { font-size: 22px; font-weight: bold; color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 8px; }
.score-tag { float: right; background: #238636; color: white; padding: 2px 12px; border-radius: 15px; font-size: 14px; }
.info-box { background: rgba(88,166,255,0.15); border-right: 4px solid #58a6ff; padding: 10px; border-radius: 8px; margin: 10px 0; }
.success-box { background: rgba(63,185,80,0.15); border-right: 4px solid #3fb950; padding: 10px; border-radius: 8px; margin: 10px 0; }
.entry-card { background: #0d1117; border: 1px solid #3fb950; border-radius: 10px; padding: 12px; margin: 10px 0; }
.breakout-card { background: linear-gradient(135deg, #0d1117, #1a1a2e); border: 2px solid #ff6f00; border-radius: 12px; padding: 15px; margin: 15px 0; }
.good { color: #3fb950; }
.bad { color: #f85149; }
.warning { color: #d29922; }
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
    with st.expander("⚙️ الإعدادات", expanded=False):
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
        sectors = ["🌍 الكل", "🏦 البنوك", "🏗️ العقارات", "🍔 الأغذية", "📡 الاتصالات", "📌 أخرى"]
        selected = st.selectbox("اختر قطاعاً", sectors, index=0)
        if selected != st.session_state.sector_filter:
            st.session_state.sector_filter = selected
            st.rerun()


# ================== شرح القرارات ==================
def render_decision_explanation(res, confidence):
    """شرح أسباب القرار بشكل واضح"""
    
    st.markdown("### 📋 أسباب قرار القناص")
    
    # تحليل كل عامل
    factors = []
    
    p = res.get('p', 0)
    sma200 = res.get('sma200', p)
    t_long = res.get('t_long', 'هابط')
    if t_long == "صاعد" or (sma200 and p > sma200):
        factors.append("✅ الاتجاه العام: **صاعد** (فوق EMA200)")
    else:
        factors.append("❌ الاتجاه العام: **هابط** (تحت EMA200)")
    
    t_short = res.get('t_short', 'هابط')
    t_med = res.get('t_med', 'هابط')
    if t_med == "صاعد" and t_short == "صاعد":
        factors.append("✅ الزخم: **إيجابي** (EMA20 و EMA50 صاعدين)")
    else:
        factors.append("❌ الزخم: **ضعيف** (الاتجاهات غير متوافقة)")
    
    rsi = res.get('rsi', 50)
    if 45 < rsi < 65:
        factors.append(f"✅ RSI: **{rsi:.0f}** (منطقة انطلاق صحية)")
    elif rsi <= 45:
        factors.append(f"⚠️ RSI: **{rsi:.0f}** (منخفض - قد يكون ضعيف)")
    else:
        factors.append(f"⚠️ RSI: **{rsi:.0f}** (مرتفع - قرب من التشبع)")
    
    ratio = res.get('ratio', 0)
    if ratio > 1.5:
        factors.append(f"✅ السيولة: **{ratio:.1f}x** (عالية - اهتمام قوي)")
    elif ratio > 1:
        factors.append(f"⚠️ السيولة: **{ratio:.1f}x** (مقبولة)")
    else:
        factors.append(f"❌ السيولة: **{ratio:.1f}x** (ضعيفة)")
    
    r1 = res.get('r1', p * 1.05)
    if r1 and r1 > p:
        dist = (r1 - p) / p * 100
        if dist < 2:
            factors.append(f"✅ الاختراق: **قرب من المقاومة** ({dist:.1f}% متبقي)")
        else:
            factors.append(f"⚠️ الاختراق: **بعيد عن المقاومة** ({dist:.1f}%)")
    
    chg = res.get('chg', 0)
    if chg > 0.2:
        factors.append(f"✅ الشمعة: **صاعدة قوية** ({chg:+.2f}%)")
    elif chg > 0:
        factors.append(f"✅ الشمعة: **صاعدة** ({chg:+.2f}%)")
    else:
        factors.append(f"❌ الشمعة: **هابطة** ({chg:+.2f}%)")
    
    for f in factors:
        st.markdown(f)
    
    st.markdown("---")
    st.markdown(f"**🎯 خلاصة القناص:** {confidence['emoji']} {confidence['advice']} (ثقة {confidence['score']}%)")


# ================== UI RENDERER ==================
def render_stock_card(res, is_top10=False):
    if res is None:
        return
    
    # العنوان
    st.markdown(f"<div class='stock-header'>{res['name']} - {res['desc']}<span class='score-tag'>Smart: {res.get('smart_score', 0)}</span></div>", unsafe_allow_html=True)
    
    # كارت القناص
    confidence = get_confidence(res)
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, #1a1a2e, #16213e); border-radius: 12px; padding: 12px; margin: 10px 0;'>
        <div style='display: flex; justify-content: space-between; align-items: center;'>
            <span style='font-size: 18px; font-weight: bold;'>{confidence['emoji']} قرار القناص</span>
            <span style='font-size: 28px; font-weight: bold;'>{confidence['score']}%</span>
        </div>
        <div style='margin-top: 5px;'>{confidence['advice']}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # شرح القرار
    with st.expander("📋 شرح أسباب القرار", expanded=True):
        render_decision_explanation(res, confidence)
    
    # المؤشرات السريعة
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: st.metric("السعر", f"{res['p']:.2f}", f"{res['chg']:+.2f}%")
    with col2: st.metric("Smart", f"{res['smart_score']}/100")
    with col3: st.metric("RR", f"{res['rr']}")
    with col4: st.metric("RSI", f"{res['rsi']:.0f}")
    with col5: st.metric("السيولة", f"{res['ratio']:.1f}x")
    
    # التحليل الفني السريع
    with st.expander("📊 نطاق الدخول والخروج", expanded=True):
        st.markdown(f"""
        <div class='entry-card'>
            🎯 <b>نطاق الدخول:</b> {res['entry_range']}<br>
            🛑 <b>وقف الخسارة:</b> {res['stop_loss']:.2f} <span class='bad'>(-{res['risk_pct']:.1f}%)</span><br>
            🏁 <b>المستهدف:</b> {res['target']:.2f} <span class='good'>(+{res['target_pct']:.1f}%)</span><br>
            ⚖️ <b>RR Ratio:</b> 1:{res['rr']}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("**📌 الاتجاهات:**")
        col1, col2, col3 = st.columns(3)
        with col1: st.markdown(f"قصير: {'🟢 صاعد' if res['t_short'] == 'صاعد' else '🔴 هابط'}")
        with col2: st.markdown(f"متوسط: {'🟢 صاعد' if res['t_med'] == 'صاعد' else '🔴 هابط'}")
        with col3: st.markdown(f"طويل: {'🟢 صاعد' if res['t_long'] == 'صاعد' else '🔴 هابط'}")
    
    # خطة الدخول السريعة
    with st.expander("💰 خطة الدخول المقترحة", expanded=False):
        deal_size = st.number_input("💰 الميزانية (ج)", value=10000, step=1000, key=f"deal_{res['name']}")
        if deal_size > 0:
            shares = int(deal_size / res['entry_price'])
            st.info(f"""
            📦 عدد الأسهم: **{shares:,}** سهم
            💰 قيمة الصفقة: **{shares * res['entry_price']:,.0f}** ج
            🟢 الربح المتوقع: **{(res['target'] - res['entry_price']) * shares:,.0f}** ج
            🔴 الخسارة المحتملة: **{(res['entry_price'] - res['stop_loss']) * shares:,.0f}** ج
            """)
    
    # مشاركة
    msg = f"📊 {res['name']}\n💰 {res['p']:.2f} ج | 🎯 ثقة: {confidence['score']}%\n🎯 {confidence['advice']}\n📈 الدخول: {res['entry_range']}\n🛑 الوقف: {res['stop_loss']:.2f}\n🏁 الهدف: {res['target']:.2f}"
    encoded = urllib.parse.quote(msg)
    st.markdown(f"[📱 مشاركة عبر واتساب](https://wa.me/?text={encoded})")


# ================== PAGES ==================
if st.session_state.all_results is None:
    get_fresh_data()

if st.session_state.page == 'home':
    st.title("🎯 قناص EGX - النسخة السريعة")
    render_mode_and_sector()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏆 أفضل 10 فرص", use_container_width=True):
            st.session_state.page = 'top10'
            st.rerun()
    with col2:
        if st.button("🚀 صائد الانفجارات", use_container_width=True):
            st.session_state.page = 'breakout'
            st.rerun()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔍 تحليل سهم", use_container_width=True):
            st.session_state.page = 'analyze'
            st.rerun()
    with col2:
        if st.button("📖 دليل الأقسام", use_container_width=True):
            st.session_state.page = 'guide'
            st.rerun()
    
    if st.button("🔄 تحديث البيانات", use_container_width=True):
        get_fresh_data()
        st.rerun()
    
    sector_filter = st.session_state.sector_filter
    filtered = filter_by_sector(st.session_state.all_results, sector_filter)
    if filtered:
        gold_count = len([r for r in filtered if r.get('smart_score', 0) >= 70])
        st.markdown(f"""
        <div style='background:#0d1117;border-radius:10px;padding:15px;margin-top:20px;'>
            <b>📊 إحصائية سريعة</b><br>
            • القطاع: {sector_filter}<br>
            • إجمالي الأسهم: {len(filtered)}<br>
            • 🔥 فرص قوية: {gold_count}
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


# ================== صائد الانفجارات ==================
elif st.session_state.page == 'breakout':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    
    st.title("🚀 صائد الانفجارات")
    st.markdown("""
    <div class='info-box'>
    🚀 <b>شروط الاختيار:</b><br>
    • قرب من المقاومة R1 | • RSI 55-75 | • سيولة عالية | • اتجاه صاعد
    </div>
    """, unsafe_allow_html=True)
    
    sector_filter = st.session_state.sector_filter
    filtered = filter_by_sector(st.session_state.all_results, sector_filter)
    
    breakout_stocks = []
    for an in filtered:
        if an:
            is_breakout, reasons, strength, expected = is_breakout_candidate(an)
            if is_breakout:
                breakout_stocks.append({'stock': an, 'reasons': reasons, 'strength': strength, 'expected': expected})
    
    if breakout_stocks:
        breakout_stocks.sort(key=lambda x: x['strength'], reverse=True)
        st.markdown(f"**🚀 عدد الفرص: {len(breakout_stocks)}**")
        
        for item in breakout_stocks:
            an = item['stock']
            reasons = item['reasons']
            strength = item['strength']
            expected = item['expected']
            
            if strength >= 80:
                color = "#ff6f00"
            elif strength >= 60:
                color = "#ff9800"
            else:
                color = "#ffc107"
            
            st.markdown(f"""
            <div class='breakout-card'>
                <div style='display:flex;justify-content:space-between;align-items:center;'>
                    <h2 style='color:#ff6f00;margin:0'>🚀 {an['name']} - {an['desc']}</h2>
                    <span style='background:{color}; padding:8px 16px; border-radius:25px; color:white;'>{strength}%</span>
                </div>
                <div style='height:6px; background:#333; margin:10px 0; border-radius:3px;'>
                    <div style='width:{strength}%; background:{color}; height:6px; border-radius:3px;'></div>
                </div>
                <div>💰 {an['p']:.2f} ج | R1: {an['r1']:.2f} ج | RSI: {an['rsi']:.0f} | سيولة: {an['ratio']:.1f}x</div>
                <div>✅ {', '.join(reasons[:4])}</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f'<div class="success-box">💡 {expected}</div>', unsafe_allow_html=True)
            render_stock_card(an)
    else:
        st.info("لا توجد فرص انفجار حالياً")


# ================== تحليل سهم ==================
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


# ================== دليل الأقسام ==================
elif st.session_state.page == 'guide':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    st.title("📖 دليل الأقسام")
    
    st.markdown("""
    <div class='info-box'>
    📚 <b>كيف يعمل التطبيق؟</b>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("🎯 قرار القناص - تقييم الفرصة", expanded=True):
        st.markdown("""
        **6 مؤشرات للتقييم:**
        
        | المؤشر | الشرط | الوزن |
        |--------|-------|-------|
        | الاتجاه العام | فوق EMA200 | 1/6 |
        | الزخم | EMA20 و EMA50 صاعدين | 1/6 |
        | RSI | 45-65 (منطقة انطلاق) | 1/6 |
        | السيولة | حجم > 1.5x المتوسط | 1/6 |
        | الاختراق | قرب من R1 (أقل من 2%) | 1/6 |
        | الشمعة | صاعدة (+0.2%) | 1/6 |
        
        **النتائج:**
        - 🔥 85-100%: فرصة ذهبية
        - ✅ 65-84%: فرصة جيدة
        - 🟡 40-64%: مراقبة
        - ❌ 0-39%: تجنب
        """)
    
    with st.expander("🚀 صائد الانفجارات", expanded=True):
        st.markdown("""
        **شروط الاختيار:**
        - قرب من المقاومة R1 (أقل من 1.5%)
        - RSI 55-75 (زخم قوي غير مشبع)
        - سيولة عالية (> 1.8x المتوسط)
        - اتجاه صاعد (EMA20 و EMA50)
        
        **التوقع:**
        - 🔥 80%+: 8-10% خلال 2-3 جلسات
        - 🚀 60%+: 5-7% خلال 3-5 جلسات
        - 📈 40%+: 3-5% خلال أسبوع
        """)
    
    with st.expander("🏆 أفضل 10 فرص", expanded=True):
        st.markdown("""
        يتم ترتيب جميع الأسهم تنازلياً حسب **Smart Score**:
        
        **Smart Score** = درجة مركبة من 8 عوامل:
        - EMA20 (15) + EMA50 (15) + EMA200 (5)
        - السيولة (20/10)
        - RSI (20/10/5)
        - RR (20/10)
        """)
    
    st.info("💡 كل قسم يعرض شرحاً مفصلاً لأسباب القرار")
