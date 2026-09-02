import streamlit as st
import pandas as pd
import re
try:
    from pypdf import PdfReader
except:
    from PyPDF2 import PdfReader

st.set_page_config(page_title="GeM ATC Pro", layout="wide")
st.title("🇮🇳 GeM Bid - AUTO Reader (Bid No Fixed)")

ALL_22 = ["Processor CPU","MB","Graphics CARD","OS","RAM","SSD","SSD (SECONDARY)","Cabinet LTR","SMPS WATT","ADAPTER","DVD WRITER","MONITOR","SPEAKER","WIRELESS + BLUETOOTH","MS OFFICE","CHASSIS SWITCH","TPM 2.0","CAMERA","ANTIVIRUS","DP PORT","SERIAL COM PORT+PARALLEL","Keyboard & Mouse"]
PRESET = {"Processor CPU":14500,"MB":4250,"RAM":17500,"SSD":3650,"MONITOR":4450,"Keyboard & Mouse":350}
KEYWORDS = {"Processor CPU":["processor","cpu","i5"],"MB":["motherboard","chipset"],"RAM":["ram","memory"],"SSD":["ssd","nvme"],"MONITOR":["monitor"],"OS":["windows"]}

def extract_all(pdf):
    reader = PdfReader(pdf)
    text = ""
    for p in reader.pages:
        text += (p.extract_text() or "") + "\n"
    return text

def parse_bid_no(text):
    # Clean text: remove extra spaces around /
    clean = text.replace(" ", "").replace("\n","").upper()

    # 1. Most common: GEM/2026/B/1234567
    m = re.search(r'GEM\/\d{4}\/B\/\d{4,8}', clean)
    if m:
        return m.group(0).replace(" ", "")

    # 2. With hyphens: GEM-2026-B-1234567
    m = re.search(r'GEM[-/]\d{4}[-/]B[-/]\d{4,8}', text, re.I)
    if m:
        return m.group(0).upper().replace("-", "/").replace(" ", "")

    # 3. Bid Number line + next line
    m = re.search(r'Bid\s*No\.?\s*[:\-]?\s*([A-Z0-9\/\- ]{10,25})', text, re.I)
    if m:
        raw = m.group(1).strip().upper()
        # Extract GEM part from it
        g = re.search(r'GEM.*?\d+', raw)
        if g:
            return g.group(0).replace(" ", "")

    # 4. Fallback: Search original text loosely
    m = re.search(r'GEM\s*\/\s*\d{4}\s*\/\s*B\s*\/\s*\d+', text, re.I)
    if m:
        return re.sub(r'\s+', '', m.group(0)).upper()

    return ""

def parse_all(text):
    dept = "BANK OF INDIA"
    low = text.lower()
    if "bank of india" in low: dept = "BANK OF INDIA"
    elif "state bank" in low or " sbi " in low: dept = "SBI"
    elif "army" in low: dept = "INDIAN ARMY"
    elif "baroda" in low: dept = "BANK OF BARODA"

    bid = parse_bid_no(text)

    qty = 65
    m = re.search(r'Quantity\s*[:\-]?\s*(\d{1,4})', text, re.I)
    if m:
        qty = int(m.group(1))
    else:
        m = re.search(r'(\d{1,4})\s*Nos', text, re.I)
        if m:
            qty = int(m.group(1))

    return dept, bid, qty

def detect(text_low):
    found=[]
    for comp,kws in KEYWORDS.items():
        if any(k in text_low for k in kws):
            found.append(comp)
    return found if len(found)>=3 else ALL_22

with st.sidebar:
    f = st.file_uploader("Upload GeM Bid PDF", type=["pdf"])
    margin = st.number_input("Margin", value=4000)

if f:
    text_orig = extract_all(f)
    dept_val, bid_val, qty_val = parse_all(text_orig)
    detected = detect(text_orig.lower())

    st.success(f"Dept: {dept_val} | Bid: {bid_val if bid_val else 'NOT FOUND'} | Qty: {qty_val}")

    # DEBUG - Very important
    with st.expander("🔍 Debug: See what app read from PDF (to fix Bid No)"):
        st.text(text_orig[:6000])
        if not bid_val:
            st.warning("Bid No not found. Copy the line where Bid No appears from above text and send me.")
else:
    st.info("Upload GeM Bid PDF")
    dept_val, bid_val, qty_val = "BANK OF INDIA", "", 65
    detected = ALL_22

c1,c2,c3 = st.columns(3)
dept = c1.text_input("Department", dept_val)
bid_no = c2.text_input("Bid No (Auto)", bid_val)
qty = c3.number_input("Qty", 1, 5000, qty_val)

# Costing
prices={}
total=0
cols=st.columns(4)
for i, comp in enumerate(detected):
    with cols[i%4]:
        with st.container(border=True):
            st.write(f"**{comp}**")
            p = st.number_input(comp, value=PRESET.get(comp,1000), key=comp, label_visibility="collapsed")
            prices[comp]=p
            total+=p

grand = total + margin + int((total+margin)*0.18)
st.metric("Grand / PC", f"₹{grand:,} | Total ₹{grand*qty:,} | Bid: {bid_no}")

df = pd.DataFrame(list(prices.items()), columns=["Component", "Cost"])
st.dataframe(df, use_container_width=True)
st.download_button("📥 Download CSV", df.to_csv(index=False).encode(), f"{dept}_{bid_no}.csv", use_container_width=True)