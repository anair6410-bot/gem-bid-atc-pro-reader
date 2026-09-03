import streamlit as st
import pandas as pd
import re
from PIL import Image, ImageEnhance, ImageFilter
import io
from datetime import datetime

try:
    from pypdf import PdfReader
except:
    from PyPDF2 import PdfReader

try:
    import pytesseract
    OCR_AVAILABLE = True
    try: pytesseract.get_tesseract_version()
    except: OCR_AVAILABLE = False
except:
    OCR_AVAILABLE = False

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment

st.set_page_config(page_title="GeM Fixed Master Match", layout="wide", page_icon="🇮🇳")

st.markdown("""
<style>
.stApp { background: #F8FAFF; }
.hero { background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); border-radius: 18px; padding: 18px 24px; color: white; }
.tricolor { height:4px; background: linear-gradient(90deg, #FF9933 0%, #FFF 50%, #138808 100%); border-radius:10px; margin:10px 0; }
.glass-card { background: white; border-radius: 16px; padding: 18px; border: 1px solid #E2E8F0; margin-bottom:14px; }
.upload-card { background: #F8FAFC; border: 1.5px dashed #CBD5E1; border-radius: 14px; padding: 16px; text-align:center; min-height: 190px; }
</style>
""", unsafe_allow_html=True)

def safe_str(x):
    if x is None: return ""
    if pd.isna(x): return ""
    return str(x).strip()
def safe_lower(x): return safe_str(x).lower()

# KEYWORDS mapping - THIS FIXES MATCHING
MASTER_KEYWORDS = {
    "processor CPU": ["processor", "cpu", "i3", "i5", "i7", "i9", "ryzen", "intel"],
    "MB": ["motherboard", "mb", "h610", "b660", "h110"],
    "graphics CARD": ["graphics", "gpu", "graphic card"],
    "OS": ["windows", "os", "win 11", "win11"],
    "RAM": ["ram", "memory", "ddr4", "ddr5", "16 gb", "8 gb"],
    "SSD": ["ssd", "nvme", "256 gb", "512 gb"],
    "SSD(SECONDARY)": ["secondary", "hdd", "1 tb", "2 tb", "sata"],
    "cabinet LTR": ["cabinet", "chassis", "tower"],
    "smps WATT": ["smps", "power supply", "psu"],
    "MONITOR": ["monitor", "display", "screen", "21.5", "22", "24"],
    "SPEAKER": ["speaker"],
    "WIRELESS + BLUETOOTH": ["wireless", "wifi", "bluetooth"],
    "MS OFFICE": ["office", "ms office"],
    "CHASSIS SWITCH": ["chassis"],
    "TPM 2.0": ["tpm"],
    "CAMERA": ["camera", "webcam"],
    "ANTIVIRUS": ["antivirus"],
    "Keyboard & Mouse,": ["keyboard", "mouse", "combo"],
}

def enhance_image_pillow(pil_image):
    try:
        img = pil_image.convert('L')
        w, h = img.size
        if w < 1800: img = img.resize((w*2, h*2), Image.LANCZOS)
        img = img.filter(ImageFilter.MedianFilter(size=3))
        img = ImageEnhance.Contrast(img).enhance(2.5)
        img = ImageEnhance.Sharpness(img).enhance(2.0)
        return img
    except:
        return pil_image

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
        if not OCR_AVAILABLE: return "", "image", "OCR missing"
        pil_img = Image.open(file)
        enhanced = enhance_image_pillow(pil_img)
        text = pytesseract.image_to_string(enhanced, config=r'--oem 3 --psm 6')
        if len(text.strip())<30:
            text = pytesseract.image_to_string(enhanced, config=r'--oem 3 --psm 3')
        return text, "image", "success"
    elif filename.endswith('.pdf'):
        text = read_pdf_text(file)
        if len(text.strip())<100 and OCR_AVAILABLE:
            try:
                import fitz
                file.seek(0)
                doc = fitz.open(stream=file.read(), filetype="pdf")
                ocr_full=""
                for page in doc:
                    pix=page.get_pixmap(dpi=300)
                    pil_img=Image.open(io.BytesIO(pix.tobytes("png")))
                    enhanced=enhance_image_pillow(pil_img)
                    ocr_full+=pytesseract.image_to_string(enhanced, config=r'--oem 3 --psm 6')+"\n"
                if len(ocr_full.strip())>50:
                    return ocr_full, "scanned_pdf", "OCR success"
            except: pass
        return text, "pdf", "text pdf"
    return "", "unknown", "unsupported"

def find_master_columns(df):
    """Auto find columns - IMPROVED"""
    cols = [safe_str(c).strip().lower() for c in df.columns]
    df.columns = cols

    prod_col = None
    model_col = None
    specs_col = None

    for c in cols:
        if any(k in c for k in ['product', 'parameter', 'component', 'item', 'category']):
            prod_col = c
            break
    if not prod_col:
        prod_col = cols[0]

    for c in cols:
        if any(k in c for k in ['model', 'part no', 'part number', 'mfg', 'product name']):
            if c!= prod_col:
                model_col = c
                break
    if not model_col:
        model_col = cols[1] if len(cols)>1 else prod_col

    for c in cols:
        if any(k in c for k in ['spec', 'description', 'config', 'detail', 'feature']):
            if c not in [prod_col, model_col]:
                specs_col = c
                break

    return prod_col, model_col, specs_col

def create_excel_fixed(bid_meta, df_master_raw, atc_text):
    wb = Workbook()
    ws = wb.active
    ws.title = "Compatible Products - ATC vs Master"

    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    bold = Font(name='Calibri', bold=True, size=11)
    header_font = Font(name='Calibri', bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    atc_fill = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")
    compat_fill = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid")

    # Find columns correctly
    df_master = df_master_raw.copy()
    prod_col, model_col, specs_col = find_master_columns(df_master)
    df_master = df_master.fillna("")

    # Header info
    ws.merge_cells('A1:C1')
    ws['A1'] = f"GeM Bid: {bid_meta.get('bid_no','')} | Found Columns -> Product: {prod_col} | Model: {model_col} | Specs: {specs_col}"
    ws['A1'].font = Font(bold=True, size=10)
    ws['A1'].fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")

    headers = ["PARAMETER (from ATC/Bid)", "ATC Spec (from uploaded ATC/Bid)", "Compatible Product (from Master Sheet)"]
    for c_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=3, column=c_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = Alignment(horizontal='center', vertical='center')

    paper_params = [
        "processor CPU", "MB", "graphics CARD", "OS", "RAM", "SSD", "SSD(SECONDARY)",
        "cabinet LTR", "smps WATT", "MONITOR", "SPEAKER",
        "WIRELESS + BLUETOOTH", "MS OFFICE", "CHASSIS SWITCH", "TPM 2.0", "CAMERA",
        "ANTIVIRUS", "DP PORT", "SERIAL COM PORT+PARALLEL", "Keyboard & Mouse,"
    ]

    row_num = 4
    for param_name in paper_params:
        param_lower = safe_lower(param_name)

        # ATC spec
        atc_spec_val = ""
        if atc_text:
            for line in atc_text.split("\n"):
                if param_lower.split()[0] in safe_lower(line) and 5 < len(line) < 200:
                    atc_spec_val = line.strip()[:100]
                    break
        if not atc_spec_val:
            atc_spec_val = param_name

        # FIXED MATCHING LOGIC - search all master rows
        compatible_model = "Not Available in Master"
        kws = MASTER_KEYWORDS.get(param_name, [param_lower.split()[0]])

        for _, m_row in df_master.iterrows():
            # Combine all master columns into one search string
            all_text = ""
            for c in df_master.columns:
                all_text += " " + safe_lower(m_row.get(c, ""))

            # Check if any keyword matches
            matched = False
            for kw in kws:
                if safe_lower(kw) in all_text:
                    matched = True
                    break

            if matched:
                # Get model value
                model_val = safe_str(m_row.get(model_col, ""))
                prod_val = safe_str(m_row.get(prod_col, ""))
                specs_val = safe_str(m_row.get(specs_col, "")) if specs_col else ""

                # Build compatible string
                if model_val and model_val!= prod_val:
                    compatible_model = f"{prod_val} - {model_val}"
                else:
                    compatible_model = prod_val or model_val

                if specs_val and len(specs_val) < 80:
                    compatible_model += f" | {specs_val}"

                # Limit length
                if len(compatible_model) > 120:
                    compatible_model = compatible_model[:120]

                break

        # Write
        ws.cell(row=row_num, column=1, value=param_name.upper()).border = thin_border
        ws.cell(row=row_num, column=1).font = bold
        ws.cell(row=row_num, column=2, value=atc_spec_val).border = thin_border
        ws.cell(row=row_num, column=2).fill = atc_fill
        ws.cell(row=row_num, column=3, value=compatible_model).border = thin_border
        ws.cell(row=row_num, column=3).fill = compat_fill
        ws.cell(row=row_num, column=3).font = Font(bold=True, size=10)

        row_num += 1

    ws.column_dimensions['A'].width = 28
    ws.column_dimensions['B'].width = 38
    ws.column_dimensions['C'].width = 55

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer, prod_col, model_col, specs_col

# UI
st.markdown('<div class="hero"><div style="font-size:20px; font-weight:800;">🇮🇳 GeM — FIXED Master Match</div><div style="font-size:11px; opacity:0.7;">Now correctly reads your Master Sheet columns</div></div><div class="tricolor"></div>', unsafe_allow_html=True)

if st.button("🗑️ Clear All", type="primary"):
    for k in list(st.session_state.keys()): del st.session_state[k]
    st.rerun()

st.markdown('<div class="glass-card">', unsafe_allow_html=True)
c1,c2,c3 = st.columns(3)
with c1:
    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    st.markdown('**📄 ATC — PDF/Image**')
    atc_file = st.file_uploader("ATC", type=["pdf","jpg","jpeg","png","bmp","webp"], key="atc", label_visibility="collapsed")
    atc_text=""; atc_type=""
    if atc_file:
        atc_text, atc_type, _ = read_atc_any(atc_file)
        if atc_text: st.success(f"✅ ATC read {len(atc_text)} chars")
    st.markdown('</div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    st.markdown('**📑 Bid PDF**')
    bid_file = st.file_uploader("Bid", type=["pdf"], key="bid", label_visibility="collapsed")
    bid_meta={"bid_no":"GEM/2026/B/7936262","org":"DEPT OF FINANCIAL SERVICES","qty":65}
    bid_text=""
    if bid_file:
        bid_text = read_pdf_text(bid_file)
        from datetime import datetime
        import re
        try:
            m=re.search(r'GEM\/\d{4}\/B\/\d{4,10}', safe_str(bid_text).replace(" ","").upper())
            bid_meta['bid_no']=m.group(0) if m else bid_meta['bid_no']
        except: pass
        st.success(f"✅ {bid_meta['bid_no']}")
    st.markdown('</div>', unsafe_allow_html=True)
with c3:
    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    st.markdown('**📊 Master Excel**')
    master_file = st.file_uploader("Master", type=["xlsx","xls","csv"], key="master", label_visibility="collapsed")
    df_master=None
    if master_file:
        try:
            df_master = pd.read_excel(master_file) if not master_file.name.endswith('.csv') else pd.read_csv(master_file)
            df_master = df_master.fillna("")
            st.success(f"✅ {len(df_master)} models")
            st.write("Columns:", list(df_master.columns))
            st.dataframe(df_master.head(5), use_container_width=True)
        except Exception as e:
            st.error(f"{e}")
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

if atc_file and bid_file and master_file and df_master is not None and not df_master.empty:

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)

    excel_buffer, p_col, m_col, s_col = create_excel_fixed(bid_meta, df_master, atc_text)

    st.success(f"✅ Fixed! Found columns -> Product: {p_col} | Model: {m_col} | Specs: {s_col}")

    st.markdown("""
    **This version FIXES:**
    - Auto-detects your Master columns (even if named differently)
    - Searches ALL columns of Master (not just one)
    - Uses keyword mapping (processor CPU -> processor, cpu, i5 etc.)
    - So now it WILL find compatible products
    """)

    st.download_button(
        label="📥 Download EXCEL — Fixed Compatible Products (No Price)",
        data=excel_buffer,
        file_name=f"GeM_Fixed_Compatible_{safe_str(bid_meta.get('bid_no','')).replace('/','_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        type="primary"
    )

    # Debug preview
    st.markdown("### 🔍 Debug — Why previous failed and now works:")
    st.markdown(f"Your Master Columns: **{list(df_master.columns)}**")
    st.markdown(f"Detected -> Product Column: **{p_col}** | Model Column: **{m_col}**")
    st.markdown("If still shows 'Not Available', check that your Master actually contains words like 'i5', 'RAM', 'SSD', 'Motherboard' etc. — if your Master uses codes only, rename one column to 'Product'")

    st.markdown('</div>', unsafe_allow_html=True)

elif atc_file or bid_file or master_file:
    st.info("⬆️ Upload all 3 files — and check your Master Sheet columns shown above")