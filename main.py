import streamlit as st
import requests

================== CONFIG ==================

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

================== DATA ==================

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

================== INDICATORS ==================

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

def liquidity(vol):
if vol > 2_000_000:
return "سيولة عالية"
elif vol > 500_000:
return "سيولة متوسطة"
else:
return "سيولة ضعيفة"

================== TREND ==================

def trend_filter(p, s1, r1):
if p > r1:
return "صاعد"
elif p < s1:
return "هابط"
return "عرضي"

================== SMART ENTRY ==================

def smart_entry_zone(p, s1, r1):
if abs(p - s1)/s1 < 0.03:
return round(s1+0.05,2), round(s1+0.20,2)
elif p > r1:
return round(r1,2), round(r1+0.25,2)
else:
mid = (s1+r1)/2
return round(mid-0.15,2), round(mid+0.15,2)

================== VOLUME ==================

def volume_spike(vol):
return vol > 1_000_000

================== SCORE ==================

def smart_score(p, s1, r1, rsi, vol):
score = 0

if 30 <= rsi <= 60:  
    score += 25  
elif rsi < 30:  
    score += 15  
elif rsi > 70:  
    score -= 10  

if vol > 2_000_000:  
    score += 25  
elif vol > 500_000:  
    score += 15  

if abs(p - s1)/s1 < 0.05:  
    score += 25  

if p > r1:  
    score += 25  

if volume_spike(vol):  
    score += 10  

return max(score, 0)

================== SIGNALS ==================

def reversal_signal(p, s1, r1, rsi):
if p <= s1 * 1.02 and rsi < 35:
return "🟢 إشارة ارتداد صاعد", "up"
if p >= r1 * 0.98 and rsi > 70:
return "🔴 إشارة ارتداد هابط", "down"
return "لا توجد إشارة ارتداد", None

def confirmation_signal(p, s1, r1, rsi, vol):
if p > r1 and rsi > 55 and volume_spike(vol):
return "🟢 تأكيد قوي (اختراق + فوليوم)", "buy"
if p < s1 and rsi < 45:
return "🔴 تأكيد بيع", "sell"
return "⚪ لا يوجد تأكيد", None

================== AI ==================

def ai_score_comment(p, s1, s2, r1, r2, rsi):
trader_score = 50
if rsi < 35: trader_score += 20
if abs(p - s1)/s1 < 0.02: trader_score += 20
if p > r1: trader_score += 10
if rsi > 70: trader_score -= 20

trader_score = max(min(trader_score,100),0)  
trader_comment = f"⚡ مناسب لمضاربة قرب الدعم {s1:.2f}"  

swing_score = 60 + (50 - abs(50 - rsi))  
swing_score = max(min(swing_score,100),0)  
swing_comment = "🔁 حركة تصحيح داخل اتجاه عام"  

invest_score = 80 if p > (r1+r2)/2 else 55  
invest_comment = "🏦 الاتجاه طويل الأجل إيجابي"  

trader_entry, trader_sl = round(s1+0.1,2), round(s1-0.15,2)  
swing_entry, swing_sl = round((s1+r1)/2,2), round((s1+r1)/2-0.25,2)  
invest_entry, invest_sl = round((s1+s2)/2,2), round(s2-0.25,2)  

return {  
    "trader": {"score": trader_score, "comment": trader_comment, "entry": trader_entry, "sl": trader_sl},  
    "swing": {"score": swing_score, "comment": swing_comment, "entry": swing_entry, "sl": swing_sl},  
    "invest": {"score": invest_score, "comment": invest_comment, "entry": invest_entry, "sl": invest_sl}  
}

================== REPORT ==================

def show_report(code, p, h, l, v):
s1, s2, r1, r2 = pivots(p, h, l)
rsi = rsi_pro(p, h, l)
liq = liquidity(v)

rev_txt, _ = reversal_signal(p, s1, r1, rsi)  
conf_txt, conf_type = confirmation_signal(p, s1, r1, rsi, v)  

rec = "انتظار"  
if conf_type == "buy":  
    rec = "شراء"  
elif conf_type == "sell":  
    rec = "بيع"  

ai = ai_score_comment(p, s1, s2, r1, r2, rsi)  
zone_low, zone_high = smart_entry_zone(p, s1, r1)  

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
🎯 <b>المضارب:</b> {ai['trader']['score']}/100<br>  
{ai['trader']['comment']} | دخول: {ai['trader']['entry']}, وقف خسارة: {ai['trader']['sl']}<br>  
🎯 منطقة الدخول الذكية: {zone_low} - {zone_high}<br>  
🔁 <b>السوينج:</b> {ai['swing']['score']}/100<br>  
{ai['swing']['comment']} | دخول: {ai['swing']['entry']}, وقف خسارة: {ai['swing']['sl']}<br>  
🏦 <b>المستثمر:</b> {ai['invest']['score']}/100<br>  
{ai['invest']['comment']} | دخول: {ai['invest']['entry']}, وقف خسارة: {ai['invest']['sl']}<br>  
<hr>  
📌 التوصية: <b>{rec}</b><br>  
📝 <b>ملحوظة للمحبوس:</b> أقرب دعم {s1:.2f}, دعم أقوى {s2:.2f}. متابعة الأسعار أمر مهم.  
</div>  
""", unsafe_allow_html=True)

================== SCANNER ==================

def scanner():
results = []

for s in WATCHLIST:  
    p,h,l,v = get_data(s)  
    if not p:  
        continue  

    s1, s2, r1, r2 = pivots(p,h,l)  
    rsi = rsi_pro(p,h,l)  

    score = smart_score(p, s1, r1, rsi, v)  
    if score < 50:  
        continue  

    zone_low, zone_high = smart_entry_zone(p, s1, r1)  

    results.append((score, f"{s} | السعر {p:.2f} | RSI {rsi:.1f} | Score {score} | 🎯 Zone {zone_low}-{zone_high}"))  

results.sort(reverse=True, key=lambda x: x[0])  
return [r[1] for r in results]

================== UI ==================

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
st.subheader("🚨 إشارات الأسهم (Filtered)")
res = scanner()
if res:
for r in res:
st.info(r)
else:
st.success("لا توجد فرص حالياً")
