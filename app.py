import streamlit as st

st.set_page_config(page_title="GeM ATC", layout="wide")
st.title("🇮🇳 GeM Bid App is Working ✅")
st.success("No error! Now I will add PDF reader.")

import pandas as pd
import PyPDF2

ALL_22 = ["Processor CPU", "MB", "RAM", "SSD", "MONITOR", "Keyboard & Mouse", "TPM 2.0", "CAMERA", "OS"]

st.sidebar.file_uploader("Upload PDF", type=["pdf"])
st.write("Components:", ALL_22)
