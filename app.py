import streamlit as st
import pandas as pd
import re
from PIL import Image, ImageEnhance
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

try:
    import cv2, numpy as np
    CV2_AVAILABLE = True
except:
    CV2_AVAILABLE = False

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils.dataframe import dataframe_to_rows

st.set_page_config(page_title="GeM Proper Excel", layout="wide", page_icon="🇮🇳")

st.markdown("""
<style>
.stApp { background: #F8FAFF; }
.hero { background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); border-radius: 18px; padding: 18px 24px; color: white; }
.tricolor { height:4px; background: linear-gradient(90deg, #FF9933 0%, #FFF 50%, #138808 100%); border-radius:10px; margin:10px 0; }
.glass-card { background: white; border-radius: 16px; padding: 18px; border: 1px solid #E2E8F0; margin-bottom:14px; }
.upload-card { background: #F8FAFC; border: 1.5px dashed #CBD5E1; border-radius: 14px; padding: 16px; text-align:center; min-height: 190px; }
</style>
""", unsafe_allow_html=True)

KEYWORDS = {
    "Processor CPU": ["processor", "cpu", "i3", "i5", "i7", "ryzen"],
    "MB": ["motherboard"], "Graphics CARD": ["graphics", "gpu"], "OS": ["windows", "linux"],
    "RAM": ["ram", "memory"], "SSD": ["ssd", "nvme"], "SSD (SECONDARY)": ["secondary hdd", "1 tb", "secondary"],
    "Cabinet LTR": ["cabinet"], "SMPS WATT": ["smps"], "MONITOR": ["monitor", "inch"],
    "SPEAKER": ["speaker"], "WIRELESS + BLUETOOTH": ["wifi", "wireless", "bluetooth"], "MS OFFICE": ["ms office"],
    "CHASSIS SWITCH": ["chassis intrusion"], "TPM 2.0": ["tpm"], "CAMERA": ["camera", "webcam"], "ANTIVIRUS": ["antivirus"],
    "DP PORT": ["display port"], "SERIAL COM PORT+PARALLEL": ["serial", "com port"], "Keyboard & Mouse": ["keyboard", "mouse"],
    "UPS": ["ups"], "PRINTER": ["printer"], "SCANNER": ["scanner"], "HDD": ["hdd"], "LAPTOP": ["laptop"]
}

def enhance_image(pil_image):
    try:
        if CV2_AVAILABLE:
            img = np.array(pil_image.convert('RGB'))
            img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            h, w = img.shape
            if w < 1500: img = cv2.resize(img, (w*2, h*2), interpolation=cv2.INTER_CUBIC)
            img = cv2.medianBlur(img, 1)
            img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            return Image.fromarray(img)
        else:
            img = pil_image.convert('L')
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)
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
    filename = file.name.lower()
    file.seek(0)
    if filename.endswith(('.jpg','.jpeg','.png','.bmp','.webp')):
        if not OCR_AVAILABLE: return "", "image", "OCR missing"
        pil_img = Image.open(file)
        enhanced = enhance_image(pil_img)
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
                    enhanced=enhance_image(pil_img)
                    ocr_full+=pytesseract.image_to_string(enhanced, config=r'--oem 3 --psm 6')+"\n"
                if len(ocr_full.strip())>50:
                    return ocr_full, "scanned_pdf", "OCR success"
            except: pass
        return text, "pdf", "text pdf"
    return "", "unknown", "unsupported"

def parse_atc_components(atc_text):
    if not atc_text: return [], {}
    low=atc_text.lower()
    required=[]; spec_map={}
    for prod,kws in KEYWORDS.items():
        for kw in kws:
            if kw in low:
                for line in atc_text.split("\n"):
                    if kw in line.lower() and 5<len(line)<250:
                        if prod not in spec_map: spec_map[prod]=line.strip()
                if prod not in required: required.append(prod)
                break
    return required, spec_map

def parse_bid_meta(bid_text):
    data={'bid_no':"", 'org':"", 'dept':"", 'item':"Desktop Computer", 'qty':65}
    try:
        m=re.search(r'GEM\/\d{4}\/B\/\d{4,10}', bid_text.replace(" ","").upper())
        data['bid_no']=m.group(0) if m else ""
        m=re.search(r'Organisation\s*Name\s*[:\-]?\s*([^\n]+)', bid_text, re.I)
        data['org']=m.group(1).strip()[:100] if m else ""
        m=re.search(r'Quantity\s*[:\-]?\s*(\d+)', bid_text, re.I)
        data['qty']=int(m.group(1)) if m else 65
    except: pass
    return data

def is_compatible(atc_spec, model, specs):
    atc=(atc_spec or "").lower()
    m=f"{model} {specs}".lower()
    if "i5" in atc and "i3" in m: return False, "ATC i5 vs i3"
    if "16 gb" in atc and "8 gb" in m: return False, "ATC 16GB"
    if "512" in atc and "256" in m: return False, "ATC 512GB"
    return True, "Compatible"

def create_proper_excel(bid_meta, df_comp, df_other, atc_products, atc_type):
    """Create Proper Formatted Excel with 4 Sheets"""
    wb = Workbook()

    # Styles
    header_font = Font(name='Calibri', bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    sub_header_fill = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")
    sub_header_fill2 = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
    other_fill = PatternFill(start_color="FFFBEB", end_color="FFFBEB", fill_type="solid")
    border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    bold = Font(bold=True)

    # ===== SHEET 1: SUMMARY =====
    ws1 = wb.active
    ws1.title = "Bid Summary"

    ws1.merge_cells('A1:E1')
    ws1['A1'] = f"GeM Bid Proposal - {bid_meta.get('bid_no','')}"
    ws1['A1'].font = Font(name='Calibri', bold=True, size=14, color="0F172A")
    ws1['A1'].alignment = Alignment(horizontal='center')

    ws1.merge_cells('A2:E2')
    ws1['A2'] = f"Generated on {datetime.now().strftime('%d-%m-%Y %H:%M')} | ATC Type: {atc_type.upper()} | Organisation: {bid_meta.get('org','')}"
    ws1['A2'].font = Font(size=10, italic=True, color="64748B")

    summary_data = [
        ["Field", "Value (Auto-filled from Bid)"],
        ["Bid Number", bid_meta.get('bid_no','')],
        ["Organisation", bid_meta.get('org','')],
        ["Department", bid_meta.get('dept','')],
        ["Item Category", bid_meta.get('item','')],
        ["Quantity", bid_meta.get('qty',65)],
        ["ATC Products Required", len(atc_products)],
        ["ATC Compatible Found", len(df_comp) if not df_comp.empty else 0],
        ["Other Products Available", len(df_other) if not df_other.empty else 0],
        [],
        ["Pricing Summary", ""],
        ["Base Price (ATC Compatible)", f"=SUM('ATC Compatible'!D2:D100)" if not df_comp.empty else 0],
        ["Margin per PC", 4000],
        ["GST 18%", f"=(B12+B13)*0.18"],
        ["Grand Price per PC", f"=B12+B13+B14"],
        ["Total Bid Value (Qty * Grand)", f"=B15*B6"],
    ]

    for r_idx, row in enumerate(summary_data, start=4):
        for c_idx, val in enumerate(row, start=1):
            cell = ws1.cell(row=r_idx, column=c_idx, value=val)
            if r_idx==4 or r_idx==11: # headers
                cell.font = header_font
                cell.fill = header_fill
                cell.border = border
            else:
                cell.border = border

    for col in ['A','B']:
        ws1.column_dimensions[col].width = 35

    # ===== SHEET 2: ATC Compatible =====
    ws2 = wb.create_sheet("ATC Compatible")

    ws2.merge_cells('A1:F1')
    ws2['A1'] = f"ATC Required Products - Compatible Models (Bid: {bid_meta.get('bid_no','')})"
    ws2['A1'].font = Font(bold=True, size=12)
    ws2['A1'].fill = sub_header_fill

    headers = ["S.No", "Product (From ATC)", "ATC Spec (Exact from ATC)", "Compatible Model (From Master)", "Price (₹)", "Reason / Compatibility"]
    for c, h in enumerate(headers, start=1):
        cell = ws2.cell(row=2, column=c, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
        cell.alignment = Alignment(horizontal='center')

    if not df_comp.empty:
        for r_idx, (_, row) in enumerate(df_comp.iterrows(), start=3):
            ws2.cell(row=r_idx, column=1, value=r_idx-2).border = border
            ws2.cell(row=r_idx, column=2, value=row.get('Product','')).border = border
            ws2.cell(row=r_idx, column=3, value=row.get('ATC Spec','')).border = border
            ws2.cell(row=r_idx, column=4, value=row.get('Compatible Model','')).border = border
            ws2.cell(row=r_idx, column=5, value=row.get('Price',0)).border = border
            ws2.cell(row=r_idx, column=5).number_format = '₹#,##0'
            ws2.cell(row=r_idx, column=6, value=row.get('Reason','')).border = border

        # Total row
        total_row = len(df_comp) + 3
        ws2.cell(row=total_row, column=2, value="TOTAL BASE PRICE").font = bold
        ws2.cell(row=total_row, column=2).border = border
        ws2.cell(row=total_row, column=5, value=f"=SUM(E3:E{total_row-1})").font = bold
        ws2.cell(row=total_row, column=5).border = border
        ws2.cell(row=total_row, column=5).number_format = '₹#,##0'

    for col, width in zip(['A','B','C','D','E','F'], [8,20,35,30,15,20]):
        ws2.column_dimensions[col].width = width

    # ===== SHEET 3: Other Products =====
    ws3 = wb.create_sheet("Other Products")

    ws3.merge_cells('A1:E1')
    ws3['A1'] = "Other Products - Available in Master List (Not Required in ATC but can be mentioned)"
    ws3['A1'].font = Font(bold=True, size=12)
    ws3['A1'].fill = PatternFill(start_color="FDE68A", end_color="FDE68A", fill_type="solid")

    headers3 = ["S.No", "Other Product", "Available Model", "Price (₹)", "Specs"]
    for c, h in enumerate(headers3, start=1):
        cell = ws3.cell(row=2, column=c, value=h)
        cell.font = header_font
        cell.fill = PatternFill(start_color="D97706", end_color="D97706", fill_type="solid")
        cell.border = border

    if not df_other.empty:
        for r_idx, (_, row) in enumerate(df_other.iterrows(), start=3):
            ws3.cell(row=r_idx, column=1, value=r_idx-2).border = border
            ws3.cell(row=r_idx, column=2, value=row.get('Other Product','')).border = border
            ws3.cell(row=r_idx, column=2).fill = other_fill
            ws3.cell(row=r_idx, column=3, value=row.get('Available Model','')).border = border
            ws3.cell(row=r_idx, column=4, value=row.get('Price (₹)',0)).border = border
            ws3.cell(row=r_idx, column=4).number_format = '₹#,##0'
            ws3.cell(row=r_idx, column=5, value=row.get('Specs','')).border = border

    for col, width in zip(['A','B','C','D','E'], [8,20,30,15,35]):
        ws3.column_dimensions[col].width = width

    # ===== SHEET 4: Final Combined =====
    ws4 = wb.create_sheet("Final Combined List")

    ws4.merge_cells('A1:F1')
    ws4['A1'] = f"FINAL COMBINED LIST - ATC + Other Products | Bid: {bid_meta.get('bid_no','')} | Qty: {bid_meta.get('qty','')}"
    ws4['A1'].font = Font(bold=True, size=12)
    ws4['A1'].fill = header_fill
    ws4['A1'].font = Font(bold=True, color="FFFFFF")

    headers4 = ["Type", "Product", "Model", "Price (₹)", "Specs / ATC Spec", "Compatibility"]
    for c, h in enumerate(headers4, start=1):
        cell = ws4.cell(row=2, column=c, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border

    row_num = 3
    if not df_comp.empty:
        for _, r in df_comp.iterrows():
            ws4.cell(row=row_num, column=1, value="ATC Required").border = border
            ws4.cell(row=row_num, column=1).fill = sub_header_fill
            ws4.cell(row=row_num, column=2, value=r.get('Product','')).border = border
            ws4.cell(row=row_num, column=3, value=r.get('Compatible Model','')).border = border
            ws4.cell(row=row_num, column=4, value=r.get('Price',0)).border = border
            ws4.cell(row=row_num, column=4).number_format = '₹#,##0'
            ws4.cell(row=row_num, column=5, value=r.get('ATC Spec','')).border = border
            ws4.cell(row=row_num, column=6, value=r.get('Compatibility','')).border = border
            row_num+=1

    if not df_other.empty:
        for _, r in df_other.iterrows():
            ws4.cell(row=row_num, column=1, value="Other Product").border = border
            ws4.cell(row=row_num, column=1).fill = other_fill
            ws4.cell(row=row_num, column=2, value=r.get('Other Product','')).border = border
            ws4.cell(row=row_num, column=3, value=r.get('Available Model','')).border = border
            ws4.cell(row=row_num, column=4, value=r.get('Price (₹)',0)).border = border
            ws4.cell(row=row_num, column=4).number_format = '₹#,##0'
            ws4.cell(row=row_num, column=5, value=r.get('Specs','')).border = border
            ws4.cell(row=row_num, column=6, value="Optional Mention").border = border
            row_num+=1

    for col, width in zip(['A','B','C','D','E','F'], [15,20,30,15,35,18]):
        ws4.column_dimensions[col].width = width

    # Save to buffer
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer

# HEADER
st.markdown('<div class="hero"><div style="font-size:20px; font-weight:800;">🇮🇳 GeM — Proper Excel Export 📊</div><div style="font-size:11px; opacity:0.7;">ATC Image + Bid + Master → Proper Formatted Excel with 4 Sheets</div></div><div class="tricolor"></div>', unsafe_allow_html=True)

if st.button("🗑️ Clear All", type="primary"):
    for k in list(st.session_state.keys()): del st.session_state[k]
    st.rerun()

st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown("#### 📂 Upload 3 Files")
c1,c2,c3 = st.columns(3)
with c1:
    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    st.markdown('**📄 ATC — PDF/Image**')
    atc_file = st.file_uploader("ATC", type=["pdf","jpg","jpeg","png","bmp","webp"], key="atc", label_visibility="collapsed")
    atc_products=[]; atc_spec_map={}; atc_text=""; atc_type=""
    if atc_file:
        atc_text, atc_type, _ = read_atc_any(atc_file)
        if atc_text:
            atc_products, atc_spec_map = parse_atc_components(atc_text)
            st.success(f"✅ {len(atc_products)} comps | {atc_type}")
        else:
            st.error("❌ Could not read ATC")
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    st.markdown('**📑 Bid PDF**')
    bid_file = st.file_uploader("Bid", type=["pdf"], key="bid", label_visibility="collapsed")
    bid_meta = {"bid_no":"","org":"","dept":"","item":"Desktop Computer","qty":65}
    bid_text=""
    if bid_file:
        bid_text = read_pdf_text(bid_file)
        bid_meta = parse_bid_meta(bid_text)
        st.success(f"✅ {bid_meta['bid_no'] or 'Bid'} | Qty {bid_meta['qty']}")
    st.markdown('</div>', unsafe_allow_html=True)

with c3:
    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    st.markdown('**📊 Master Excel**')
    master_file = st.file_uploader("Master", type=["xlsx","xls","csv"], key="master", label_visibility="collapsed")
    df_master=None
    if master_file:
        try:
            df_master = pd.read_excel(master_file) if not master_file.name.endswith('.csv') else pd.read_csv(master_file)
            st.success(f"✅ {len(df_master)} models")
        except Exception as e:
            st.error(f"{e}")
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

if atc_file and bid_file and master_file and df_master is not None and not df_master.empty:

    df_master.columns = [str(c).strip().lower() for c in df_master.columns]
    prod_col = next((c for c in df_master.columns if 'product' in c or 'component' in c), df_master.columns[0])
    model_col = next((c for c in df_master.columns if 'model' in c), df_master.columns[1] if len(df_master.columns)>1 else prod_col)
    price_col = next((c for c in df_master.columns if 'price' in c or 'rate' in c), df_master.columns[2] if len(df_master.columns)>2 else prod_col)
    specs_col = next((c for c in df_master.columns if 'spec' in c), None)

    if len(atc_products)==0:
        atc_products = list(df_master[prod_col].astype(str).unique())[:15]

    fresh_rows=[]; other_rows=[]
    for comp in atc_products:
        mask = df_master[prod_col].astype(str).str.lower().str.contains(comp.lower().split()[0], na=False)
        df_filtered = df_master[mask] if mask.any() else pd.DataFrame()
        if df_filtered.empty:
            for kw in KEYWORDS.get(comp, [comp.lower()]):
                mask = df_master[prod_col].astype(str).str.lower().str.contains(kw, na=False)
                if mask.any():
                    df_filtered = df_master[mask]
                    break
        if df_filtered.empty:
            fresh_rows.append({"Product": comp, "ATC Spec": atc_spec_map.get(comp, ""), "Compatible Model": "Not in Master", "Price": 0, "Compatibility": "❌ Missing", "Reason": "Add"})
            continue
        found=False
        for _, row in df_filtered.iterrows():
            try:
                model=str(row[model_col]); specs=str(row[specs_col]) if specs_col and specs_col in row else ""; price=row[price_col]
                ok,reason=is_compatible(atc_spec_map.get(comp, ""),model,specs)
                if ok:
                    fresh_rows.append({"Product": comp, "ATC Spec": atc_spec_map.get(comp, ""), "Compatible Model": model, "Price": price, "Specs": specs, "Compatibility": "✅ Compatible", "Reason": reason})
                    found=True; break
            except: continue
        if not found:
            try:
                row=df_filtered.iloc[0]; model=str(row[model_col]); specs=str(row[specs_col]) if specs_col and specs_col in df_filtered.columns else ""; price=row[price_col]
                fresh_rows.append({"Product": comp, "ATC Spec": atc_spec_map.get(comp, ""), "Compatible Model": model, "Price": price, "Specs": specs, "Compatibility": "❌ Not Compatible", "Reason": "Check spec"})
            except: pass

    all_master_products = df_master[prod_col].astype(str).unique().tolist()
    for prod in all_master_products:
        if prod.lower() not in [p.lower() for p in atc_products] and prod.lower().split()[0] not in [p.lower().split()[0] for p in atc_products]:
            df_other_temp = df_master[df_master[prod_col].astype(str)==prod]
            if not df_other_temp.empty:
                try:
                    df_other_sorted = df_other_temp.sort_values(by=price_col, ascending=True)
                    row=df_other_sorted.iloc[0]
                    other_rows.append({"Other Product": prod, "Available Model": str(row[model_col]), "Price (₹)": row[price_col], "Specs": str(row[specs_col]) if specs_col and specs_col in row else "", "Category": "Other"})
                except:
                    row=df_other_temp.iloc[0]
                    other_rows.append({"Other Product": prod, "Available Model": str(row[model_col]), "Price (₹)": row[price_col], "Specs": "", "Category": "Other"})

    df_fresh = pd.DataFrame(fresh_rows) if fresh_rows else pd.DataFrame(columns=["Product","ATC Spec","Compatible Model","Price","Compatibility","Reason"])
    df_other = pd.DataFrame(other_rows) if other_rows else pd.DataFrame(columns=["Other Product","Available Model","Price (₹)","Specs"])
    df_comp = df_fresh[df_fresh["Compatibility"]=="✅ Compatible"] if "Compatibility" in df_fresh.columns and not df_fresh.empty else pd.DataFrame()

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)

    tab1,tab2,tab3 = st.tabs(["✅ ATC Compatible", "📦 Other Products", "📊 Proper Excel Download"])

    with tab1:
        if not df_comp.empty:
            st.dataframe(df_comp, use_container_width=True)
        else:
            st.dataframe(df_fresh, use_container_width=True)

    with tab2:
        if not df_other.empty:
            st.dataframe(df_other, use_container_width=True)
        else:
            st.info("No other products")

    with tab3:
        st.markdown("### 📊 Proper Excel File — 4 Sheets Formatted")
        st.markdown("""
        **Excel contains:**
        - **Sheet 1: Bid Summary** — Bid No, Org, Qty, Total Value with formulas
        - **Sheet 2: ATC Compatible** — S.No, Product, ATC Spec, Compatible Model, Price (₹ formatted)
        - **Sheet 3: Other Products** — Other product types with model & price
        - **Sheet 4: Final Combined List** — ATC + Other together for submission
        """)

        if not df_comp.empty or not df_other.empty:
            excel_buffer = create_proper_excel(bid_meta, df_comp, df_other, atc_products, atc_type)

            st.success("✅ Proper Excel Generated!")

            st.download_button(
                label="📥 Download PROPER EXCEL FILE (4 Sheets, Formatted)",
                data=excel_buffer,
                file_name=f"GeM_Proper_{bid_meta.get('bid_no','Bid')}_{datetime.now().strftime('%d%m%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary"
            )

            # Also show preview
            st.markdown("**Preview — Final Combined:**")
            combined_preview = []
            if not df_comp.empty:
                for _, r in df_comp.iterrows():
                    combined_preview.append([ "ATC Required", r.get('Product',''), r.get('Compatible Model',''), r.get('Price',0), r.get('ATC Spec','') ])
            if not df_other.empty:
                for _, r in df_other.iterrows():
                    combined_preview.append([ "Other Product", r.get('Other Product',''), r.get('Available Model',''), r.get('Price (₹)',0), r.get('Specs','') ])
            if combined_preview:
                df_prev = pd.DataFrame(combined_preview, columns=["Type","Product","Model","Price","Specs"])
                st.dataframe(df_prev, use_container_width=True)

        else:
            st.warning("No data to generate Excel")

    st.markdown('</div>', unsafe_allow_html=True)

elif atc_file or bid_file or master_file:
    st.info("⬆️ Upload all 3 files to get Proper Excel")