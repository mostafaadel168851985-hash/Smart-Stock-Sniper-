import streamlit as st
import requests
import urllib.parse
import pandas as pd
import numpy as np

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

# ================== STYLE ==================
st.markdown("""
<style>
body, .stApp, .main {background-color: #0d1117; color: #ffffff;}
h1,h2,h3,p,label,span {color: #ffffff;}
.stButton>button {background-color:#25D366;color:white;font-weight:bold;}
.stTabs button {background-color:#161b22;color:white;font-weight:bold;}
.card {background-color:#161b22; padding:20px; border-radius:15px; margin-bottom:20px;}
.whatsapp-btn {
    background: linear-gradient(135deg,#25D366,#128C7E);
    padding:12px;
    border-radius:14px;
    text-align:center;
    color:white !important;
    font-weight:bold;
    text-decoration:none;
    display:block;
    margin-top:12px;
}
hr {border: 1px solid #ffffff; margin:8px 0;}
</style>
""", unsafe_allow_html=True)

# ================== DATA ==================
@st.cache_data(ttl=300)
def get_data(symbol):
    try:
        url = "https://scanner.tradingview.com/egypt/scan"
        payload = {
            "symbols": {"tickers": [f"EGX:{symbol.upper()}"], "query": {"types": []}},
            "columns": ["close", "high", "low", "volume"]
        }
        r = requests.post(url, json=payload, timeout=10).json()
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

def rsi_fake(p, h, l):
    if h == l:
        return 50
    return ((p - l) / (h - l)) * 100

def liquidity(vol):
    if vol > 2_000_000:
        return "سيولة عالية"
    elif vol > 500_000:
        return "سيولة متوسطة"
    else:
        return "سيولة ضعيفة"

# ================== REVERSAL & CONFIRMATION ==================
def reversal_signal(p, s1, r1, rsi):
    if p <= s1 * 1.02 and rsi < 30:
        return "🟢 إشارة ارتداد صاعد", "up"
    if p >= r1 * 0.98 and rsi > 70:
        return "🔴 إشارة ارتداد هابط", "down"
    return "لا توجد إشارة ارتداد", None

def confirmation_signal(p, s1, r1, rsi):
    if p > r1 and rsi > 50:
        return "🟢 تأكيد شراء بعد كسر مقاومة", "buy"
    if p < s1 and rsi < 50:
        return "🔴 تأكيد بيع بعد كسر دعم", "sell"
    return "⚪ لا يوجد تأكيد", None

# ================== AI COMMENTS + SCORES ==================
def ai_score_comment(p, s1, s2, r1, r2, rsi):
    # المضارب
    trader_score = min(100, 50 + (20 if rsi < 30 else 0) + (15 if abs(p - s1)/s1 < 0.02 else 0))
    trader_comment = f"⚡ مناسب لمضاربة سريعة قرب الدعم {s1:.2f} مع الالتزام بوقف الخسارة."

    # سوينج
    swing_score = min(100, 60 + (50 - abs(50 - rsi)))
    swing_comment = "🔁 السهم في حركة تصحيح داخل اتجاه عام، مراقبة الارتداد مطلوبة."

    # مستثمر
    invest_score = 80 if p > (r1+r2)/2 else 55
    invest_comment = "🏦 الاتجاه طويل الأجل إيجابي طالما السعر أعلى المتوسط 50 يوم."

    # دخول و وقف خسارة
    trader_entry, trader_sl = round(s1+0.1,2), round(s1-0.15,2)
    swing_entry, swing_sl = round((s1+r1)/2,2), round((s1+r1)/2-0.25,2)
    invest_entry, invest_sl = round((s1+s2)/2,2), round(s2-0.25,2)

    return {
        "trader": {"score": trader_score, "comment": trader_comment, "entry": trader_entry, "sl": trader_sl},
        "swing": {"score": swing_score, "comment": swing_comment, "entry": swing_entry, "sl": swing_sl},
        "invest": {"score": invest_score, "comment": invest_comment, "entry": invest_entry, "sl": invest_sl}
    }

# ================== REPORT ==================
def show_report(code, p, h, l, v):
    s1, s2, r1, r2 = pivots(p, h, l)
    rsi = rsi_fake(p, h, l)
    liq = liquidity(v)

    rev_txt, rev_type = reversal_signal(p, s1, r1, rsi)
    conf_txt, conf_type = confirmation_signal(p, s1, r1, rsi)

    rec = "انتظار"
    if conf_type == "buy":
        rec = "شراء"
    elif conf_type == "sell":
        rec = "بيع"

    ai = ai_score_comment(p, s1, s2, r1, r2, rsi)

    st.markdown(f"""
    <div class="card">
    <h3>{code} - {COMPANIES.get(code,'')}</h3>
    💰 السعر الحالي: {p:.2f}<br>
    📉 RSI: {rsi:.1f}<br>
    🧱 الدعم: {s1:.2f} / {s2:.2f}<br>
    🚧 المقاومة: {r1:.2f} / {r2:.2f}<br>
    💧 السيولة: {liq}<br>
    <hr>
    🔄 {rev_txt}<br>
    ⚡ {conf_txt}<br>
    <hr>
    🎯 **المضارب:** {ai['trader']['score']}/100<br>
    ⚡ {ai['trader']['comment']} | دخول: {ai['trader']['entry']}, وقف خسارة: {ai['trader']['sl']}<br>
    🔁 **السوينج:** {ai['swing']['score']}/100<br>
    {ai['swing']['comment']} | دخول: {ai['swing']['entry']}, وقف خسارة: {ai['swing']['sl']}<br>
    🏦 **المستثمر:** {ai['invest']['score']}/100<br>
    {ai['invest']['comment']} | دخول: {ai['invest']['entry']}, وقف خسارة: {ai['invest']['sl']}<br>
    <hr>
    📌 التوصية: <b>{rec}</b><br>
    📝 <b>ملحوظة للمحبوس:</b> أقرب دعم {s1:.2f}, دعم أقوى {s2:.2f}. متابعة الأسعار أمر مهم.
    </div>
    """, unsafe_allow_html=True)

    wa_msg = f"""
📊 تحليل سهم {code}
💰 السعر: {p:.2f}
📉 RSI: {rsi:.1f}
🧱 الدعم: {s1:.2f} / {s2:.2f}
🚧 المقاومة: {r1:.2f} / {r2:.2f}
💧 السيولة: {liq}

🔄 {rev_txt}
⚡ {conf_txt}

🎯 المضارب: {ai['trader']['score']}/100 | {ai['trader']['comment']} | دخول: {ai['trader']['entry']}, وقف خسارة: {ai['trader']['sl']}
🔁 السوينج: {ai['swing']['score']}/100 | {ai['swing']['comment']} | دخول: {ai['swing']['entry']}, وقف خسارة: {ai['swing']['sl']}
🏦 المستثمر: {ai['invest']['score']}/100 | {ai['invest']['comment']} | دخول: {ai['invest']['entry']}, وقف خسارة: {ai['invest']['sl']}

📌 التوصية: {rec}
📝 ملحوظة للمحبوس: أقرب دعم {s1:.2f}, دعم أقوى {s2:.2f}. متابعة الأسعار أمر مهم.
"""
    wa_url = "https://wa.me/?text=" + urllib.parse.quote(wa_msg)
    st.markdown(f'<a href="{wa_url}" class="whatsapp-btn">📲 مشاركة التحليل على واتساب</a>', unsafe_allow_html=True)

# ================== SCANNER ==================
def scanner():
    results = []
    for s in WATCHLIST:
        p,h,l,v = get_data(s)
        if not p:
            continue
        s1, s2, r1, r2 = pivots(p,h,l)
        rsi = rsi_fake(p,h,l)
        liq = liquidity(v)

        rev_txt, rev_type = reversal_signal(p, s1, r1, rsi)
        conf_txt, conf_type = confirmation_signal(p, s1, r1, rsi)
        ai = ai_score_comment(p, s1, s2, r1, r2, rsi)

        result = f"{s} | السعر {p:.2f} | دعم {s1:.2f}/{s2:.2f} | مقاومة {r1:.2f}/{r2:.2f} | RSI {rsi:.1f} | سيولة {liq} | {rev_txt} | {conf_txt} | 🎯 المضارب: دخول {ai['trader']['entry']}, وقف خسارة {ai['trader']['sl']} | 🔁 السوينج: دخول {ai['swing']['entry']}, وقف خسارة {ai['swing']['sl']} | 🏦 المستثمر: دخول {ai['invest']['entry']}, وقف خسارة {ai['invest']['sl']}"
        results.append(result)

    return results

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
    st.subheader("🚨 إشارات الأسهم")
    res = scanner()
    if res:
        for r in res:
            st.info(r)
    else:
        st.success("لا توجد إشارات حالياً")
