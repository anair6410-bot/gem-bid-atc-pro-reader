import streamlit as st
import pandas as pd
import re
import io
from pypdf import PdfReader
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment

st.set_page_config(page_title="GeM All Components", layout="wide")

def safe_str(x):
    if x is None: return ""
    try:
        if pd.isna(x): return ""
    except: pass
    return str(x).strip()
def safe_lower(x): return safe_str(x).lower()

def read_pdf_text(file):
    try:
        file.seek(0)
        r = PdfReader(file)
        return "\n".join([(p.extract_text() or "") for p in r.pages])
    except:
        return ""

# ===== COMPREHENSIVE CATEGORY RULES FOR ALL COMPONENTS =====
CATEGORY_RULES = {
    "MB": {
        "keywords": ["h610","b660","b760","h670","z790","b760m","h610m","motherboard","mainboard"," mb "],
        "requirement": "Intel H610 DDR5",
        "alternative_note": "If H610 not available: B660 DDR5, B760 DDR5, H670 DDR5, Z790 DDR5 are HIGHLY SUITABLE - All support 14th Gen, DDR5"
    },
    "processor CPU": {
        "keywords": ["i5 14400","i5-14400","i5 14500","i7","i3","processor","cpu","intel core","ryzen","14400","13400"],
        "requirement": "Intel Core i5 14400",
        "alternative_note": "If i5-14400 not available: i5-14400F, i5-14500, i5-13400, i7-12700 are suitable (same or higher)"
    },
    "RAM": {
        "keywords": ["ram","memory","ddr5","ddr4","16 gb","32 gb","8 gb","16gb","32gb","4800mhz","5600mhz"],
        "requirement": "16 GB DDR5",
        "alternative_note": "If 16GB DDR5 not available: 32GB DDR5 is suitable & better, 16GB DDR5 5600MHz is better speed, 2x8GB DDR5 is suitable"
    },
    "SSD": {
        "keywords": ["256 gb","256gb","512 gb","512gb","nvme","m.2","ssd 256","ssd 512"],
        "requirement": "256 GB NVMe SSD",
        "alternative_note": "If 256GB NVMe not available: 512GB NVMe, 1TB NVMe are suitable & better (higher capacity)"
    },
    "SSD(SECONDARY)": {
        "keywords": ["1 tb","1tb","2 tb","2tb","1000 gb","sata ssd","secondary","hdd ssd"],
        "requirement": "1 TB SATA SSD",
        "alternative_note": "If 1TB SATA SSD not available: 1TB NVMe, 2TB SATA SSD, 2TB NVMe are suitable & better"
    },
    "MONITOR": {
        "keywords": ["monitor","display","21.5","22 inch","24 inch","23.8","27 inch","ips","led","fhd"],
        "requirement": '21.5" IPS FHD Monitor',
        "alternative_note": "If 21.5 IPS not available: 22 IPS, 23.8 IPS, 24 IPS are suitable & better (larger size)"
    },
    "OS": {
        "keywords": ["windows","win 11","win11","os","operating system"],
        "requirement": "Windows 11 Pro",
        "alternative_note": "Must be Windows 11 Pro - Home not suitable"
    },
    "cabinet LTR": {
        "keywords": ["cabinet","chassis","tower","atx","micro atx","smps cabinet"],
        "requirement": "Tower Cabinet",
        "alternative_note": "Any Tower / ATX / Micro ATX cabinet suitable"
    },
    "smps WATT": {
        "keywords": ["smps","power supply","psu","200 watt","300 watt","450 watt","watt"],
        "requirement": "200 Watt SMPS",
        "alternative_note": "If 200W not available: 250W, 300W, 450W are suitable & better (higher wattage)"
    },
    "Keyboard & Mouse": {
        "keywords": ["keyboard","mouse","combo","wired","wireless"],
        "requirement": "Wired Keyboard + Mouse",
        "alternative_note": "Wired or Wireless combo both suitable"
    },
    "SPEAKER": {
        "keywords": ["speaker","audio"],
        "requirement": "Speaker",
        "alternative_note": "Internal or External speaker suitable"
    },
    "WIRELESS + BLUETOOTH": {
        "keywords": ["wifi","wireless","bluetooth","bt","wlan"],
        "requirement": "WiFi + Bluetooth",
        "alternative_note": "WiFi 5 / WiFi 6 / Bluetooth 5.0 all suitable"
    },
    "MS OFFICE": {
        "keywords": ["office","ms office","microsoft office","office 2021","office 2019"],
        "requirement": "MS Office",
        "alternative_note": "Office 2019 / 2021 / 365 all suitable"
    },
    "TPM 2.0": {
        "keywords": ["tpm","tpm 2.0"],
        "requirement": "TPM 2.0",
        "alternative_note": "TPM 2.0 Enabled motherboard"
    },
    "graphics CARD": {
        "keywords": ["graphics","gpu","graphic card","integrated","vga"],
        "requirement": "Integrated Graphics",
        "alternative_note": "Integrated graphics suitable, dedicated GPU also suitable & better"
    },
}

st.markdown("""
<div style="background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); border-radius: 18px; padding: 18px 24px; color: white;">
<h3 style="margin:0; color:white;">🇮🇳 GeM - ALL Components From Master (RAM, SSD, MB, CPU, Monitor etc.)</h3>
<p style="margin:4px 0 0 0; opacity:0.7; font-size:12px;">If H610 not available → Shows B660/B760. If 16GB RAM not available → Shows 32GB. For ALL components.</p>
</div>
""", unsafe_allow_html=True)

c1,c2,c3 = st.columns(3)
with c1:
    atc_file = st.file_uploader("1. ATC PDF/Image", type=["pdf","jpg","jpeg","png"], key="atc")
with c2:
    bid_file = st.file_uploader("2. Bid PDF", type=["pdf"], key="bid")
with c3:
    master_file = st.file_uploader("3. Master Excel", type=["xlsx","xls","csv"], key="master")

if master_file:
    df_raw = pd.read_excel(master_file) if not master_file.name.endswith('.csv') else pd.read_csv(master_file)
    df_raw = df_raw.fillna("")

    st.success(f"✅ Master Loaded: {len(df_raw)} rows | Columns: {list(df_raw.columns)}")
    st.dataframe(df_raw.head(8), use_container_width=True)

    # Find model column
    model_col = df_raw.columns[0]
    for c in df_raw.columns:
        if any(k in str(c).lower() for k in ["model","product","name","item","description"]):
            model_col = c
            break

    # Create categorized master
    def get_category_for_row(row_text):
        rt = safe_lower(row_text)
        for cat, rule in CATEGORY_RULES.items():
            for kw in rule["keywords"]:
                if safe_lower(kw) in rt:
                    return cat
        return "OTHER"

    df_raw['CATEGORY'] = df_raw.apply(lambda r: get_category_for_row(" ".join([safe_str(r[c]) for c in df_raw.columns])), axis=1)
    df_raw['MODEL_TEXT'] = df_raw.apply(lambda r: safe_str(r[model_col]), axis=1)

    # Show category count
    st.markdown("### 📊 Your Master Sheet Category Count (What will show in Excel):")
    cat_count = df_raw['CATEGORY'].value_counts()
    st.dataframe(cat_count, use_container_width=True)

    # Create Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "All Components - Master"

    thin = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    bold = Font(bold=True, size=11)
    h_font = Font(bold=True, color="FFFFFF", size=11)
    h_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    blue = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")
    green = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid")
    yellow = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
    red = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")

    bid_text = ""
    bid_no = "GEM/BID/7936262"
    if bid_file:
        bid_text = read_pdf_text(bid_file)
        import re
        m = re.search(r'GEM\/\d{4}\/B\/\d+', bid_text.replace(" ","").upper())
        if m: bid_no = m.group(0)

    ws.merge_cells('A1:E1')
    ws['A1'] = f"Bid: {bid_no} | ALL COMPONENTS - Shows all products from YOUR Master Sheet per category (RAM, SSD, MB, CPU, Monitor etc.)"
    ws['A1'].font = Font(bold=True, size=11)
    ws['A1'].fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")

    headers = ["PARAMETER", "Bid Requirement", "Your Master Sheet Products (ALL from that category)", "Details / Specs", "Alternative Logic - Why Suitable?"]
    for i,h in enumerate(headers, start=1):
        c = ws.cell(row=3, column=i, value=h)
        c.font = h_font
        c.fill = h_fill
        c.border = thin
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    row_num = 4
    for param, rule in CATEGORY_RULES.items():
        req = rule["requirement"]
        alt_note = rule["alternative_note"]

        # Get all master products for this category
        matched = df_raw[df_raw['CATEGORY'] == param]

        ws.cell(row=row_num, column=1, value=param.upper()).font = bold
        ws.cell(row=row_num, column=1).border = thin
        ws.cell(row=row_num, column=2, value=req).border = thin
        ws.cell(row=row_num, column=2).fill = blue
        ws.cell(row=row_num, column=2).alignment = Alignment(wrap_text=True)

        if matched.empty:
            ws.cell(row=row_num, column=3, value=f"No {param} found in Master - Check Master has keywords: {', '.join(rule['keywords'][:4])}").border = thin
            ws.cell(row=row_num, column=3).fill = red
            ws.cell(row=row_num, column=4, value="—").border = thin
            ws.cell(row=row_num, column=5, value=alt_note).border = thin
            ws.cell(row=row_num, column=5).fill = yellow
            ws.cell(row=row_num, column=5).alignment = Alignment(wrap_text=True)
            row_num += 1
        else:
            first = True
            for _, mrow in matched.iterrows():
                model = safe_str(mrow[model_col])
                full = " | ".join([safe_str(mrow[c]) for c in df_raw.columns if c not in ['CATEGORY','MODEL_TEXT']][:3])

                if not first:
                    ws.cell(row=row_num, column=1, value="").border = thin
                    ws.cell(row=row_num, column=2, value="").border = thin

                ws.cell(row=row_num, column=3, value=model).border = thin
                ws.cell(row=row_num, column=3).fill = green
                ws.cell(row=row_num, column=3).font = Font(bold=True, size=10)

                ws.cell(row=row_num, column=4, value=full[:100]).border = thin
                ws.cell(row=row_num, column=4).alignment = Alignment(wrap_text=True)

                ws.cell(row=row_num, column=5, value=alt_note).border = thin
                ws.cell(row=row_num, column=5).fill = yellow
                ws.cell(row=row_num, column=5).alignment = Alignment(wrap_text=True)

                row_num += 1
                first = False
        row_num += 1 # gap

    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 25
    ws.column_dimensions['C'].width = 35
    ws.column_dimensions['D'].width = 35
    ws.column_dimensions['E'].width = 45

    # Sheet 2: Full categorized master
    ws2 = wb.create_sheet("Your Master Categorized")
    ws2.append(list(df_raw.columns))
    for _, r in df_raw.iterrows():
        ws2.append([safe_str(r[c]) for c in df_raw.columns])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    st.success(f"✅ Excel Ready - Shows ALL Components: RAM, SSD, MB, CPU, Monitor etc. from YOUR Master!")

    # Show preview for RAM and MB
    st.markdown("### 🔍 Preview - RAM and MB from YOUR Master:")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**MB Category (H610/B660/B760):**")
        mb_df = df_raw[df_raw['CATEGORY']=="MB"]
        if not mb_df.empty:
            st.dataframe(mb_df[[model_col,'CATEGORY']].head(10), use_container_width=True)
        else:
            st.warning("No MB found in Master - Does your Master have words like H610, B660, B760, motherboard?")
    with col2:
        st.markdown("**RAM Category:**")
        ram_df = df_raw[df_raw['CATEGORY']=="RAM"]
        if not ram_df.empty:
            st.dataframe(ram_df[[model_col,'CATEGORY']].head(10), use_container_width=True)
        else:
            st.warning("No RAM found - Does your Master have words like RAM, DDR4, DDR5, 16GB?")

    st.download_button(
        "📥 Download EXCEL - ALL Components (RAM, MB, SSD, CPU etc.)",
        data=buf,
        file_name=f"FINAL_ALL_COMPONENTS_{bid_no.replace('/','_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        type="primary"
    )
else:
    st.info("⬆️ Upload Master Excel to see output")