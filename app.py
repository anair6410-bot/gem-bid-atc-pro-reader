import streamlit as st
import pandas as pd
import re
try:
    from pypdf import PdfReader
except:
    from PyPDF2 import PdfReader

st.set_page_config(page_title="GeM Full Bid Auto-Fill", layout="wide", page_icon="🇮🇳")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800&display=swap');
* { font-family: 'Outfit', sans-serif; }
.stApp { background: #F8FAFF; }
.hero { background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); border-radius: 18px; padding: 18px 24px; color: white; display:flex; justify-content:space-between; }
.tricolor { height:4px; background: linear-gradient(90deg, #FF9933 0%, #FFF 50%, #138808 100%); border-radius:10px; margin:10px 0; }
.glass-card { background: white; border-radius: 16px; padding: 18px; border: 1px solid #E2E8F0; box-shadow: 0 4px 20px rgba(0,0,0,0.05); margin-bottom:14px; }
.upload-card { background: #F8FAFC; border: 1.5px dashed #CBD5E1; border-radius: 14px; padding: 16px; text-align:center; }
.upload-card:hover { border-color: #6366F1; background: #EEF2FF; }
.autofill-badge { background:#DCFCE7; color:#166534; border:1px solid #86EFAC; padding:2px 8px; border-radius:20px; font-size:10px; font-weight:700; }
.prod-card { background:white; border-radius:12px; padding:12px; border:1px solid #E2E8F0; border-left:4px solid #10B981; }
.raw-box { background:#0F172A; color:#E2E8F0; padding:12px; border-radius:10px; font-size:11px; max-height:250px; overflow:auto; white-space:pre-wrap; }
div[data-testid="stMetric"] { background:white; border-radius:14px; border:1px solid #E2E8F0; }
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

def read_pdf_full(file):
    reader = PdfReader(file)
    full = ""
    for p in reader.pages:
        full += (p.extract_text() or "") + "\n"
    return full

def extract_exact_gem_bid(text):
    """Reads EXACT data from full GeM Bid document"""
    t = text
    tl = text.lower()
    data = {}

    # 1. BID NUMBER - GEM/2025/B/1234567 format - Most important
    m = re.search(r'GEM\/\d{4}\/B\/\d{4,10}', t.replace(" ", "").upper())
    if m:
        data['bid_no'] = m.group(0)
    else:
        m = re.search(r'Bid\s*Number\s*[:\-]?\s*(GEM\/\d{4}\/B\/\d+)', t, re.I)
        data['bid_no'] = m.group(1) if m else ""

    # 2. ORGANISATION NAME
    patterns_org = [
        r'Organisation\s*Name\s*[:\-]?\s*([^\n\r]+)',
        r'Organization\s*Details.*?Organisation\s*Name\s*[:\-]?\s*([^\n\r]+)',
        r'Buyer\s*Organization\s*[:\-]?\s*([^\n\r]+)',
        r'Name\s*of\s*the\s*Organisation\s*[:\-]?\s*([^\n\r]+)',
    ]
    data['org'] = ""
    for pat in patterns_org:
        m = re.search(pat, t, re.I | re.S)
        if m:
            val = m.group(1).strip().split('\n')[0].strip()
            if 3 < len(val) < 150 and 'bid' not in val.lower():
                data['org'] = val
                break

    # 3. DEPARTMENT / MINISTRY - EXACT
    patterns_dept = [
        r'Ministry\s*Name\s*[:\-]?\s*([^\n\r]+)',
        r'Department\s*Name\s*[:\-]?\s*([^\n\r]+)',
        r'Ministry\s*\/\s*Department\s*[:\-]?\s*([^\n\r]+)',
        r'Department\s*[:\-]?\s*(Ministry of[^\n\r]+)',
    ]
    data['dept'] = ""
    for pat in patterns_dept:
        m = re.search(pat, t, re.I)
        if m:
            val = m.group(1).strip().split('\n')[0].strip()
            if len(val) > 3:
                data['dept'] = val
                break

    # 4. ITEM CATEGORY - EXACT from Bid Details
    patterns_item = [
        r'Item\s*Category\s*[:\-]?\s*([^\n\r]+)',
        r'Category\s*[:\-]?\s*(Desktop Computer[^\n]*|All in One[^\n]*|Laptop[^\n]*|High End[^\n]*|Entry Level[^\n]*)',
        r'Schedule\s*1\s*.*?([^\n]*Desktop Computer[^\n]*|[^\n]*All in One[^\n]*)',
        r'Item\s*Name\s*[:\-]?\s*([^\n\r]+Computer[^\n]*)',
    ]
    data['item'] = "Desktop Computer"
    for pat in patterns_item:
        m = re.search(pat, t, re.I)
        if m:
            val = m.group(1).strip().split('\n')[0].strip()
            if len(val) > 5 and len(val) < 150:
                data['item'] = val
                break

    # 5. QUANTITY - EXACT
    m = re.search(r'Quantity\s*[:\-]?\s*(\d+)\s*(?:pieces|nos|units)?', t, re.I)
    data['qty'] = int(m.group(1)) if m else 65
    # Try to get from table: Look for Qty in bid table
    if data['qty'] == 65:
        m = re.search(r'Consignee.*?Quantity\s*[:\-]?\s*(\d+)', t, re.I | re.S)
        if m:
            try: data['qty'] = int(m.group(1))
            except: pass

    # 6. CONSIGNEE / LOCATION
    m = re.search(r'Consignee.*?([A-Z][a-z]+,\s*[A-Z][a-z]+|Pincode\s*[:\-]?\s*\d+)', t, re.I | re.S)
    data['consignee'] = m.group(0)[:100] if m else ""

    # 7. EMD / BID VALUE / PAST EXPERIENCE if needed
    m = re.search(r'Bid\s*Value\s*[:\-]?\s*Rs?\.?\s*([\d,]+)', t, re.I)
    data['bid_value'] = m.group(1) if m else ""

    return data

def detect_products(text):
    low=text.lower()
    return [p for p,kws in KEYWORDS.items() if any(k in low for k in kws)]

# HEADER
st.markdown('<div class="hero"><div><div style="font-size:21px; font-weight:800;">🇮🇳 GeM Full Document Auto-Fill Engine</div><div style="font-size:12px; opacity:0.7;">Upload Full Bid PDF → Exact Auto-fill in correct field • ATC Products Only</div></div><div style="font-size:11px; opacity:0.5;">V5 Exact</div></div><div class="tricolor"></div>', unsafe_allow_html=True)

c1,c2,c3 = st.columns([4,1,1])
with c2:
    if st.button("💹 Set Market Price", use_container_width=True):
        for k,v in MARKET.items(): st.session_state[f"pr_{k}"]=v
        st.rerun()
with c3:
    if st.button("🗑️ Clear All", use_container_width=True, type="primary"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

# DUAL UPLOAD
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown("#### 📂 Upload Full Documents")
u1,u2 = st.columns(2)
with u1:
    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    st.markdown("**📄 ATC Document** <span class='autofill-badge'>PRODUCTS</span>")
    st.caption("Upload ATC PDF - Will track only ATC products")
    atc_file = st.file_uploader("ATC", type=["pdf"], key="atc", label_visibility="collapsed")
    atc_text=""; atc_products=[]
    if atc_file:
        atc_text = read_pdf_full(atc_file)
        atc_products = detect_products(atc_text)
        st.success(f"✅ {len(atc_products)} products tracked from ATC")
    st.markdown('</div>', unsafe_allow_html=True)

with u2:
    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    st.markdown("**📑 FULL GeM Bid Document** <span class='autofill-badge'>AUTO-FILL</span>")
    st.caption("Upload Full Bid PDF - 50-100 pages supported")
    bid_file = st.file_uploader("Bid Full", type=["pdf"], key="bid_full", label_visibility="collapsed")
    bid_data={"bid_no":"","org":"","dept":"","item":"Desktop Computer","qty":65,"consignee":"","bid_value":""}
    bid_text=""
    if bid_file:
        bid_text = read_pdf_full(bid_file)
        bid_data = extract_exact_gem_bid(bid_text)
        st.success(f"✅ Exact data extracted: {bid_data['bid_no'] or 'Bid found'}")
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# SHOW EXACT EXTRACTION
if bid_file:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("##### 🔍 Exact Data Read From Full Bid Document — Auto-fill Preview")
    k1,k2,k3,k4 = st.columns(4)
    k1.metric("Bid No (Exact)", bid_data.get('bid_no','Not Found'), "Auto-filled")
    k2.metric("Organisation (Exact)", bid_data.get('org','')[:22] or "Not Found", "Auto-filled")
    k3.metric("Quantity (Exact)", f"{bid_data.get('qty',65)} Units", "From Table")
    k4.metric("Item Category (Exact)", bid_data.get('item','')[:22] or "Not Found", "Auto-filled")

    with st.expander("📄 See Full Raw Text Extracted (Verification)"):
        st.markdown(f'<div class="raw-box">{bid_text[:8000]}</div>', unsafe_allow_html=True)
        st.caption("If any field is wrong, you can edit below - but this is exact text from PDF")
    st.markdown('</div>', unsafe_allow_html=True)

# FINAL AUTO-FILLED FIELDS IN CORRECT PLACE
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown("##### ✅ Correct Fields — Auto-filled From Your Uploaded Documents <span class='autofill-badge'>EXACT</span>")

# Combine: Bid doc has priority for bid fields, ATC for products
final_bid_no = bid_data.get('bid_no','') if bid_file else ""
final_org = bid_data.get('org','') if bid_file else ""
final_dept_raw = bid_data.get('dept','') if bid_file else ""
final_item_raw = bid_data.get('item','Desktop Computer') if bid_file else "Desktop Computer"
final_qty_raw = bid_data.get('qty',65) if bid_file else 65

# Departments
DEPTS = ["BANK OF INDIA","SBI","BANK OF BARODA","INDIAN ARMY","INDIAN AIR FORCE","MINISTRY OF DEFENCE","MINISTRY OF FINANCE","MINISTRY OF HOME AFFAIRS","MINISTRY OF EDUCATION","MINISTRY OF RAILWAYS","MINISTRY OF ELECTRONICS & IT","NITI AAYOG","ISRO","NIC", final_dept_raw]
DEPTS = list(dict.fromkeys([d for d in DEPTS if d])) # unique
ITEMS = ["Desktop Computer","All in One PC","All in One PC - High End","High End Desktop Computer","Entry Level Desktop Computer","Mid Level Desktop Computer","Entry and Mid Level Desktop Computer","Laptop - Notebook", final_item_raw]
ITEMS = list(dict.fromkeys([d for d in ITEMS if d]))

col1,col2,col3,col4 = st.columns(4)
with col1:
    # Department - auto-fill
    try: d_idx = next((i for i,o in enumerate(DEPTS) if final_dept_raw and (final_dept_raw.lower() in o.lower() or o.lower() in final_dept_raw.lower())),0)
    except: d_idx=0
    dept_val = st.selectbox("Department (Auto-filled from Bid)", DEPTS, index=d_idx, key="dept_final")
    if final_dept_raw and final_dept_raw not in DEPTS:
        dept_val = final_dept_raw
        st.text_input("Exact Department from PDF (Auto-filled)", value=final_dept_raw, key="dept_exact_manual")

with col2:
    org_val = st.text_input("Organisation Name (Auto-filled from Bid)", value=final_org, key="org_final")
    st.caption(f"<span class='autofill-badge'>From Bid PDF: {final_org[:30] if final_org else 'Not found'}</span>", unsafe_allow_html=True)

with col3:
    bid_no_val = st.text_input("Bid Number (Auto-filled from Bid)", value=final_bid_no, key="bid_final")
    st.caption(f"<span class='autofill-badge'>Exact: {final_bid_no or 'Not found'}</span>", unsafe_allow_html=True)

with col4:
    qty_val = st.number_input("Quantity (Auto-filled from Bid Table)", min_value=1, max_value=10000, value=final_qty_raw, key="qty_final")
    st.caption(f"<span class='autofill-badge'>Exact from sheet: {final_qty_raw}</span>", unsafe_allow_html=True)

c_a,c_b = st.columns([3,1])
with c_a:
    try: i_idx = next((i for i,o in enumerate(ITEMS) if final_item_raw and (final_item_raw.lower() in o.lower() or o.lower() in final_item_raw.lower())),0)
    except: i_idx=0
    item_val = st.selectbox("Item Category (Auto-filled from Bid)", ITEMS, index=i_idx, key="item_final")
    st.caption(f"Exact from PDF: {final_item_raw[:80]}" if final_item_raw else "")
with c_b:
    margin_val = st.number_input("Margin per PC ₹", value=st.session_state.get("margin",4000), step=500, key="margin_final")

st.markdown('</div>', unsafe_allow_html=True)

# PRICING - ONLY ATC PRODUCTS
detected = atc_products if atc_products else (detect_products(bid_text) if bid_text else [])

st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown(f"##### 💰 Pricing — Only {len(detected)} Products From ATC Document")

if detected:
    for p in detected:
        if f"pr_{p}" not in st.session_state: st.session_state[f"pr_{p}"]=MARKET.get(p,0)
    prices={}; total=0
    cols=st.columns(3)
    for i,comp in enumerate(detected):
        with cols[i%3]:
            st.markdown('<div class="prod-card">', unsafe_allow_html=True)
            st.markdown(f"**{comp}** — Market ₹{MARKET.get(comp,0):,}")
            v=st.number_input(comp, value=st.session_state[f"pr_{comp}"], key=f"pr_{comp}", label_visibility="collapsed")
            prices[comp]=v; total+=v
            st.markdown('</div>', unsafe_allow_html=True)
            st.write("")
    gst=int((total+margin_val)*0.18); grand=total+margin_val+gst; total_bid=grand*qty_val
    m1,m2,m3,m4=st.columns(4)
    m1.metric("Base", f"₹{total:,}"); m2.metric("Margin", f"₹{margin_val:,}"); m3.metric("GST 18%", f"₹{gst:,}"); m4.metric("Grand / PC", f"₹{grand:,}")
    st.markdown(f'<div style="background:#0F172A; color:white; padding:14px; border-radius:12px; text-align:center;"><b>Total Bid Value: ₹{total_bid:,} for {qty_val} Units | {dept_val} | {bid_no_val}</b></div>', unsafe_allow_html=True)

    df = pd.DataFrame([
        ["Department (Auto-filled from Bid Full Doc)",dept_val],
        ["Organisation (Auto-filled)",org_val],
        ["Bid Number (Auto-filled)",bid_no_val],
        ["Item Category (Auto-filled)",item_val],
        ["Quantity (Auto-filled)",qty_val],
        ["ATC Products Count", len(detected)],
        ["ATC Products List", ", ".join(detected)]
    ]+list(prices.items())+[["Base",total],["Margin",margin_val],["GST",gst],["Grand Per PC",grand],["Total Bid Value",total_bid]], columns=["Field","Value"])
    st.dataframe(df, use_container_width=True)
    st.download_button("📥 Download Auto-filled Report CSV", df.to_csv(index=False).encode(), f"AUTO_{bid_no_val}.csv", use_container_width=True, type="primary")
else:
    st.warning("⬆️ Upload ATC PDF to get products • Upload Full Bid PDF to auto-fill Organisation, Bid No, Qty, Item")
st.markdown('</div>', unsafe_allow_html=True)