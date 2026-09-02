import streamlit as st
import pandas as pd
import re
try:
    from pypdf import PdfReader
except:
    from PyPDF2 import PdfReader

st.set_page_config(page_title="GeM ATC Pro", layout="wide")
st.title("🇮🇳 GeM Bid - Dept with Ministries")

ALL_22 = ["Processor CPU","MB","Graphics CARD","OS","RAM","SSD","SSD (SECONDARY)","Cabinet LTR","SMPS WATT","ADAPTER","DVD WRITER","MONITOR","SPEAKER","WIRELESS + BLUETOOTH","MS OFFICE","CHASSIS SWITCH","TPM 2.0","CAMERA","ANTIVIRUS","DP PORT","SERIAL COM PORT+PARALLEL","Keyboard & Mouse"]
PRESET = {"Processor CPU":14500,"MB":4250,"RAM":17500,"SSD":3650,"SSD (SECONDARY)":11500,"MONITOR":4450,"Keyboard & Mouse":350,"TPM 2.0":700,"CAMERA":500,"OS":600,"Cabinet LTR":1850}

# FULL LIST - Banks + Ministries + Defence + PSUs
DEPT_OPTIONS = [
    "--- BANKS ---",
    "BANK OF INDIA",
    "SBI - STATE BANK OF INDIA",
    "BANK OF BARODA",
    "CANARA BANK",
    "PUNJAB NATIONAL BANK",
    "UNION BANK OF INDIA",
    "BANK OF MAHARASHTRA",
    "CENTRAL BANK OF INDIA",
    "UCO BANK",
    "INDIAN BANK",
    "BANK OF BARODA (BOB)",
    "INDIAN OVERSEAS BANK",
    "--- DEFENCE & PARAMILITARY ---",
    "INDIAN ARMY",
    "INDIAN AIR FORCE",
    "INDIAN NAVY",
    "DRDO",
    "BSF - BORDER SECURITY FORCE",
    "CRPF - CENTRAL RESERVE POLICE FORCE",
    "CISF",
    "ITBP",
    "--- CENTRAL MINISTRIES ---",
    "MINISTRY OF DEFENCE",
    "MINISTRY OF FINANCE",
    "MINISTRY OF HOME AFFAIRS",
    "MINISTRY OF EDUCATION",
    "MINISTRY OF HEALTH & FAMILY WELFARE",
    "MINISTRY OF RAILWAYS",
    "MINISTRY OF ELECTRONICS & IT (MeitY)",
    "MINISTRY OF LAW & JUSTICE",
    "MINISTRY OF EXTERNAL AFFAIRS",
    "MINISTRY OF AGRICULTURE",
    "MINISTRY OF ROAD TRANSPORT & HIGHWAYS",
    "MINISTRY OF POWER",
    "MINISTRY OF PETROLEUM & NATURAL GAS",
    "MINISTRY OF COMMUNICATIONS",
    "MINISTRY OF HOUSING & URBAN AFFAIRS",
    "MINISTRY OF LABOUR & EMPLOYMENT",
    "MINISTRY OF INFORMATION & BROADCASTING",
    "MINISTRY OF SCIENCE & TECHNOLOGY",
    "MINISTRY OF SKILL DEVELOPMENT",
    "NITI AAYOG",
    "ISRO - DEPARTMENT OF SPACE",
    "--- STATE GOVT & PSU ---",
    "STATE GOVERNMENT - MADHYA PRADESH",
    "STATE GOVERNMENT - UTTAR PRADESH",
    "STATE GOVERNMENT - MAHARASHTRA",
    "STATE GOVERNMENT - OTHER",
    "BHEL",
    "ONGC",
    "NTPC",
    "IOCL - INDIAN OIL",
    "NIC - NATIONAL INFORMATICS CENTRE",
    "OTHER - Type Manually"
]

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

def parse_auto(first_page, full_text):
    text = first_page + "\n" + full_text[:5000]
    org = ""
    m = re.search(r'Organisation\s*Name\s*[:\-]?\s*(.+?)\n', text, re.I)
    if m: org = m.group(1).strip()[:120]
    if not org:
        low = text.lower()
        if "bank of india" in low: org = "Bank of India"
        elif "defence" in low: org = "Ministry of Defence"
        elif "railway" in low: org = "Ministry of Railways"

    item_cat = "Desktop Computer"
    m = re.search(r'Item\s*Category\s*[:\-]?\s*(.+?)\n', text, re.I)
    if m: item_cat = m.group(1).strip()[:100]

    clean = text.replace(" ", "")
    m = re.search(r'GEM\/\d{4}\/B\/\d{4,8}', clean.upper())
    bid = m.group(0) if m else ""
    if not bid:
        m = re.search(r'GEM\s*\/\s*\d{4}\s*\/\s*B\s*\/\s*\d+', text, re.I)
        if m: bid = re.sub(r'\s+', '', m.group(0)).upper()

    qty = 65
    m = re.search(r'Quantity\s*[:\-]?\s*(\d{1,4})', text, re.I)
    if m: qty = int(m.group(1))

    return org, item_cat, bid, qty

with st.sidebar:
    f = st.file_uploader("Upload GeM Bid PDF", type=["pdf"])
    margin = st.number_input("Margin", value=4000)

if f:
    first, full = extract_pages(f)
    org_v, item_v, bid_v, qty_v = parse_auto(first, full)
    st.success(f"Auto: {org_v} | {item_v} | {bid_v} | Qty {qty_v}")
else:
    org_v, item_v, bid_v, qty_v = "", "Desktop Computer", "", 65
    st.info("Upload PDF")

# DEPARTMENT DROPDOWN WITH MINISTRIES
c1,c2,c3 = st.columns(3)
dept_selected = c1.selectbox("Department (Banks + Ministries)", DEPT_OPTIONS, index=1)

if "---" in dept_selected:
    st.warning("Please select a valid Department, not a heading")
    dept = "BANK OF INDIA"
elif "OTHER" in dept_selected:
    dept = c1.text_input("Type Department Manually", placeholder="e.g. MINISTRY OF...") or "OTHER"
else:
    dept = dept_selected

org = c2.text_input("Organisation Name (Auto)", org_v)
bid_no = c3.text_input("Bid No (Auto)", bid_v)

c4,c5 = st.columns(2)
item_cat = c4.text_input("Item Category (Auto)", item_v)
qty = c5.number_input("Qty (Auto)", 1, 5000, qty_v)

# Costing
st.divider()
st.subheader(f"💰 Costing - {dept} - {qty} Units")
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
st.metric("Summary", f"₹{grand:,} / PC | Total ₹{total_bid:,}")

df = pd.DataFrame([
    ["Department", dept],
    ["Organisation", org],
    ["Bid Number", bid_no],
    ["Item Category", item_cat],
    ["Quantity", qty],
] + list(prices.items()) + [["GRAND TOTAL / PC", grand],["TOTAL BID", total_bid]],
columns=["Field", "Value"])

st.dataframe(df, use_container_width=True)
st.download_button("📥 Download CSV", df.to_csv(index=False).encode(), f"{bid_no}_{dept}.csv", use_container_width=True)