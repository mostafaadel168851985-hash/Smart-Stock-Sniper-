import streamlit as st
import requests

# ================== CONFIG ==================
st.set_page_config(page_title="EGX Sniper PRO", layout="wide")

WATCHLIST = ["TMGH", "COMI", "ETEL", "SWDY", "EFID", "ATQA", "ALCN", "RMDA"]

COMPANIES = {
    "TMGH": "طلعت مصطفى",
    "COMI": "البنك التجاري الدولي",
    "ETEL": "المصرية للاتصالات",
    "SWDY": "السويدي إليكتريك",
    "EFID": "إيديتا",
    "ATQA": "عتاقة",
    "ALCN": "ألكون",
    "RMDA": "رمادا"
}

# ================== MODE ==================
mode = st.radio("الوضع", ["⚡ سريع", "🧠 احترافي"])

# ================== DATA ==================
@st.cache_data(ttl=120)
def get_data(symbol):
    try:
        url = "https://scanner.tradingview.com/egypt/scan"
        payload = {
            "symbols": {"tickers": [f"EGX:{symbol.upper()}"], "query": {"types": []}},
            "columns": ["close", "high", "low", "volume"]
        }
        r = requests.post(url, json=payload, timeout=10).json()

        if not r.get("data"):
            return None, None, None, None

        d = r["data"][0]["d"]
        return float(d[0]), float(d[1]), float(d[2]), float(d[3])

    except:
        return None, None, None, None

# ================== INDICATORS ==================
def pivots(p, h, l):
    piv = (p + h + l) / 3
    s1 = (2 * piv) - h
    s2 = piv - (h - l)
    r1 = (2 * piv) - l
    r2 = piv + (h - l)
    return s1, s2, r1, r2

def rsi_pro(p, h, l):
    if h == l:
        return 50
    val = ((p - l) / (h - l)) * 100
    if val < 20: return val + 5
    if val > 80: return val - 5
    return val

# EMA approximation (خفيف)
def ema_fake(p, h, l):
    mid = (h + l) / 2
    ema20 = (p * 0.7) + (mid * 0.3)
    ema50 = (p * 0.4) + (mid * 0.6)
    return round(ema20,2), round(ema50,2)

def liquidity(vol):
    if vol > 2_000_000:
        return "سيولة عالية"
    elif vol > 500_000:
        return "سيولة متوسطة"
    else:
        return "سيولة ضعيفة"

# ================== SMART ENTRY ==================
def smart_entry_zone(p, s1, r1, trend):
    if trend == "صاعد":
        return round(s1+0.05,2), round(s1+0.25,2)
    elif trend == "هابط":
        return round(r1-0.25,2), round(r1-0.05,2)
    else:
        mid = (s1+r1)/2
        return round(mid-0.15,2), round(mid+0.15,2)

# ================== TREND ==================
def trend_filter(p, ema20, ema50):
    if p > ema20 > ema50:
        return "صاعد"
    elif p < ema20 < ema50:
        return "هابط"
    return "عرضي"

# ================== SCORE ==================
def smart_score(p, s1, r1, rsi, vol, trend):
    score = 0

    if 30 <= rsi <= 60:
        score += 25
    elif rsi < 30:
        score += 20

    if vol > 1_000_000:
        score += 20

    if abs(p - s1)/s1 < 0.05:
        score += 25

    if trend == "صاعد":
        score += 20

    return score

# ================== REPORT ==================
def show_report(code, p, h, l, v):
    s1, s2, r1, r2 = pivots(p, h, l)
    rsi = rsi_pro(p, h, l)
    liq = liquidity(v)

    if mode == "🧠 احترافي":
        ema20, ema50 = ema_fake(p, h, l)
        trend = trend_filter(p, ema20, ema50)
    else:
        ema20, ema50 = "-", "-"
        trend = "عرضي"

    zone_low, zone_high = smart_entry_zone(p, s1, r1, trend)

    st.markdown(f"""
    <div class="card">
    <h3>{code} - {COMPANIES.get(code,'')}</h3>
    💰 السعر الحالي: {p:.2f}<br>
    📉 RSI: {rsi:.1f}<br>
    📊 EMA20 / EMA50: {ema20} / {ema50}<br>
    📈 الاتجاه: {trend}<br>
    🧱 الدعم: {s1:.2f} / {s2:.2f}<br>
    🚧 المقاومة: {r1:.2f} / {r2:.2f}<br>
    💧 السيولة: {liq}<br>
    <hr>
    🎯 منطقة الدخول الذكية: {zone_low} - {zone_high}<br>
    </div>
    """, unsafe_allow_html=True)

# ================== SCANNER ==================
def scanner():
    results = []

    for s in WATCHLIST:
        p,h,l,v = get_data(s)
        if not p:
            continue

        s1, s2, r1, r2 = pivots(p,h,l)
        rsi = rsi_pro(p,h,l)

        if mode == "🧠 احترافي":
            ema20, ema50 = ema_fake(p, h, l)
            trend = trend_filter(p, ema20, ema50)
        else:
            trend = "عرضي"

        score = smart_score(p, s1, r1, rsi, v, trend)

        zone_low, zone_high = smart_entry_zone(p, s1, r1, trend)

        results.append((score, f"{s} | السعر {p:.2f} | RSI {rsi:.1f} | Score {score} | 🎯 Zone {zone_low}-{zone_high}"))

    results.sort(reverse=True, key=lambda x: x[0])
    return [r[1] for r in results[:5]]

# ================== UI ==================
st.title("🏹 EGX Sniper PRO")

tab1, tab2, tab3 = st.tabs(["📡 التحليل الآلي", "🛠️ التحليل اليدوي", "🚨 Scanner"])

with tab1:
    code = st.text_input("ادخل كود السهم").upper().strip()
    if code:
        p,h,l,v = get_data(code)
        if p:
            show_report(code,p,h,l,v)
        else:
            st.error("البيانات غير متاحة")

with tab2:
    p = st.number_input("السعر", format="%.2f")
    h = st.number_input("أعلى سعر", format="%.2f")
    l = st.number_input("أقل سعر", format="%.2f")
    v = st.number_input("السيولة")
    if p > 0:
        show_report("MANUAL",p,h,l,v)

with tab3:
    st.subheader("🚨 إشارات الأسهم (Top فرص)")
    res = scanner()
    if res:
        for r in res:
            st.info(r)
    else:
        st.warning("لا توجد بيانات حالياً")
