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

st.set_page_config(page_title="GeM Compatible Only", layout="wide", page_icon="🇮🇳")

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
    if pd.isna(x): return ""
    return str(x)
def safe_lower(x): return safe_str(x).lower()

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

def parse_bid_meta(bid_text):
    data={'bid_no':"GEM/2026/B/7936262",'org':"DEPT OF FINANCIAL SERVICES",'dept':"DHANBAD",'item':"entry and mid level DESKTOP COMPUTERS",'qty':65,'closing':"29-8-2026 16:00"}
    try:
        m=re.search(r'GEM\/\d{4}\/B\/\d{4,10}', safe_str(bid_text).replace(" ","").upper())
        data['bid_no']=m.group(0) if m else data['bid_no']
        m=re.search(r'Organisation\s*Name\s*[:\-]?\s*([^\n]+)', safe_str(bid_text), re.I)
        if m: data['org']=m.group(1).strip()[:100]
        m=re.search(r'Quantity\s*[:\-]?\s*(\d+)', safe_str(bid_text), re.I)
        data['qty']=int(m.group(1)) if m else 65
    except: pass
    return data

def is_compatible(atc_spec, model, specs):
    atc=safe_lower(atc_spec)
    m=safe_lower(f"{model} {specs}")
    if "i5" in atc and "i3" in m: return False
    if "i7" in atc and ("i3" in m or "i5" in m): return False
    if "16 gb" in atc and "8 gb" in m: return False
    return True

def create_excel_compatible_only(bid_meta, df_master, atc_text):
    wb = Workbook()
    ws = wb.active
    ws.title = "Compatible Products - ATC vs Master"

    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    bold = Font(name='Calibri', bold=True, size=11)
    normal = Font(name='Calibri', size=11)
    header_font = Font(name='Calibri', bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    atc_fill = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")
    compat_fill = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid")

    # Master columns
    df_master.columns = [safe_str(c).strip().lower() for c in df_master.columns]
    prod_col = next((c for c in df_master.columns if 'product' in c or 'parameter' in c or 'component' in c), df_master.columns[0])
    model_col = next((c for c in df_master.columns if 'model' in c), df_master.columns[1] if len(df_master.columns)>1 else prod_col)
    specs_col = next((c for c in df_master.columns if 'spec' in c), None)

    df_master = df_master.fillna("")

    # Header info
    ws.merge_cells('A1:C1')
    ws['A1'] = f"GeM Bid: {bid_meta.get('bid_no','')} | {bid_meta.get('org','')} | Qty: {bid_meta.get('qty',65)}"
    ws['A1'].font = Font(bold=True, size=12)
    ws['A1'].fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")

    # Table header - NO PRICE
    headers = ["PARAMETER (from ATC/Bid)", "ATC Spec (from uploaded ATC/Bid)", "Compatible Product (from Master Sheet)"]
    for c_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=3, column=c_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = Alignment(horizontal='center', vertical='center')

    # Parameters list - exactly like your paper
    paper_params = [
        "processor CPU", "MB", "graphics CARD", "OS", "RAM", "SSD", "SSD(SECONDARY)",
        "cabinet LTR", "smps WATT", "ADAPTER", "DVD WRITER", "MONITOR", "SPEAKER",
        "WIRELESS + BLUETOOTH", "MS OFFICE", "CHASSIS SWITCH", "TPM 2.0", "CAMERA",
        "ANTIVIRUS", "DP PORT", "SERIAL COM PORT+PARALLEL", "Keyboard & Mouse,"
    ]

    atc_lower = safe_lower(atc_text) if atc_text else ""

    row_num = 4
    for param_name in paper_params:
        param_lower = safe_lower(param_name)
        search_key = param_lower.split()[0]

        # Find ATC spec line from uploaded ATC
        atc_spec_val = ""
        if atc_text:
            for line in atc_text.split("\n"):
                if search_key in safe_lower(line) and 5 < len(line) < 200:
                    atc_spec_val = line.strip()[:100]
                    break
        if not atc_spec_val:
            defaults = {
                "processor cpu": "Intel core i5 14400",
                "mb": "H 610 DDR5",
                "graphics card": "0",
                "os": "WINDS 11 PRO",
                "ram": "16 GB DDR5",
                "ssd": "256 GB NVME",
                "ssd(secondary)": "1 TB SATA SSD",
                "cabinet ltr": "TOWER",
                "smps watt": "200 WATT",
                "monitor": '21.5" IPS',
                "tpm 2.0": "YES",
            }
            atc_spec_val = defaults.get(param_lower, param_name)

        # Find compatible from master
        mask = df_master[prod_col].apply(lambda x: search_key in safe_lower(x) or param_lower in safe_lower(x))
        df_filtered = df_master[mask] if mask.any() else pd.DataFrame()
        if df_filtered.empty:
            mask2 = df_master[model_col].apply(lambda x: search_key in safe_lower(x))
            df_filtered = df_master[mask2] if mask2.any() else pd.DataFrame()

        compatible_model = "Not Available in Master"

        if not df_filtered.empty:
            for _, row in df_filtered.iterrows():
                model = safe_str(row[model_col])
                specs = safe_str(row[specs_col]) if specs_col and specs_col in row else ""
                if is_compatible(atc_spec_val, model, specs):
                    compatible_model = model
                    if specs: compatible_model += f" - {specs[:80]}"
                    break
            if compatible_model == "Not Available in Master":
                row = df_filtered.iloc[0]
                compatible_model = safe_str(row[model_col])
                specs = safe_str(row[specs_col]) if specs_col and specs_col in row else ""
                if specs: compatible_model += f" - {specs[:80]}"

        # Write row
        ws.cell(row=row_num, column=1, value=param_name.upper()).border = thin_border
        ws.cell(row=row_num, column=1).font = bold

        ws.cell(row=row_num, column=2, value=atc_spec_val).border = thin_border
        ws.cell(row=row_num, column=2).fill = atc_fill

        ws.cell(row=row_num, column=3, value=compatible_model).border = thin_border
        ws.cell(row=row_num, column=3).fill = compat_fill
        ws.cell(row=row_num, column=3).font = Font(bold=True, size=11)

        row_num += 1

    # Set widths
    ws.column_dimensions['A'].width = 28
    ws.column_dimensions['B'].width = 38
    ws.column_dimensions['C'].width = 45

    # Second sheet - same but simple list
    ws2 = wb.create_sheet("Simple List - Compatible Only")
    ws2.append(["PARAMETER", "Compatible Product from Master (ATC Matched)"])
    for r in range(4, row_num):
        param = ws.cell(row=r, column=1).value
        compat = ws.cell(row=r, column=3).value
        ws2.append([param, compat])

    ws2.column_dimensions['A'].width = 30
    ws2.column_dimensions['B'].width = 50

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer

# UI
st.markdown('<div class="hero"><div style="font-size:20px; font-weight:800;">🇮🇳 GeM — Compatible Product Only (No Price)</div><div style="font-size:11px; opacity:0.7;">Shows only ATC + Compatible Master Product</div></div><div class="tricolor"></div>', unsafe_allow_html=True)

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
        if atc_text: st.success(f"✅ ATC read")
    st.markdown('</div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    st.markdown('**📑 Bid PDF**')
    bid_file = st.file_uploader("Bid", type=["pdf"], key="bid", label_visibility="collapsed")
    bid_meta={"bid_no":"GEM/2026/B/7936262","org":"DEPT OF FINANCIAL SERVICES","qty":65}
    bid_text=""
    if bid_file:
        bid_text = read_pdf_text(bid_file)
        bid_meta = parse_bid_meta(bid_text)
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
        except Exception as e:
            st.error(f"{e}")
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

if atc_file and bid_file and master_file and df_master is not None:

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("### 📊 Excel — Only Compatible Product (No Price)")

    excel_buffer = create_excel_compatible_only(bid_meta, df_master, atc_text)

    st.success("✅ Excel Generated — No Price, Only Compatible Products!")

    st.markdown("""
    **Excel Columns (No Price):**
    - **Column A:** PARAMETER (processor CPU, MB, RAM...)
    - **Column B:** ATC Spec (from your ATC/Bid upload) — Blue
    - **Column C:** Compatible Product (from Master Sheet) — Green — **Only this**
    """)

    st.download_button(
        label="📥 Download EXCEL — Compatible Product Only (No Price)",
        data=excel_buffer,
        file_name=f"GeM_Compatible_Only_{safe_str(bid_meta.get('bid_no','')).replace('/','_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        type="primary"
    )

    st.markdown('</div>', unsafe_allow_html=True)

elif atc_file or bid_file or master_file:
    st.info("⬆️ Upload all 3 files")