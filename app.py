import streamlit as st
import pandas as pd
import re
try:
    from pypdf import PdfReader
except:
    from PyPDF2 import PdfReader

st.set_page_config(page_title="GeM ATC + Bid Tracker", layout="wide", page_icon="🇮🇳")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
* { font-family: 'Inter', sans-serif; }
.stApp { background: #F8FAFC; }
.main-header { background: white; padding: 20px 25px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); border: 1px solid #E2E8F0; margin-bottom: 18px; display:flex; justify-content:space-between; align-items:center; }
.logo-text { font-size: 23px; font-weight: 800; color: #0F172A; }
.step-card { background: white; border-radius: 16px; padding: 22px; box-shadow: 0 4px 20px rgba(0,0,0,0.05); border: 1px solid #E2E8F0; margin-bottom: 18px; }
.upload-box { background: #F8FAFC; border: 2px dashed #CBD5E1; border-radius: 12px; padding: 15px; text-align:center; }
.product-card { background: white; border-radius: 12px; padding: 14px; border: 1px solid #E2E8F0; border-left: 4px solid #10B981; }
.market-tag { background: #ECFDF5; color: #065F46; font-size: 11px; padding: 3px 8px; border-radius: 20px; font-weight: 600; }
.atc-chip { background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin: 3px; display:inline-block; }
.bid-chip { background: #FEF3C7; color: #92400E; border: 1px solid #FCD34D; padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin: 3px; display:inline-block; }
div[data-testid="stMetric"] { background: white; border-radius: 14px; padding: 16px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 1px solid #E2E8F0; }
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

DEPTS = ["BANK OF INDIA","SBI","BANK OF BARODA","INDIAN ARMY","INDIAN AIR FORCE","MINISTRY OF DEFENCE","MINISTRY OF FINANCE","MINISTRY OF HOME AFFAIRS","MINISTRY OF EDUCATION","MINISTRY OF RAILWAYS","MINISTRY OF ELECTRONICS & IT","NITI AAYOG","ISRO","NIC"]
ITEMS = ["Desktop Computer","All in One PC","All in One PC - High End","High End Desktop Computer","Entry Level Desktop Computer","Mid Level Desktop Computer","Entry and Mid Level Desktop Computer","Laptop - Notebook"]

def read_pdf(f):
    r = PdfReader(f)
    return "\n".join([p.extract_text() or "" for p in r.pages])

def detect(text):
    low=text.lower()
    return [prod for prod, kws in KEYWORDS.items() if any(k in low for k in kws)]

def parse_bid_meta(text):
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

# HEADER
st.markdown("""
<div class="main-header">
<div><div class="logo-text">🇮🇳 GeM Dual Document Tracker</div><div style="color:#64748B; font-size:13px;">ATC + Bid Document Tracking • Only ATC Products Priced</div></div>
<div style="color:#64748B; font-size:12px;">Market Price Sep 2026</div>
</div>
""", unsafe_allow_html=True)

top1,top2,top3 = st.columns([3,1,1])
with top3:
    if st.button("🗑️ Clear All", use_container_width=True, type="primary"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
with top2:
    if st.button("💹 Set Market Price", use_container_width=True):
        for k,v in MARKET.items():
            st.session_state[f"pr_{k}"]=v
        st.rerun()

# DUAL UPLOAD SECTION
st.markdown('<div class="step-card">', unsafe_allow_html=True)
st.markdown("### 📂 Step 1 • Upload Documents — ATC + Bid (Dual Tracker)")

u1,u2 = st.columns(2)
with u1:
    st.markdown('<div class="upload-box">', unsafe_allow_html=True)
    st.markdown("**📄 Upload ATC Document**")
    st.caption("Product specs, processor, RAM, SSD etc.")
    atc_file = st.file_uploader("ATC PDF", type=["pdf"], key="atc_up", label_visibility="collapsed")
    if atc_file:
        st.success(f"✅ ATC Loaded: {atc_file.name}")
    st.markdown('</div>', unsafe_allow_html=True)

with u2:
    st.markdown('<div class="upload-box">', unsafe_allow_html=True)
    st.markdown("**📑 Upload Bid Document**")
    st.caption("Organisation, Bid No, Qty, Item Category")
    bid_file = st.file_uploader("Bid PDF", type=["pdf"], key="bid_up", label_visibility="collapsed")
    if bid_file:
        st.success(f"✅ Bid Loaded: {bid_file.name}")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# PROCESS DOCUMENTS
atc_text=""; bid_text=""; detected=[]; org_v=""; item_v=""; bid_v=""; qty_v=65; dept_v=""; bid_meta_found=False; atc_meta_found=False

if atc_file:
    atc_text = read_pdf(atc_file)
    detected = detect(atc_text)
    org_v1,item_v1,bid_v1,qty_v1,dept_v1 = parse_bid_meta(atc_text)
    if detected: atc_meta_found=True

if bid_file:
    bid_text = read_pdf(bid_file)
    org_v2,item_v2,bid_v2,qty_v2,dept_v2 = parse_bid_meta(bid_text)
    bid_meta_found=True
    # Merge: Bid doc has priority for Organisation/Bid details
    org_v = org_v2 or org_v1 if atc_file else org_v2
    item_v = item_v2 or item_v1 if atc_file else item_v2
    bid_v = bid_v2 or bid_v1 if atc_file else bid_v2
    qty_v = qty_v2 or qty_v1 if atc_file else qty_v2
    dept_v = dept_v2 or dept_v1 if atc_file else dept_v2
    # Also detect products from bid if ATC not uploaded
    if not detected:
        detected = detect(bid_text)
else:
    if atc_file:
        org_v,item_v,bid_v,qty_v,dept_v = parse_bid_meta(atc_text)

# TRACKING STATUS
st.markdown('<div class="step-card">', unsafe_allow_html=True)
st.markdown("### 🔍 Document Tracking Status")

t1,t2,t3 = st.columns(3)
with t1:
    st.markdown("**ATC Document**")
    if atc_file:
        st.markdown(f'<span class="atc-chip">✅ {len(detected)} Products Found</span>', unsafe_allow_html=True)
        st.markdown(f'<span class="atc-chip">📄 {atc_file.name[:25]}</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="atc-chip">❌ Not Uploaded</span>', unsafe_allow_html=True)

with t2:
    st.markdown("**Bid Document**")
    if bid_file:
        st.markdown(f'<span class="bid-chip">✅ Organisation Found</span>' if org_v else '<span class="bid-chip">⚠️ Organisation Not Found</span>', unsafe_allow_html=True)
        st.markdown(f'<span class="bid-chip">✅ Bid: {bid_v[:20] if bid_v else "Not Found"}</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="bid-chip">❌ Not Uploaded</span>', unsafe_allow_html=True)

with t3:
    st.markdown("**Combined**")
    if atc_file and bid_file:
        st.success("Both docs tracked — Full auto-fill")
    elif atc_file or bid_file:
        st.warning("One doc uploaded — Partial tracking")
    else:
        st.info("Upload both for full tracking")

if detected:
    st.markdown("**ATC Products Tracked:**")
    st.markdown("".join([f'<span class="atc-chip">✅ {p}</span>' for p in detected]), unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# STEP 2 - DETAILS
st.markdown('<div class="step-card">', unsafe_allow_html=True)
st.markdown("### Step 2 • Bid Details (Auto-filled from Bid Document)")

c1,c2,c3,c4 = st.columns(4)
with c1:
    try: d_idx = next((i for i,o in enumerate(DEPTS) if dept_v and dept_v.lower() in o.lower() or o.lower() in dept_v.lower()),0)
    except: d_idx=0
    dept = st.selectbox("Department", DEPTS, index=d_idx, key="dept")
    st.caption(f"Tracked from Bid: {dept_v}" if dept_v else "From Bid doc")
with c2: org = st.text_input("Organisation", value=org_v, key="org")
with c3: bid_no = st.text_input("Bid Number", value=bid_v, key="bidno")
with c4: qty = st.number_input("Quantity", 1, 5000, qty_v, key="qty")

col_a,col_b = st.columns([3,1])
with col_a:
    try: i_idx = next((i for i,o in enumerate(ITEMS) if item_v and o.lower() in item_v.lower() or item_v.lower() in o.lower()),0)
    except: i_idx=0
    item_cat = st.selectbox("Item Category", ITEMS, index=i_idx, key="itemcat")
    st.caption(f"Tracked from Bid: {item_v[:50]}" if item_v else "")
with col_b:
    margin = st.number_input("Margin per PC ₹", value=st.session_state.get("margin",4000), step=500, key="margin")
st.markdown('</div>', unsafe_allow_html=True)

# STEP 3 - PRICING ONLY ATC
st.markdown('<div class="step-card">', unsafe_allow_html=True)
st.markdown(f"### Step 3 • Pricing — Only {len(detected)} Products from ATC Document")

if detected:
    for p in detected:
        if f"pr_{p}" not in st.session_state:
            st.session_state[f"pr_{p}"] = MARKET.get(p,0)

    prices={}; total=0
    cols=st.columns(3)
    for i, comp in enumerate(detected):
        with cols[i%3]:
            st.markdown('<div class="product-card">', unsafe_allow_html=True)
            st.markdown(f"**{comp}** <span class='market-tag'>₹{MARKET.get(comp,0):,}</span>", unsafe_allow_html=True)
            v = st.number_input(comp, value=st.session_state[f"pr_{comp}"], key=f"pr_{comp}", label_visibility="collapsed")
            prices[comp]=v; total+=v
            st.markdown('</div>', unsafe_allow_html=True)
            st.write("")

    gst = int((total+margin)*0.18)
    grand = total+margin+gst
    total_bid_val = grand*qty

    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Base", f"₹{total:,}")
    m2.metric("Margin", f"₹{margin:,}")
    m3.metric("GST 18%", f"₹{gst:,}")
    m4.metric("Grand / PC", f"₹{grand:,}")

    st.markdown(f"""
    <div style="background:#0F172A; color:white; padding:16px; border-radius:12px; text-align:center;">
    <b>Total: ₹{total_bid_val:,} for {qty} Units | {dept} | {bid_no}</b>
    </div>
    """, unsafe_allow_html=True)

    df = pd.DataFrame(
        [["Department",dept],["Organisation",org],["Bid No",bid_no],["Item",item_cat],["Qty",qty],
         ["ATC File", atc_file.name if atc_file else "Not Uploaded"],["Bid File", bid_file.name if bid_file else "Not Uploaded"],
         ["ATC Products",", ".join(detected)]]+list(prices.items())+[["Base",total],["Margin",margin],["GST",gst],["Grand",grand],["Total Bid",total_bid_val]],
        columns=["Field","Value"]
    )
    st.dataframe(df, use_container_width=True)
    st.download_button("📥 Download Tracked CSV", df.to_csv(index=False).encode(), f"TRACKED_{bid_no}.csv", use_container_width=True)
else:
    st.warning("Upload ATC document to track products for pricing")

st.markdown('</div>', unsafe_allow_html=True)