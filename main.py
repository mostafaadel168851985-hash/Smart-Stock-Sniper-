import streamlit as st
import requests

# ================== CONFIG ==================
st.set_page_config(page_title="🤖 Sniper AI v21 Smart", layout="wide")

if 'page' not in st.session_state:
    st.session_state.page = 'home'

def go_to(p):
    st.session_state.page = p
    st.rerun()

# ================== DATA ==================
@st.cache_data(ttl=300)
def fetch_egx_data(query_val=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"

    cols = ["name","close","RSI","volume","average_volume_10d_calc",
            "high","low","change","description","SMA50"]

    payload = {
        "filter":[{"left":"volume","operation":"greater","right":10000}],
        "columns":cols,
        "range":[0,150]
    }

    if not scan_all and query_val:
        payload["filter"].append({
            "left":"name",
            "operation":"match",
            "right":query_val.upper()
        })

    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r.get("data", [])
    except:
        return []

# ================== ANALYSIS ==================
def analyze_stock(d_row):
    try:
        d = d_row['d']
        name,p,rsi,v,avg_v,h,l,chg,desc,sma50 = d

        # Pivot
        pp = (h + l + p) / 3
        r1, s1 = (2 * pp) - l, (2 * pp) - h
        r2, s2 = pp + (h - l), pp - (h - l)

        ratio = v / (avg_v or 1)

        # Chase
        is_chase = (p > r1 * 1.02) or (chg > 6 and rsi > 70)

        # ===== SCORE =====
        score = 0

        if p > sma50:
            score += 20

        if ratio > 1.5:
            score += 25
        elif ratio > 1:
            score += 15

        if 45 < rsi < 60:
            score += 20

        if p > r1:
            score += 15

        if is_chase:
            score -= 40

        score = max(min(score, 100), 0)

        # ===== SIGNAL =====
        if is_chase:
            signal = "🚨 مطاردة"
        elif p <= s1 and score >= 60:
            signal = "💎 دعم قوي"
        elif p > r1:
            signal = "🚀 اختراق"
        elif score >= 50:
            signal = "🟡 فرصة"
        else:
            signal = "⚪ ضعيف"

        return {
            "name":name,"desc":desc,"p":p,"rsi":rsi,"chg":chg,
            "ratio":ratio,
            "r1":r1,"r2":r2,"s1":s1,"s2":s2,
            "score":score,
            "signal":signal,
            "is_chase":is_chase
        }

    except:
        return None

# ================== UI ==================
def render(an):

    if an['is_chase']:
        st.error("🚨 تحذير مطاردة")

    # Entry
    c1, c2, c3 = st.columns(3)
    c1.metric("🎯 دخول دعم", f"{an['s1']:.2f}")
    c2.metric("🚀 دخول اختراق", f"{an['r1']:.2f}")
    c3.metric("📊 السعر", f"{an['p']:.2f}")

    st.divider()

    # Targets
    st.success(f"🎯 هدف: {an['r1']:.2f} → {an['r2']:.2f}")
    st.error(f"🛑 وقف مضارب: {an['s1']:.2f} | وقف سوينج: {an['s2']:.2f}")

# ================== MAIN ==================
if st.session_state.page == 'home':
    st.title("🏹 Sniper AI Smart Scanner")

    c1, c2 = st.columns(2)
    if c1.button("🔍 تحليل سهم"):
        go_to('analyze')
    if c2.button("🔭 كشاف السوق"):
        go_to('scanner')

# ========= ANALYZE =========
elif st.session_state.page == 'analyze':
    if st.button("🏠"):
        go_to('home')

    q = st.text_input("ادخل الرمز").upper()

    if q:
        data = fetch_egx_data(query_val=q)
        if data:
            render(analyze_stock(data[0]))
        else:
            st.error("السهم غير موجود")

# ========= SCANNER =========
elif st.session_state.page == 'scanner':
    if st.button("🏠"):
        go_to('home')

    data = fetch_egx_data(scan_all=True)

    stocks = []
    for r in data:
        an = analyze_stock(r)
        if an:
            stocks.append(an)

    # 🔥 ترتيب حسب السكور
    stocks = sorted(stocks, key=lambda x: x['score'], reverse=True)

    # 🔝 TOP 10
    st.subheader("🔥 Top Opportunities")

    for an in stocks[:10]:
        with st.expander(f"{an['name']} | {an['signal']} | Score: {an['score']}"):
            render(an)

    # باقي السوق
    st.subheader("📊 باقي السوق")

    for an in stocks[10:]:
        with st.expander(f"{an['name']} | {an['signal']} | Score: {an['score']}"):
            render(an)
