import streamlit as st
import pandas as pd
try:
    from pypdf import PdfReader
except:
    from PyPDF2 import PdfReader

st.set_page_config(page_title="GeM ATC Pro", page_icon="🇮🇳", layout="wide")

st.markdown("""
<style>
.header {background: linear-gradient(90deg, #0f172a, #1e40af); padding:22px; border-radius:15px; color:white; text-align:center; margin-bottom:18px;}
div[data-testid="stMetric"] {background:#f8fafc; border:1px solid #e2e8f0; padding:12px; border-radius:10px;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="header"><h1>🇮🇳 GeM Bid - SMART ATC READER PRO</h1><p>Upload BOI / SBI / Army ATC → App shows ONLY mentioned components from your 22 list</p></div>', unsafe_allow_html=True)

ALL_22 = [
    "Processor CPU", "MB", "Graphics CARD", "OS", "RAM", "SSD",
    "SSD (SECONDARY)", "Cabinet LTR", "SMPS WATT", "ADAPTER",
    "DVD WRITER", "MONITOR", "SPEAKER", "WIRELESS + BLUETOOTH",
    "MS OFFICE", "CHASSIS SWITCH", "TPM 2.0", "CAMERA",
    "ANTIVIRUS", "DP PORT", "SERIAL COM PORT+PARALLEL", "Keyboard & Mouse"
]

PRESET = {
    "Processor CPU":14500, "MB":4250, "Graphics CARD":0, "OS":600, "RAM":17500,
    "SSD":3650, "SSD (SECONDARY)":11500, "Cabinet LTR":1850, "SMPS WATT":0,
    "ADAPTER":0, "DVD WRITER":0, "MONITOR":4450, "SPEAKER":0,
    "WIRELESS + BLUETOOTH":0, "MS OFFICE":0, "CHASSIS SWITCH":0,
    "TPM 2.0":700, "CAMERA":500, "ANTIVIRUS":0, "DP PORT":0,
    "SERIAL COM PORT+PARALLEL":0, "Keyboard & Mouse":350
}

KEYWORDS = {
    "Processor CPU": ["processor", "cpu", "intel", "i5", "ryzen", "14400"],
    "MB": ["motherboard", "baseboard", "chipset", "h610"],
    "Graphics CARD": ["graphics", "gpu"],
    "OS": ["operating system", "windows"],
    "RAM": ["ram", "memory", "ddr5", "16 gb"],
    "SSD": ["ssd", "nvme", "512", "256"],
    "SSD (SECONDARY)": ["1 tb", "secondary", "sata ssd", "hdd"],
    "Cabinet LTR": ["cabinet", "tower", "sff"],
    "SMPS WATT": ["smps", "power supply"],
    "ADAPTER": ["adapter"],
    "DVD WRITER": ["dvd", "optical"],
    "MONITOR": ["monitor", "display", "21.5", "24 inch"],
    "SPEAKER": ["speaker"],
    "WIRELESS + BLUETOOTH": ["wireless", "bluetooth", "wifi"],
    "MS OFFICE": ["ms office", "office 2021"],
    "CHASSIS SWITCH": ["chassis intrusion", "intrusion"],
    "TPM 2.0": ["tpm", "trusted"],
    "CAMERA": ["webcam", "camera"],
    "ANTIVIRUS": ["antivirus"],
    "DP PORT": ["hdmi", "dp port"],
    "SERIAL COM PORT+PARALLEL": ["serial", "com port", "parallel"],
    "Keyboard & Mouse": ["keyboard", "mouse"]
}

def extract_text(pdf):
    reader = PdfReader(pdf)
    text = ""
    for p in reader.pages:
        text += (p.extract_text() or "") + " "
    return text.lower()

def detect(text):
    found=[]
    for comp, kws in KEYWORDS.items():
        if any(k in text for k in kws):
            found.append(comp)
    return found if len(found)>=3 else ALL_22

# Sidebar
with st.sidebar:
    st.subheader("📤 STEP 1: Upload ATC")
    f = st.file_uploader("BOI / SBI / Army ATC PDF", type=["pdf"])
    st.divider()
    dept = st.text_input("Department", "BANK OF INDIA")
    bid_no = st.text_input("Bid No", "GEM/2026/B/7936262")
    qty = st.number_input("Quantity", 1, 1000, 65)
    margin = st.number_input("Your Margin / PC", value=4000)

if f:
    txt = extract_text(f)
    detected = detect(txt)
    st.success(f"✅ ATC Read! Found {len(detected)} / 22 components mentioned")
    with st.expander("👁️ See Detected"):
        st.write(", ".join(detected))
else:
    st.info("👆 Upload ATC PDF to auto-filter. Showing all 22 for now.")
    detected = ALL_22

# Costing Cards
st.subheader(f"💰 Costing - {len(detected)}/22 Components")

prices={}
total=0
cols=st.columns(4)
for i, comp in enumerate(detected):
    with cols[i%4]:
        with st.container(border=True):
            st.markdown(f"**🔹 {comp}**")
            p = st.number_input(comp, value=PRESET.get(comp,0), key=comp, label_visibility="collapsed")
            prices[comp]=p
            total+=p
            if p==0:
                st.caption("Not Costed")
            else:
                st.caption(f"₹{p:,}")

# Totals
sub = total + margin
gst = int(sub*0.18)
grand = sub+gst
total_bid = grand*qty

st.divider()
c1,c2,c3,c4 = st.columns(4)
c1.metric("Total Cost", f"₹{total:,}")
c2.metric("Margin", f"₹{margin:,}")
c3.metric("Grand / PC", f"₹{grand:,}", f"+18% GST ₹{gst}")
c4.metric("Total Bid Value", f"₹{total_bid:,}")

df = pd.DataFrame(list(prices.items()), columns=["Component (ATC Filtered)", "Cost (₹)"])
df.loc[len(df)] = ["TOTAL COST", total]
df.loc[len(df)] = ["MARGIN", margin]
df.loc[len(df)] = ["GST 18%", gst]
df.loc[len(df)] = ["GRAND TOTAL", grand]

st.dataframe(df, use_container_width=True, hide_index=True)

# CSV Only - No Excel
csv = df.to_csv(index=False).encode('utf-8')
st.download_button("📥 Download CSV (No Excel)", csv, file_name=f"{dept}_{grand}.csv", mime="text/csv", type="primary", use_container_width=True)