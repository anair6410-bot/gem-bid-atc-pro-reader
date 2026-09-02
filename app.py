import streamlit as st
import pandas as pd
from io import BytesIO
import PyPDF2

st.set_page_config(page_title="GeM ATC Pro", page_icon="🇮🇳", layout="wide")

# --- CSS FOR BEAUTIFUL LOOK ---
st.markdown("""
<style>
.header {background: linear-gradient(90deg, #0f172a, #1e40af); padding:20px; border-radius:15px; color:white; text-align:center; margin-bottom:20px;}
div[data-testid="stSidebar"] {background:#f1f5f9;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="header"><h1>🇮🇳 GeM Bid - SMART ATC READER</h1><p>Upload BOI / SBI / PNB ATC → App shows ONLY mentioned components from your 22 list</p></div>', unsafe_allow_html=True)

# YOUR 22 COMPONENTS
ALL_22 = [
    "Processor CPU", "MB", "Graphics CARD", "OS", "RAM", "SSD",
    "SSD (SECONDARY)", "Cabinet LTR", "SMPS WATT", "ADAPTER",
    "DVD WRITER", "MONITOR", "SPEAKER", "WIRELESS + BLUETOOTH",
    "MS OFFICE", "CHASSIS SWITCH", "TPM 2.0", "CAMERA",
    "ANTIVIRUS", "DP PORT", "SERIAL COM PORT+PARALLEL", "Keyboard & Mouse"
]

KEYWORDS = {
    "Processor CPU": ["processor", "cpu", "intel", "core i5", "ryzen", "14400", "7600"],
    "MB": ["motherboard", "baseboard", "chipset"],
    "Graphics CARD": ["graphics", "gpu"],
    "OS": ["operating system", "windows", "os"],
    "RAM": ["ram", "system memory", "ddr5", "memory"],
    "SSD": ["ssd", "nvme", "256 gb", "512 gb", "storage"],
    "SSD (SECONDARY)": ["1 tb", "sata ssd", "secondary", "hdd"],
    "Cabinet LTR": ["cabinet", "tower", "sff"],
    "SMPS WATT": ["smps", "power supply"],
    "ADAPTER": ["adapter"],
    "DVD WRITER": ["dvd writer", "optical"],
    "MONITOR": ["monitor", "display", "21.5", "24 inch"],
    "SPEAKER": ["speaker", "audio"],
    "WIRELESS + BLUETOOTH": ["wireless", "bluetooth", "wifi"],
    "MS OFFICE": ["ms office", "microsoft office"],
    "CHASSIS SWITCH": ["chassis", "intrusion"],
    "TPM 2.0": ["tpm"],
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

def extract_text_from_pdf(pdf_file):
    text = ""
    reader = PyPDF2.PdfReader(pdf_file)
    for page in reader.pages:
        text += (page.extract_text() or "") + "\n"
    return text.lower()

def detect_components(text):
    found = []
    for comp, kws in KEYWORDS.items():
        for kw in kws:
            if kw in text:
                found.append(comp)
                break
    return found

# --- SIDEBAR ---
with st.sidebar:
    st.subheader("📤 STEP 1: Upload ATC")
    atc_file = st.file_uploader("Upload ATC PDF (BOI/SBI/Army)", type=["pdf"])

    st.divider()
    st.subheader("📋 STEP 2: Details")
    dept = st.text_input("Department", "BANK OF INDIA")
    bid_no = st.text_input("Bid No", "GEM/2026/B/7936262")
    qty = st.number_input("Quantity", 1, 1000, 65)
    margin = st.number_input("Company Margin", 4000)

# --- MAIN LOGIC ---
if atc_file:
    pdf_text = extract_text_from_pdf(atc_file)
    detected = detect_components(pdf_text)

    if len(detected) == 0:
        st.warning("⚠️ PDF is scanned image (text not readable). Showing all 22. Please upload searchable PDF.")
        detected = ALL_22
    else:
        st.success(f"✅ ATC Read Success! Found {len(detected)} components mentioned in ATC")
        with st.expander("👁️ See what ATC contains"):
            st.text(pdf_text[:6000])
            st.write("**Detected:**", ", ".join(detected))
else:
    st.info("👆 Please upload BOI ATC PDF to test. Currently showing all 22 components.")
    detected = ALL_22

# --- SHOW ONLY DETECTED COMPONENTS ---
st.subheader(f"💰 Costing - Showing {len(detected)} / 22 Components (ATC Based)")

prices = {}
total_cost = 0
cols = st.columns(4)

for i, comp in enumerate(detected):
    with cols[i % 4]:
        with st.container(border=True):
            st.markdown(f"**🔹 {comp}**")
            default_price = PRESET.get(comp, 0)
            price = st.number_input(f"price_{comp}", value=default_price, key=comp, label_visibility="collapsed")
            prices[comp] = price
            total_cost += price
            st.caption(f"₹{price:,}")

# --- TOTALS ---
sub_total = total_cost + margin
gst = int(sub_total * 0.18)
grand = sub_total + gst
total_bid_value = grand * qty

st.divider()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Cost", f"₹{total_cost:,}")
c2.metric("Grand Total / PC", f"₹{grand:,}", delta="18% GST")
c3.metric("Total Bid Value", f"₹{total_bid_value:,}")
c4.metric("ATC Filter", f"{len(detected)}/22 Shown")

# Table
df = pd.DataFrame(list(prices.items()), columns=["Component (From ATC)", "Cost (₹)"])
df.loc[len(df)] = ["---", "---"]
df.loc[len(df)] = ["TOTAL COST", total_cost]
df.loc[len(df)] = ["MARGIN", margin]
df.loc[len(df)] = ["GST 18%", gst]
df.loc[len(df)] = ["GRAND TOTAL", grand]

st.dataframe(df, use_container_width=True, hide_index=True)

def to_excel(dataframe):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        dataframe.to_excel(writer, index=False, sheet_name="ATC Costing")
    return output.getvalue()

st.download_button(
    "📥 Download Excel - Only ATC Components",
    data=to_excel(df),
    file_name=f"{dept}_ATC_Based_{grand}.xlsx",
    type="primary",
    use_container_width=True
)