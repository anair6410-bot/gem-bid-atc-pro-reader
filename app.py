import streamlit as st
import pandas as pd
import re
try:
    from pypdf import PdfReader
except:
    from PyPDF2 import PdfReader

st.set_page_config(page_title="GeM ATC Smart Reader", layout="wide", page_icon="📄")

st.markdown("""
<style>
 .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #e4eaf5 100%); }
  h1 { background: linear-gradient(90deg, #FF9933 0%, #138808 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight:800!important; text-align:center; }
  div[data-testid="stMetric"] { background:white; padding:15px; border-radius:15px; box-shadow:0 4px 15px rgba(0,0,0,0.1); border-left:5px solid #138808; }
  div[data-testid="stContainer"] { background:white; border-radius:12px!important; box-shadow:0 2px 10px rgba(0,0,0,0.05)!important; }
 .stDownloadButton>button { background: linear-gradient(90deg, #138808, #075E54); color:white; border-radius:25px; width:100%; font-weight:bold; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1>📄 GeM ATC Reader - Only ATC Products Pricing</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center'>Upload ATC → App will show ONLY products mentioned in ATC for pricing</p>", unsafe_allow_html=True)

# ALL PRODUCTS WITH KEYWORDS TO DETECT IN ATC
PRODUCT_KEYWORDS = {
    "Processor CPU": ["processor", "cpu", "intel", "amd", "ryzen", "core i3", "core i5", "core i7", "core i9"],
    "MB": ["motherboard", "mb ", "chipset", "h610", "b660", "h670"],
    "Graphics CARD": ["graphics", "gpu", "graphic card", "nvidia", "radeon", "intel uhd", "integrated graphics"],
    "OS": ["operating system", "os", "windows 11", "windows 10", "linux", "ubuntu"],
    "RAM": ["ram", "memory", "ddr4", "ddr5", "16 gb", "8 gb", "32 gb"],
    "SSD": ["ssd", "solid state", "nvme", "512 gb ssd", "256 gb"],
    "SSD (SECONDARY)": ["secondary storage", "second ssd", "1 tb", "hdd", "hard disk"],
    "Cabinet LTR": ["cabinet", "chassis", "form factor", "tower", "sff", "micro tower"],
    "SMPS WATT": ["smps", "power supply", "watt", "180w", "240w", "300w"],
    "ADAPTER": ["adapter", "power adapter", "65w adapter", "90w"],
    "DVD WRITER": ["dvd", "optical drive", "writer", "dvd rw"],
    "MONITOR": ["monitor", "display", "screen", "inch", "23.8", "21.5", "27 inch", "fhd"],
    "SPEAKER": ["speaker", "audio", "2w speaker", "internal speaker"],
    "WIRELESS + BLUETOOTH": ["wireless", "wifi", "bluetooth", "wi-fi", "802.11", "bt 5"],
    "MS OFFICE": ["ms office", "microsoft office", "office 2021", "office 365", "libre office"],
    "CHASSIS SWITCH": ["chassis intrusion", "intrusion switch", "chassis switch"],
    "TPM 2.0": ["tpm", "trusted platform", "tpm 2.0"],
    "CAMERA": ["camera", "webcam", "web camera", "hd camera"],
    "ANTIVIRUS": ["antivirus", "security", "quick heal", "mcafee", "factory preloaded"],
    "DP PORT": ["display port", "dp port", "dp 1.2", "dp 1.4"],
    "SERIAL COM PORT+PARALLEL": ["serial port", "com port", "parallel port", "rs232"],
    "Keyboard & Mouse": ["keyboard", "mouse", "wired keyboard", "wireless keyboard"]
}

PRESET = {"Processor CPU":14500,"MB":4250,"OS":600,"RAM":17500,"SSD":3650,"SSD (SECONDARY)":11500,"Cabinet LTR":1850,"MONITOR":4450,"Keyboard & Mouse":350,"TPM 2.0":700,"CAMERA":500,"SMPS WATT":1000}

DEPT_OPTIONS = ["BANK OF INDIA","SBI - STATE BANK OF INDIA","BANK OF BARODA","INDIAN ARMY","INDIAN AIR FORCE","MINISTRY OF DEFENCE","MINISTRY OF FINANCE","MINISTRY OF HOME AFFAIRS","MINISTRY OF EDUCATION","MINISTRY OF HEALTH","MINISTRY OF RAILWAYS","MINISTRY OF ELECTRONICS & IT","NITI AAYOG","ISRO","NIC","OTHER - Type Manually"]
ITEM_OPTIONS = ["Desktop Computer","All in One PC","All in One PC - High End","High End Desktop Computer","Entry Level Desktop Computer","Mid Level Desktop Computer","Entry and Mid Level Desktop Computer","Laptop - Notebook","OTHER - Type Manually"]

def read_atc_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    full = ""
    for p in reader.pages:
        full += (p.extract_text() or "") + "\n"
    return full

def detect_products_in_atc(text):
    low = text.lower()
    detected = []
    reasons = {}
    for product, keywords in PRODUCT_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in low:
                detected.append(product)
                reasons[product] = kw
                break
    return list(dict.fromkeys(detected)), reasons # unique

def parse_atc_meta(text):
    org=""; m=re.search(r'Organisation\s*Name\s*[:\-]?\s*(.+?)\n',text,re.I)
    if m: org=m.group(1).strip()[:120]
    item_cat="Desktop Computer"; m=re.search(r'Item\s*Category\s*[:\-]?\s*(.+?)\n',text,re.I)
    if m: item_cat=m.group(1).strip()[:100]
    bid=""; clean=text.replace(" ",""); m=re.search(r'GEM\/\d{4}\/B\/\d{4,8}',clean.upper())
    if m: bid=m.group(0)
    qty=65; m=re.search(r'Quantity\s*[:\-]?\s*(\d{1,4})',text,re.I)
    if m: qty=int(m.group(1))
    return org, item_cat, bid, qty

with st.sidebar:
    st.markdown("### 📄 Upload ATC PDF")
    atc_file = st.file_uploader("ATC Only", type=["pdf"], label_visibility="collapsed")
    st.divider()
    margin = st.number_input("Margin / PC", value=4000, step=500)
    st.divider()
    st.caption("Only ATC products will be priced")

if atc_file:
    full_text = read_atc_pdf(atc_file)
    detected_products, reasons = detect_products_in_atc(full_text)
    org_v, item_v, bid_v, qty_v = parse_atc_meta(full_text)

    st.markdown(f"""
    <div style='background:white; padding:15px; border-radius:12px; border-left:5px solid #138808;'>
    ✅ <b>ATC Read:</b> Found <b>{len(detected_products)} products</b> in ATC | Bid: {bid_v} | Qty: {qty_v}
    </div><br>
    """, unsafe_allow_html=True)

    if detected_products:
        st.success(f"🎯 Products Mentioned in ATC: {', '.join(detected_products)}")
        with st.expander("🔍 Why detected? (Keyword found)"):
            for p in detected_products:
                st.write(f"**{p}** → keyword `{reasons[p]}` found in ATC")
    else:
        st.warning("No products detected — showing all 22 as fallback")
        detected_products = list(PRODUCT_KEYWORDS.keys())

    with st.expander("📄 Full ATC Text"):
        st.text(full_text[:8000])

else:
    detected_products = []
    org_v, item_v, bid_v, qty_v = "", "Desktop Computer", "", 65
    st.warning("⬆️ Upload ATC PDF — App will auto-detect products from ATC for pricing")

# FORM SAME
c1,c2,c3 = st.columns(3)
with c1:
    with st.container(border=True):
        st.markdown("🏛️ **Department**")
        dept_sel = st.selectbox("Dept", DEPT_OPTIONS, index=0, label_visibility="collapsed")
        dept = st.text_input("Manual Dept") if "OTHER" in dept_sel else dept_sel
with c2:
    with st.container(border=True):
        st.markdown("🏢 **Org & Bid**")
        org = st.text_input("Organisation", value=org_v, label_visibility="collapsed")
        bid_no = st.text_input("Bid No", value=bid_v, label_visibility="collapsed")
with c3:
    with st.container(border=True):
        st.markdown("📦 **Item & Qty**")
        idx=0
        for i,opt in enumerate(ITEM_OPTIONS):
            if opt.lower() in item_v.lower(): idx=i; break
        item_sel = st.selectbox("Item", ITEM_OPTIONS, index=idx, label_visibility="collapsed")
        item_cat = st.text_input("Manual Item", value=item_v) if "OTHER" in item_sel else item_sel
        qty = st.number_input("Qty", 1, 5000, qty_v, label_visibility="collapsed")

# ONLY ATC PRODUCTS FOR PRICING
st.divider()
if detected_products:
    st.markdown(f"### 💰 Pricing ONLY for {len(detected_products)} Products Mentioned in ATC")
    st.caption(f"Filtered from ATC: {', '.join(detected_products)}")
else:
    st.markdown("### 💰 Costing (Upload ATC to filter)")

prices={}; total=0
cols=st.columns(4)

# SHOW ONLY DETECTED
products_to_show = detected_products if detected_products else list(PRODUCT_KEYWORDS.keys())

for i, comp in enumerate(products_to_show):
    with cols[i%4]:
        with st.container(border=True):
            kw = reasons.get(comp, "") if atc_file else ""
            if kw:
                st.markdown(f"**{comp}** <span style='color:green; font-size:10px'>✅ {kw}</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"**{comp}**")
            p = st.number_input(comp, value=PRESET.get(comp,0), key=f"only_{comp}", label_visibility="collapsed")
            prices[comp]=p
            total+=p
            if p>0: st.caption(f"₹{p:,}")

# GRAND
grand = total + margin + int((total+margin)*0.18)
total_bid = grand*qty
gst = int((total+margin)*0.18)

m1,m2,m3,m4 = st.columns(4)
m1.metric("Base (ATC Only)", f"₹{total:,}")
m2.metric("Margin", f"₹{margin:,}")
m3.metric("GST", f"₹{gst:,}")
m4.metric("Grand / PC", f"₹{grand:,}")

st.markdown(f"""
<div style='background: linear-gradient(90deg, #138808, #075E54); padding:20px; border-radius:15px; color:white; text-align:center; margin-top:10px;'>
<h2 style='color:white; margin:0;'>Total: ₹{total_bid:,} for {qty} Units (Only ATC Products)</h2>
<p style='margin:5px 0 0 0;'>{dept} • {bid_no} • {item_cat} • {len(products_to_show)} Items from ATC</p>
</div>
""", unsafe_allow_html=True)

df = pd.DataFrame([
    ["Source", "ATC PDF - Filtered Products Only"],
    ["Department", dept],["Organisation", org],["Bid Number", bid_no],["Item Category", item_cat],["Quantity", qty],
    ["Products Found in ATC", ", ".join(products_to_show)],
    ["---","---"],
] + list(prices.items()) + [["TOTAL (ATC Products)", total],["MARGIN", margin],["GST", gst],["GRAND / PC", grand],["TOTAL BID", total_bid]],
columns=["Field","Value"])

st.dataframe(df, use_container_width=True)
st.download_button("📥 Download ATC-Only Pricing CSV", df.to_csv(index=False).encode(), f"ATC_ONLY_{bid_no}_{dept}.csv", use_container_width=True)