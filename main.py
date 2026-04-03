import streamlit as st
import requests

# ================== CONFIG ==================
st.set_page_config(page_title="EGX Sniper Elite v9.0", layout="wide")

# ================== STYLE ==================
st.markdown("""
<style>
button[data-baseweb="tab"] { padding:2px !important; font-size:11px !important; }
.stock-header { font-size:18px; font-weight:bold; color:#58a6ff; }
.price-callout { font-size:18px; font-weight:bold; color:#3fb950; }
.stoploss-callout { font-size:16px; font-weight:bold; color:#f85149; }
.warning-box { background:#2e2a0b; border-left:5px solid #ffd700; padding:10px; border-radius:6px; }
.gold { border:2px solid gold; padding:10px; border-radius:10px; margin:10px 0;}
.breakout { border:2px solid #00ffcc; padding:10px; border-radius:10px; margin:10px 0;}
</style>
""", unsafe_allow_html=True)

# ================== DATA ==================
@st.cache_data(ttl=300)
def fetch(symbol=None, scan=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    try:
        if scan:
            payload = {
                "filter":[{"left":"volume","operation":"greater","right":50000}],
                "columns":["name","close","RSI","volume","average_volume_10d_calc","high","low","change","description"],
                "range":[0,60]
            }
        else:
            payload = {
                "symbols":{"tickers":[f"EGX:{symbol}"],"query":{"types":[]}},
                "columns":["close","high","low","volume","RSI","average_volume_10d_calc","change","description"]
            }

        r = requests.post(url,json=payload,timeout=10).json()
        return r.get("data",[])
    except:
        return []

# ================== ANALYSIS ==================
def analyze(row, scan=False):
    try:
        d = row['d']
        if scan:
            name,p,rsi,v,avg,h,l,chg,desc = d
        else:
            p,h,l,v,rsi,avg,chg,desc = d
            name = ""

        if not p: return None

        pp = (p+h+l)/3
        s1 = (2*pp)-h
        r1 = (2*pp)-l
        s2 = pp-(h-l)
        r2 = pp+(h-l)

        ratio = v/(avg or 1)
        rsi = rsi or 0

        # 💎 GOLD
        is_gold = (ratio > 1.6 and 48 < rsi < 66 and chg > 0.5)

        # 🚀 BREAKOUT (نسخة واقعية)
        is_breakout = (
            p > r1 * 0.995 and
            ratio > 1.2 and
            rsi > 50 and
            chg > 0.3
        )

        return {
            "name":name,"desc":desc,"p":p,"rsi":rsi,"ratio":ratio,"chg":chg,
            "s1":s1,"r1":r1,"s2":s2,"r2":r2,
            "gold":is_gold,
            "break":is_breakout
        }
    except:
        return None

# ================== UI ==================
def show(res):
    st.markdown(f"<div class='stock-header'>{res['name']} {res['desc'][:15]}</div>",unsafe_allow_html=True)

    c1,c2,c3 = st.columns(3)
    c1.metric("السعر",f"{res['p']:.2f}",f"{res['chg']:.1f}%")
    c2.metric("RSI",f"{res['rsi']:.1f}")
    c3.metric("الزخم",f"{res['ratio']:.1f}x")

    # ⚠️ تحذير المطاردة
    entry_top = res['s1'] * 1.008
    if res['p'] > entry_top * 1.01:
        st.markdown("<div class='warning-box'>⚠️ السعر بعيد عن نقطة الدخول (خطر)</div>",unsafe_allow_html=True)

    st.divider()

    st.markdown(f"🎯 دخول: <span class='price-callout'>{res['s1']:.2f}</span>",unsafe_allow_html=True)
    st.markdown(f"🎯 هدف: <span class='price-callout'>{res['r1']:.2f}</span>",unsafe_allow_html=True)
    st.markdown(f"🛑 وقف: <span class='stoploss-callout'>{res['s1']*0.98:.2f}</span>",unsafe_allow_html=True)

# ================== APP ==================
st.title("🏹 EGX Sniper Elite v9.0")

tab1,tab2,tab3,tab4,tab5 = st.tabs([
    "📡 تحليل",
    "🔭 مراقبة",
    "🧮 متوسط",
    "💎 ذهب",
    "🚀 اختراق مؤكد"
])

# ================== TAB1 ==================
with tab1:
    sym = st.text_input("كود السهم").upper()
    if sym:
        d = fetch(sym)
        if d:
            r = analyze(d[0])
            if r: show(r)

# ================== TAB2 ==================
with tab2:
    if st.button("فحص السوق"):
        data = fetch(scan=True)
        for row in data:
            r = analyze(row,True)
            if r and (r['rsi']>45 and r['ratio']>1):
                with st.expander(f"{r['name']}"):
                    show(r)

# ================== TAB3 ==================
with tab3:
    old_p = st.number_input("سعرك",0.0)
    old_q = st.number_input("كميتك",0)
    new_p = st.number_input("سعر جديد",0.0)

    if old_p>0 and old_q>0 and new_p>0:
        target = st.number_input("هدف المتوسط",old_p-0.01)
        if new_p < target < old_p:
            need = (old_q*(old_p-target))/(target-new_p)
            st.success(f"اشتري {int(need)} سهم")

# ================== TAB4 ==================
with tab4:
    if st.button("💎 صيد الذهب"):
        data = fetch(scan=True)
        for row in data:
            r = analyze(row,True)
            if r and r['gold']:
                st.markdown("<div class='gold'>💎 فرصة ذهبية</div>",unsafe_allow_html=True)
                show(r)

# ================== TAB5 ==================
with tab5:
    if st.button("🚀 كشف الاختراقات"):
        data = fetch(scan=True)
        found=False
        for row in data:
            r = analyze(row,True)
            if r and r['break']:
                found=True
                st.markdown("<div class='breakout'>🚀 اختراق حقيقي</div>",unsafe_allow_html=True)
                show(r)
        if not found:
            st.warning("لا يوجد اختراقات حالياً")
