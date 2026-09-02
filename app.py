import streamlit as st
import pandas as pd
import re
try:
    from pypdf import PdfReader
except:
    from PyPDF2 import PdfReader

st.set_page_config(page_title="GeM ATC Pro - Full Parser", layout="wide")
st.title("🇮🇳 GeM Bid - FULL First Page Reader")

ALL_22 = ["Processor CPU","MB","Graphics CARD","OS","RAM","SSD","SSD (SECONDARY)","Cabinet LTR","SMPS WATT","ADAPTER","DVD WRITER","MONITOR","SPEAKER","WIRELESS + BLUETOOTH","MS OFFICE","CHASSIS SWITCH","TPM 2.0","CAMERA","ANTIVIRUS","DP PORT","SERIAL COM PORT+PARALLEL","Keyboard & Mouse"]
PRESET = {"Processor CPU":14500,"MB":4250,"RAM":17500,"SSD":3650,"SSD (SECONDARY)":11500,"MONITOR":4450,"Keyboard & Mouse":350,"TPM 2.0":700,"CAMERA":500,"OS":600,"Cabinet LTR":1850}

def extract_pages(pdf):
    reader = PdfReader(pdf)
    full = ""
    first = ""
    for i, p in enumerate(reader.pages):
        txt = p.extract_text() or ""
        full += txt + "\n"
        if i == 0:
            first = txt
    return first, full

def smart_find(patterns, text, default=""):
    for pat in patterns:
        m = re.search(pat, text, re.I | re.M)
        if m:
            val = m.group(1).strip()
            val = re.sub(r'\s{2,}', ' ', val)
            if len(val) > 3:
                return val[:120]
    return default

def parse_first_page(first_page):
    # Department
    dept_patterns = [
        r'Department\s*[:\-]?\s*(.+?)\n',
        r'Department Name\s*[:\-]?\s*(.+?)\n',
        r'Name of Department\s*[:\-]?\s*(.+?)\n',
    ]
    dept = smart_find(dept_patterns, first_page, "BANK OF INDIA")

    # Organisation
    org_patterns = [
        r'Organisation\s*Name\s*[:\-]?\s*(.+?)\n',
        r'Organization\s*Name\s*[:\-]?\s*(.+?)\n',
        r'Ministry.*?\n.*Organisation\s*[:\-]?\s*(.+?)\n',
        r'Buyer.*Organisation\s*[:\-]?\s*(.+?)\n',
    ]
    org = smart_find(org_patterns, first_page, "")

    # Item Category
    item_patterns = [
        r'Item\s*Category\s*[:\-]?\s*(.+?)\n',
        r'Category\s*[:\-]?\s*(Desktop Computers?|All in One|Computer.*?)\n?',
        r'Item\s*:\s*(Desktop.*?)\n',
        r'Schedule.*?:\s*(Desktop.*?)\n',
    ]
    item_cat = smart_find(item_patterns, first_page, "Desktop Computer")

    # Bid No
    clean = first_page.replace(" ", "")
    m = re.search(r'GEM\/\d{4}\/B\/\d{4,8}', clean.upper())
    bid = m.group(0) if m else ""
    if not bid:
        m = re.search(r'GEM\s*\/\s*\d{4}\s*\/\s*B\s*\/\s*\d+', first_page, re.I)
        bid = re.sub(r'\s+', '', m.group(0)).upper() if m else ""

    # Quantity
    qty = 65
    m = re.search(r'Quantity\s*[:\-]?\s*(\d{1,4})', first_page, re.I)
    if m:
        qty = int(m.group(1))
    else:
        # Search in full schedule
        m = re.search(r'(\d{1,4})\s*Pieces', first_page, re.I)
        if m: qty = int(m.group(1))

    # Bid Value / Department logic
    if not org:
        if "bank of india" in first_page.lower(): org = "Bank of India"
        elif "state bank" in first_page.lower(): org = "State Bank of India"

    return dept, org, item_cat, bid, qty

with st.sidebar:
    f = st.file_uploader("Upload GeM Bid (Page 1)", type=["pdf"])
    margin = st.number_input("Margin", value=4000)

if f:
    first, full = extract_pages(f)
    dept_v, org_v, item_v, bid_v, qty_v = parse_first_page(first + "\n" + full[:5000])

    st.success("✅ First Page Auto-Read Done")

    # Show Parsed Header
    h1,h2 = st.columns(2)
    with h1:
        st.info(f"**Organisation:** {org_v}\n\n**Department:** {dept_v}\n\n**Bid No:** {bid_v}")
    with h2:
        st.info(f"**Item Category:** {item_v}\n\n**Quantity:** {qty_v}")

    with st.expander("🔍 Debug First Page Text"):
        st.text(first[:7000])
else:
    st.info("Upload GeM Bid PDF - First Page will be auto-parsed")
    dept_v, org_v, item_v, bid_v, qty_v = "BANK OF INDIA", "Bank of India", "Desktop Computers", "", 65

# Editable Fields
c1,c2,c3 = st.columns(3)
dept = c1.text_input("Department", dept_v)
org = c2.text_input("Organisation Name", org_v)
bid_no = c3.text_input("Bid No", bid_v)

c4,c5,c6 = st.columns(3)
item_cat = c4.text_input("Item Category", item_v)
qty = c5.number_input("Qty", 1, 5000, qty_v)
# margin already in sidebar

# Costing
st.divider()
st.subheader(f"💰 Costing for: {item_cat} - {qty} Units")
prices={}
total=0
cols=st.columns(4)
for i, comp in enumerate(ALL_22):
    with cols[i%4]:
        with st.container(border=True):
            st.write(f"**{comp}**")
            p = st.number_input(comp, value=PRESET.get(comp,0), key=comp, label_visibility="collapsed")
            prices[comp]=p
            total+=p

grand = total + margin + int((total+margin)*0.18)
total_bid = grand*qty

st.metric("Summary", f"Grand ₹{grand:,} | Total Bid ₹{total_bid:,} | {org} - {dept}")

df = pd.DataFrame([
    ["Organisation", org],
    ["Department", dept],
    ["Bid Number", bid_no],
    ["Item Category", item_cat],
    ["Quantity", qty],
    ["---", "---"],
] + list(prices.items()) + [["TOTAL", total],["MARGIN", margin],["GRAND TOTAL / PC", grand],["TOTAL BID VALUE", total_bid]],
columns=["Field", "Value"])

st.dataframe(df, use_container_width=True)
st.download_button("📥 Download Full Summary CSV", df.to_csv(index=False).encode(), f"{bid_no}_{dept}.csv", use_container_width=True)