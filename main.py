import streamlit as st
import requests

# ================== CONFIG & MODERN STYLE ==================
st.set_page_config(page_title="🤖 Sniper AI v20.2", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 15px; height: 3.8em; font-weight: bold; border: 1px solid #30363d; }
    .entry-card { padding: 15px; border-radius: 12px; margin-bottom: 10px; border: 1px solid #30363d; text-align: center; }
    .support-entry { background: rgba(35, 134, 54, 0.1); border-left: 5px solid #3fb950; }
    .break-entry { background: rgba(31, 111, 235, 0.1); border-left: 5px solid #58a6ff; }
    .current-p { background: rgba(173, 186, 199, 0.1); border-left: 5px solid #adbac7; }
    .chase-alert { background: rgba(248, 81, 73, 0.15); border: 2px solid #f85149; padding: 15px; border-radius: 12px; text-align: center; color: #f85149; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'home'
def go_to(p): st.session_state.page = p; st.rerun()

# ================== DATA ENGINE ==================
@st.cache_data(ttl=300)
def fetch_egx_data(query_val=None, scan_all=False):
    url = "https://scanner.tradingview.com/egypt/scan"
    cols = ["name","close","RSI","volume","average_volume_10d_calc","high","low","change","description","SMA50","SMA200"]
    payload = {"filter":[{"left":"volume","operation":"greater","right":30000}],"columns":cols,"range":[0,100]}
    if not scan_all and query_val:
        payload["filter"].append({"left":"name","operation":"match","right":query_val.upper()})
    try:
        r = requests.post(url,json=payload,timeout=10).json()
        return r.get("data", [])
    except: return []

# ================== AI CORE LOGIC ==================
def analyze_stock(d_row):
    try:
        d = d_row['d']
        name,p,rsi,v,avg_v,h,l,chg,desc,sma50,sma200 = d
        pp = (h+l+p)/3
        r1,s1,r2,s2 = (2*pp)-l,(2*pp)-h, pp+(h-l),pp-(h-l)
        ratio, rsi_val = v/(avg_v or 1), rsi or 0
        
        is_chase = (p > r1 * 1.02) or (chg > 6 and rsi_val > 70)
        score = 0
        if not is_chase:
            if p > sma50: score += 30
            if ratio > 1.2: score += 20
            if 40 < rsi_val < 62: score += 20
        
        return {
            "name":name,"desc":desc,"p":p,"rsi":rsi_val,"chg":chg,"ratio":ratio,
            "t_score":max(min(score, 100), 0),"r1":r1,"r2":r2,"s1":s1,"s2":s2,"pp":pp,
            "is_chase": is_chase
        }
    except: return None

# ================== UI RENDERER ==================
def render(an):
    # 1. تنبيه المطاردة (بشكل مودرن)
    if an['is_chase']:
        st.markdown(f"<div class='chase-alert'>🚨 تنبيه مطاردة خطرة: السعر ابتعد عن مناطق الأمان</div>", unsafe_allow_html=True)
    
    st.write("")
    
    # 2. خطة الدخول المقترحة (التعديل الجديد)
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='entry-card support-entry'>🎯 دخول آمن (دعم)<br><b style='font-size:20px;'>{an['s1']:.2f}</b></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='entry-card break-entry'>🚀 دخول اختراق<br><b style='font-size:20px;'>{an['r1']:.2f}</b></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='entry-card current-p'>📊 السعر الحالي<br><b style='font-size:20px;'>{an['p']:.2f}</b></div>", unsafe_allow_html=True)

    # 3. الهيدر والـ Score
    st.markdown("---")
    ch1, ch2 = st.columns([3, 1])
    ch1.title(f"{an['name']} | <small>{an['desc']}</small>")
    color = "#3fb950" if an['t_score'] > 60 else "#d29922" if an['t_score'] > 40 else "#f85149"
    ch2.markdown(f"<div style='border:2px solid {color}; border-radius:15px; text-align:center; padding:10px;'>AI Confidence<br><b style='color:{color}; font-size:25px;'>{an['t_score']}%</b></div>", unsafe_allow_html=True)

    # 4. التبويبات
    st.markdown("---")
    t1, t2, t3 = st.tabs(["🎯 الأهداف والوقف", "💰 المحفظة (20k)", "🧮 الحاسبة الذكية v12.7"])
    
    with t1:
        cc1, cc2 = st.columns(2)
        cc1.success(f"**الأهداف:** {an['r1']:.2f} ثم {an['r2']:.2f}")
        cc2.error(f"**وقف الخسارة:** كسر {an['s2']:.2f} بإغلاق")
    
    with t2:
        st.write("تقسيم السيولة لهذا السهم:")
        st.info(f"شراء 35% عند {an['p']:.2f} | تعزيز 35% عند {an['r1']:.2f} | تبريد 30% عند {an['s2']:.2f}")

    with t3:
        st.subheader("🛠️ مساعد التعديل وحساب المتوسط")
        cp1, cp2 = st.columns(2)
        old_p = cp1.number_input("سعرك القديم", value=float(an['p'] + 0.5), key=f"op_{an['name']}")
        old_q = cp2.number_input("كميتك الحالية", value=1000, key=f"oq_{an['name']}")
        
        target_avg = st.number_input("المتوسط المستهدف؟", value=float(an['p'] + 0.2), step=0.01, key=f"tg_{an['name']}")
        
        curr_p = float(an['p'])
        if target_avg > curr_p and target_avg < old_p:
            needed_q = (old_q * (old_p - target_avg)) / (target_avg - curr_p)
            cost = needed_q * curr_p
            st.success(f"للوصول لمتوسط {target_avg:.2f}: اشترِ {int(needed_q):,} سهم بتكلفة {cost:,.0f} ج")
        else:
            st.warning("تأكد أن المتوسط المستهدف بين سعرك القديم وسعر السوق الحالي.")

# ================== PAGES ==================
if st.session_state.page == 'home':
    st.title("🏹 Sniper AI v20.2")
    c1, c2 = st.columns(2)
    if c1.button("🔍 تحليل سهم"): go_to('analyze')
    if c2.button("🔭 كشاف السوق"): go_to('scanner')
    if c1.button("🚀 الاختراقات"): go_to('breakout')
    if c2.button("💎 قنص الذهب"): go_to('gold')

elif st.session_state.page == 'analyze':
    if st.button("🏠 الرئيسية"): go_to('home')
    q = st.text_input("ادخل الرمز").upper()
    if q:
        data = fetch_egx_data(query_val=q)
        if data: render(analyze_stock(data[0]))
