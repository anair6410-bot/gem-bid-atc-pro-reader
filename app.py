import streamlit as st
import pandas as pd
import re
try:
    from pypdf import PdfReader
except:
    from PyPDF2 import PdfReader

st.set_page_config(page_title="GeM ATC Studio", layout="wide", page_icon="🇮🇳")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
* { font-family: 'Inter', sans-serif; }
.stApp { background: #F8FAFC; }
.main-header { background: white; padding: 20px 25px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); border: 1px solid #E2E8F0; margin-bottom: 20px; display:flex; justify-content:space-between; align-items:center; }
.logo-text { font-size: 24px; font-weight: 800; color: #0F172A; }
.sub-text { color: #64748B; font-size: 13px; }
.step-card { background: white; border-radius: 16px; padding: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.05); border: 1px solid #E2E8F0; margin-bottom: 18px; }
.product-card { background: white; border-radius: 12px; padding: 14px; border: 1px solid #E2E8F0; border-left: 4px solid #10B981; transition: 0.2s; }
.product-card:hover { box-shadow: 0 8px 25px rgba(0,0,0,0.08); transform: translateY(-2px); }
.market-tag { background: #ECFDF5; color: #065F46; font-size: 11px; padding: 3px 8px; border-radius: 20px; font-weight: 600; }
.atc-chip { background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin: 3px; display:inline-block; }
div[data-testid="stMetric"] { background: white; border-radius: 14px; padding: 16px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 1px solid #E2E8F0; }
</style>
""", unsafe_allow_html=True)

# MARKET PRICE
MARKET = {
    "Processor CPU": 14500, "MB": 6500, "RAM": 5200, "SSD": 3200, "SSD (SECONDARY)": 5400,
    "Cabinet LTR": 2200, "SMPS WATT": 1800, "MONITOR": 7200, "SPEAKER": 450,
    "WIRELESS + BLUETOOTH": 850, "Keyboard & Mouse": 750, "ANTIVIRUS": 350,
    "CHASSIS SWITCH": 300, "SERIAL COM PORT+PARALLEL": 250, "Graphics CARD": 0, "OS": 0,
    "MS OFFICE": 0, "TPM 2.0": 0, "CAMERA": 0, "DP PORT": 0
}

KEYWORDS = {
    "Processor CPU": ["processor", "cpu", "i3", "i5", "i7", "ryzen"],
    "MB": ["motherboard"], "Graphics CARD": ["graphics", "gpu"], "OS": ["windows", "linux"],
    "RAM": ["ram"], "SSD": ["ssd", "nvme"], "SSD (SECONDARY)": ["secondary", "hdd", "1 tb"],
    "Cabinet LTR": ["cabinet", "chassis"], "SMPS WATT": ["smps"], "MONITOR": ["monitor", "inch"],
    "SPEAKER": ["speaker"], "WIRELESS + BLUETOOTH": ["wifi", "wireless", "bluetooth"],
    "MS OFFICE": ["ms office"], "CHASSIS SWITCH": ["chassis intrusion"], "TPM 2.0": ["tpm"],
    "CAMERA": ["camera"], "ANTIVIRUS": ["antivirus"], "DP PORT": ["display port"],
    "SERIAL COM PORT+PARALLEL": ["serial", "com port"], "Keyboard & Mouse": ["keyboard", "mouse"]
}

DEPTS = ["BANK OF INDIA","SBI","BANK OF BARODA","INDIAN ARMY","INDIAN AIR FORCE","MINISTRY OF DEFENCE","MINISTRY OF FINANCE","MINISTRY OF HOME AFFAIRS","MINISTRY OF EDUCATION","MINISTRY OF RAILWAYS","MINISTRY OF ELECTRONICS & IT","NITI AAYOG","ISRO","NIC"]
ITEMS = ["Desktop Computer","All in One PC","All in One PC - High End","High End Desktop Computer","Entry Level Desktop Computer","Mid Level Desktop Computer","Entry and Mid Level Desktop Computer","Laptop - Notebook"]

def read_pdf(f):
    r = PdfReader(f)
    return "\n".join([p.extract_text() or "" for p in r.pages])

def detect(text):
    low=text.lower()
    return [prod for prod, kws in KEYWORDS.items() if any(k in low for k in kws)]

def meta(text):
    org=""; m=re.search(r'Organisation\s*Name\s*[:\-]?\s*(.+?)\n',text,re.I)
    if m: org=m.group(1).strip()[:80]
    bid=""; m=re.search(r'GEM\/\d{4}\/B\/\d{4,8}',text.replace(" ","").upper())
    if m: bid=m.group(0)
    qty=65; m=re.search(r'Quantity\s*[:\-]?\s*(\d+)',text,re.I)
    if m: qty=int(m.group(1))
    item="Desktop Computer"; m=re.search(r'Item\s*Category\s*[:\-]?\s*(.+?)\n',text,re.I)
    if m: item=m.group(1).strip()[:80]
    return org,item,bid,qty

# HEADER WITH CLEAR
st.markdown(f"""
<div class="main-header">
<div><div class="logo-text">🇮🇳 GeM ATC Studio</div><div class="sub-text">Designed for ATC-Only Pricing • Current Market Price Sep 2026</div></div>
<div class="sub-text">Clean Design V1</div>
</div>
""", unsafe_allow_html=True)

c_head1, c_head2, c_head3 = st.columns([3,1,1])
with c_head3:
    if st.button("🗑️ Clear All", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
with c_head2:
    if st.button("💹 Set Market Price", use_container_width=True):
        for k,v in MARKET.items():
            st.session_state[f"pr_{k}"]=v
        st.rerun()

# STEP 1 - UPLOAD
with st.container():
    st.markdown('<div class="step-card">', unsafe_allow_html=True)
    st.markdown("### Step 1 • Upload ATC Document")
    pdf = st.file_uploader("Drag & Drop ATC PDF here", type=["pdf"], label_visibility="collapsed")
    if pdf:
        txt = read_pdf(pdf)
        detected = detect(txt)
        org_v,item_v,bid_v,qty_v = meta(txt)
        if not detected: detected = list(KEYWORDS.keys())
    else:
        txt=""; detected=[]; org_v,item_v,bid_v,qty_v="","","",65
    st.markdown('</div>', unsafe_allow_html=True)

# STEP 2 - META
with st.container():
    st.markdown('<div class="step-card">', unsafe_allow_html=True)
    st.markdown("### Step 2 • Bid Details")
    col1,col2,col3,col4 = st.columns(4)
    with col1: dept = st.selectbox("Department", DEPTS, key="dept")
    with col2: org = st.text_input("Organisation", value=org_v, key="org")
    with col3: bid = st.text_input("Bid No", value=bid_v, key="bid")
    with col4: qty = st.number_input("Quantity", 1, 5000, qty_v, key="qty")
    c1,c2 = st.columns([2,1])
    with c1:
        try: idx = next((i for i,o in enumerate(ITEMS) if o.lower() in item_v.lower()),0)
        except: idx=0
        item = st.selectbox("Item Category", ITEMS, index=idx, key="item")
    with c2:
        margin = st.number_input("Margin per PC (₹)", value=st.session_state.get("margin",4000), step=500, key="margin")

    if detected:
        st.markdown("**ATC Detected Products:**")
        chips = "".join([f'<span class="atc-chip">✅ {p}</span>' for p in detected])
        st.markdown(chips, unsafe_allow_html=True)
    else:
        st.info("Upload ATC to auto-detect products")
    st.markdown('</div>', unsafe_allow_html=True)

# STEP 3 - PRICING - ONLY ATC PRODUCTS
st.markdown('<div class="step-card">', unsafe_allow_html=True)
st.markdown(f"### Step 3 • Pricing — Only {len(detected) if detected else 0} Products from ATC")
st.caption("Only products mentioned in ATC are shown for pricing")

products = detected if detected else []
if products:
    for p in products:
        if f"pr_{p}" not in st.session_state:
            st.session_state[f"pr_{p}"] = MARKET.get(p,0)

    prices={}; total=0
    cols = st.columns(3)
    for i, comp in enumerate(products):
        with cols[i%3]:
            st.markdown('<div class="product-card">', unsafe_allow_html=True)
            st.markdown(f"**{comp}** <span class='market-tag'>Market ₹{MARKET.get(comp,0):,}</span>", unsafe_allow_html=True)
            val = st.number_input(comp, value=st.session_state[f"pr_{comp}"], key=f"pr_{comp}", label_visibility="collapsed")
            prices[comp]=val
            total+=val
            st.markdown('</div>', unsafe_allow_html=True)
            st.write("")

    gst = int((total+margin)*0.18)
    grand = total+margin+gst
    total_bid = grand*qty

    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Base", f"₹{total:,}")
    m2.metric("Margin", f"₹{margin:,}")
    m3.metric("GST", f"₹{gst:,}")
    m4.metric("Grand / PC", f"₹{grand:,}")

    st.markdown(f"""
    <div style="background:#0F172A; color:white; padding:18px; border-radius:12px; text-align:center; margin-top:15px;">
    <h3 style="margin:0; color:white;">Total Bid Value: ₹{total_bid:,} • {qty} Units</h3>
    <p style="margin:5px 0 0 0; opacity:0.7; font-size:13px;">{dept} | {bid} | {item}</p>
    </div>
    """, unsafe_allow_html=True)

    df = pd.DataFrame(
        [["Department",dept],["Organisation",org],["Bid",bid],["Item",item],["Qty",qty],["ATC Products",", ".join(products)]]+
        list(prices.items())+[["Base",total],["Margin",margin],["GST",gst],["Grand",grand],["Total Bid",total_bid]],
        columns=["Field","Value"]
    )
    st.dataframe(df, use_container_width=True)
    st.download_button("📥 Download CSV", df.to_csv(index=False).encode(), f"{bid}_{dept}.csv", use_container_width=True)
else:
    st.warning("No ATC uploaded — Upload PDF to start pricing")
st.markdown('</div>', unsafe_allow_html=True)