import streamlit as st
import requests
from datetime import datetime, date
import json
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io

# ================== 📁 PERFORMANCE TRACKING ==================
TRADES_FILE = "trades_data.json"

def load_trades():
    if os.path.exists(TRADES_FILE):
        try:
            with open(TRADES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                return []
        except:
            return []
    return []

def save_trades(trades):
    try:
        with open(TRADES_FILE, 'w', encoding='utf-8') as f:
            json.dump(trades, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving trades: {e}")

def record_trade(res, trade_type):
    trades = load_trades()
    today = datetime.now().strftime("%Y-%m-%d")
    
    for t in trades:
        if t.get('name') == res['name'] and t.get('date_recorded') == today:
            return
    
    trades.append({
        "name": res['name'],
        "desc": res['desc'],
        "entry_price": res['entry_price'],
        "entry_min": res['entry_price'] * 0.98,
        "entry_max": res['entry_price'] * 1.01,
        "target": res['target'],
        "stop_loss": res['stop_loss'],
        "target_pct": res['target_pct'],
        "risk_pct": res['risk_pct'],
        "rr": res['rr'],
        "rsi_at_entry": res['rsi'],
        "smart_score": res['smart_score'],
        "trade_type": trade_type,
        "date_recorded": today,
        "last_price": None,
        "last_update": None,
        "status": "pending",
        "profit_pct": None,
        "entry_hit": False,
        "days_open": None
    })
    save_trades(trades)

def update_all_trades(current_prices):
    trades = load_trades()
    today = date.today()
    updated = False
    
    for trade in trades:
        if trade.get('status') in ['pending', 'still_open']:
            symbol = trade.get('name')
            if symbol in current_prices:
                current_price = current_prices[symbol]
                trade['last_price'] = current_price
                trade['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                if not trade.get('entry_hit', False):
                    entry_min = trade.get('entry_min', 0)
                    entry_max = trade.get('entry_max', 0)
                    if entry_min <= current_price <= entry_max:
                        trade['entry_hit'] = True
                
                recorded_date = datetime.strptime(trade['date_recorded'], "%Y-%m-%d").date()
                trade['days_open'] = (today - recorded_date).days
                
                target = trade.get('target', 0)
                stop_loss = trade.get('stop_loss', 0)
                target_pct = trade.get('target_pct', 0)
                risk_pct = trade.get('risk_pct', 0)
                
                if current_price >= target:
                    trade['status'] = 'hit_target'
                    trade['profit_pct'] = target_pct
                    updated = True
                elif current_price <= stop_loss:
                    trade['status'] = 'stopped_out'
                    trade['profit_pct'] = -risk_pct
                    updated = True
                else:
                    trade['status'] = 'still_open'
    
    if updated:
        save_trades(trades)
    return trades

def get_performance_stats(trades):
    if not trades or not isinstance(trades, list):
        trades = []
    
    total = len(trades)
    if total == 0:
        return {
            'total': 0, 'hit_target': 0, 'stopped_out': 0, 'still_open': 0,
            'success_rate': 0, 'avg_rr': 0, 'total_return': 0, 'avg_return': 0,
            'top10_count': 0, 'gold_count': 0,
            'top10_success': 0, 'gold_success': 0,
            'top10_return': 0, 'gold_return': 0,
            'avg_holding_days': 0, 'entry_accuracy': 0
        }
    
    hit_target = len([t for t in trades if t.get('status') == 'hit_target'])
    stopped_out = len([t for t in trades if t.get('status') == 'stopped_out'])
    still_open = len([t for t in trades if t.get('status') in ['pending', 'still_open']])
    closed = hit_target + stopped_out
    success_rate = (hit_target / closed * 100) if closed > 0 else 0
    
    completed_trades = [t for t in trades if t.get('profit_pct') is not None]
    total_return = sum(t.get('profit_pct', 0) for t in completed_trades)
    avg_return = total_return / len(completed_trades) if completed_trades else 0
    
    avg_rr = sum(t.get('rr', 0) for t in trades) / total if total > 0 else 0
    
    closed_trades = [t for t in trades if t.get('status') in ['hit_target', 'stopped_out'] and t.get('days_open') is not None]
    avg_holding_days = sum(t.get('days_open', 0) for t in closed_trades) / len(closed_trades) if closed_trades else 0
    
    trades_with_entry = [t for t in trades if t.get('entry_hit', False)]
    entry_accuracy = (len(trades_with_entry) / total * 100) if total > 0 else 0
    
    top10_trades = [t for t in trades if t.get('trade_type') == 'top10']
    gold_trades = [t for t in trades if t.get('trade_type') == 'gold']
    
    top10_closed = [t for t in top10_trades if t.get('status') in ['hit_target', 'stopped_out']]
    gold_closed = [t for t in gold_trades if t.get('status') in ['hit_target', 'stopped_out']]
    
    top10_success = (len([t for t in top10_closed if t.get('status') == 'hit_target']) / len(top10_closed) * 100) if top10_closed else 0
    gold_success = (len([t for t in gold_closed if t.get('status') == 'hit_target']) / len(gold_closed) * 100) if gold_closed else 0
    
    top10_return = sum(t.get('profit_pct', 0) for t in top10_trades if t.get('profit_pct') is not None)
    gold_return = sum(t.get('profit_pct', 0) for t in gold_trades if t.get('profit_pct') is not None)
    
    return {
        'total': total, 'hit_target': hit_target, 'stopped_out': stopped_out, 'still_open': still_open,
        'success_rate': round(success_rate, 1), 'avg_rr': round(avg_rr, 2),
        'total_return': round(total_return, 1), 'avg_return': round(avg_return, 1),
        'top10_count': len(top10_trades), 'gold_count': len(gold_trades),
        'top10_success': round(top10_success, 1), 'gold_success': round(gold_success, 1),
        'top10_return': round(top10_return, 1), 'gold_return': round(gold_return, 1),
        'avg_holding_days': round(avg_holding_days, 1), 'entry_accuracy': round(entry_accuracy, 1)
    }


# ================== 📄 PDF GENERATION ==================
def generate_pdf_report(top_results, gold_results, scalp_results):
    """توليد تقرير PDF بالفرص (يدعم العربية)"""
    
    # إنشاء ملف PDF في الذاكرة
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1*cm, leftMargin=1*cm, topMargin=1*cm, bottomMargin=1*cm)
    
    # استخدام خط يدعم العربية (Helvetica كبديل)
    font_name = 'Helvetica'
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ArabicTitle', fontName=font_name, fontSize=18, alignment=1, spaceAfter=20))
    styles.add(ParagraphStyle(name='ArabicHeading', fontName=font_name, fontSize=14, alignment=0, spaceAfter=10, textColor=colors.HexColor('#238636')))
    styles.add(ParagraphStyle(name='ArabicBody', fontName=font_name, fontSize=9, alignment=0))
    styles.add(ParagraphStyle(name='ArabicCell', fontName=font_name, fontSize=8, alignment=1))
    
    elements = []
    
    # عنوان التقرير
    elements.append(Paragraph("EGX Sniper Pro - تقرير الفرص", styles['ArabicTitle']))
    elements.append(Paragraph(f"تاريخ التقرير: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['ArabicBody']))
    elements.append(Spacer(1, 20))
    
    # أفضل 10 فرص
    elements.append(Paragraph("أفضل 10 فرص حسب Smart Score", styles['ArabicHeading']))
    elements.append(Spacer(1, 10))
    
    if top_results:
        top_data = [["#", "السهم", "السعر", "Smart", "RR", "RSI", "الهدف"]]
        for i, an in enumerate(top_results[:10], 1):
            top_data.append([
                str(i), an['name'][:15], f"{an['p']:.2f}", str(an['smart_score']),
                str(an['rr']), f"{an['rsi']:.1f}", f"{an['target']:.2f}"
            ])
        top_table = Table(top_data, colWidths=[0.8*cm, 3.5*cm, 1.5*cm, 1.2*cm, 1*cm, 1.2*cm, 1.8*cm])
        top_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#238636')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(top_table)
    else:
        elements.append(Paragraph("لا توجد بيانات كافية لأفضل 10 فرص", styles['ArabicBody']))
    
    elements.append(Spacer(1, 20))
    
    # الفرص الذهبية
    elements.append(Paragraph("الفرص الذهبية", styles['ArabicHeading']))
    elements.append(Spacer(1, 10))
    
    if gold_results:
        gold_data = [["السهم", "السعر", "RR", "RSI", "الهدف"]]
        for an in gold_results[:10]:
            gold_data.append([an['name'][:15], f"{an['p']:.2f}", str(an['rr']), f"{an['rsi']:.1f}", f"{an['target']:.2f}"])
        gold_table = Table(gold_data, colWidths=[3.5*cm, 1.5*cm, 1*cm, 1.2*cm, 1.8*cm])
        gold_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d29922')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(gold_table)
    else:
        elements.append(Paragraph("لا توجد فرص ذهبية حاليا", styles['ArabicBody']))
    
    elements.append(Spacer(1, 20))
    
    # المضاربات السريعة
    elements.append(Paragraph("مضاربات سريعة", styles['ArabicHeading']))
    elements.append(Spacer(1, 10))
    
    if scalp_results:
        scalp_data = [["السهم", "السعر", "RR", "RSI", "الهدف"]]
        for an in scalp_results[:10]:
            scalp_data.append([an['name'][:15], f"{an['p']:.2f}", str(an['rr']), f"{an['rsi']:.1f}", f"{an['target']:.2f}"])
        scalp_table = Table(scalp_data, colWidths=[3.5*cm, 1.5*cm, 1*cm, 1.2*cm, 1.8*cm])
        scalp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#58a6ff')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(scalp_table)
    else:
        elements.append(Paragraph("لا توجد مضاربات سريعة حاليا", styles['ArabicBody']))
    
    # تذييل
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("تقرير تلقائي من EGX Sniper Pro - هذا التقرير لأغراض تعليمية فقط", styles['ArabicBody']))
    
    # بناء PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


# ================== 🔥 SMART ADDITIONS ==================
def smart_score_pro(res):
    score = 0
    if res.get('t_short') == "صاعد": score += 15
    if res.get('t_med') == "صاعد": score += 15
    if res.get('t_long') == "صاعد": score += 10
    if res.get('ratio', 0) > 2: score += 20
    elif res.get('ratio', 0) > 1.5: score += 10
    if 50 < res.get('rsi', 50) < 65: score += 20
    elif 65 <= res.get('rsi', 50) < 75: score += 10
    elif res.get('rsi', 50) < 40: score += 5
    if res.get('rr', 0) >= 2: score += 20
    elif res.get('rr', 0) >= 1.5: score += 10
    return int(score)

def is_fake_breakout(res):
    if res.get('rsi', 50) > 75 and res.get('rr', 0) < 1.3:
        return True
    if res.get('ratio', 0) < 1.2:
        return True
    return False

def smart_decision(res):
    assert 'smart_score' in res, "smart_score missing from stock data"
    score = res['smart_score']
    fake = is_fake_breakout(res)
    if fake:
        return "❌ فخ سيولة", "danger"
    elif score >= 70:
        return "🔥 فرصة قوية جداً", "strong"
    elif score >= 50:
        return "✅ فرصة جيدة", "good"
    elif score >= 30:
        return "⚠️ تحت المراقبة", "watch"
    else:
        return "❄️ ضعيف", "weak"

def expected_success_rate(res):
    score = 0
    trends = [res.get('t_short', 'هابط'), res.get('t_med', 'هابط'), res.get('t_long', 'هابط')]
    if all(t == "صاعد" for t in trends):
        score += 30
    elif trends.count("صاعد") >= 2:
        score += 20
    elif trends.count("صاعد") == 1:
        score += 10
    
    ratio = res.get('ratio', 0)
    if ratio > 2:
        score += 25
    elif ratio > 1.5:
        score += 15
    elif ratio > 1:
        score += 8
    elif ratio == 0:
        score -= 10
    
    risk_range = res.get('target_pct', 0) - abs(res.get('risk_pct', 0))
    if risk_range > 5:
        score += 15
    elif risk_range > 3:
        score += 10
    elif risk_range > 1:
        score += 5
    
    if res.get('rr', 0) >= 2:
        score += 10
    elif res.get('rr', 0) >= 1.5:
        score += 5
    
    success_rate = min(85, max(0, score))
    if success_rate >= 70: level = "🔥 ممتازة"
    elif success_rate >= 55: level = "✅ جيدة"
    elif success_rate >= 40: level = "⚠️ متوسطة"
    else: level = "❌ ضعيفة"
    return success_rate, level

def calculate_trailing_stop(entry_price, current_price, highest_price, rr):
    if current_price <= entry_price:
        return entry_price * 0.97
    profit_pct = (current_price - entry_price) / entry_price * 100
    if profit_pct >= 5 and rr >= 1.5:
        new_stop = entry_price + (profit_pct / 2) / 100 * entry_price
        return round(min(new_stop, current_price * 0.98), 2)
    elif profit_pct >= 3:
        return round(entry_price, 2)
    else:
        return round(entry_price * 0.97, 2)

def calculate_stochastic_rsi(rsi):
    if rsi <= 20: return {"k": 90, "d": 85, "signal": "🟢 تشبع بيع - فرصة انعكاس (تقديري)"}
    elif rsi <= 35: return {"k": 70, "d": 65, "signal": "🟡 منطقة شراء محتملة (تقديري)"}
    elif rsi <= 65: return {"k": 50, "d": 50, "signal": "⚪ منطقة حيادية"}
    elif rsi <= 80: return {"k": 30, "d": 35, "signal": "🟠 منطقة بيع محتملة (تقديري)"}
    else: return {"k": 10, "d": 15, "signal": "🔴 تشبع شراء - خطر (تقديري)"}


# ================== CONFIG & STYLE ==================
st.set_page_config(page_title="EGX Sniper Pro v15.8", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-size: 18px !important; font-weight: bold !important; margin-bottom: 10px; }
    .stock-header { font-size: 26px !important; font-weight: bold; color: #58a6ff; border-bottom: 2px solid #30363d; padding-bottom: 10px; }
    .score-tag { float: left; background: #238636; color: white; padding: 2px 15px; border-radius: 10px; font-size: 18px; margin-top: 5px; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 10px; padding: 10px !important; }
    .trend-pill { padding: 4px 12px; border-radius: 15px; font-size: 13px; font-weight: bold; margin: 2px; display: inline-block; border: 1px solid #30363d; }
    .trend-up { background-color: rgba(63, 185, 80, 0.15); color: #3fb950; border-color: #3fb950; }
    .trend-down { background-color: rgba(248, 81, 73, 0.15); color: #f85149; border-color: #f85149; }
    .signal-pill { padding: 8px 20px; border-radius: 20px; font-weight: bold; display: inline-block; margin: 10px 0; font-size: 16px; }
    .buy-strong { background: #238636; color: white; }
    .buy-caution { background: rgba(240, 139, 55, 0.2); color: #f08b37; border: 1px solid #f08b37; }
    .wait { background: #161b22; color: #8b949e; border: 1px solid #30363d; }
    .entry-card-new { background-color: #0d1117; border: 1px solid #3fb950; border-radius: 12px; padding: 15px; text-align: center; margin-bottom: 15px; border-top: 4px solid #3fb950; }
    .target-box { border: 2px solid #58a6ff; border-radius: 12px; padding: 15px; text-align: center; background: #0d1117; margin-top: 10px; font-size: 18px; }
    .plan-container { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-top: 15px; border-right: 5px solid #238636; }
    .investor-card { background-color: #161b22; border: 1px solid #d29922; border-radius: 12px; padding: 15px; margin-bottom: 15px; border-top: 4px solid #d29922; }
    .investor-title { color: #d29922; font-weight: bold; font-size: 18px; margin-bottom: 10px; display: block; border-bottom: 1px solid #30363d; padding-bottom: 5px; }
    .level-box { display: flex; justify-content: space-between; padding: 3px 0; border-bottom: 1px solid #21262d; }
    .sup-text { color: #3fb950; font-weight: bold; }
    .res-text { color: #f85149; font-weight: bold; }
    .alert-success { background-color: rgba(63, 185, 80, 0.2); border-right: 4px solid #3fb950; padding: 10px; border-radius: 8px; margin: 10px 0; }
    .alert-danger { background-color: rgba(248, 81, 73, 0.2); border-right: 4px solid #f85149; padding: 10px; border-radius: 8px; margin: 10px 0; }
    </style>
    """, unsafe_allow_html=True)

# ================== HELPERS ==================
def get_rr_rating(rr):
    if rr < 1: return "❌ ضعيف", "RR سيء - مخاطرة أعلى من العائد"
    elif rr < 1.5: return "⚠️ متوسط", "مضاربة سريعة فقط"
    elif rr < 2: return "✅ جيد", "صفقة كويسة"
    else: return "🔥 ممتاز", "فرصة قوية جداً"

def get_volume_rating(ratio):
    if ratio == 0: return "❓ غير معروف", "لا توجد بيانات سيولة كافية"
    elif ratio < 1: return "❄️ ضعيفة", "مفيش سيولة كفاية"
    elif ratio < 1.5: return "🙂 عادية", "سيولة طبيعية"
    elif ratio < 2: return "⚡ نشطة", "في اهتمام بالسهم"
    else: return "🚀 قوية", "سيولة عالية واختراق محتمل"

def get_rsi_signal(rsi):
    if rsi < 30: return "🟢 تشبع بيع (فرصة انعكاس)", "oversold"
    elif rsi < 50: return "🟡 ضعيف", "weak"
    elif rsi < 65: return "🟢 زخم صحي", "good"
    elif rsi < 75: return "⚠️ قرب تشبع شراء", "caution"
    else: return "🔴 تشبع شراء خطر", "overbought"

def classify_stock(res):
    rr = res.get('rr', 0)
    ratio = res.get('ratio', 0)
    t_short = res.get('t_short', 'هابط')
    t_med = res.get('t_med', 'هابط')
    rsi = res.get('rsi', 50)
    mode = st.session_state.mode
    if "محافظ" in mode: rr_min = 1.7
    elif "هجومي" in mode: rr_min = 1.0
    else: rr_min = 1.3
    if ratio == 0: return "weak"
    if rr >= 1.5 and t_short == "صاعد" and 50 < rsi < 70: return "gold"
    elif ratio > 2 and t_short == "صاعد" and rsi < 75: return "breakout"
    elif ratio > 1.5 and rr >= 1.2 and rsi < 80: return "scalp"
    elif rr >= rr_min and ratio > 1.2: return "watchlist"
    else: return "weak"

# ================== SESSION STATE ==================
if "mode" not in st.session_state:
    st.session_state.mode = "⚖️ متوازن"
if 'page' not in st.session_state: 
    st.session_state.page = 'home'

if "market_data" not in st.session_state:
    st.session_state.market_data = None
if "all_results" not in st.session_state:
    st.session_state.all_results = None

def render_mode_selector():
    with st.expander("🧠 اختر نوع التداول", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🛡️ محافظ"): st.session_state.mode = "🛡️ محافظ (محترف)"
        with col2:
            if st.button("⚖️ متوازن"): st.session_state.mode = "⚖️ متوازن"
        with col3:
            if st.button("🚀 هجومي"): st.session_state.mode = "🚀 هجومي"
    mode = st.session_state.mode
    color = "#238636" if "محافظ" in mode else "#f85149" if "هجومي" in mode else "#d29922"
    icon = "🛡️" if "محافظ" in mode else "🚀" if "هجومي" in mode else "⚖️"
    st.markdown(f"""
    <div style="background:{color}; padding:10px; border-radius:10px; text-align:center; font-weight:bold; margin-top:10px; color:white; margin-bottom: 20px;">
        🎯 النمط الحالي: {icon} {mode}
    </div>
    """, unsafe_allow_html=True)

# ================== DATA & ANALYSIS ENGINE ==================
@st.cache_data(ttl=300, show_spinner=False)
def get_all_data():
    url = "https://scanner.tradingview.com/egypt/scan"
    cols = ["name","close","RSI","volume","average_volume_10d_calc","high","low","change","description","SMA20","SMA50","SMA200"]
    payload = {
        "filter": [{"left": "volume", "operation": "greater", "right": 5000}],
        "columns": cols,
        "sort": {"sortBy": "change", "sortOrder": "desc"},
        "range": [0, 300]
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Origin": "https://www.tradingview.com",
        "Referer": "https://www.tradingview.com/"
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if r.status_code != 200:
            st.error(f"⚠️ خطأ في API: Status {r.status_code}")
            return []
        
        data = r.json()
        return data.get("data", [])
    except Exception as e:
        st.error(f"⚠️ فشل الاتصال بـ TradingView: {e}")
        return []

def analyze_stock(d_row):
    try:
        d = d_row.get('d', [])
        
        if len(d) != 12:
            return None
        
        name, p, rsi, v, avg_v, h, l, chg, desc, sma20, sma50, sma200 = d
        if p is None: return None
        
        if not desc or desc == "":
            desc = name
        
        rsi_val = rsi or 0
        
        if avg_v and avg_v > 0:
            ratio = v / avg_v
        else:
            ratio = 0
        
        t_short = "صاعد" if (sma20 and p > sma20) else "هابط"
        t_med = "صاعد" if (sma50 and p > sma50) else "هابط"
        t_long = "صاعد" if (sma200 and p > sma200) else "هابط"
        entry_min = p * 0.98
        entry_max = p * 1.01
        entry_price = (entry_min + entry_max) / 2
        pp = (p + (h or p) + (l or p)) / 3
        s1, r1 = (2 * pp) - (h or p), (2 * pp) - (l or p)
        s2, r2 = pp - ((h or p) - (l or p)), pp + ((h or p) - (l or p))
        stop_loss = min(s2, entry_price * 0.97)
        target = max(r1, entry_price * 1.05)
        profit_ps = target - entry_price
        loss_ps = entry_price - stop_loss
        if loss_ps <= 0: return None
        rr = round(profit_ps / loss_ps, 2)
        
        if rr >= 2 and t_short == "صاعد" and t_med == "صاعد" and rsi_val < 70:
            signal, sig_cls = "شراء قوي 🔥", "buy-strong"
        elif ratio > 2 and t_short == "صاعد" and rsi_val < 75:
            signal, sig_cls = "اختراق قوي 🚀", "buy-strong"
        elif ratio > 1.5 and rr >= 1.2 and rsi_val < 75:
            signal, sig_cls = "فرصة مضاربية ⚡", "buy-caution"
        elif rr >= 1.2 and rsi_val < 70:
            signal, sig_cls = "شراء حذر ⚠️", "buy-caution"
        else:
            signal, sig_cls = "انتظار ⏳", "wait"
        
        temp_res = {
            't_short': t_short, 't_med': t_med, 't_long': t_long,
            'ratio': ratio, 'rsi': rsi_val, 'rr': rr
        }
        smart_score = smart_score_pro(temp_res)
        
        return {
            "name": name, "desc": desc, "p": p, "rsi": rsi_val, "chg": chg, "ratio": ratio,
            "signal": signal, "sig_cls": sig_cls, "t_short": t_short, "t_med": t_med, "t_long": t_long,
            "s1": s1, "s2": s2, "r1": r1, "r2": r2, "pp": pp,
            "entry_range": f"{entry_min:.2f} - {entry_max:.2f}", "entry_price": entry_price,
            "stop_loss": stop_loss, "target": target, "rr": rr, "risk_pct": (loss_ps/entry_price)*100, 
            "target_pct": (profit_ps/entry_price)*100, "score": int((min(ratio, 2) if ratio > 0 else 0) * 20 + (rsi_val / 2 if rsi_val else 25)),
            "smart_score": smart_score
        }
    except Exception as e:
        print(f"Analysis Error: {e}")
        return None

def preprocess_all_data(raw_data):
    results = []
    for r in raw_data:
        an = analyze_stock(r)
        if an:
            results.append(an)
    return results

def get_top_ranked(results, limit=10):
    sorted_results = sorted(results, key=lambda x: (x.get('smart_score', 0), x.get('rr', 0)), reverse=True)
    return sorted_results[:limit]

def get_fresh_data():
    with st.spinner("🔄 جاري تحميل بيانات السوق..."):
        raw_data = get_all_data()
        if raw_data:
            st.session_state.market_data = raw_data
            st.session_state.all_results = preprocess_all_data(raw_data)
            return True
        return False

# ================== UI RENDERER ==================
def render_stock_ui(res, is_top10=False, is_gold=False):
    st.markdown(f"""
    <div class='stock-header'>
        {res['name']} - {res['desc']}
        <span class='score-tag'>Score: {res['score']}</span>
    </div>
    """, unsafe_allow_html=True)
    smart_text, smart_type = smart_decision(res)
    smart_score = res['smart_score']
    st.markdown(f"""
    <div style="background:#161b22;border:1px solid #30363d;padding:12px;border-radius:10px;margin:10px 0;">
        🤖 <b>Smart Score:</b> {smart_score}/100 <br>
        🎯 <b>التقييم الذكي:</b> {smart_text}
    </div>
    """, unsafe_allow_html=True)
    
    tab_analysis, tab_management, tab_scenario, tab_indicators = st.tabs([
        "📊 التحليل الفني", "📉 إدارة المخاطر والسيولة", "🧠 الوضع الحالي", "📈 مؤشرات متقدمة"
    ])

    with tab_analysis:
        t_short_c = "trend-up" if res['t_short'] == "صاعد" else "trend-down"
        t_med_c = "trend-up" if res['t_med'] == "صاعد" else "trend-down"
        t_long_c = "trend-up" if res['t_long'] == "صاعد" else "trend-down"
        st.markdown(f"""
        <div style='margin-bottom: 15px;'>
            <span class='trend-pill {t_short_c}'>قصير: {res['t_short']}</span>
            <span class='trend-pill {t_med_c}'>متوسط: {res['t_med']}</span>
            <span class='trend-pill {t_long_c}'>طويل: {res['t_long']}</span>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"<span class='signal-pill {res['sig_cls']}'>{res['signal']}</span>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4) 
        c1.metric("السعر الحالي", f"{res['p']:.2f}", f"{res['chg']:.1f}%")
        vol_label, vol_desc = get_volume_rating(res['ratio'])
        c2.metric("نشاط السيولة", f"{res['ratio']:.1f}x {vol_label}" if res['ratio'] > 0 else "❓ غير معروف", vol_label)
        rr_label, rr_desc = get_rr_rating(res['rr'])
        c3.metric("R/R Ratio", f"{res['rr']} {rr_label}")
        rsi_label, rsi_type = get_rsi_signal(res['rsi'])
        c4.metric("RSI", f"{res['rsi']:.1f}", rsi_label)
        with c2: st.caption(f"📊 {vol_desc}")
        with c3: st.caption(f"🧠 {rr_desc}")
        with c4: st.caption(f"📈 حالة الزخم: {rsi_label}")
        
        st.markdown("### 📊 مستويات الدعم والمقاومة")
        max_price = max(res['r2'], res['p']) * 1.02
        min_price = min(res['s2'], res['p']) * 0.98
        range_price = max_price - min_price
        chart_width = 40
        current_pos = int(((res['p'] - min_price) / range_price) * chart_width) if range_price > 0 else 20
        r2_pos = int(((res['r2'] - min_price) / range_price) * chart_width) if res['r2'] > min_price and range_price > 0 else 0
        r1_pos = int(((res['r1'] - min_price) / range_price) * chart_width) if res['r1'] > min_price and range_price > 0 else 0
        s1_pos = int(((res['s1'] - min_price) / range_price) * chart_width) if res['s1'] > min_price and range_price > 0 else 0
        s2_pos = int(((res['s2'] - min_price) / range_price) * chart_width) if res['s2'] > min_price and range_price > 0 else 0
        chart_line = ["─"] * chart_width
        if 0 <= current_pos < chart_width: chart_line[current_pos] = "●"
        if 0 <= r2_pos < chart_width: chart_line[r2_pos] = "▲"
        if 0 <= r1_pos < chart_width: chart_line[r1_pos] = "△"
        if 0 <= s1_pos < chart_width: chart_line[s1_pos] = "▼"
        if 0 <= s2_pos < chart_width: chart_line[s2_pos] = "▽"
        st.code("".join(chart_line))
        st.caption(f"R2▲ {res['r2']:.2f} | R1△ {res['r1']:.2f} | السعر● {res['p']:.2f} | S1▼ {res['s1']:.2f} | S2▽ {res['s2']:.2f}")
        st.markdown(f"""
        <div class='investor-card'>
            <span class='investor-title'>🏛️ بيانات استرشادية (للمستثمر طويل الأجل)</span>
            <div class='level-box'><span>المقاومة الثانية (R2):</span><span class='res-text'>{res['r2']:.2f}</span></div>
            <div class='level-box'><span>المقاومة الأولى (R1):</span><span class='res-text'>{res['r1']:.2f}</span></div>
            <div style='text-align:center; color:#8b949e; margin:5px 0;'>--- نقطة الارتكاز: {res['pp']:.2f} ---</div>
            <div class='level-box'><span>الدعم الأول (S1):</span><span class='sup-text'>{res['s1']:.2f}</span></div>
            <div class='level-box'><span>الدعم الثاني (S2):</span><span class='sup-text'>{res['s2']:.2f}</span></div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"""
        <div class='entry-card-new'>
            🎯 <b>نطاق الدخول المقترح:</b> {res['entry_range']}<br>
            🛑 <b>وقف الخسارة:</b> {res['stop_loss']:.2f} <span style='color:#f85149'>(⚠️ -{res['risk_pct']:.1f}%)</span>
        </div>
        <div class='target-box'>
            🏁 <b>المستهدف:</b> {res['target']:.2f} <span style='color:#58a6ff'>(🎯 +{res['target_pct']:.1f}%)</span>
        </div>
        """, unsafe_allow_html=True)

    with tab_management:
        col_port, col_risk = st.columns(2)
        portfolio = col_port.number_input("إجمالي حجم المحفظة (ج):", value=100000, step=1000, key=f"port_{res['name']}")
        risk_per_trade = col_risk.slider("نسبة مخاطرة الصفقة (%)", 0.5, 5.0, 2.0, key=f"risk_{res['name']}")
        max_loss_allowed = portfolio * (risk_per_trade / 100)
        risk_per_share = res['entry_price'] - res['stop_loss']
        shares_to_buy_initial = int(max_loss_allowed / risk_per_share) if risk_per_share > 0 else 0
        max_position_size = portfolio * 0.25
        recommended_position_size = min(shares_to_buy_initial * res['entry_price'], max_position_size)
        shares_to_buy = max(1, int(recommended_position_size / res['entry_price'])) if res['entry_price'] > 0 else 0
        profit_val = (res['target'] - res['entry_price']) * shares_to_buy
        loss_val = (res['entry_price'] - res['stop_loss']) * shares_to_buy
        actual_risk_pct = (loss_val / portfolio) * 100
        st.markdown(f"""
        <div style='background: rgba(88, 166, 255, 0.1); border: 1px solid #58a6ff; padding: 15px; border-radius: 10px; margin-top: 10px;'>
            🧠 <b>إجمالي السيولة المقررة: { (shares_to_buy * res['entry_price']):,.0f} ج</b><br>
            ⚠️ <b>المخاطرة الفعلية: {actual_risk_pct:.2f}%</b>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"""
        <div class='plan-container' style='border-right: 5px solid #238636;'>
        📊 <b>تقييم مالي للصفقة ({shares_to_buy:,} سهم):</b><br>
        🟢 الربح المتوقع: {profit_val:,.0f} ج<br>
        🔴 الخسارة المحتملة: {loss_val:,.0f} ج<br>
        ⚖️ معدل RR المحقق: {res['rr']}
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("## 💰 إدارة الصفقة المباشرة")
        deal_size = st.number_input("💰 حدد ميزانية الصفقة (ج)", value=10000, step=1000, key=f"deal_budget_{res['name']}")
        if deal_size > 0:
            if deal_size > portfolio * 0.3: st.warning("⚠️ الصفقة كبيرة مقارنة بالمحفظة")
            shares_deal = int(deal_size / res['entry_price']) if res['entry_price'] > 0 else 0
            actual_value = shares_deal * res['entry_price']
            profit_val_d = (res['target'] - res['entry_price']) * shares_deal
            loss_val_d = (res['entry_price'] - res['stop_loss']) * shares_deal
            st.markdown(f"""
            <div style='background: rgba(63, 185, 80, 0.1); border: 1px solid #3fb950; padding: 15px; border-radius: 10px; margin-top: 10px;'>
                💰 <b>قيمة الصفقة الفعلية: {actual_value:,.0f} ج</b><br>
                📦 <b>عدد الأسهم: {shares_deal:,}</b>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"""
            <div class='plan-container'>
            🟢 الربح المتوقع: {profit_val_d:,.0f} ج<br>
            🔴 الخسارة المحتملة: {loss_val_d:,.0f} ج<br>
            ⚖️ RR: {res['rr']}
            </div>
            """, unsafe_allow_html=True)
            range_size_d = res['entry_price'] - res['stop_loss']
            e1_p_d = res['entry_price']
            e2_p_d = max(res['entry_price'] - (range_size_d * 0.5), res['stop_loss'] * 1.02)
            e3_p_d = res['entry_price'] + (res['target'] - res['entry_price']) * 0.3
            if res['rr'] >= 2: weights_d = [0.7, 0.2, 0.1]
            elif res['rr'] >= 1.5: weights_d = [0.5, 0.3, 0.2]
            else: weights_d = [0.3, 0.4, 0.3]
            e1_m_d = deal_size * weights_d[0]
            e2_m_d = deal_size * weights_d[1]
            e3_m_d = deal_size * weights_d[2]
            e1_s_d = int(e1_m_d / e1_p_d) if e1_p_d > 0 else 0
            e2_s_d = int(e2_m_d / e2_p_d) if e2_p_d > 0 else 0
            e3_s_d = int(e3_m_d / e3_p_d) if e3_p_d > 0 else 0
            st.markdown("### 🏹 خطة التنفيذ المباشرة")
            st.markdown(f"""
            <div class='plan-container'>
            🟢 <b>لو السعر ≈ {e1_p_d:.2f} ج ➜ اشتري (دخول أساسي)</b><br>
            📦 الكمية: {e1_s_d:,} سهم | 💰 القيمة: {e1_m_d:,.0f} ج<br><br>
            🟡 <b>لو السعر نزل لـ {e2_p_d:.2f} ج ➜ اشتري (تعزيز دعم)</b><br>
            📦 الكمية: {e2_s_d:,} سهم | 💰 القيمة: {e2_m_d:,.0f} ج<br><br>
            🔵 <b>لو السعر اخترق {e3_p_d:.2f} ج ➜ اشتري (تأكيد اختراق)</b><br>
            📦 الكمية: {e3_s_d:,} سهم | 💰 القيمة: {e3_m_d:,.0f} ج
            </div>
            """, unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("### 🧮 تعديل متوسط السعر")
        c_avg1, c_avg2 = st.columns(2)
        add_price = c_avg1.number_input("سعر التعزيز الجديد", value=res['p'], key=f"ap_{res['name']}")
        add_qty_input = c_avg2.number_input("عدد الأسهم الجديدة", value=0, key=f"aq_{res['name']}")
        if add_qty_input > 0:
            new_total_qty = shares_to_buy + add_qty_input
            new_total_cost = (shares_to_buy * res['entry_price']) + (add_qty_input * add_price)
            new_avg = new_total_cost / new_total_qty
            st.info(f"📊 متوسط السعر بعد التعزيز: {new_avg:.2f}")
        range_size = res['entry_price'] - res['stop_loss']
        e1_p, e2_p = res['entry_price'], max(res['entry_price'] - (range_size * 0.5), res['stop_loss'] * 1.02)
        e3_p = res['entry_price'] + (res['target'] - res['entry_price']) * 0.3
        if res['rr'] >= 2: weights = [0.7, 0.2, 0.1]
        elif res['rr'] >= 1.5: weights = [0.5, 0.3, 0.2]
        else: weights = [0.3, 0.4, 0.3]
        current_total_val = shares_to_buy * res['entry_price']
        e1_m, e2_m, e3_m = current_total_val * weights[0], current_total_val * weights[1], current_total_val * weights[2]
        e1_s, e2_s, e3_s = int(e1_m / e1_p) if e1_p > 0 else 0, int(e2_m / e2_p) if e2_p > 0 else 0, int(e3_m / e3_p) if e3_p > 0 else 0
        st.markdown("### 🏹 خطة التنفيذ (حسب إدارة المخاطر)")
        st.markdown(f"""
        <div class='plan-container'>
        🟢 <b>لو السعر ≈ {e1_p:.2f} ج ➜ اشتري (دخول أساسي)</b><br>
        📦 الكمية: {e1_s:,} سهم | 💰 القيمة: {e1_m:,.0f} ج<br><br>
        🟡 <b>لو السعر نزل لـ {e2_p:.2f} ج ➜ اشتري (تعزيز دعم)</b><br>
        📦 الكمية: {e2_s:,} سهم | 💰 القيمة: {e2_m:,.0f} ج<br><br>
        🔵 <b>لو السعر اخترق {e3_p:.2f} ج ➜ اشتري (تأكيد اختراق)</b><br>
        📦 الكمية: {e3_s:,} سهم | 💰 القيمة: {e3_m:,.0f} ج
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### 🎯 وقف الخسارة المتحرك (Trailing Stop)")
        current_price_trail = st.number_input("السعر الحالي", value=res['p'], key=f"trail_price_{res['name']}")
        highest_price_trail = st.number_input("أعلى سعر تم الوصول إليه", value=res['p'], key=f"highest_{res['name']}")
        trailing_stop = calculate_trailing_stop(res['entry_price'], current_price_trail, highest_price_trail, res['rr'])
        st.markdown(f"""
        <div class='alert-success'>
        🛡️ <b>وقف الخسارة المتحرك المقترح:</b> {trailing_stop:.2f}<br>
        📍 <b>وقف الخسارة الأصلي:</b> {res['stop_loss']:.2f}
        </div>
        """, unsafe_allow_html=True)

    with tab_scenario:
        st.markdown("### 🧠 تحليل وضعك الحالي")
        col1, col2 = st.columns(2)
        buy_price = col1.number_input("سعر الشراء", value=res['p'], key=f"buy_{res['name']}")
        qty = col2.number_input("عدد الأسهم", value=100, step=1, key=f"qty_{res['name']}")
        if qty > 0 and buy_price > 0:
            current_price = res['p']
            pnl = (current_price - buy_price) * qty
            pnl_pct = ((current_price - buy_price) / buy_price) * 100
            if pnl > 0:
                st.success(f"🟢 انت كسبان: {pnl:,.0f} ج (+{pnl_pct:.2f}%)")
                if pnl_pct >= 3: st.info(f"💡 حرك وقف الخسارة لنقطة الدخول: {buy_price:.2f}")
            elif pnl < 0: st.error(f"🔴 انت خسران: {pnl:,.0f} ج ({pnl_pct:.2f}%)")
            else: st.info("⚖️ انت على التعادل")
            if current_price >= res['target']:
                st.markdown("<div class='alert-success'>🎉 تم تحقيق الهدف! أنصح بجني الأرباح</div>", unsafe_allow_html=True)
            elif current_price <= res['stop_loss']:
                st.markdown("<div class='alert-danger'>⚠️ كسر وقف الخسارة! أنصح بالخروج الفوري</div>", unsafe_allow_html=True)
            st.markdown("---")
            trend_score = (1 if res['t_short'] == "صاعد" else 0) + (1 if res['t_med'] == "صاعد" else 0) + (1 if res['ratio'] > 1.5 else 0)
            st.markdown("### 🟢 الاستمرار (Hold)")
            if trend_score >= 2: st.success(f"الاتجاه كويس ✅ خليك مستمر طالما السعر فوق {res['stop_loss']:.2f}")
            else: st.warning("الاتجاه ضعيف ⚠️ الأفضل تأمين جزء من الربح")
            st.markdown("### 🟡 التبريد (Averaging)")
            avg_zone = res['entry_price'] * 0.97
            if res['t_short'] == "صاعد" and res['ratio'] > 1.2 and current_price > res['stop_loss']:
                st.success(f"✅ تبريد آمن نسبيًا عند {avg_zone:.2f}")
            else: st.warning(f"⚠️ تبريد خطر عند {avg_zone:.2f}")
            st.markdown("### 🔴 الخروج (Exit)")
            st.error(f"وقف الخسارة: {res['stop_loss']:.2f} | لو كسرها ➜ خروج فوري ❌")
            st.markdown("### 🤖 القرار الذكي")
            if pnl_pct >= 7: st.success("🔒 تأمين قوي → بيع 50%")
            elif pnl_pct >= 3: st.info("⚖️ تأمين جزئي → بيع 25%")
            elif pnl_pct <= -3:
                if trend_score >= 2: st.warning("🟡 تبريد بحذر")
                else: st.error("🔴 تقليل مركز / خروج")
            else: st.info("⚖️ استنى إشارة أوضح")
            st.markdown("### 🚨 تنبيهات")
            alerts = []
            if res['ratio'] > 2: alerts.append("🚀 سيولة قوية")
            elif res['ratio'] == 0: alerts.append("❓ سيولة غير معروفة")
            if res['rr'] < 1: alerts.append("❌ RR ضعيف")
            if res['t_short'] == "هابط": alerts.append("🔻 اتجاه هابط")
            if res['rsi'] > 75: alerts.append("🔴 تشبع شراء خطر")
            if current_price <= res['stop_loss']: alerts.append("⛔ كسر وقف الخسارة")
            for a in alerts: st.warning(a)
            if not alerts: st.success("✅ لا يوجد خطر حالي")

    with tab_indicators:
        st.markdown("### 📊 مؤشرات فنية إضافية")
        stoch = calculate_stochastic_rsi(res['rsi'])
        st.markdown(f"""
        <div style='background:#161b22;border:1px solid #30363d;border-radius:10px;padding:15px;margin-bottom:15px;'>
            <b>🔄 Stochastic RSI</b><br>
            📈 K={stoch['k']:.1f} | D={stoch['d']:.1f}<br>
            🧠 {stoch['signal']}
            <div style='font-size:11px;color:#8b949e;margin-top:5px;'>⚠️ تقدير تقريبي بناءً على RSI فقط</div>
        </div>
        """, unsafe_allow_html=True)
        success_rate, success_level = expected_success_rate(res)
        st.markdown(f"""
        <div style='background:#161b22;border:1px solid #d29922;border-radius:10px;padding:15px;margin-bottom:15px;'>
            <b>📈 نسبة النجاح المتوقعة</b><br>
            🎯 <b>{success_rate}%</b> - {success_level}<br>
            <div style='font-size:11px;color:#8b949e;margin-top:5px;'>📌 تعتمد على: تناسق الاتجاهات، السيولة، نطاق التحرك المتوقع</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("### 💡 توصيات إضافية")
        recs = []
        if res['rsi'] < 30: recs.append("🔴 RSI في تشبع بيع → احتمالية ارتداد")
        elif res['rsi'] > 70: recs.append("🟡 RSI في تشبع شراء → احتمالية تصحيح")
        if res['ratio'] > 2: recs.append("🚀 سيولة عالية جدًا → اختراق قوي محتمل")
        elif res['ratio'] == 0: recs.append("❓ سيولة غير معروفة → تحقق يدويًا")
        elif res['ratio'] < 0.8: recs.append("❄️ سيولة ضعيفة → تجنب الدخول")
        if res['rr'] >= 2: recs.append("💰 RR ممتاز → مناسب للمحافظ المحافظة")
        elif res['rr'] < 1: recs.append("⚠️ RR سيء → غير مناسب")
        for rec in recs: st.info(rec)
        if not recs: st.success("✅ لا توجد توصيات إضافية")


# ================== NAVIGATION ==================
if st.session_state.market_data is None:
    get_fresh_data()

if st.session_state.page == 'home':
    st.title("🏹 Sniper Elite v15.8 Pro")
    render_mode_selector()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📡 تحليل سهم محدد"): st.session_state.page = 'analyze'; st.rerun()
        if st.button("🔭 كشاف السوق"): st.session_state.page = 'scanner'; st.rerun()
        if st.button("🧮 حاسبة المتوسط"): st.session_state.page = 'avg'; st.rerun()
    with col2:
        if st.button("🚀 الاختراقات"): st.session_state.page = 'breakout'; st.rerun()
        if st.button("💎 قنص الذهب"): st.session_state.page = 'gold'; st.rerun()
        if st.button("⚡ مضاربات سريعة"): st.session_state.page = 'scalp'; st.rerun()
        if st.button("🏆 أفضل 10 فرص"): st.session_state.page = 'top10'; st.rerun()
        if st.button("📊 تقييم الأداء"): st.session_state.page = 'performance'; st.rerun()
        if st.button("📖 دليل المؤشرات"): st.session_state.page = 'guide'; st.rerun()
        if st.button("🔄 تحديث البيانات"): 
            get_fresh_data()
            st.success("✅ تم تحديث البيانات!")
            st.rerun()
    
    # زر تحميل PDF
    if st.session_state.all_results:
        st.markdown("---")
        st.markdown("### 📄 تقارير يومية")
        
        # تجهيز البيانات للتقرير
        top_results = get_top_ranked(st.session_state.all_results, limit=10)
        gold_results = [an for an in st.session_state.all_results if classify_stock(an) == "gold"]
        scalp_results = [an for an in st.session_state.all_results if classify_stock(an) == "scalp"]
        
        if st.button("📥 تحميل تقرير PDF (أفضل 10 + ذهب + مضاربات)"):
            with st.spinner("جاري إنشاء التقرير..."):
                pdf_bytes = generate_pdf_report(top_results, gold_results, scalp_results)
                st.download_button(
                    label="📄 تحميل التقرير",
                    data=pdf_bytes,
                    file_name=f"EGX_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf"
                )
    else:
        st.info("⚠️ لا توجد بيانات لعمل تقرير. اضغط على 'تحديث البيانات' أولاً.")

elif st.session_state.page == 'avg':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    st.title("🧮 حاسبة متوسط السعر")
    c1, c2 = st.columns(2)
    p1 = c1.number_input("سعر الشراء الأول", value=0.0, format="%.2f")
    q1 = c2.number_input("عدد الأسهم", value=0, step=1)
    p2 = c1.number_input("سعر التعزيز", value=0.0, format="%.2f")
    q2 = c2.number_input("عدد الأسهم (تعزيز)", value=0, step=1)
    if (q1 + q2) > 0:
        avg = ((p1 * q1) + (p2 * q2)) / (q1 + q2)
        st.success(f"📊 متوسط السعر الجديد: {avg:.2f}")

elif st.session_state.page == 'guide':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    st.title("📖 دليل المؤشرات الفنية")
    st.markdown("مرحباً بك في دليل المؤشرات! هنا شرح مبسط لكل مؤشر تستخدمه في التطبيق.")
    
    with st.expander("📊 مؤشر القوة النسبية (RSI)"):
        st.markdown("""
        ### ما هو RSI؟
        **RSI** هو مؤشر يقيس سرعة وتغير حركة السعر. قيمته تتراوح بين 0 و 100.
        
        ### دلالات RSI:
        | القيمة | الدلالة | التصرف المتوقع |
        |--------|---------|----------------|
        | **فوق 70** | 🔴 **تشبع شراء** | السهم ممكن ينزل (بيع/جني أرباح) |
        | **تحت 30** | 🟢 **تشبع بيع** | السهم ممكن يصعد (فرصة شراء) |
        | **بين 40 و 60** | 🟡 **منطقة محايدة** | استنى تأكيد إضافي |
        | **بين 30 و 40 أو 60 و 70** | ⚪ **ضعيف** | زخم السهم ضعيف |
        
        ### نصيحة:
        الأفضل للدخول في صفقة شراء عندما يكون RSI **بين 40 و 65** (زخم صحي).
        """)
    
    with st.expander("⚡ Stochastic RSI"):
        st.markdown("""
        ### ما هو Stochastic RSI؟
        هو مؤشر **يقيس قوة الـ RSI نفسه**، وليس قوة السعر مباشرة. يظهر كخطين: **K (السريع)** و **D (البطيء)**.
        
        ### دلالات Stochastic RSI:
        | القيمة | الدلالة | التصرف |
        |--------|---------|--------|
        | **K و D فوق 80** | 🔴 تشبع شراء شديد | استعداد للبيع |
        | **K و D تحت 20** | 🟢 تشبع بيع شديد | استعداد للشراء |
        | **K يقطع D من تحت لفوق** | 🟢 إشارة شراء | منطقة آمنة نسبياً |
        | **K يقطع D من فوق لتحت** | 🔴 إشارة بيع | منطقة خطر |
        
        > ⚠️ **تنبيه:** المؤشر في التطبيق **تقديري** بسبب محدودية البيانات.
        """)
    
    with st.expander("🎯 Smart Score"):
        st.markdown("""
        ### ما هو Smart Score؟
        **Smart Score** هو ابتكارنا الخاص في هذا التطبيق! هو درجة مركبة من 0 إلى 100 تقييم قوة السهم.
        
        ### كيفية حسابه:
        | العامل | الوزن |
        |--------|-------|
        | اتجاه قصير صاعد | +15 |
        | اتجاه متوسط صاعد | +15 |
        | اتجاه طويل صاعد | +10 |
        | سيولة عالية (ratio > 2) | +20 |
        | سيولة جيدة (ratio > 1.5) | +10 |
        | RSI في المنطقة الصحية (50-65) | +20 |
        | RR ممتاز (>= 2) | +20 |
        | RR جيد (>= 1.5) | +10 |
        
        ### دلالات Smart Score:
        | الدرجة | التقييم | التصرف |
        |--------|---------|--------|
        | **70-100** | 🔥 فرصة قوية جداً | مناسب للدخول |
        | **50-69** | ✅ فرصة جيدة | دخول بحذر |
        | **30-49** | ⚠️ تحت المراقبة | استنى تأكيد |
        | **0-29** | ❄️ ضعيف | تجنب |
        """)
    
    with st.expander("💰 نسبة المخاطرة/العائد (RR Ratio)"):
        st.markdown("""
        ### ما هو RR Ratio؟
        **RR Ratio** = (الهدف - سعر الدخول) / (سعر الدخول - وقف الخسارة)
        
        ### دلالات RR:
        | القيمة | التقييم |
        |--------|---------|
        | **>= 2** | 🔥 ممتاز (الربح المتوقع ضعف الخسارة) |
        | **1.5 - 2** | ✅ جيد |
        | **1 - 1.5** | ⚠️ متوسط (مضاربة سريعة فقط) |
        | **< 1** | ❌ سيء (الخسارة أكبر من الربح) |
        
        ### نصيحة ذهبية:
        > **لا تدخل أي صفقة RR أقل من 1.5** إلا إذا كنت مضارب محترف جداً.
        """)
    
    with st.expander("📈 الاتجاهات (المتوسطات المتحركة)"):
        st.markdown("""
        ### كيف نحدد الاتجاه؟
        نقارن السعر الحالي بالمتوسطات المتحركة:
        
        | المتوسط | الفترة | الدلالة |
        |----------|--------|---------|
        | **SMA20** | 20 يوم | اتجاه **قصير المدى** |
        | **SMA50** | 50 يوم | اتجاه **متوسط المدى** |
        | **SMA200** | 200 يوم | اتجاه **طويل المدى** |
        
        ### دلالة الاتجاه:
        - **صاعد:** السعر > المتوسط (اتجاه إيجابي)
        - **هابط:** السعر < المتوسط (اتجاه سلبي)
        
        ### قوة الإشارة:
        كلما زاد عدد الاتجاهات الصاعدة (قصير + متوسط + طويل)، كانت الفرصة أقوى.
        """)
    
    with st.expander("📊 حجم التداول (Volume Ratio)"):
        st.markdown("""
        ### ما هو Volume Ratio؟
        **Ratio** = حجم التداول اليوم / متوسط حجم التداول في آخر 10 أيام
        
        ### دلالات Ratio:
        | القيمة | الدلالة |
        |--------|---------|
        | **> 2** | 🚀 سيولة قوية جداً (اختراق محتمل) |
        | **1.5 - 2** | ⚡ نشطة (في اهتمام) |
        | **1 - 1.5** | 🙃 عادية |
        | **< 1** | ❄️ ضعيفة |
        | **0** | ❓ غير معروفة (بيانات غير كافية) |
        
        ### أهميته:
        السيولة العالية تعني اهتمام أكبر من المتداولين، وتزيد فرصة نجاح الاختراق.
        """)
    
    with st.expander("🏛️ الدعم والمقاومة (Pivot Points)"):
        st.markdown("""
        ### ما هي نقاط الارتكاز؟
        هي مستويات سعرية محسوبة من أعلى وأدنى وإغلاق اليوم السابق.
        
        ### المستويات:
        | المستوى | المعنى |
        |----------|--------|
        | **R2** | مقاومة قوية (صعبة الاختراق) |
        | **R1** | مقاومة أولى |
        | **PP** | نقطة الارتكاز (المحور) |
        | **S1** | دعم أول |
        | **S2** | دعم قوي |
        
        ### كيفية الاستخدام:
        - **اختراق R1** → إشارة صعود
        - **كسر S1** → إشارة هبوط
        - **الارتداد من S1/S2** → فرصة شراء
        - **الارتداد من R1/R2** → فرصة بيع
        """)
    
    with st.expander("🛡️ فخ السيولة (Fake Breakout)"):
        st.markdown("""
        ### ما هو فخ السيولة؟
        هو اختراق وهمي للسهم (صاعد أو هابط) ثم يعكس اتجاهه بسرعة.
        
        ### كيف نكتشفه في التطبيق؟
        التطبيق يعتبر السهم **"فخ سيولة"** إذا تحقق أحد الشرطين:
        1. RSI > 75 و RR < 1.3 (تشبع شراء مع RR ضعيف)
        2. حجم التداول أقل من المتوسط (ratio < 1.2)
        
        ### دلالة فخ السيولة:
        ❌ **تجنب الدخول نهائياً** - السهم غير مستقر وقد ينعكس عليك.
        """)
    
    st.info("💡 **تذكير:** هذه المؤشرات هي أدوات مساعدة، وليست قرارات نهائية. القرار النهائي يعتمد على تحليلك الشخصي وإدارة المخاطر الخاصة بك.")

elif st.session_state.page == 'performance':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    st.title("📊 تقييم أداء التطبيق")
    
    trades = load_trades()
    
    if st.button("🔄 تحديث البيانات"):
        with st.spinner("جاري تحديث البيانات..."):
            if st.session_state.all_results:
                current_prices = {res['name']: res['p'] for res in st.session_state.all_results if res}
                trades = update_all_trades(current_prices)
                st.success("تم تحديث البيانات بنجاح!")
                st.rerun()
            else:
                st.error("لا توجد بيانات محدثة")
    
    stats = get_performance_stats(trades)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📊 إجمالي الصفقات", stats['total'])
    col2.metric("✅ حققت الهدف", stats['hit_target'])
    col3.metric("❌ كسرت الوقف", stats['stopped_out'])
    col4.metric("⏳ لا تزال مفتوحة", stats['still_open'])
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📈 نسبة النجاح", f"{stats['success_rate']}%")
    col2.metric("💰 إجمالي العائد %", f"{stats['total_return']}%")
    col3.metric("📊 متوسط العائد %", f"{stats['avg_return']}%")
    col4.metric("⚖️ متوسط RR", stats['avg_rr'])
    
    col1, col2, col3 = st.columns(3)
    col1.metric("📅 متوسط أيام الاحتفاظ", f"{stats['avg_holding_days']} يوم")
    col2.metric("🎯 دقة الدخول", f"{stats['entry_accuracy']}%")
    col3.metric("🏆 أفضل 10 (نسبة نجاح)", f"{stats['top10_success']}%")
    
    st.markdown(f"""
    <div style='background:#161b22;border:1px solid #30363d;border-radius:10px;padding:15px;margin:15px 0;'>
        <b>💎 الفرص الذهبية:</b> {stats['gold_count']} صفقة | نسبة نجاح: {stats['gold_success']}% | إجمالي العائد: {stats['gold_return']}%
    </div>
    """, unsafe_allow_html=True)
    
    if stats['gold_count'] >= 5:
        if stats['gold_success'] > stats['top10_success']:
            st.success("💡 Insight: الفرص الذهبية تتفوق على أفضل 10 فرص!")
        elif stats['top10_success'] > stats['gold_success']:
            st.info("💡 Insight: أفضل 10 فرص تتفوق على الفرص الذهبية!")
    
    st.markdown("---")
    st.markdown("### 📋 تفاصيل الصفقات")
    
    filter_option = st.radio(
        "🔍 اختر الفلتر:",
        ["📋 كل الصفقات", "✅ الناجحة فقط (حققت الهدف)", "❌ الفاشلة فقط (كسرت الوقف)", "⏳ المفتوحة فقط"],
        horizontal=True
    )
    
    if filter_option == "✅ الناجحة فقط (حققت الهدف)":
        filtered_trades = [t for t in trades if t.get('status') == 'hit_target']
    elif filter_option == "❌ الفاشلة فقط (كسرت الوقف)":
        filtered_trades = [t for t in trades if t.get('status') == 'stopped_out']
    elif filter_option == "⏳ المفتوحة فقط":
        filtered_trades = [t for t in trades if t.get('status') in ['pending', 'still_open']]
    else:
        filtered_trades = trades
    
    if filtered_trades:
        st.markdown(f"**عدد الصفقات: {len(filtered_trades)}**")
        for trade in reversed(filtered_trades[-30:]):
            if trade.get('status') == 'hit_target':
                status_color = "🟢"
                status_text = "حققت الهدف"
            elif trade.get('status') == 'stopped_out':
                status_color = "🔴"
                status_text = "كسرت الوقف"
            else:
                status_color = "🟡"
                status_text = "لا تزال مفتوحة"
            
            entry_hit_mark = "✅" if trade.get('entry_hit', False) else "❌"
            profit_text = f" | {'🟢' if trade.get('profit_pct', 0) > 0 else '🔴'} {trade.get('profit_pct', 0):+.1f}%" if trade.get('profit_pct') is not None else ""
            
            st.markdown(f"""
            <div style='background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:10px;margin:5px 0;'>
                <b>{trade.get('name', 'N/A')}</b> ({trade.get('trade_type', 'N/A')}) - {status_color} {status_text}{profit_text}<br>
                📅 التسجيل: {trade.get('date_recorded', 'N/A')} | {entry_hit_mark} دخول في النطاق<br>
                🎯 الهدف: {trade.get('target', 0):.2f} | 🛑 الوقف: {trade.get('stop_loss', 0):.2f}<br>
                📊 RR: {trade.get('rr', 0)} | RSI: {trade.get('rsi_at_entry', 0):.1f}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("لا توجد صفقات تطابق الفلتر المختار.")

elif st.session_state.page == 'top10':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    render_mode_selector()
    
    if not st.session_state.all_results:
        st.error("⚠️ لا توجد بيانات. اضغط على 'تحديث البيانات' في الصفحة الرئيسية.")
        st.stop()
    
    top_results = get_top_ranked(st.session_state.all_results, limit=10)
    
    for an in top_results:
        if an:
            record_trade(an, "top10")
    
    st.markdown("## 🏆 أقوى 10 فرص حسب Smart Score")
    for i, an in enumerate(top_results, 1):
        if an:
            with st.expander(f"#{i} - {an['name']} | Smart Score: {an['smart_score']} | RR: {an['rr']}"):
                render_stock_ui(an, is_top10=True)

elif st.session_state.page in ['gold', 'scanner', 'breakout', 'scalp']:
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    render_mode_selector()
    
    if not st.session_state.all_results:
        st.error("⚠️ لا توجد بيانات. اضغط على 'تحديث البيانات' في الصفحة الرئيسية.")
        st.stop()
    
    if st.session_state.page == 'gold':
        found = False
        for an in st.session_state.all_results:
            if an and classify_stock(an) == "gold":
                record_trade(an, "gold")
                with st.expander(f"✨ ذهبي: {an['name']} (RR: {an['rr']} | RSI: {an['rsi']:.1f})"): 
                    render_stock_ui(an, is_gold=True)
                    found = True
        if not found: st.info("لا توجد فرص ذهبية حالياً.")
    
    elif st.session_state.page == 'scanner':
        results = [an for an in st.session_state.all_results if an and classify_stock(an) == "watchlist"]
        results.sort(key=lambda x: (x.get('smart_score', 0), x.get('rr', 0)), reverse=True)
        for an in results[:15]:
            with st.expander(f"{an['name']} | {an['signal']}"): render_stock_ui(an)
    
    elif st.session_state.page == 'breakout':
        for an in st.session_state.all_results:
            if an and classify_stock(an) == "breakout":
                with st.expander(f"🚀 اختراق: {an['name']} (RSI: {an['rsi']:.1f})"): render_stock_ui(an)
    
    elif st.session_state.page == 'scalp':
        found = False
        for an in st.session_state.all_results:
            if an and classify_stock(an) == "scalp":
                with st.expander(f"⚡ مضاربة: {an['name']} (RSI: {an['rsi']:.1f})"):
                    render_stock_ui(an)
                    found = True
        if not found: st.info("لا توجد مضاربات سريعة حالياً.")

elif st.session_state.page == 'analyze':
    if st.button("🏠 الرئيسية"): st.session_state.page = 'home'; st.rerun()
    render_mode_selector()
    
    if not st.session_state.all_results:
        st.error("⚠️ لا توجد بيانات. اضغط على 'تحديث البيانات' في الصفحة الرئيسية.")
        st.stop()
    
    sym = st.text_input("رمز السهم").upper().strip()
    if sym:
        with st.spinner("🔍 جاري البحث عن السهم..."):
            res = next((x for x in st.session_state.all_results if x['name'] == sym), None)
            
            if not res:
                st.error("❌ السهم غير موجود في البيانات الحالية")
                symbols = [x['name'] for x in st.session_state.all_results]
                similar = [s for s in symbols if sym[:2] in s or s[:2] in sym][:5]
                if similar:
                    st.info(f"💡 هل تقصد: {', '.join(similar)}")
            else:
                render_stock_ui(res)
