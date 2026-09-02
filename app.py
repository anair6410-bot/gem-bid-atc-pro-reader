import streamlit as st
import pandas as pd
import re
try:
    from pypdf import PdfReader
except:
    from PyPDF2 import PdfReader

st.set_page_config(page_title="GeM Exact Tracker", layout="wide", page_icon="🇮🇳")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800&display=swap');
* { font-family: 'Outfit', sans-serif; }
.stApp { background: #F8FAFF; }
.hero { background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); border-radius: 18px; padding: 20px 24px; color: white; display:flex; justify-content:space-between; box-shadow: 0 15px 30px rgba(0,0,0,0.2); }
.tricolor { height:4px; background: linear-gradient(90deg, #FF9933 0%, #FFF 50%, #138808 100%); border-radius:10px; margin:12px 0; }
.glass-card { background: white; border-radius: 16px; padding: 20px; border: 1px solid #E2E8F0; box-shadow: 0 4px 20px rgba(0,0,0,0.05); margin-bottom:14px; }
.upload-card { background: #F8FAFC; border: 1.5px dashed #CBD5E1; border-radius: 14px; padding: 16px; text-align:center; }
.upload-card:hover { border-color: #6366F1; background: #F0F4FF; }
.prod-card { background:white; border-radius:12px; padding:12px; border:1px solid #E2E8F0; border-left:4px solid #10B981; }
.raw-box { background:#0F172A; color:#E2E8F0; padding:12px; border-radius:10px; font-size:12px; max-height:200px; overflow:auto; white-space:pre-wrap; }
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
DEPTS = ["BANK OF INDIA","SBI","BANK OF BARODA","INDIAN ARMY","MINISTRY OF DEFENCE","MINISTRY OF FINANCE","MINISTRY OF HOME AFFAIRS","MINISTRY OF EDUCATION","MINISTRY OF RAILWAYS","MINISTRY OF ELECTRONICS & IT","NITI AAYOG","ISRO","NIC","OTHER"]

def read_pdf_exact(file):
    """Read PDF with all pages - exact text"""
    try:
        reader = PdfReader(file)
        full_text = ""
        for i, page in enumerate(reader.pages):
            txt = page.extract_text() or ""
            full_text += f"\n--- PAGE {i+1} ---\n" + txt
        return full_text
    except Exception as e:
        return f"Error reading PDF: {e}"

def read_excel_exact(file):
    """Read Excel/CSV sheet exact"""
    try:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        return df
    except Exception as e:
        return None

def parse_exact_bid_data(text):
    """
    EXACT parser - Tries 10+ patterns for each field
    """
    # Normalize text for searching but keep original for extraction
    text_upper = text.upper()
    text_clean = text.replace("\n", " ").replace(" ", " ")

    results = {"org": "", "bid_no": "", "qty": 65, "item": "", "dept": "", "ministry": "", "raw_matches": []}

    # 1. BID NUMBER - Multiple patterns
    bid_patterns = [
        r'GEM\/\d{4}\/B\/\d{4,10}',
        r'GEM\s*\/\s*\d{4}\s*\/\s*B\s*\/\s*\d+',
        r'Bid\s*Number\s*[:\-]?\s*(GEM\/\d{4}\/B\/\d+)',
        r'Bid\s*No\.?\s*[:\-]?\s*(GEM\/\d{4}\/B\/\d+)',
        r'Bid\s*Number\s*[:\-]?\s*([A-Z]+\/\d+\/B\/\d+)',
    ]
    for pat in bid_patterns:
        m = re.search(pat, text_upper)
        if m:
            results["bid_no"] = m.group(1) if len(m.groups())>0 else m.group(0)
            results["raw_matches"].append(f"Bid: {m.group(0)}")
            break

    # 2. ORGANISATION - Multiple patterns
    org_patterns = [
        r'Organisation\s*Name\s*[:\-]?\s*([^\n]+)',
        r'Organization\s*Name\s*[:\-]?\s*([^\n]+)',
        r'Buyer\s*[:\-]?\s*([^\n]+?Ministry[^\n]+)',
        r'Organisation\s*Details\s*[:\-]?\s*([^\n]+)',
        r'Name\s*of\s*Organisation\s*[:\-]?\s*([^\n]+)',
        r'Buyer\s*Organisation\s*[:\-]?\s*([^\n]+)',
    ]
    for pat in org_patterns:
        m = re.search(pat, text, re.I)
        if m:
            val = m.group(1).strip()
            if len(val) > 5 and len(val) < 150:
                results["org"] = val
                results["raw_matches"].append(f"Org: {val}")
                break

    # 3. QUANTITY - Multiple patterns
    qty_patterns = [
        r'Quantity\s*[:\-]?\s*(\d{1,5})',
        r'Qty\s*[:\-]?\s*(\d{1,5})',
        r'Total\s*Quantity\s*[:\-]?\s*(\d+)',
        r'Required\s*Quantity\s*[:\-]?\s*(\d+)',
        r'Item\s*Quantity\s*[:\-]?\s*(\d+)',
    ]
    for pat in qty_patterns:
        m = re.search(pat, text, re.I)
        if m:
            try:
                q = int(m.group(1))
                if 1 <= q <= 10000:
                    results["qty"] = q
                    results["raw_matches"].append(f"Qty: {q}")
                    break
            except: pass

    # 4. ITEM CATEGORY - Multiple patterns
    item_patterns = [
        r'Item\s*Category\s*[:\-]?\s*([^\n]+)',
        r'Category\s*[:\-]?\s*(Desktop[^\n]+|All in One[^\n]+|Laptop[^\n]+)',
        r'Product\s*Category\s*[:\-]?\s*([^\n]+)',
        r'Item\s*Name\s*[:\-]?\s*([^\n]+)',
        r'Schedule\s*1\s*[:\-]?\s*([^\n]+Computer[^\n]*)',
    ]
    for pat in item_patterns:
        m = re.search(pat, text, re.I)
        if m:
            val = m.group(1).strip()
            if len(val) > 3 and len(val) < 120:
                results["item"] = val
                results["raw_matches"].append(f"Item: {val}")
                break

    # 5. DEPARTMENT / MINISTRY
    dept_patterns = [
        r'Ministry\s*[:\-]?\s*([^\n]+)',
        r'Department\s*Name\s*[:\-]?\s*([^\n]+)',
        r'Department\s*[:\-]?\s*([^\n]+)',
        r'Ministry\s*\/\s*Department\s*[:\-]?\s*([^\n]+)',
        r'Name\s*of\s*Ministry\s*[:\-]?\s*([^\n]+)',
    ]
    for pat in dept_patterns:
        m = re.search(pat, text, re.I)
        if m:
            val = m.group(1).strip()
            if len(val) > 3 and len(val) < 150:
                results["dept"] = val
                results["raw_matches"].append(f"Dept: {val}")
                break

    return results

def detect_products(text):
    low=text.lower()
    return [p for p,kws in KEYWORDS.items() if any(k in low for k in kws)]

# HERO
st.markdown('<div class="hero"><div><div style="font-size:22px; font-weight:800;">🇮🇳 GeM Exact Data Tracker</div><div style="font-size:12px; opacity:0.7;">Fixed Parser • Reads EXACT data from PDF & Excel Sheet</div></div><div style="font-size:11px; opacity:0.6;">V4 - Exact</div></div><div class="tricolor"></div>', unsafe_allow_html=True)

top1,top2,top3 = st.columns([4,1,1])
with top2:
    if st.button("💹 Market Price", use_container_width=True):
        for k,v in MARKET.items(): st.session_state[f"pr_{k}"]=v
        st.rerun()
with top3:
    if st.button("🗑️ Clear", use_container_width=True, type="primary"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

# DUAL UPLOAD WITH EXCEL SUPPORT
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown("#### 📂 Upload — Now Supports PDF + Excel Sheet")

u1,u2 = st.columns(2)
with u1:
    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    st.markdown("**📄 ATC Document (PDF)**")
    atc_file = st.file_uploader("ATC PDF", type=["pdf"], key="atc", label_visibility="collapsed")
    if atc_file:
        st.success(f"Loaded: {atc_file.name}")
        atc_text = read_pdf_exact(atc_file)
        atc_products = detect_products(atc_text)
        atc_meta = parse_exact_bid_data(atc_text)
    else:
        atc_text=""; atc_products=[]; atc_meta={"org":"","item":"","bid_no":"","qty":65,"dept":"","raw_matches":[]}
    st.markdown('</div>', unsafe_allow_html=True)

with u2:
    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    st.markdown("**📑 Bid Document (PDF / Excel / CSV)**")
    st.caption("Supports:.pdf,.xlsx,.xls,.csv")
    bid_file = st.file_uploader("Bid Doc", type=["pdf","xlsx","xls","csv"], key="bid", label_visibility="collapsed")
    bid_df=None; bid_text=""; bid_meta={"org":"","item":"","bid_no":"","qty":65,"dept":"","raw_matches":[]}; bid_products=[]
    if bid_file:
        st.success(f"Loaded: {bid_file.name}")
        if bid_file.name.endswith(('.xlsx','.xls','.csv')):
            bid_df = read_excel_exact(bid_file)
            if isinstance(bid_df, pd.DataFrame):
                # Try to find columns with exact data
                bid_text = " ".join([str(c) + " " + " ".join(bid_df[c].astype(str).tolist()[:10]) for c in bid_df.columns])
                # Exact column mapping
                for col in bid_df.columns:
                    col_low = str(col).lower()
                    if 'organisation' in col_low or 'organization' in col_low or 'buyer' in col_low:
                        if len(bid_df[col].dropna())>0:
                            bid_meta["org"] = str(bid_df[col].dropna().iloc[0])[:100]
                    if 'bid' in col_low and 'number' in col_low:
                        if len(bid_df[col].dropna())>0:
                            bid_meta["bid_no"] = str(bid_df[col].dropna().iloc[0])
                    if 'quantity' in col_low or 'qty' in col_low:
                        try: bid_meta["qty"] = int(bid_df[col].dropna().iloc[0])
                        except: pass
                    if 'item' in col_low or 'category' in col_low:
                        if len(bid_df[col].dropna())>0:
                            bid_meta["item"] = str(bid_df[col].dropna().iloc[0])[:100]
                    if 'department' in col_low or 'ministry' in col_low:
                        if len(bid_df[col].dropna())>0:
                            bid_meta["dept"] = str(bid_df[col].dropna().iloc[0])[:100]
        else:
            bid_text = read_pdf_exact(bid_file)
            bid_meta = parse_exact_bid_data(bid_text)
            bid_products = detect_products(bid_text)
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# COMBINE EXACT DATA - Bid has priority
final_org = bid_meta.get("org") or atc_meta.get("org") or ""
final_bid = bid_meta.get("bid_no") or atc_meta.get("org") or "" # fix
final_bid = bid_meta.get("bid_no") or atc_meta.get("bid_no") or ""
final_qty = bid_meta.get("qty") if bid_meta.get("qty")!=65 else atc_meta.get("qty",65)
final_item = bid_meta.get("item") or atc_meta.get("item") or "Desktop Computer"
final_dept = bid_meta.get("dept") or atc_meta.get("dept") or ""
detected = atc_products if atc_products else bid_products

# SHOW WHAT WE EXTRACTED EXACTLY - DEBUG VIEW
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown("##### 🔍 Exact Data Extracted From Your Sheet")

d1,d2 = st.columns(2)
with d1:
    st.markdown("**From ATC PDF:**")
    if atc_file:
        st.write(f"Org: {atc_meta.get('org') or 'Not found'}")
        st.write(f"Bid: {atc_meta.get('bid_no') or 'Not found'}")
        st.write(f"Qty: {atc_meta.get('qty')}")
        st.write(f"Item: {atc_meta.get('item') or 'Not found'}")
        st.write(f"Dept: {atc_meta.get('dept') or 'Not found'}")
        with st.expander("See raw extracted text (ATC)"):
            st.markdown(f'<div class="raw-box">{atc_text[:4000]}</div>', unsafe_allow_html=True)
    else:
        st.info("Upload ATC")

with d2:
    st.markdown("**From Bid Document (Exact Sheet Data):**")
    if bid_file:
        if bid_df is not None and isinstance(bid_df, pd.DataFrame):
            st.write("**Excel Data Preview:**")
            st.dataframe(bid_df.head(), use_container_width=True)
            st.write(f"Org: {bid_meta.get('org') or 'Not found in sheet'}")
            st.write(f"Bid: {bid_meta.get('bid_no') or 'Not found'}")
            st.write(f"Qty: {bid_meta.get('qty')}")
            st.write(f"Item: {bid_meta.get('item') or 'Not found'}")
            st.write(f"Dept: {bid_meta.get('dept') or 'Not found'}")
        else:
            st.write(f"Org: {bid_meta.get('org') or 'Not found'}")
            st.write(f"Bid: {bid_meta.get('bid_no') or 'Not found'}")
            st.write(f"Qty: {bid_meta.get('qty')}")
            st.write(f"Item: {bid_meta.get('item') or 'Not found'}")
            st.write(f"Dept: {bid_meta.get('dept') or 'Not found'}")
            st.caption("Matches found:")
            for m in bid_meta.get("raw_matches",[])[:10]:
                st.code(m)
            with st.expander("See raw extracted text (Bid)"):
                st.markdown(f'<div class="raw-box">{bid_text[:5000]}</div>', unsafe_allow_html=True)
    else:
        st.info("Upload Bid PDF/Excel")
st.markdown('</div>', unsafe_allow_html=True)

# FINAL EDITABLE FIELDS - Auto-filled with EXACT data
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown("##### ✅ Final Data (Auto-filled from Exact Sheet - You can edit)")

c1,c2,c3,c4 = st.columns(4)
with c1:
    dept_options = DEPTS
    # Try to match exact dept
    try:
        idx = next((i for i,o in enumerate(dept_options) if final_dept and (final_dept.lower() in o.lower() or o.lower() in final_dept.lower())),0)
    except: idx=0
    dept = st.selectbox("Department (Exact from sheet)", dept_options, index=idx, key="dept_exact")
    if final_dept and final_dept not in dept_options:
        st.caption(f"Exact from sheet: {final_dept}")
        dept = st.text_input("Exact Dept from sheet", value=final_dept, key="dept_manual_exact")
with c2:
    org = st.text_input("Organisation (Exact from sheet)", value=final_org, key="org_exact")
with c3:
    bid_no = st.text_input("Bid Number (Exact)", value=final_bid, key="bid_exact")
with c4:
    qty = st.number_input("Quantity (Exact)", 1, 10000, final_qty, key="qty_exact")

ca,cb = st.columns([3,1])
with ca:
    try: i_idx = next((i for i,o in enumerate(["Desktop Computer","All in One PC","All in One PC - High End","High End Desktop Computer","Entry Level Desktop Computer","Mid Level Desktop Computer","Entry and Mid Level Desktop Computer","Laptop - Notebook"]) if final_item and (final_item.lower() in o.lower() or o.lower() in final_item.lower())),0)
    except: i_idx=0
    item_cat = st.selectbox("Item Category (Exact from sheet)", ["Desktop Computer","All in One PC","All in One PC - High End","High End Desktop Computer","Entry Level Desktop Computer","Mid Level Desktop Computer","Entry and Mid Level Desktop Computer","Laptop - Notebook"], index=i_idx, key="item_exact")
    if final_item:
        st.caption(f"Exact from sheet: {final_item[:80]}")
        if final_item not in ["Desktop Computer","All in One PC","All in One PC - High End","High End Desktop Computer","Entry Level Desktop Computer","Mid Level Desktop Computer","Entry and Mid Level Desktop Computer","Laptop - Notebook"]:
            item_cat = st.text_input("Exact Item from sheet", value=final_item, key="item_manual_exact")
with cb:
    margin = st.number_input("Margin ₹", value=st.session_state.get("margin",4000), step=500, key="margin_exact")
st.markdown('</div>', unsafe_allow_html=True)

# PRICING
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown(f"##### 💰 Pricing - {len(detected)} Products from ATC")
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
    gst=int((total+margin)*0.18); grand=total+margin+gst; total_bid_val=grand*qty
    m1,m2,m3,m4=st.columns(4)
    m1.metric("Base", f"₹{total:,}"); m2.metric("Margin", f"₹{margin:,}"); m3.metric("GST", f"₹{gst:,}"); m4.metric("Grand/PC", f"₹{grand:,}")
    st.markdown(f'<div style="background:#0F172A; color:white; padding:14px; border-radius:12px; text-align:center;"><b>Total Bid: ₹{total_bid_val:,} for {qty} Units | {dept} | {bid_no}</b></div>', unsafe_allow_html=True)
    df = pd.DataFrame([["Department",dept],["Organisation",org],["Bid No",bid_no],["Item",item_cat],["Qty",qty],["Products",", ".join(detected)]]+list(prices.items())+[["Base",total],["Margin",margin],["GST",gst],["Grand",grand],["Total",total_bid_val]], columns=["Field","Value"])
    st.dataframe(df, use_container_width=True)
    st.download_button("📥 Download Exact Report", df.to_csv(index=False).encode(), f"EXACT_{bid_no}.csv", use_container_width=True)
else:
    st.warning("Upload ATC to get products")
st.markdown('</div>', unsafe_allow_html=True)