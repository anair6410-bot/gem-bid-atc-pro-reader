import streamlit as st
import pandas as pd
import re
try:
    from pypdf import PdfReader
except:
    from PyPDF2 import PdfReader

st.set_page_config(page_title="GeM ATC Pro", layout="wide", page_icon="🇮🇳")

# BEAUTIFY CSS
st.markdown("""
<style>
   .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #e4eaf5 100%); }
    h1 {
        background: linear-gradient(90deg, #FF9933 0%, #138808 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800!important;
        text-align: center;
        padding: 10px;
    }
    div[data-testid="stMetric"] {
        background: white;
        padding: 15px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border-left: 5px solid #138808;
    }
    div[data-testid="stContainer"] {
        background: white;
        border-radius: 12px!important;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05)!important;
    }
   .stSelectbox,.stTextInput,.stNumberInput {
        background: white;
        border-radius: 10px;
    }
   .stButton>button {
        background: linear-gradient(90deg, #FF9933, #138808);
        color: white;
        border-radius: 25px;
        font-weight: bold;
        border: none;
        padding: 10px 25px;
    }
   .stDownloadButton>button {
        background: linear-gradient(90deg, #138808, #075E54);
        color: white;
        border-radius: 25px;
        width: 100%;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1>🇮🇳 GeM Bid - Smart Costing Studio</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#666;'>Auto Reader • Department + Ministries • Beautified Costing</p>", unsafe_allow_html=True)

ALL_22 = ["Processor CPU","MB","Graphics CARD","OS","RAM","SSD","SSD (SECONDARY)","Cabinet LTR","SMPS WATT","ADAPTER","DVD WRITER","MONITOR","SPEAKER","WIRELESS + BLUETOOTH","MS OFFICE","CHASSIS SWITCH","TPM 2.0","CAMERA","ANTIVIRUS","DP PORT","SERIAL COM PORT+PARALLEL","Keyboard & Mouse"]
PRESET = {"Processor CPU":14500,"MB":4250,"Graphics CARD":0,"OS":600,"RAM":17500,"SSD":3650,"SSD (SECONDARY)":11500,"Cabinet LTR":1850,"SMPS WATT":1000,"MONITOR":4450,"SPEAKER":400,"WIRELESS + BLUETOOTH":400,"CHASSIS SWITCH":350,"TPM 2.0":700,"CAMERA":500,"ANTIVIRUS":200,"DP PORT":500,"Keyboard & Mouse":350}

DEPT_OPTIONS = ["BANK OF INDIA","SBI - STATE BANK OF INDIA","BANK OF BARODA","CANARA BANK","PUNJAB NATIONAL BANK","UNION BANK","INDIAN ARMY","INDIAN AIR FORCE","INDIAN NAVY","DRDO","BSF","CRPF","MINISTRY OF DEFENCE","MINISTRY OF FINANCE","MINISTRY OF HOME AFFAIRS","MINISTRY OF EDUCATION","MINISTRY OF HEALTH","MINISTRY OF RAILWAYS","MINISTRY OF ELECTRONICS & IT","NITI AAYOG","ISRO","NIC","BHEL","ONGC","NTPC","OTHER - Type Manually"]

ITEM_OPTIONS = ["Desktop Computer","All in One PC","All in One PC - High End","High End Desktop Computer","Entry Level Desktop Computer","Mid Level Desktop Computer","Entry and Mid Level Desktop Computer","Mid Level Desktop Computer with Monitor","High End Desktop Computer with Monitor","Laptop - Notebook","Workstation","Thin Client","OTHER - Type Manually"]

def extract_pages(pdf):
    reader = PdfReader(pdf)
    full = ""; first = ""
    for i,p in enumerate(reader.pages):
        txt = p.extract_text() or ""
        full += txt + "\n"
        if i==0: first = txt
    return first, full

def parse_auto(first_page, full_text):
    text = first_page + "\n" + full_text[:5000]
    org=""; m=re.search(r'Organisation\s*Name\s*[:\-]?\s*(.+?)\n',text,re.I)
    if m: org=m.group(1).strip()[:120]
    item_cat="Desktop Computer"; m=re.search(r'Item\s*Category\s*[:\-]?\s*(.+?)\n',text,re.I)
    if m: item_cat=m.group(1).strip()[:100]
    clean=text.replace(" ",""); m=re.search(r'GEM\/\d{4}\/B\/\d{4,8}',clean.upper())
    bid=m.group(0) if m else ""
    if not bid:
        m=re.search(r'GEM\s*\/\s*\d{4}\s*\/\s*B\s*\/\s*\d+',text,re.I)
        if m: bid=re.sub(r'\s+','',m.group(0)).upper()
    qty=65; m=re.search(r'Quantity\s*[:\-]?\s*(\d{1,4})',text,re.I)
    if m: qty=int(m.group(1))
    return org, item_cat, bid, qty

# SIDEBAR BEAUTIFIED
with st.sidebar:
    st.markdown("### 📤 Upload Bid")
    f = st.file_uploader("GeM Bid PDF", type=["pdf"], label_visibility="collapsed")
    st.divider()
    st.markdown("### 💸 Margin")
    margin = st.number_input("Margin / PC", value=4000, step=500, label_visibility="collapsed")
    st.info(f"Current Margin: ₹{margin:,}")
    st.divider()
    st.markdown("Made for **GeM Sellers** 🇮🇳")

if f:
    first, full = extract_pages(f)
    org_v, item_v, bid_v, qty_v = parse_auto(first, full)
    st.markdown(f"""
    <div style='background:white; padding:15px; border-radius:12px; border-left:5px solid #FF9933; box-shadow: 0 2px 10px rgba(0,0,0,0.05);'>
    ✅ <b>Auto Detected:</b> {org_v} | <b>{bid_v}</b> | Qty: <b>{qty_v}</b> | {item_v}
    </div><br>
    """, unsafe_allow_html=True)
else:
    org_v, item_v, bid_v, qty_v = "", "Desktop Computer", "", 65

# TOP CARDS
c1,c2,c3 = st.columns(3)
with c1:
    with st.container(border=True):
        st.markdown("🏛️ **Department**")
        dept_sel = st.selectbox("Dept", DEPT_OPTIONS, index=0, label_visibility="collapsed")
        if "OTHER" in dept_sel:
            dept = st.text_input("Manual Dept", placeholder="Type...", label_visibility="collapsed") or "OTHER"
        else:
            dept = dept_sel
        st.caption(f"Selected: {dept}")

with c2:
    with st.container(border=True):
        st.markdown("🏢 **Organisation & Bid**")
        org = st.text_input("Organisation", value=org_v, placeholder="Auto from PDF", label_visibility="collapsed")
        bid_no = st.text_input("Bid No", value=bid_v, placeholder="GEM/...", label_visibility="collapsed")
        st.caption(f"Org: {org[:30]} | Bid: {bid_no}")

with c3:
    with st.container(border=True):
        st.markdown("📦 **Item & Quantity**")
        try:
            idx = 0
            for i, opt in enumerate(ITEM_OPTIONS):
                if opt.lower() in item_v.lower(): idx=i; break
        except: idx=0
        item_sel = st.selectbox("Item", ITEM_OPTIONS, index=idx, label_visibility="collapsed")
        if "OTHER" in item_sel:
            item_cat = st.text_input("Manual Item", value=item_v, label_visibility="collapsed") or item_v
        else:
            item_cat = item_sel
        qty = st.number_input("Qty", 1, 5000, qty_v, label_visibility="collapsed")
        st.caption(f"{item_cat} | Qty: {qty}")

# COSTING GRID
st.divider()
st.markdown(f"### 💰 Component Costing - <span style='color:#138808'>{dept}</span> | <span style='color:#FF9933'>{item_cat}</span>", unsafe_allow_html=True)

prices={}; total=0
cols=st.columns(4)
for i, comp in enumerate(ALL_22):
    with cols[i%4]:
        with st.container(border=True):
            st.markdown(f"<div style='font-weight:600; font-size:13px; color:#333;'>{comp}</div>", unsafe_allow_html=True)
            p = st.number_input(comp, value=PRESET.get(comp,0), key=f"c_{comp}", label_visibility="collapsed")
            prices[comp]=p
            total+=p
            if p>0:
                st.caption(f"₹{p:,}")

# GRAND TOTAL CARD
grand = total + margin + int((total+margin)*0.18)
total_bid = grand*qty
gst = int((total+margin)*0.18)

st.markdown("<br>", unsafe_allow_html=True)
m1,m2,m3,m4 = st.columns(4)
m1.metric("💵 Base Cost", f"₹{total:,}")
m2.metric("📈 Margin", f"₹{margin:,}")
m3.metric("🧾 GST 18%", f"₹{gst:,}")
m4.metric("🏆 Grand / PC", f"₹{grand:,}")

st.markdown(f"""
<div style='background: linear-gradient(90deg, #138808, #075E54); padding:20px; border-radius:15px; color:white; text-align:center; margin-top:10px;'>
<h2 style='color:white; margin:0;'>Total Bid Value: ₹{total_bid:,} for {qty} Units</h2>
<p style='margin:5px 0 0 0; opacity:0.9;'>{dept} • {bid_no} • {item_cat}</p>
</div>
""", unsafe_allow_html=True)

# TABLE & DOWNLOAD
st.divider()
df = pd.DataFrame([
    ["Department", dept],["Organisation", org],["Bid Number", bid_no],["Item Category", item_cat],["Quantity", qty],["---","---"]
] + list(prices.items()) + [["TOTAL COST", total],["MARGIN", margin],["GST 18%", gst],["GRAND TOTAL / PC", grand],["TOTAL BID VALUE", total_bid]],
columns=["Field", "Value"])

st.dataframe(df, use_container_width=True, height=400)

st.download_button("📥 Download Beautiful Summary CSV", df.to_csv(index=False).encode(), f"{bid_no}_{dept}_{item_cat}.csv", use_container_width=True)