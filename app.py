import streamlit as st
import pandas as pd
from io import BytesIO
import PyPDF2

st.set_page_config(page_title="GeM ATC Pro", page_icon="🇮🇳", layout="wide")

st.markdown("""
<style>
.header {background: linear-gradient(90deg, #0f172a, #1e40af); padding:22px; border-radius:15px; color:white; text-align:center; margin-bottom:20px;}
div[data-testid="stSidebar"] {background:#f1f5f9;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="header"><h1>🇮🇳 GeM Bid - SMART ATC READER PRO</h1><p>Upload ANY Bank ATC PDF → Shows ONLY mentioned components from your 22 list</p></div>', unsafe_allow_html=True)

ALL_22 = [
    "Processor CPU", "MB", "Graphics CARD", "OS", "RAM", "SSD",
    "SSD (SECONDARY)", "Cabinet LTR", "SMPS WATT", "ADAPTER",
    "DVD WRITER", "MONITOR", "SPEAKER", "WIRELESS + BLUETOOTH",
    "MS OFFICE", "CHASSIS SWITCH", "TPM 2.0", "CAMERA",
    "ANTIVIRUS", "DP PORT", "SERIAL COM PORT+PARALLEL", "Keyboard & Mouse"
]

KEYWORDS = {
    "Processor CPU": ["processor", "cpu", "intel", "i5", "ryzen", "14400"],
    "MB": ["motherboard", "baseboard", "chipset", "h610"],
    "Graphics CARD": ["graphics", "gpu", "uhd"],
    "OS": ["operating system", "windows", "os"],
    "RAM": ["ram", "memory", "ddr5", "16 gb"],
    "SSD": ["ssd", "nvme", "512 gb", "256 gb"],
    "SSD (SECONDARY)": ["1 tb", "secondary", "sata ssd", "hdd"],
    "Cabinet LTR": ["cabinet", "chassis", "tower", "sff"],
    "SMPS WATT": ["smps", "power supply"],
    "ADAPTER": ["adapter"],
    "DVD WRITER": ["dvd", "optical"],
    "MONITOR": ["monitor", "display", "21.5", "24 inch", "1920"],
    "SPEAKER": ["speaker", "audio"],
    "WIRELESS + BLUETOOTH": ["wireless", "bluetooth", "wifi"],
    "MS OFFICE": ["ms office", "office 2021"],
    "CHASSIS SWITCH": ["chassis intrusion", "intrusion"],
    "TPM 2.0": ["tpm", "trusted"],
    "CAMERA": ["webcam", "camera"],
    "ANTIVIRUS": ["antivirus"],
    "DP PORT": ["hdmi", "dp port", "display port"],
    "SERIAL COM PORT+PARALLEL": ["serial", "com port", "parallel"],
    "Keyboard & Mouse": ["keyboard", "mouse"]
}

PRESET = {
    "Processor CPU":14500, "MB":4250, "Graphics CARD":0, "OS":600, "RAM":17500,
    "SSD":3650, "SSD (SECONDARY)":11500, "Cabinet LTR":1850, "SMPS WATT":0,
    "ADAPTER":0, "DVD WRITER":0, "MONITOR":4450, "SPEAKER":0,
    "WIRELESS + BLUETOOTH":0, "MS OFFICE":0, "CHASSIS SWITCH":0,
    "TPM 2.0":700, "CAMERA":500, "ANTIVIRUS":0, "DP PORT":0,
    "SERIAL COM PORT+PARALLEL":0, "Keyboard & Mouse":350
}

def extract_text(pdf_file):
    text = ""
    reader = PyPDF2.PdfReader(pdf_file)
    for page in reader.pages:
        text += (page.extract_text() or "") + "\n"
    return text.lower()

def detect(text):
    found=[]
    for comp,kws in KEYWORDS.items():
        if any(k in text for k in kws):
            found.append(comp)
    return found

with st.sidebar:
    st.subheader("📤 Upload ATC")
    f = st.file_uploader("BOI / SBI / Army ATC PDF", type=["pdf"])
    dept = st.text_input("Department", "BANK OF INDIA")
    qty = st.number_input("Qty", 1, 1000, 65)
    margin = st.number_input("Margin", 4000)

if f:
    txt = extract_text(f)
    detected = detect(txt)
    if not detected:
        st.warning("Scanned PDF - showing all 22")
        detected = ALL_22
    else:
        st.success(f"✅ Found {len(detected)} components in ATC")
        with st.expander("View ATC Text"):
            st.text(txt[:5000])
else:
    st.info("👆 Upload ATC PDF to auto-filter. Showing all 22 for now.")
    detected = ALL_22

st.subheader(f"💰 Costing - {len(detected)}/22 Components (ATC Based)")

prices={}
total=0
cols=st.columns(4)
for i, comp in enumerate(detected):
    with cols[i%4]:
        with st.container(border=True):
            st.markdown(f"**🔹 {comp}**")
            p = st.number_input(comp, value=PRESET.get(comp, 500), key=comp, label_visibility="collapsed")
            prices[comp]=p
            total+=p
            st.caption(f"₹{p:,}")

sub = total + margin
gst = int(sub*0.18)
grand = sub+gst
total_bid = grand*qty

st.divider()
c1,c2,c3,c4=st.columns(4)
c1.metric("Total Cost", f"₹{total:,}")
c2.metric("Grand / PC", f"₹{grand:,}")
c3.metric("Total Bid", f"₹{total_bid:,}")
c4.metric("Filter", f"{len(detected)}/22")

df = pd.DataFrame(list(prices.items()), columns=["Component (ATC Filtered)", "Cost"])
df.loc[len(df)] = ["TOTAL COST", total]
df.loc[len(df)] = ["MARGIN", margin]
df.loc[len(df)] = ["GST 18%", gst]
df.loc[len(df)] = ["GRAND TOTAL", grand]

st.dataframe(df, use_container_width=True, hide_index=True)

def to_excel(d):
    out=BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as w:
        d.to_excel(w, index=False)
    return out.getvalue()

st.download_button("📥 Download Excel (ATC Based)", to_excel(df), file_name=f"{dept}_{grand}.xlsx", type="primary", use_container_width=True)
