import streamlit as st
import pandas as pd
import re
from PIL import Image, ImageEnhance, ImageFilter
import io

try:
    from pypdf import PdfReader
except:
    from PyPDF2 import PdfReader
try:
    import pytesseract
    OCR_AVAILABLE = True
except:
    OCR_AVAILABLE = False

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment

st.set_page_config(page_title="GeM All Products From Master", layout="wide", page_icon="🇮🇳")

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

def read_atc_any(file):
    filename = safe_lower(file.name)
    file.seek(0)
    if filename.endswith(('.jpg','.jpeg','.png','.bmp','.webp')):
        if not OCR_AVAILABLE:
            return "", "image", "OCR missing"
        try:
            pil_img = Image.open(file)
            img = pil_img.convert('L')
            w,h = img.size
            if w < 1800: img = img.resize((w*2, h*2), Image.LANCZOS)
            img = ImageEnhance.Contrast(img).enhance(2.5)
            text = pytesseract.image_to_string(img, config=r'--oem 3 --psm 6')
            return text, "image", "success"
        except Exception as e:
            return "", "image", str(e)
    elif filename.endswith('.pdf'):
        text = read_pdf_text(file)
        return text, "pdf", "text pdf"
    return "", "unknown", "unsupported"

# ===== CATEGORY DETECTION FROM MASTER =====
def detect_category(text):
    t = safe_lower(text)
    if any(k in t for k in ["h610", "b660", "b760", "h670", "z790", "motherboard", " mb ", "mainboard"]):
        return "MB"
    if any(k in t for k in ["i5", "i7", "i3", "processor", "cpu", "ryzen", "intel core"]):
        return "processor CPU"
    if any(k in t for k in ["ram", "ddr4", "ddr5", "memory"]):
        return "RAM"
    if "ssd" in t and ("1 tb" in t or "1000 gb" in t or "secondary" in t):
        return "SSD(SECONDARY)"
    if "ssd" in t or "nvme" in t:
        return "SSD"
    if any(k in t for k in ["monitor", "display", "21.5", "22 inch", "24 inch", "23.8"]):
        return "MONITOR"
    if "cabinet" in t or "chassis" in t or "tower" in t:
        return "cabinet LTR"
    if "smps" in t or "power supply" in t or "psu" in t:
        return "smps WATT"
    if "keyboard" in t or "mouse" in t or "combo" in t:
        return "Keyboard & Mouse,"
    if "windows" in t or "win 11" in t or "win11" in t or " os " in t:
        return "OS"
    if "tpm" in t:
        return "TPM 2.0"
    if "graphics" in t or "gpu" in t:
        return "graphics CARD"
    if "wifi" in t or "wireless" in t or "bluetooth" in t:
        return "WIRELESS + BLUETOOTH"
    if "office" in t:
        return "MS OFFICE"
    if "speaker" in t:
        return "SPEAKER"
    return "OTHER"

def create_final_excel(bid_meta, df_master_raw, atc_text):
    wb = Workbook()
    ws = wb.active
    ws.title = "All Compatible Products From Master"

    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    bold = Font(name='Calibri', bold=True, size=11)
    header_font = Font(name='Calibri', bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    exact_fill = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid")
    alt_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
    not_avail_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    blue_fill = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")

    # Normalize master columns
    df = df_master_raw.copy()
    df.columns = [safe_str(c).lower() for c in df.columns]
    # Find model column (most important)
    model_col = df.columns[0]
    for c in df.columns:
        if "model" in c or "product" in c or "name" in c:
            model_col = c
            break
    spec_col = None
    for c in df.columns:
        if "spec" in c or "desc" in c or "config" in c:
            spec_col = c
            break

    df = df.fillna("")
    # Add category column
    df['detected_category'] = df.apply(lambda row: detect_category(" ".join([safe_str(row.get(c,"")) for c in df.columns])), axis=1)

    # Header
    ws.merge_cells('A1:E1')
    ws['A1'] = f"BID: {bid_meta.get('bid_no','')} | Showing ALL products from Master per component category. If H610 not available, shows all other chipsets from Master"
    ws['A1'].font = Font(bold=True, size=11)
    ws['A1'].fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")

    headers = ["PARAMETER (Bid)", "Bid Requirement (ATC)", "All Products from Master (Same Category)", "Chipset / Model Details", "Suitability"]
    for i,h in enumerate(headers, start=1):
        cell = ws.cell(row=3, column=i, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    # Bid parameters
    bid_params = {
        "processor CPU": "Intel Core i5 14400",
        "MB": "Intel H610 DDR5",
        "RAM": "16 GB DDR5",
        "SSD": "256 GB NVMe",
        "SSD(SECONDARY)": "1 TB SATA SSD",
        "MONITOR": '21.5" IPS',
        "cabinet LTR": "Tower",
        "smps WATT": "200 Watt",
        "Keyboard & Mouse,": "Wired",
        "OS": "Windows 11 Pro",
        "TPM 2.0": "TPM 2.0",
        "graphics CARD": "Integrated",
        "WIRELESS + BLUETOOTH": "WiFi + BT",
        "MS OFFICE": "MS Office",
        "SPEAKER": "Speaker",
    }

    # Try to get real ATC specs
    if atc_text:
        for line in atc_text.split("\n"):
            ll = safe_lower(line)
            if "h610" in ll or "b660" in ll or "b760" in ll:
                bid_params["MB"] = line.strip()[:60]
            if "i5" in ll and "14400" in ll:
                bid_params["processor CPU"] = line.strip()[:60]
            if "16 gb" in ll and "ddr5" in ll:
                bid_params["RAM"] = line.strip()[:60]

    row_num = 4
    for param, req in bid_params.items():
        # Find all master products for this category
        matched = df[df['detected_category'] == param]

        ws.cell(row=row_num, column=1, value=param.upper()).font = bold
        ws.cell(row=row_num, column=1).border = thin_border
        ws.cell(row=row_num, column=2, value=req).border = thin_border
        ws.cell(row=row_num, column=2).fill = blue_fill

        if matched.empty:
            ws.cell(row=row_num, column=3, value="No product of this category in Master Sheet").border = thin_border
            ws.cell(row=row_num, column=3).fill = not_avail_fill
            ws.cell(row=row_num, column=4, value="—").border = thin_border
            ws.cell(row=row_num, column=5, value="❌ Not in Master").border = thin_border
            ws.cell(row=row_num, column=5).fill = not_avail_fill
            row_num += 1
        else:
            first = True
            for _, mrow in matched.iterrows():
                model_val = safe_str(mrow.get(model_col,""))
                spec_val = safe_str(mrow.get(spec_col,"")) if spec_col else ""
                full_text = " ".join([safe_str(mrow.get(c,"")) for c in df.columns if c!='detected_category'])

                if not first:
                    ws.cell(row=row_num, column=1, value="").border = thin_border
                    ws.cell(row=row_num, column=2, value="").border = thin_border

                ws.cell(row=row_num, column=3, value=model_val).border = thin_border
                ws.cell(row=row_num, column=3).fill = exact_fill if safe_lower(req).split()[0] in safe_lower(model_val) else alt_fill
                ws.cell(row=row_num, column=3).font = Font(bold=True, size=10)

                ws.cell(row=row_num, column=4, value=spec_val or full_text[:80]).border = thin_border
                ws.cell(row=row_num, column=4).alignment = Alignment(wrap_text=True)

                # Suitability logic
                if param == "MB":
                    if "h610" in safe_lower(model_val) or "h610" in safe_lower(spec_val):
                        suit = "✅ Exact Match - H610"
                    elif any(x in safe_lower(model_val+spec_val) for x in ["b660","b760","h670","z790"]):
                        suit = f"⚠️ Suitable Alternative - {model_val} (Better than H610, supports 14th Gen)"
                    else:
                        suit = "⚠️ Same Category - Check DDR5 support"
                elif param == "processor CPU":
                    if "14400" in safe_lower(model_val):
                        suit = "✅ Exact Match"
                    elif any(x in safe_lower(model_val) for x in ["14500","14600","12700","i7","i9"]):
                        suit = "⚠️ Suitable - Higher than required"
                    else:
                        suit = "Check generation"
                else:
                    suit = "Suitable - Same Category"

                ws.cell(row=row_num, column=5, value=suit).border = thin_border
                ws.cell(row=row_num, column=5).alignment = Alignment(wrap_text=True)

                row_num += 1
                first = False

        # Gap
        row_num += 1

    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 28
    ws.column_dimensions['C'].width = 35
    ws.column_dimensions['D'].width = 35
    ws.column_dimensions['E'].width = 40

    # Sheet 2: Master category summary
    ws2 = wb.create_sheet("Master Category Summary")
    ws2.append(["Category Detected", "Product/Model from Master", "Full Row"])
    for _, r in df.iterrows():
        ws2.append([r['detected_category'], safe_str(r.get(model_col,"")), " | ".join([safe_str(r.get(c,"")) for c in df.columns if c!='detected_category'])[:100])

    ws2.column_dimensions['A'].width = 20
    ws2.column_dimensions['B'].width = 30
    ws2.column_dimensions['C'].width = 60

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer, df

# UI
st.markdown("""
<div style="background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); border-radius: 18px; padding: 18px 24px; color: white;">
<div style="font-size:20px; font-weight:800;">🇮🇳 GeM — Show ALL Master Products Per Component</div>
<div style="font-size:11px; opacity:0.7;">If H610 not available, shows all chipsets from YOUR Master Sheet</div>
</div>
<div style="height:4px; background: linear-gradient(90deg, #FF9933 0%, #FFF 50%, #138808 100%); border-radius:10px; margin:10px 0;"></div>
""", unsafe_allow_html=True)

if st.button("🗑️ Clear All", type="primary"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

c1,c2,c3 = st.columns(3)
with c1:
    st.markdown("**📄 ATC — PDF/Image**")
    atc_file = st.file_uploader("ATC", type=["pdf","jpg","jpeg","png","bmp","webp"], key="atc", label_visibility="collapsed")
    atc_text, atc_type, atc_msg = "", "", ""
    if atc_file:
        atc_text, atc_type, atc_msg = read_atc_any(atc_file)
        if atc_text: st.success(f"✅ ATC: {len(atc_text)} chars")
        else: st.warning(atc_msg)
with c2:
    st.markdown("**📑 Bid PDF**")
    bid_file = st.file_uploader("Bid", type=["pdf"], key="bid", label_visibility="collapsed")
    bid_meta = {"bid_no": "GEM/2026/B/7936262"}
    bid_text = ""
    if bid_file:
        bid_text = read_pdf_text(bid_file)
        import re
        m = re.search(r'GEM\/\d{4}\/B\/\d{4,10}', safe_str(bid_text).replace(" ","").upper())
        bid_meta['bid_no'] = m.group(0) if m else bid_meta['bid_no']
        st.success(f"✅ {bid_meta['bid_no']}")
with c3:
    st.markdown("**📊 Master Excel**")
    master_file = st.file_uploader("Master", type=["xlsx","xls","csv"], key="master", label_visibility="collapsed")
    df_master = None
    if master_file:
        try:
            df_master = pd.read_excel(master_file) if not master_file.name.endswith('.csv') else pd.read_csv(master_file)
            df_master = df_master.fillna("")
            st.success(f"✅ {len(df_master)} rows")
            st.dataframe(df_master.head(5), use_container_width=True)
        except Exception as e:
            st.error(f"{e}")

if atc_file and bid_file and master_file and df_master is not None and not df_master.empty:
    st.markdown("---")
    st.markdown("### 🧠 Final Excel — All Products from Master by Category")

    excel_buffer, df_cat = create_final_excel(bid_meta, df_master, atc_text)

    st.success("✅ Generated — Now shows ALL chipsets/products from YOUR Master")

    st.markdown("""
    **How this works now:**
    - It reads YOUR Master Sheet and auto-detects category (H610/B660/B760 etc = MB)
    - For **MB** parameter, it shows **EVERY motherboard** from your Master
    - If H610 not found, it shows B660, B760, Z790 etc that ARE in your Master with note "Suitable Alternative - Better than H610"
    - Same for Processor, RAM, SSD etc — all products from Master listed
    """)

    st.dataframe(df_cat[['detected_category'] + [c for c in df_cat.columns if c!='detected_category'][:2]].head(20), use_container_width=True)

    st.download_button(
        label="📥 Download EXCEL — All Master Products Per Component (Final)",
        data=excel_buffer,
        file_name=f"GeM_All_Master_Products_{safe_str(bid_meta.get('bid_no','')).replace('/','_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        type="primary"
    )
elif atc_file or bid_file or master_file:
    st.info("⬆️ Upload all 3 files")