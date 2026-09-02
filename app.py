import streamlit as st
import pandas as pd
import re
try:
    from pypdf import PdfReader
except:
    from PyPDF2 import PdfReader

st.set_page_config(page_title="GeM ATC Market Price", layout="wide", page_icon="📄")

st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #f5f7fa 0%, #e4eaf5 100%); }
  h1 { background: linear-gradient(90deg, #FF9933 0%, #138808 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight:800!important; text-align:center; }
  div[data-testid="stMetric"] { background:white; padding:15px; border-radius:15px; box-shadow:0 4px 15px rgba(0,0,0,0.1); border-left:5px solid #138808; }
  div[data-testid="stContainer"] { background:white; border-radius:12px!important; }
.stDownloadButton>button { background: linear-gradient(90deg, #138808, #075E54); color:white; border-radius:25px; width:100%; height:50px; font-weight:bold;}
.clear-btn>button { background: #ff4b4b!important; color:white!important; border-radius:20px!important; font-weight:bold; border:none; }
</style>
""", unsafe_allow_html=True)

LIVE_MARKET_2026 = {
    "Processor CPU": 14500, "MB": 6500, "Graphics CARD": 0, "OS": 0, "RAM": 5200, "SSD": 3200,
    "SSD (SECONDARY)": 5400, "Cabinet LTR": 2200, "SMPS WATT": 1800, "ADAPTER": 0, "DVD WRITER": 0,
    "MONITOR": 7200, "SPEAKER": 450, "WIRELESS + BLUETOOTH": 850, "MS OFFICE": 0, "CHASSIS SWITCH": 300,
    "TPM 2.0": 0, "CAMERA": 0, "ANTIVIRUS": 350, "DP PORT": 0, "SERIAL COM PORT+PARALLEL": 250, "Keyboard & Mouse": 750
}

PRODUCT_KEYWORDS = {
    "Processor CPU": ["processor", "cpu", "intel", "amd", "ryzen", "i3", "i5", "i7"],
    "MB": ["motherboard", "chipset"], "Graphics CARD": ["graphics", "gpu"], "OS": ["windows 11", "windows 10", "linux", "operating system"],
    "RAM": ["ram", "memory"], "SSD": ["ssd", "nvme"], "SSD (SECONDARY)": ["secondary", "1 tb", "hdd"],
    "Cabinet LTR": ["cabinet", "chassis"], "SMPS WATT": ["smps", "power supply"], "MONITOR": ["monitor", "display", "inch"],
    "SPEAKER": ["speaker"], "WIRELESS + BLUETOOTH": ["wireless", "wifi", "bluetooth"], "MS OFFICE": ["ms office"],
    "CHASSIS SWITCH": ["chassis intrusion"], "TPM 2.0": ["tpm"], "CAMERA": ["camera", "webcam"], "ANTIVIRUS": ["antivirus"],
    "DP PORT": ["display port"], "SERIAL COM PORT+PARALLEL": ["serial port", "com port"], "Keyboard & Mouse": ["keyboard", "mouse"]
}

DEPT_OPTIONS = ["BANK OF INDIA","SBI","INDIAN ARMY","MINISTRY OF DEFENCE","MINISTRY OF FINANCE","MINISTRY OF HOME AFFAIRS","MINISTRY OF EDUCATION","MINISTRY OF RAILWAYS","MINISTRY OF ELECTRONICS & IT","NITI AAYOG","ISRO","NIC","OTHER - Type Manually"]
ITEM_OPTIONS = ["Desktop Computer","All in One PC","All in One PC - High End","High End Desktop Computer","Entry Level Desktop Computer","Mid Level Desktop Computer","Entry and Mid Level Desktop Computer","Laptop - Notebook","OTHER - Type Manually"]

def read_atc(file):
    reader = PdfReader(file)
    return "\n".join([p.extract_text() or "" for p in reader.pages])

def detect(text):
    low=text.lower(); det=[]; rs={}
    for prod,kws in PRODUCT_KEYWORDS.items():
        for kw in kws:
            if kw in low:
                det.append(prod); rs[prod]=kw; break
    return list(dict.fromkeys(det)), rs

def parse_meta(text):
    org=""; m=re.search(r'Organisation\s*Name\s*[:\-]?\s*(.+?)\n',text,re.I)
    if m: org=m.group(1).strip()[:120]
    bid=""; clean=text.replace(" ",""); m=re.search(r'GEM\/\d{4}\/B\/\d{4,8}',clean.upper())
    if m: bid=m.group(0)
    qty=65; m=re.search(r'Quantity\s*[:\-]?\s*(\d{1,4})',text,re.I)
    if m: qty=int(m.group(1))
    item="Desktop Computer"; m=re.search(r'Item\s*Category\s*[:\-]?\s*(.+?)\n',text,re.I)
    if m: item=m.group(1).strip()[:100]
    return org,item,bid,qty

# TOP CLEAR BUTTON
top1, top2 = st.columns([4,1])
with top1:
    st.markdown("<h1>📄 GeM ATC Reader - Market Price</h1>", unsafe_allow_html=True)
with top2:
    st.markdown('<div class="clear-btn">', unsafe_allow_html=True)
    if st.button("🗑️ CLEAR ALL", use_container_width=True, key="clear_top"):
        # Clear all session states
        for key in list(st.session_state.keys()):
            if key.startswith("p_") or key in ["margin", "dept", "org", "bid", "item", "qty", "dept_manual", "item_manual"]:
                del st.session_state[key]
        st.session_state.margin = 0
        st.toast("✅ All fields cleared!", icon="🗑️")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 📄 Upload ATC PDF")
    atc_file = st.file_uploader("ATC", type=["pdf"], label_visibility="collapsed")
    st.markdown("### 💸 Margin")
    if "margin" not in st.session_state: st.session_state.margin = 4000
    st.session_state.margin = st.number_input("Margin", value=st.session_state.margin, step=500, label_visibility="collapsed")
    st.divider()
    st.markdown("### 💹 Market Price")
    fetch_live = st.button("Fetch Current Market Price", use_container_width=True, type="primary")
    if fetch_live:
        for comp, price in LIVE_MARKET_2026.items():
            st.session_state[f"p_{comp}"] = price
        st.toast("Market Price Updated")
        st.rerun()
    st.divider()
    # Also clear in sidebar
    if st.button("🗑️ Clear All Fields", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key.startswith("p_") or key in ["margin"]:
                del st.session_state[key]
        st.session_state.margin = 0
        st.rerun()

if atc_file:
    text = read_atc(atc_file)
    detected, reasons = detect(text)
    org_v,item_v,bid_v,qty_v = parse_meta(text)
    if not detected: detected = list(PRODUCT_KEYWORDS.keys())
    st.success(f"✅ ATC Read - {len(detected)} products: {', '.join(detected)}")
else:
    text=""; detected=[]; reasons={}; org_v,item_v,bid_v,qty_v="","Desktop Computer","",65

c1,c2,c3 = st.columns(3)
with c1:
    with st.container(border=True):
        dept = st.selectbox("🏛️ Department", DEPT_OPTIONS, label_visibility="collapsed", key="dept")
with c2:
    with st.container(border=True):
        org = st.text_input("Organisation", value=org_v, label_visibility="collapsed", key="org")
        bid_no = st.text_input("Bid No", value=bid_v, label_visibility="collapsed", key="bid")
with c3:
    with st.container(border=True):
        idx=0
        for i,opt in enumerate(ITEM_OPTIONS):
            if opt.lower() in item_v.lower(): idx=i; break
        item_cat = st.selectbox("📦 Item", ITEM_OPTIONS, index=idx, label_visibility="collapsed", key="item")
        qty = st.number_input("Qty", 1, 5000, qty_v, label_visibility="collapsed", key="qty")

products = detected if detected else list(PRODUCT_KEYWORDS.keys())

st.divider()
st.markdown(f"### 💰 Pricing - ONLY ATC Products ({len(products)})")

for comp in products:
    if f"p_{comp}" not in st.session_state:
        st.session_state[f"p_{comp}"] = LIVE_MARKET_2026.get(comp, 0)

prices={}; total=0
cols=st.columns(4)
for i, comp in enumerate(products):
    with cols[i%4]:
        with st.container(border=True):
            kw = reasons.get(comp,"")
            st.markdown(f"**{comp}**" + (f" <span style='color:green;font-size:10px'>✅ {kw}</span>" if kw else ""), unsafe_allow_html=True)
            st.caption(f"Market: ₹{LIVE_MARKET_2026.get(comp,0):,}")
            p = st.number_input(comp, value=st.session_state[f"p_{comp}"], key=f"p_{comp}", label_visibility="collapsed")
            prices[comp]=p
            total+=p

margin = st.session_state.get("margin", 0)
gst = int((total+margin)*0.18)
grand = total+margin+gst
total_bid = grand*qty

m1,m2,m3,m4 = st.columns(4)
m1.metric("Base (Market)", f"₹{total:,}")
m2.metric("Margin", f"₹{margin:,}")
m3.metric("GST 18%", f"₹{gst:,}")
m4.metric("Grand / PC", f"₹{grand:,}")

st.markdown(f"""
<div style='background: linear-gradient(90deg, #138808, #075E54); padding:18px; border-radius:12px; color:white; text-align:center;'>
<h3 style='color:white; margin:0;'>Total Bid Value: ₹{total_bid:,} for {qty} Units</h3>
<p style='margin:4px 0 0 0; font-size:13px;'>{dept} • {bid_no} • {item_cat}</p>
</div>
""", unsafe_allow_html=True)

df = pd.DataFrame(
    [["Department",dept], ["Organisation",org], ["Bid Number",bid_no], ["Item Category",item_cat], ["Quantity",qty], ["ATC Products", ", ".join(products)]] +
    list(prices.items()) + [["TOTAL BASE", total],["MARGIN", margin],["GST", gst],["GRAND / PC", grand],["TOTAL BID VALUE", total_bid]],
    columns=["Field","Value"]
)
st.dataframe(df, use_container_width=True)
st.download_button("📥 Download Costing CSV", df.to_csv(index=False).encode(), f"ATC_{bid_no}_{dept}.csv", use_container_width=True)