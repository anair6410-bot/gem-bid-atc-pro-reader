import streamlit as st
import pandas as pd
import re
from PIL import Image, ImageEnhance, ImageFilter
import io
import math

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

st.set_page_config(page_title="GeM Intelligent Alternative", layout="wide", page_icon="🇮🇳")

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

# ============ INTELLIGENT COMPATIBILITY RULES ============
COMPATIBILITY_RULES = {
    "processor CPU": {
        "required": "Intel core i5 14400",
        "exact_keywords": ["i5 14400", "i5-14400"],
        "suitable_alternatives": [
            ("i5 14400F", "Same performance, no iGPU - Suitable"),
            ("i5 14500", "Higher gen same i5 - Suitable & Better"),
            ("i5 13400", "Previous gen, slightly lower - Suitable"),
            ("i7 12700", "Higher category - Suitable & Better"),
            ("i5 14600", "Higher - Suitable & Better"),
        ],
        "must_contain": ["i5", "intel"],
        "reject": ["i3"]
    },
    "MB": {
        "required": "H610 DDR5",
        "exact_keywords": ["h610"],
        "suitable_alternatives": [
            ("B660 DDR5", "B660 supports 12th/13th/14th gen, better than H610 - HIGHLY SUITABLE"),
            ("H670 DDR5", "Higher chipset than H610 - SUITABLE"),
            ("B760 DDR5", "Newer B760, supports 14th gen - HIGHLY SUITABLE & Better"),
            ("H610M DDR5", "M-ATX version of H610 - EXACT SUITABLE"),
            ("Z790 DDR5", "Top chipset, fully compatible - SUITABLE & Better"),
            ("B660M DDR5", "M-ATX B660 - SUITABLE"),
        ],
        "must_contain": ["ddr5"],
        "reject": ["ddr3", "ddr4"] # if bid says DDR5, reject DDR4
    },
    "RAM": {
        "required": "16 GB DDR5",
        "exact_keywords": ["16 gb ddr5", "16gb ddr5"],
        "suitable_alternatives": [
            ("32 GB DDR5", "Higher capacity - SUITABLE & Better"),
            ("16 GB DDR5 4800", "Exact - SUITABLE"),
            ("16 GB DDR5 5600", "Higher speed - SUITABLE & Better"),
            ("2x8 GB DDR5", "16GB in dual channel - SUITABLE"),
        ],
        "must_contain": ["ddr5"],
        "reject": []
    },
    "SSD": {
        "required": "256 GB NVME",
        "exact_keywords": ["256 gb nvme", "256gb nvme"],
        "suitable_alternatives": [
            ("512 GB NVME", "Higher capacity - SUITABLE & Better"),
            ("1 TB NVME", "Much higher - SUITABLE & Better"),
            ("256 GB NVME Gen4", "Faster Gen4 - SUITABLE & Better"),
        ],
        "must_contain": ["nvme"],
        "reject": []
    },
    "SSD(SECONDARY)": {
        "required": "1 TB SATA SSD",
        "exact_keywords": ["1 tb ssd", "1tb sata"],
        "suitable_alternatives": [
            ("1 TB NVME", "NVMe better than SATA - SUITABLE & Better"),
            ("2 TB SATA SSD", "Higher capacity - SUITABLE & Better"),
            ("1 TB SSD", "Any 1TB SSD - SUITABLE"),
        ],
        "must_contain": ["ssd"],
        "reject": []
    },
    "MONITOR": {
        "required": '21.5" IPS',
        "exact_keywords": ["21.5", "22 inch"],
        "suitable_alternatives": [
            ("24\" IPS", "Larger IPS - SUITABLE & Better"),
            ("22\" IPS", "Slightly larger - SUITABLE"),
            ("21.5\" IPS FHD", "Exact - SUITABLE"),
            ("23.8\" IPS", "Bigger - SUITABLE & Better"),
        ],
        "must_contain": ["ips"],
        "reject": []
    },
    "OS": {
        "required": "WIN 11 PRO",
        "exact_keywords": ["win 11 pro", "windows 11 pro"],
        "suitable_alternatives": [
            ("Windows 11 Pro", "Exact - SUITABLE"),
        ],
        "must_contain": ["pro"],
        "reject": ["home", "dos", "linux", "ubuntu"]
    }
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
        if not OCR_AVAILABLE: return "", "image"
        pil_img = Image.open(file)
        enhanced = enhance_image_pillow(pil_img)
        text = pytesseract.image_to_string(enhanced, config=r'--oem 3 --psm 6')
        return text, "image"
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
                    return ocr_full, "scanned_pdf"
            except: pass
        return text, "pdf"
    return "", "unknown"

def find_suitable_from_master(param_name, required_spec, df_master, prod_col, model_col, specs_col):
    """Find exact + alternative suitable products"""
    param_lower = safe_lower(param_name)
    rules = COMPATIBILITY_RULES.get(param_name, None)
    if not rules:
        rules = {
            "required": required_spec,
            "exact_keywords": [safe_lower(required_spec).split()[0]],
            "suitable_alternatives": [],
            "must_contain": [],
            "reject": []
        }

    exact_match = None
    suitable_list = []

    # Search master
    for _, row in df_master.iterrows():
        all_text = " ".join([safe_lower(row.get(c, "")) for c in df_master.columns])
        model_text = safe_lower(row.get(model_col, "")) + " " + safe_lower(row.get(prod_col, "")) + " " + safe_lower(row.get(specs_col, "")) if specs_col else ""

        # Check reject
        rejected = False
        for rej in rules.get("reject", []):
            if rej in model_text and param_name in ["MB", "RAM", "OS"]:
                if rej == "ddr4" and "ddr5" in rules.get("must_contain", []):
                    rejected = True
                    break
        if rejected:
            continue

        # Check exact keywords
        is_exact = False
        for ek in rules.get("exact_keywords", []):
            if safe_lower(ek) in model_text:
                is_exact = True
                break

        if is_exact:
            exact_match = {
                "product": safe_str(row.get(prod_col, "")) + " - " + safe_str(row.get(model_col, "")),
                "full": safe_str(row.get(model_col, "")) + " | " + safe_str(row.get(specs_col, "")) if specs_col else safe_str(row.get(model_col, "")),
                "reason": f"Exact match for {required_spec}"
            }
            break

    # If no exact, find suitable alternatives
    if not exact_match:
        for _, row in df_master.iterrows():
            all_text = " ".join([safe_lower(row.get(c, "")) for c in df_master.columns])
            model_text = safe_lower(row.get(model_col, "")) + " " + safe_lower(row.get(prod_col, ""))

            # Check must contain
            must_ok = True
            for must in rules.get("must_contain", []):
                if must not in all_text:
                    must_ok = False
                    break
            if not must_ok and rules.get("must_contain"):
                continue

            # Check if any alternative keyword in master
            for alt_name, alt_reason in rules.get("suitable_alternatives", []):
                alt_kw = safe_lower(alt_name).split()[0]
                if alt_kw in model_text or safe_lower(alt_name) in all_text:
                    suitable_list.append({
                        "product": safe_str(row.get(model_col, "")) or safe_str(row.get(prod_col, "")),
                        "alternative_spec": alt_name,
                        "reason": alt_reason,
                        "full": safe_str(row.get(model_col, "")) + f" ({alt_name})"
                    })

            # Generic suitable - if product category matches
            if param_lower.split()[0] in all_text and len(suitable_list) < 3:
                # Add as generic suitable
                if not any(s['product'] == safe_str(row.get(model_col, "")) for s in suitable_list):
                    suitable_list.append({
                        "product": safe_str(row.get(model_col, "")) or safe_str(row.get(prod_col, "")),
                        "alternative_spec": safe_str(row.get(specs_col, ""))[:50] if specs_col else "",
                        "reason": f"Same category {param_name} - Check specs",
                        "full": safe_str(row.get(model_col, ""))
                    })

    return exact_match, suitable_list[:3]

def create_intelligent_excel(bid_meta, df_master_raw, atc_text):
    wb = Workbook()
    ws = wb.active
    ws.title = "Intelligent Compatible List"

    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    bold = Font(name='Calibri', bold=True, size=11)
    header_font = Font(name='Calibri', bold=True, color="FFFFFF", size=10)
    header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    exact_fill = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid")
    alt_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
    not_avail_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")

    # Find columns
    cols = [safe_str(c).strip().lower() for c in df_master_raw.columns]
    df_master_raw.columns = cols
    prod_col = next((c for c in cols if 'product' in c or 'parameter' in c or 'item' in c), cols[0])
    model_col = next((c for c in cols if 'model' in c or 'part' in c), cols[1] if len(cols)>1 else cols[0])
    specs_col = next((c for c in cols if 'spec' in c or 'desc' in c), None)
    df_master = df_master_raw.fillna("")

    # Header
    ws.merge_cells('A1:F1')
    ws['A1'] = f"GeM Bid: {bid_meta.get('bid_no','')} | Intelligent Alternative Logic - If exact not available, shows suitable chipset/product"
    ws['A1'].font = Font(bold=True, size=11)
    ws['A1'].fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")

    headers = ["PARAMETER", "Bid Requirement (ATC/Bid)", "Exact Match (Master)", "Alternative Suitable (Master)", "Why Suitable?", "Status"]
    for c_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=3, column=c_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    paper_params = [
        "processor CPU", "MB", "graphics CARD", "OS", "RAM", "SSD", "SSD(SECONDARY)",
        "cabinet LTR", "smps WATT", "MONITOR", "SPEAKER", "WIRELESS + BLUETOOTH",
        "MS OFFICE", "CHASSIS SWITCH", "TPM 2.0", "CAMERA", "ANTIVIRUS", "Keyboard & Mouse,"
    ]

    row_num = 4
    for param_name in paper_params:
        rules = COMPATIBILITY_RULES.get(param_name, {})
        required_spec = rules.get("required", param_name)

        # Try to get actual ATC spec from OCR if available
        if atc_text:
            for line in atc_text.split("\n"):
                if param_name.split()[0].lower() in safe_lower(line) and 5 < len(line) < 150:
                    required_spec = line.strip()[:80]
                    break

        exact_match, suitable_list = find_suitable_from_master(param_name, required_spec, df_master, prod_col, model_col, specs_col)

        # Write row
        ws.cell(row=row_num, column=1, value=param_name.upper()).font = bold
        ws.cell(row=row_num, column=1).border = thin_border

        ws.cell(row=row_num, column=2, value=required_spec).border = thin_border
        ws.cell(row=row_num, column=2).alignment = Alignment(wrap_text=True)

        if exact_match:
            ws.cell(row=row_num, column=3, value=exact_match['full']).border = thin_border
            ws.cell(row=row_num, column=3).fill = exact_fill
            ws.cell(row=row_num, column=3).font = Font(bold=True)
            ws.cell(row=row_num, column=4, value="—").border = thin_border
            ws.cell(row=row_num, column=5, value=exact_match['reason']).border = thin_border
            ws.cell(row=row_num, column=6, value="✅ EXACT AVAILABLE").border = thin_border
            ws.cell(row=row_num, column=6).fill = exact_fill
        elif suitable_list:
            # Show first alternative as main
            alt = suitable_list[0]
            ws.cell(row=row_num, column=3, value="Not Available - H610 not in Master").border = thin_border
            ws.cell(row=row_num, column=3).fill = not_avail_fill

            ws.cell(row=row_num, column=4, value=alt['full']).border = thin_border
            ws.cell(row=row_num, column=4).fill = alt_fill
            ws.cell(row=row_num, column=4).font = Font(bold=True)

            ws.cell(row=row_num, column=5, value=alt['reason']).border = thin_border
            ws.cell(row=row_num, column=5).alignment = Alignment(wrap_text=True)

            ws.cell(row=row_num, column=6, value="⚠️ ALTERNATIVE SUITABLE").border = thin_border
            ws.cell(row=row_num, column=6).fill = alt_fill

            # If more alternatives, add extra rows
            for extra_alt in suitable_list[1:]:
                row_num += 1
                ws.cell(row=row_num, column=1, value="").border = thin_border
                ws.cell(row=row_num, column=2, value="").border = thin_border
                ws.cell(row=row_num, column=3, value="").border = thin_border
                ws.cell(row=row_num, column=4, value=extra_alt['full']).border = thin_border
                ws.cell(row=row_num, column=4).fill = alt_fill
                ws.cell(row=row_num, column=5, value=extra_alt['reason']).border = thin_border
                ws.cell(row=row_num, column=6, value="Alternative Option").border = thin_border
        else:
            ws.cell(row=row_num, column=3, value="Not in Master").border = thin_border
            ws.cell(row=row_num, column=3).fill = not_avail_fill
            ws.cell(row=row_num, column=4, value="No suitable found in Master").border = thin_border
            ws.cell(row=row_num, column=5, value="Master doesn't have this category").border = thin_border
            ws.cell(row=row_num, column=6, value="❌ NOT AVAILABLE").border = thin_border
            ws.cell(row=row_num, column=6).fill = not_avail_fill

        row_num += 1

    # Set widths
    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 28
    ws.column_dimensions['C'].width = 32
    ws.column_dimensions['D'].width = 32
    ws.column_dimensions['E'].width = 38
    ws.column_dimensions['F'].width = 22

    # Second sheet - Chipset alternatives explained
    ws2 = wb.create_sheet("Chipset Alternatives Guide")
    ws2.append(["If Required Chipset Not Available", "Suitable Alternatives from Master", "Reason"])
    for param, rule in COMPATIBILITY_RULES.items():
        if param == "MB":
            for alt_name, alt_reason in rule["suitable_alternatives"]:
                ws2.append([rule["required"], alt_name, alt_reason])

    ws2.column_dimensions['A'].width = 25
    ws2.column_dimensions['B'].width = 25
    ws2.column_dimensions['C'].width = 50

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer

# UI
st.markdown('<div class="hero"><div style="font-size:20px; font-weight:800;">🇮🇳 GeM — Intelligent Alternative Logic</div><div style="font-size:11px; opacity:0.7;">If H610 not available, shows B660/B760/Z790 as suitable</div></div><div class="tricolor"></div>', unsafe_allow_html=True)

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
        try:
            import re
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
            st.dataframe(df_master.head(3), use_container_width=True)
        except Exception as e:
            st.error(f"{e}")
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

if atc_file and bid_file and master_file and df_master is not None and not df_master.empty:

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("### 🧠 Intelligent Compatible List — With Alternatives")

    excel_buffer = create_intelligent_excel(bid_meta, df_master, atc_text)

    st.success("✅ Excel Generated — Shows Alternatives if Exact Not Available!")

    st.markdown("""
    **Example for your H610 case:**

    | PARAMETER | Bid Requirement | Exact Match | Alternative Suitable | Why Suitable? | Status |
    |---|---|---|---|---|---|
    | MB | H610 DDR5 | Not Available | **B660 DDR5** | B660 supports 12th/13th/14th gen, better than H610 - HIGHLY SUITABLE | ⚠️ ALTERNATIVE SUITABLE |
    | MB | | | **B760 DDR5** | Newer B760, supports 14th gen - HIGHLY SUITABLE | Alternative Option |
    | MB | | | **H610M DDR5** | M-ATX version of H610 - EXACT SUITABLE | Alternative Option |

    **Logic for ALL components:**
    - If exact H610 not in Master -> Shows B660, H670, B760, Z790 as suitable
    - If exact i5 14400 not -> Shows i5 14500, i7 12700 as suitable
    - If 256GB NVMe not -> Shows 512GB NVMe as better suitable
    """)

    st.download_button(
        label="📥 Download EXCEL — Intelligent Alternatives (H610 -> B660/B760)",
        data=excel_buffer,
        file_name=f"GeM_Intelligent_Alternatives_{safe_str(bid_meta.get('bid_no','')).replace('/','_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        type="primary"
    )

    st.markdown('</div>', unsafe_allow_html=True)

elif atc_file or bid_file or master_file:
    st.info("⬆️ Upload all 3 files")