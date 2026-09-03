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

st.set_page_config(page_title="GeM Paper + Compatible", layout="wide", page_icon="🇮🇳")

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
    if "512" in atc and "256" in m: return False
    return True

def create_paper_format_excel(bid_meta, df_master, atc_text, bid_text):
    """Paper Format + Compatible Product Column from Master"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Paper Format - Cost Sheet"

    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    bold = Font(name='Calibri', bold=True, size=11)
    normal = Font(name='Calibri', size=11)
    header_fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
    compat_fill = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid") # Green for compatible
    atc_fill = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid") # Blue for ATC

    # Parse ATC components for compatibility check
    atc_lower = safe_lower(atc_text) if atc_text else ""

    # Prepare master lookup
    df_master.columns = [safe_str(c).strip().lower() for c in df_master.columns]
    prod_col = next((c for c in df_master.columns if 'product' in c or 'component' in c or 'parameter' in c), df_master.columns[0])
    model_col = next((c for c in df_master.columns if 'model' in c), df_master.columns[1] if len(df_master.columns)>1 else prod_col)
    price_col = next((c for c in df_master.columns if 'price' in c or 'rate' in c), df_master.columns[2] if len(df_master.columns)>2 else prod_col)
    specs_col = next((c for c in df_master.columns if 'spec' in c), None)

    df_master = df_master.fillna("")

    # Define paper parameters exactly as your photo
    paper_params = [
        ("DEPARTMENT NAME", "DEPT OF FINANCIAL SERVICES", "entry and mid level DESKTOP COMPUTERS", "", "65"),
        ("GEM BID NO.", "GEM/2026/B/7936262", "", "DHANBAD", ""),
        ("Bid Closing Date/Time", "29-8-2026 16:00", "12:00 AM", "", ""),
        ("PARAMETER", "ATC Spec (from ATC/Bid)", "Compatible Product (from Master)", "price", "Amount (₹)"),
        ("processor CPU", "", "", "", ""),
        ("MB", "", "", "DDR5", ""),
        ("graphics CARD", "", "", "", ""),
        ("OS", "", "", "", ""),
        ("RAM", "", "", "", ""),
        ("SSD", "", "", "", ""),
        ("SSD(SECONDARY)", "", "", "", ""),
        ("cabinet LTR", "", "", "", ""),
        ("smps WATT", "", "", "", ""),
        ("ADAPTER", "", "", "", ""),
        ("DVD WRITER", "", "", "", ""),
        ("MONITOR", "", "", "IPS", ""),
        ("SPEAKER", "", "", "", ""),
        ("WIRELESS + BLUETOOTH", "", "", "", ""),
        ("MS OFFICE", "", "", "", ""),
        ("CHASSIS SWITCH", "", "", "", ""),
        ("TPM 2.0", "", "", "", ""),
        ("CAMERA", "", "", "", ""),
        ("ANTIVIRUS", "", "", "", ""),
        ("DP PORT", "", "", "", ""),
        ("SERIAL COM PORT+PARALLEL", "", "", "", ""),
        ("Keyboard & Mouse,", "", "", "", ""),
        ("", "", "COST", "", ""),
        ("WARRANTY", "3 YEARS", "", "", ""),
        ("FREIGHT/ DELEVERY EXPENSES", "", "", "", ""),
        ("INSTALLATION Charge", "", "", "", ""),
        ("SERCURITY", "", "", "", ""),
        ("SERVICE Charge", "", "", "", ""),
        ("NON RETURN OF HDD", "", "", "", ""),
        ("BG PERCENTAGE AND EXPENSES", "", "", "", ""),
        ("ORC", "", "", "", ""),
        ("DISTRI MARGIN", "", "", "", ""),
        ("LATE DELVERY 1%", "", "", "", ""),
        ("GeM charges (0.5%)", "", "", "", ""),
        ("INSPECTION", "", "", "Total", ""),
        ("", "", "", "Company Margin", ""),
        ("", "", "", "Sub Total", ""),
        ("", "", "", "GST 18%", ""),
        ("", "", "", "Grant Total", ""),
    ]

    # Override first 3 rows with actual bid meta
    paper_params[0] = ("DEPARTMENT NAME", bid_meta.get('org','DEPT OF FINANCIAL SERVICES'), bid_meta.get('item','entry and mid level DESKTOP COMPUTERS'), "", str(bid_meta.get('qty',65)))
    paper_params[1] = ("GEM BID NO.", bid_meta.get('bid_no','GEM/2026/B/7936262'), "", bid_meta.get('dept','DHANBAD'), "")
    paper_params[2] = ("Bid Closing Date/Time", bid_meta.get('closing','29-8-2026 16:00'), "12:00 AM", "", "")

    # Write header
    for r_idx, row_data in enumerate(paper_params, start=1):
        for c_idx, val in enumerate(row_data, start=1):
            cell = ws.cell(row=r_idx, column=c_idx, value=val)
            cell.border = thin_border
            cell.font = normal
            cell.alignment = Alignment(vertical='center', horizontal='left' if c_idx<=2 else 'center')
            if c_idx==1 and val!="": cell.font = bold
            if r_idx<=4:
                cell.fill = header_fill
                cell.font = bold
                if r_idx==4:
                    if c_idx==2: cell.fill = atc_fill
                    if c_idx==3: cell.fill = compat_fill

    # Now fill compatible products for each parameter row (5 to 26)
    total_base = 0
    for r_idx in range(5, 27):
        param_name = safe_str(ws.cell(row=r_idx, column=1).value).strip()
        if not param_name: continue

        # Find in master
        param_lower = safe_lower(param_name)
        search_key = param_lower.split()[0] # first word

        # Find compatible rows in master
        mask = df_master[prod_col].apply(lambda x: search_key in safe_lower(x) or param_lower in safe_lower(x) or safe_lower(x) in param_lower)
        df_filtered = df_master[mask] if mask.any() else pd.DataFrame()

        # Also try model column
        if df_filtered.empty:
            mask2 = df_master[model_col].apply(lambda x: search_key in safe_lower(x))
            df_filtered = df_master[mask2] if mask2.any() else pd.DataFrame()

        compatible_model = "Not in Master"
        atc_spec_val = "0"
        price_val = 0
        found_compatible = False

        # Check ATC text for spec line
        if atc_text:
            for line in atc_text.split("\n"):
                if search_key in safe_lower(line) and 5 < len(line) < 200:
                    atc_spec_val = line.strip()[:80]
                    break

        # Default specs if ATC not found
        if atc_spec_val == "0":
            default_specs = {
                "processor cpu": "Intel core i5 14400",
                "mb": "H 610",
                "graphics card": "0",
                "os": "WINDS 11 PRO",
                "ram": "16 GB DDR5",
                "ssd": "256 GB NVME",
                "ssd(secondary)": "1 TB SATA SSD",
                "cabinet ltr": "TOWER",
                "smps watt": "200 WATT",
                "monitor": '21.5"',
                "keyboard & mouse,": "WIRED",
                "tpm 2.0": "YES",
                "ms office": "NO",
            }
            atc_spec_val = default_specs.get(param_lower, "0")

        if not df_filtered.empty:
            # Find first compatible
            for _, row in df_filtered.iterrows():
                model = safe_str(row[model_col])
                specs = safe_str(row[specs_col]) if specs_col and specs_col in row else ""
                price = row[price_col]
                try: price_num = float(price) if price!="" else 0
                except: price_num = 0

                # Check compatibility with ATC
                if is_compatible(atc_spec_val, model, specs):
                    compatible_model = model
                    price_val = price_num
                    found_compatible = True
                    break

            # If no compatible found, take first
            if not found_compatible:
                row = df_filtered.iloc[0]
                compatible_model = safe_str(row[model_col])
                price = row[price_col]
                try: price_val = float(price) if price!="" else 0
                except: price_val = 0
        else:
            # Use default price from your photo
            default_prices = {
                "processor cpu": 14500, "mb": 4250, "graphics card": 0, "os": 600,
                "ram": 17500, "ssd": 3650, "ssd(secondary)": 11500, "cabinet ltr": 15500,
                "smps watt": 1850, "monitor": 0, "speaker": 0, "wireless + bluetooth": 4450,
                "ms office": 0, "tpm 2.0": 700, "keyboard & mouse,": 350
            }
            price_val = default_prices.get(param_lower, 0)
            compatible_model = f"{param_name} - {atc_spec_val}" if atc_spec_val!="0" else "0"

        # Fill columns: B=ATC Spec, C=Compatible Product (Master), D=price label, E=Amount
        ws.cell(row=r_idx, column=2, value=atc_spec_val).border = thin_border
        ws.cell(row=r_idx, column=2).fill = atc_fill

        ws.cell(row=r_idx, column=3, value=compatible_model).border = thin_border
        ws.cell(row=r_idx, column=3).fill = compat_fill
        ws.cell(row=r_idx, column=3).font = Font(bold=True, size=10)

        ws.cell(row=r_idx, column=5, value=price_val).border = thin_border
        ws.cell(row=r_idx, column=5).number_format = '#,##0'

        total_base += price_val

    # COST row
    ws.cell(row=27, column=3, value="COST").font = bold
    ws.cell(row=27, column=5, value=total_base).font = bold
    ws.cell(row=27, column=5).border = thin_border
    ws.cell(row=27, column=5).number_format = '#,##0'

    # Other charges
    other_charges = [
        ("WARRANTY", 0), ("FREIGHT/ DELEVERY EXPENSES", 600), ("INSTALLATION Charge", 300),
        ("SERCURITY", 0), ("SERVICE Charge", 0), ("NON RETURN OF HDD", 250),
        ("BG PERCENTAGE AND EXPENSES", 0), ("ORC", 0), ("DISTRI MARGIN", 0),
        ("LATE DELVERY 1%", 300), ("GeM charges (0.5%)", 0), ("INSPECTION", 0),
    ]

    current_total = total_base
    for idx, (charge_name, charge_val) in enumerate(other_charges):
        r = 28 + idx
        ws.cell(row=r, column=1, value=charge_name).font = bold
        ws.cell(row=r, column=5, value=charge_val).border = thin_border
        ws.cell(row=r, column=5).number_format = '#,##0'
        current_total += charge_val
        if idx==0:
            ws.cell(row=r, column=2, value="3 YEARS").border = thin_border

    ws.cell(row=40, column=5, value=current_total).font = bold
    ws.cell(row=40, column=5).border = thin_border

    company_margin = 4000
    ws.cell(row=41, column=4, value="Company Margin").font = bold
    ws.cell(row=41, column=5, value=company_margin).border = thin_border
    ws.cell(row=41, column=5).number_format = '#,##0'
    ws.cell(row=41, column=6, value="CLASS 1").border = thin_border
    ws.cell(row=41, column=7, value="50%").border = thin_border

    sub_total = current_total + company_margin
    ws.cell(row=42, column=4, value="Sub Total").font = bold
    ws.cell(row=42, column=5, value=sub_total).font = bold
    ws.cell(row=42, column=5).border = thin_border
    ws.cell(row=42, column=6, value="RA RULE").border = thin_border
    ws.cell(row=42, column=7, value="50%").border = thin_border

    gst = round(sub_total * 0.18)
    ws.cell(row=43, column=4, value="GST 18%").font = bold
    ws.cell(row=43, column=5, value=gst).border = thin_border
    ws.cell(row=43, column=6, value="RA").border = thin_border
    ws.cell(row=43, column=7, value="NO").border = thin_border

    grant_total = sub_total + gst
    ws.cell(row=44, column=4, value="Grant Total").font = Font(bold=True, size=12)
    ws.cell(row=44, column=5, value=grant_total).font = Font(bold=True, size=12)
    ws.cell(row=44, column=5).border = thin_border
    ws.cell(row=44, column=6, value="BID PRICE").font = bold
    ws.cell(row=44, column=6).border = thin_border

    ws.column_dimensions['A'].width = 28
    ws.column_dimensions['B'].width = 28
    ws.column_dimensions['C'].width = 32
    ws.column_dimensions['D'].width = 14
    ws.column_dimensions['E'].width = 14
    ws.column_dimensions['F'].width = 14
    ws.column_dimensions['G'].width = 10

    # Sheet 2: Detailed compatible list
    ws2 = wb.create_sheet("ATC+BID vs Master - Detailed")
    ws2.append(["PARAMETER (ATC/BID)", "ATC Spec", "Compatible Product (Master)", "Model Specs", "Price (₹)", "Status"])
    for r_idx in range(5, 27):
        param = safe_str(ws.cell(row=r_idx, column=1).value)
        atc_spec = safe_str(ws.cell(row=r_idx, column=2).value)
        compat = safe_str(ws.cell(row=r_idx, column=3).value)
        price = ws.cell(row=r_idx, column=5).value
        status = "✅ Compatible" if compat!="Not in Master" and compat!="0" else "❌ Missing"
        ws2.append([param, atc_spec, compat, "", price, status])

    for col in ['A','B','C','D','E','F']: ws2.column_dimensions[col].width = 22

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer

# UI
st.markdown('<div class="hero"><div style="font-size:20px; font-weight:800;">🇮🇳 GeM — Paper Format + Compatible Column</div><div style="font-size:11px; opacity:0.7;">Now shows ATC Spec + Compatible Master Product + Price like your paper</div></div><div class="tricolor"></div>', unsafe_allow_html=True)

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
    bid_meta={"bid_no":"GEM/2026/B/7936262","org":"DEPT OF FINANCIAL SERVICES","dept":"DHANBAD","item":"entry and mid level DESKTOP COMPUTERS","qty":65,"closing":"29-8-2026 16:00"}
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
            st.dataframe(df_master.head(3), use_container_width=True)
        except Exception as e:
            st.error(f"{e}")
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

if atc_file and bid_file and master_file and df_master is not None:

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("### 📊 Excel with Compatible Product Column")

    excel_buffer = create_paper_format_excel(bid_meta, df_master, atc_text, bid_text)

    st.success("✅ Excel Generated — Now includes Compatible Product from Master!")

    st.markdown("""
    **New Excel Columns:**
    - **Column A:** PARAMETER (processor CPU, MB, etc.)
    - **Column B:** ATC Spec (fetched from ATC/BID PDF/Image) — Blue
    - **Column C:** **Compatible Product (from Master Sheet)** — Green — This is NEW
    - **Column D:** price / DDR5 / IPS labels
    - **Column E:** Amount ₹ (price from Master)
    - **Column F-G:** CLASS 1, RA RULE etc.
    """)

    st.download_button(
        label="📥 Download PAPER FORMAT EXCEL with Compatible Product Column",
        data=excel_buffer,
        file_name=f"GeM_Paper_Compatible_{safe_str(bid_meta.get('bid_no','')).replace('/','_')}_{datetime.now().strftime('%d%m%Y')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        type="primary"
    )

    st.markdown('</div>', unsafe_allow_html=True)

elif atc_file or bid_file or master_file:
    st.info("⬆️ Upload all 3 files")