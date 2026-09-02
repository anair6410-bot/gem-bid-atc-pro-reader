import streamlit as st
import pandas as pd
import re
try:
    from pypdf import PdfReader
except:
    from PyPDF2 import PdfReader

st.set_page_config(page_title="GeM ATC Pro", layout="wide", page_icon="🇮🇳")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800&display=swap');
* { font-family: 'Outfit', sans-serif; }

.stApp {
    background: radial-gradient(1200px at 10% -10%, #FFE9C6 0%, transparent 60%),
                radial-gradient(1000px at 90% 0%, #C6F6D5 0%, transparent 50%),
                linear-gradient(180deg, #F8FAFF 0%, #EEF2FF 100%);
}

.hero {
    background: linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0F172A 100%);
    border-radius: 20px;
    padding: 22px 26px;
    color: white;
    display:flex; justify-content:space-between; align-items:center;
    box-shadow: 0 20px 40px rgba(15,23,42,0.25);
    border: 1px solid rgba(255,255,255,0.1);
    position:relative; overflow:hidden;
}
.hero::before {
    content:''; position:absolute; top:-50px; left:-50px; width:200px; height:200px;
    background: radial-gradient(circle, #FF9933 0%, transparent 70%); opacity:0.25;
}
.hero::after {
    content:''; position:absolute; bottom:-60px; right:100px; width:250px; height:250px;
    background: radial-gradient(circle, #138808 0%, transparent 70%); opacity:0.25;
}
.hero-title { font-size: 26px; font-weight: 800; letter-spacing: -0.5px; }
.hero-sub { font-size: 13px; opacity:0.7; margin-top:4px; }
.tricolor { height:4px; border-radius:10px; background: linear-gradient(90deg, #FF9933 0%, #FFFFFF 50%, #138808 100%); margin: 14px 0; }

.glass-card {
    background: rgba(255,255,255,0.85);
    backdrop-filter: blur(12px);
    border-radius: 18px;
    padding: 20px;
    border: 1px solid rgba(255,255,255,0.8);
    box-shadow: 0 8px 32px rgba(15,23,42,0.08), 0 0 0 1px rgba(15,23,42,0.04);
    margin-bottom: 16px;
}
.upload-card {
    background: white;
    border-radius: 16px;
    padding: 18px;
    border: 1.5px dashed #CBD5E1;
    text-align:center;
    transition: all 0.2s;
}
.upload-card:hover { border-color: #6366F1; background: #F8FAFF; transform: translateY(-2px); box-shadow: 0 12px 24px rgba(99,102,241,0.12); }
.upload-icon { font-size: 28px; margin-bottom: 6px; }

.prod-card {
    background: white;
    border-radius: 14px;
    padding: 14px 16px;
    border: 1px solid #E2E8F0;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04);
    position:relative; overflow:hidden;
}
.prod-card::before { content:''; position:absolute; left:0; top:0; bottom:0; width:4px; background: linear-gradient(180deg, #10B981, #059669); }
.prod-head { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }
.prod-name { font-weight:700; font-size:13px; color:#0F172A; }
.price-pill { background:#0F172A; color:white; font-size:11px; padding:4px 10px; border-radius:20px; font-weight:600; }
.market-pill { background:#ECFDF5; color:#065F46; font-size:10px; padding:2px 8px; border-radius:20px; border:1px solid #A7F3D0; }

.status-dot { width:8px; height:8px; border-radius:50%; display:inline-block; margin-right:6px; }
.dot-green { background:#10B981; box-shadow:0 0 0 4px #D1FAE5; }
.dot-red { background:#EF4444; box-shadow:0 0 0 4px #FEE2E2; }
.dot-yellow { background:#F59E0B; box-shadow:0 0 0 4px #FEF3C7; }

div[data-testid="stMetric"] { background:white; border-radius:16px; border:1px solid #E2E8F0; box-shadow:0 4px 16px rgba(0,0,0,0.06); }
.stButton>button { border-radius:12px!important; font-weight:600!important; }
</style>
""", unsafe_allow_html=True)

MARKET = {
    "Processor CPU": 14500, "MB": 6500, "RAM": 5200, "SSD": 3200, "SSD (SECONDARY)": 5400,
    "Cabinet LTR": 2200, "SMPS WATT": 1800, "MONITOR": 7200, "SPEAKER": 450,
    "WIRELESS + BLUETOOTH": 850, "Keyboard & Mouse": 750, "ANTIVIRUS": 350,
    "CHASSIS SWITCH": 300, "SERIAL COM PORT+PARALLEL": 250, "Graphics CARD": 0, "OS": 0,
    "MS OFFICE": 0, "TPM 2.0": 0, "CAMERA": 0, "DP PORT": 0
}
KEYWORDS = {
    "Processor CPU": ["processor", "cpu", "i3", "i5", "i7", "ryzen"],
    "MB": ["motherboard"], "Graphics CARD": ["graphics", "gpu"], "OS": ["windows", "linux", "operating system"],
    "RAM": ["ram", "memory"], "SSD": ["ssd", "nvme"], "SSD (SECONDARY)": ["secondary", "hdd", "1 tb"],
    "Cabinet LTR": ["cabinet", "chassis"], "SMPS WATT": ["smps", "power supply"], "MONITOR": ["monitor", "inch", "display"],
    "SPEAKER": ["speaker"], "WIRELESS + BLUETOOTH": ["wifi", "wireless", "bluetooth"], "MS OFFICE": ["ms office"],
    "CHASSIS SWITCH": ["chassis intrusion"], "TPM 2.0": ["tpm"], "CAMERA": ["camera", "webcam"], "ANTIVIRUS": ["antivirus"],
    "DP PORT": ["display port"], "SERIAL COM PORT+PARALLEL": ["serial", "com port"], "Keyboard & Mouse": ["keyboard", "mouse"]
}
DEPTS = ["BANK OF INDIA","SBI","BANK OF BARODA","INDIAN ARMY","MINISTRY OF DEFENCE","MINISTRY OF FINANCE","MINISTRY OF HOME AFFAIRS","MINISTRY OF EDUCATION","MINISTRY OF RAILWAYS","MINISTRY OF ELECTRONICS & IT","NITI AAYOG","ISRO","NIC"]
ITEMS = ["Desktop Computer","All in One PC","All in One PC - High End","High End Desktop Computer","Entry Level Desktop Computer","Mid Level Desktop Computer","Entry and Mid Level Desktop Computer","Laptop - Notebook"]

def read_pdf(f):
    r = PdfReader(f)
    return "\n".join([p.extract_text() or "" for p in r.pages])
def detect(text):
    low=text.lower()
    return [prod for prod, kws in KEYWORDS.items() if any(k in low for k in kws)]
def parse_meta(text):
    org=""; m=re.search(r'Organisation\s*Name\s*[:\-]?\s*(.+?)\n',text,re.I)
    if m: org=m.group(1).strip()[:100]
    bid=""; m=re.search(r'GEM\/\d{4}\/B\/\d{4,8}',text.replace(" ","").upper())
    if m: bid=m.group(0)
    qty=65; m=re.search(r'Quantity\s*[:\-]?\s*(\d+)',text,re.I)
    if m: qty=int(m.group(1))
    item="Desktop Computer"; m=re.search(r'Item\s*Category\s*[:\-]?\s*(.+?)\n',text,re.I)
    if m: item=m.group(1).strip()[:100]
    dept=""; m=re.search(r'Ministry\s*[:\-]?\s*(.+?)\n|Department\s*Name\s*[:\-]?\s*(.+?)\n',text,re.I)
    if m: dept=(m.group(1) or m.group(2) or "").strip()[:100]
    return org,item,bid,qty,dept

# HERO HEADER
st.markdown("""
<div class="hero">
<div>
<div class="hero-title">🇮🇳 GeM ATC Pro Studio</div>
<div class="hero-sub">Dual Document Tracker • ATC + Bid • Real-time Market Pricing Sep 2026</div>
</div>
<div style="text-align:right;">
<div style="font-size:11px; opacity:0.6;">APPEARANCE V3</div>
<div style="font-size:13px; font-weight:600; margin-top:2px;">✨ Premium Glass UI</div>
</div>
</div>
<div class="tricolor"></div>
""", unsafe_allow_html=True)

# TOP ACTIONS
a1,a2,a3,a4 = st.columns([4,1.2,1.2,0.8])
with a2:
    if st.button("💹 Market Price", use_container_width=True):
        for k,v in MARKET.items(): st.session_state[f"pr_{k}"]=v
        st.toast("Market price set")
        st.rerun()
with a3:
    if st.button("🎨 Change Theme", use_container_width=True):
        st.session_state["theme"] = "dark" if st.session_state.get("theme")!="dark" else "light"
        st.rerun()
with a4:
    if st.button("🗑️", use_container_width=True, help="Clear All"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

# DUAL UPLOAD - NEW APPEARANCE
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown("#### 📂 Upload Center — Two Documents")
c1,c2 = st.columns(2, gap="medium")
with c1:
    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    st.markdown('<div class="upload-icon">📄</div><b>ATC Document</b><div style="font-size:12px; color:#64748B; margin:6px 0;">Product specs, processor, RAM, SSD, etc.</div>', unsafe_allow_html=True)
    atc_file = st.file_uploader("ATC", type=["pdf"], key="atc", label_visibility="collapsed")
    if atc_file: st.markdown(f'<div style="margin-top:8px;"><span class="status-dot dot-green"></span><span style="font-size:12px; font-weight:600; color:#065F46;">{atc_file.name[:30]} loaded</span></div>', unsafe_allow_html=True)
    else: st.markdown(f'<div style="margin-top:8px;"><span class="status-dot dot-red"></span><span style="font-size:12px; color:#64748B;">Waiting for ATC PDF</span></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    st.markdown('<div class="upload-icon">📑</div><b>Bid Document</b><div style="font-size:12px; color:#64748B; margin:6px 0;">Organisation, Bid No, Qty, Item Category</div>', unsafe_allow_html=True)
    bid_file = st.file_uploader("Bid", type=["pdf"], key="bid", label_visibility="collapsed")
    if bid_file: st.markdown(f'<div style="margin-top:8px;"><span class="status-dot dot-green"></span><span style="font-size:12px; font-weight:600; color:#065F46;">{bid_file.name[:30]} loaded</span></div>', unsafe_allow_html=True)
    else: st.markdown(f'<div style="margin-top:8px;"><span class="status-dot dot-yellow"></span><span style="font-size:12px; color:#64748B;">Waiting for Bid PDF</span></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# PROCESS
atc_text=""; bid_text=""; detected=[]; org_v=""; item_v=""; bid_v=""; qty_v=65; dept_v=""
if atc_file:
    atc_text = read_pdf(atc_file)
    detected = detect(atc_text)
    org_v,item_v,bid_v,qty_v,dept_v = parse_meta(atc_text)
if bid_file:
    bid_text = read_pdf(bid_file)
    org2,item2,bid2,qty2,dept2 = parse_meta(bid_text)
    org_v = org2 or org_v; item_v = item2 or item_v; bid_v = bid2 or bid_v; qty_v = qty2 or qty_v; dept_v = dept2 or dept_v
    if not detected: detected = detect(bid_text)

# TRACKING DASHBOARD - NEW LOOK
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown("##### 🔍 Live Document Tracking")
k1,k2,k3,k4 = st.columns(4)
with k1:
    st.metric("ATC Products", f"{len(detected)} Found" if detected else "0", "✅ Tracked" if atc_file else "❌ Missing")
with k2:
    st.metric("Organisation", org_v[:18] if org_v else "Not Found", "📑 From Bid" if bid_file else "Waiting")
with k3:
    st.metric("Bid Number", bid_v[:18] if bid_v else "Not Found", "Tracked" if bid_v else "Pending")
with k4:
    st.metric("Quantity", f"{qty_v} Units", f"{dept_v[:12] if dept_v else 'Dept'}")
if detected:
    st.markdown(" ".join([f'<span style="background:#0F172A; color:white; padding:4px 10px; border-radius:20px; font-size:11px; margin:2px; display:inline-block;">{p}</span>' for p in detected]), unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# DETAILS - GLASS
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown("##### ⚙️ Bid Configuration")
c1,c2,c3,c4 = st.columns(4)
with c1:
    try: d_idx = next((i for i,o in enumerate(DEPTS) if dept_v and (dept_v.lower() in o.lower() or o.lower() in dept_v.lower())),0)
    except: d_idx=0
    dept = st.selectbox("Department", DEPTS, index=d_idx, key="dept")
with c2: org = st.text_input("Organisation", value=org_v, key="org")
with c3: bid_no = st.text_input("Bid No", value=bid_v, key="bidno")
with c4: qty = st.number_input("Quantity", 1, 5000, qty_v, key="qty_final")

c_a,c_b = st.columns([3,1])
with c_a:
    try: i_idx = next((i for i,o in enumerate(ITEMS) if item_v and (o.lower() in item_v.lower() or item_v.lower() in o.lower())),0)
    except: i_idx=0
    item_cat = st.selectbox("Item Category", ITEMS, index=i_idx, key="item")
with c_b:
    margin = st.number_input("Margin ₹ / PC", value=st.session_state.get("margin",4000), step=500, key="margin")
st.markdown('</div>', unsafe_allow_html=True)

# PRICING - PREMIUM CARDS
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown(f"##### 💰 Pricing Studio — Only {len(detected)} ATC Products")

if detected:
    for p in detected:
        if f"pr_{p}" not in st.session_state: st.session_state[f"pr_{p}"] = MARKET.get(p,0)
    prices={}; total=0
    cols=st.columns(3)
    for i, comp in enumerate(detected):
        with cols[i%3]:
            st.markdown('<div class="prod-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="prod-head"><span class="prod-name">{comp}</span><span class="price-pill">₹{st.session_state[f"pr_{comp}"]:,}</span></div><div class="market-pill">Market ₹{MARKET.get(comp,0):,}</div>', unsafe_allow_html=True)
            v = st.number_input(comp, value=st.session_state[f"pr_{comp}"], key=f"pr_{comp}", label_visibility="collapsed")
            prices[comp]=v; total+=v
            st.markdown('</div>', unsafe_allow_html=True)
            st.write("")

    gst = int((total+margin)*0.18)
    grand = total+margin+gst
    total_bid_val = grand*qty

    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Base Cost", f"₹{total:,}")
    m2.metric("Margin", f"₹{margin:,}")
    m3.metric("GST 18%", f"₹{gst:,}")
    m4.metric("Grand / PC", f"₹{grand:,}")

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); padding:18px; border-radius:14px; color:white; text-align:center; position:relative; overflow:hidden; margin-top:10px;">
    <div style="position:absolute; top:-30px; left:20%; width:150px; height:150px; background: radial-gradient(circle, #FF9933 0%, transparent 70%); opacity:0.2;"></div>
    <div style="font-size:12px; opacity:0.6; letter-spacing:1px;">TOTAL BID VALUE</div>
    <div style="font-size:24px; font-weight:800; margin-top:4px;">₹{total_bid_val:,} • {qty} Units</div>
    <div style="font-size:12px; opacity:0.6; margin-top:4px;">{dept} | {bid_no} | {item_cat}</div>
    </div>
    """, unsafe_allow_html=True)

    df = pd.DataFrame(
        [["Department",dept],["Organisation",org],["Bid No",bid_no],["Item",item_cat],["Qty",qty],
         ["ATC File", atc_file.name if atc_file else "No"],["Bid File", bid_file.name if bid_file else "No"],
         ["Products",", ".join(detected)]]+list(prices.items())+[["Base",total],["Margin",margin],["GST",gst],["Grand",grand],["Total Bid",total_bid_val]],
        columns=["Field","Value"]
    )
    st.dataframe(df, use_container_width=True)
    st.download_button("📥 Download Premium Report", df.to_csv(index=False).encode(), f"GeM_{bid_no}.csv", use_container_width=True, type="primary")
else:
    st.info("⬆️ Upload ATC PDF to see premium pricing cards")
st.markdown('</div>', unsafe_allow_html=True)