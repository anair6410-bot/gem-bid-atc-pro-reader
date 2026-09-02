import streamlit as st
import pandas as pd

# Try both imports
try:
    from pypdf import PdfReader
except:
    from PyPDF2 import PdfReader

st.set_page_config(page_title="GeM ATC Pro", page_icon="🇮🇳", layout="wide")
st.title("🇮🇳 GeM Bid - SMART ATC READER ✅ Working")

ALL_22 = ["Processor CPU", "MB", "Graphics CARD", "OS", "RAM", "SSD","SSD (SECONDARY)", "Cabinet LTR", "SMPS WATT", "ADAPTER","DVD WRITER", "MONITOR", "SPEAKER", "WIRELESS + BLUETOOTH","MS OFFICE", "CHASSIS SWITCH", "TPM 2.0", "CAMERA","ANTIVIRUS", "DP PORT", "SERIAL COM PORT+PARALLEL", "Keyboard & Mouse"]

KEYWORDS = {
    "Processor CPU": ["processor", "cpu", "i5", "ryzen"],
    "MB": ["motherboard", "chipset"],
    "RAM": ["ram", "memory", "ddr5"],
    "SSD": ["ssd", "nvme"],
    "MONITOR": ["monitor", "display"],
    "TPM 2.0": ["tpm"],
    "OS": ["windows", "operating system"],
    "Keyboard & Mouse": ["keyboard", "mouse"]
}

def get_text(pdf):
    try:
        reader = PdfReader(pdf)
        text = ""
        for p in reader.pages:
            text += (p.extract_text() or "") + " "
        return text.lower()
    except Exception as e:
        st.error(f"Error: {e}")
        return ""

def detect(text):
    found = []
    for comp, kws in KEYWORDS.items():
        if any(k in text for k in kws):
            found.append(comp)
    return found if len(found) >= 3 else ALL_22

with st.sidebar:
    f = st.file_uploader("Upload ATC PDF", type=["pdf"])
    qty = st.number_input("Qty", 1, 1000, 65)
    margin = st.number_input("Margin", 4000)

detected = ALL_22
if f:
    txt = get_text(f)
    detected = detect(txt)
    st.success(f"Detected {len(detected)} components")

st.subheader(f"Costing - {len(detected)}/22")
prices = {}
total = 0
cols = st.columns(3)
for i, comp in enumerate(detected):
    with cols[i%3]:
        with st.container(border=True):
            st.write(f"**{comp}**")
            p = st.number_input(comp, value=1000, key=comp, label_visibility="collapsed")
            prices[comp] = p
            total += p

grand = total + margin + int((total+margin)*0.18)
st.metric("Grand Total", f"₹{grand:,} | Total Bid ₹{grand*qty:,}")

df = pd.DataFrame(list(prices.items()), columns=["Component", "Cost"])
st.dataframe(df, use_container_width=True)
st.download_button("📥 Download CSV", df.to_csv(index=False).encode(), "ATC.csv", use_container_width=True)