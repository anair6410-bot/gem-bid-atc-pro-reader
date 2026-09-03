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

st.set_page_config(page_title="GeM Proper Excel Fixed", layout="wide", page_icon="🇮🇳")

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

def safe_str(x):
    """FIX: Convert float NaN to string safely"""
    if pd.isna(x):
        return ""
    return str(x)

def safe_lower(x):
    """FIX: Safe lower for float"""
    return safe_str(x).lower()

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
            return enhancer.enhance(2.0)
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
    low=safe_lower(atc_text)
    required=[]; spec_map={}
    for prod,kws in KEYWORDS.items():
        for kw in kws:
            if kw in low:
                for line in atc_text.split("\n"):
                    if safe_lower(kw) in safe_lower(line) and 5<len(line)<250:
                        if prod not in spec_map: spec_map[prod]=line.strip()
                if prod not in required: required.append(prod)
                break
    return required, spec_map

def parse_bid_meta(bid_text):
    data={'bid_no':"", 'org':"", 'dept':"", 'item':"Desktop Computer", 'qty':65}
    try:
        m=re.search(r'GEM\/\d{4}\/B\/\d{4,10}', safe_str(bid_text).replace(" ","").upper())
        data['bid_no']=m.group(0) if m else ""
        m=re.search(r'Organisation\s*Name\s*[:\-]?\s*([^\n]+)', safe_str(bid_text), re.I)
        data['org']=safe_str(m.group(1).strip()[:100]) if m else ""
        m=re.search(r'Quantity\s*[:\-]?\s*(\d+)', safe_str(bid_text), re.I)
        data['qty']=int(m.group(1)) if m else 65
    except: pass
    return data

def is_compatible(atc_spec, model, specs):
    atc=safe_lower(atc_spec)
    m=safe_lower(f"{model} {specs}")
    if "i5" in atc and "i3" in m: return False, "ATC i5 vs i3"
    if "16 gb" in atc and "8 gb" in m: return False, "ATC 16GB"
    if "512" in atc and "256" in m: return False, "ATC 512GB"
    return True, "Compatible"

def create_proper_excel(bid_meta, df_comp, df_other, atc_products, atc_type):
    wb = Workbook()
    header_font = Font(name='Calibri', bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    bold = Font(bold=True)

    # Sheet 1: Summary
    ws1 = wb.active
    ws1.title = "Bid Summary"
    ws1.merge_cells('A1:E1')
    ws1['A1'] = f"GeM Bid Proposal - {safe_str(bid_meta.get('bid_no',''))}"
    ws1['A1'].font = Font(bold=True, size=14)

    summary_data = [
        ["Field", "Value"],
        ["Bid Number", safe_str(bid_meta.get('bid_no',''))],
        ["Organisation", safe_str(bid_meta.get('org',''))],
        ["Quantity", bid_meta.get('qty',65)],
        ["ATC Products Required", len(atc_products)],
        ["ATC Compatible Found", len(df_comp) if not df_comp.empty else 0],
        ["Other Products", len(df_other) if not df_other.empty else 0],
        [],
        ["Pricing Summary", ""],
        ["Base Price", f"=SUM('ATC Compatible'!D2:D100)" if not df_comp.empty else 0],
        ["Margin per PC", 4000],
        ["GST 18%", f"=(B10+B11)*0.18"],
        ["Grand Price per PC", f"=B10+B11+B12"],
        ["Total Bid Value", f"=B13*B4"],
    ]
    for r_idx, row in enumerate(summary_data, start=3):
        for c_idx, val in enumerate(row, start=1):
            cell = ws1.cell(row=r_idx, column=c_idx, value=val)
            cell.border = border
            if r_idx==3 or r_idx==9:
                cell.font = header_font
                cell.fill = header_fill

    for col in ['A','B']: ws1.column_dimensions[col].width = 35

    # Sheet 2: ATC Compatible
    ws2 = wb.create_sheet("ATC Compatible")
    headers = ["S.No", "Product (From ATC)", "ATC Spec", "Compatible Model", "Price (₹)", "Reason"]
    for c, h in enumerate(headers, start=1):
        cell = ws2.cell(row=1, column=c, value=h)
        cell.font = header_font; cell.fill = header_fill; cell.border = border

    if not df_comp.empty:
        for r_idx, (_, row) in enumerate(df_comp.iterrows(), start=2):
            ws2.cell(row=r_idx, column=1, value=r_idx-1).border=border
            ws2.cell(row=r_idx, column=2, value=safe_str(row.get('Product',''))).border=border
            ws2.cell(row=r_idx, column=3, value=safe_str(row.get('ATC Spec',''))).border=border
            ws2.cell(row=r_idx, column=4, value=safe_str(row.get('Compatible Model',''))).border=border
            ws2.cell(row=r_idx, column=5, value=row.get('Price',0)).border=border
            ws2.cell(row=r_idx, column=5).number_format='₹#,##0'
            ws2.cell(row=r_idx, column=6, value=safe_str(row.get('Reason',''))).border=border

        total_row = len(df_comp)+2
        ws2.cell(row=total_row, column=2, value="TOTAL").font=bold; ws2.cell(row=total_row, column=2).border=border
        ws2.cell(row=total_row, column=5, value=f"=SUM(E2:E{total_row-1})").font=bold; ws2.cell(row=total_row, column=5).border=border

    for col, w in zip(['A','B','C','D','E','F'], [8,20,35,30,15,20]): ws2.column_dimensions[col].width=w

    # Sheet 3: Other Products
    ws3 = wb.create_sheet("Other Products")
    headers3 = ["S.No", "Other Product", "Available Model", "Price (₹)", "Specs"]
    for c, h in enumerate(headers3, start=1):
        cell=ws3.cell(row=1, column=c, value=h)
        cell.font=header_font; cell.fill=PatternFill(start_color="D97706", end_color="D97706", fill_type="solid"); cell.border=border

    if not df_other.empty:
        for r_idx, (_, row) in enumerate(df_other.iterrows(), start=2):
            ws3.cell(row=r_idx, column=1, value=r_idx-1).border=border
            ws3.cell(row=r_idx, column=2, value=safe_str(row.get('Other Product',''))).border=border
            ws3.cell(row=r_idx, column=3, value=safe_str(row.get('Available Model',''))).border=border
            ws3.cell(row=r_idx, column=4, value=row.get('Price (₹)',0)).border=border
            ws3.cell(row=r_idx, column=4).number_format='₹#,##0'
            ws3.cell(row=r_idx, column=5, value=safe_str(row.get('Specs',''))).border=border

    for col, w in zip(['A','B','C','D','E'], [8,20,30,15,35]): ws3.column_dimensions[col].width=w

    # Sheet 4: Final Combined
    ws4 = wb.create_sheet("Final Combined List")
    headers4 = ["Type", "Product", "Model", "Price (₹)", "Specs / ATC Spec", "Compatibility"]
    for c, h in enumerate(headers4, start=1):
        cell=ws4.cell(row=1, column=c, value=h)
        cell.font=header_font; cell.fill=header_fill; cell.border=border

    row_num=2
    if not df_comp.empty:
        for _, r in df_comp.iterrows():
            ws4.cell(row=row_num, column=1, value="ATC Required").border=border
            ws4.cell(row=row_num, column=2, value=safe_str(r.get('Product',''))).border=border
            ws4.cell(row=row_num, column=3, value=safe_str(r.get('Compatible Model',''))).border=border
            ws4.cell(row=row_num, column=4, value=r.get('Price',0)).border=border
            ws4.cell(row=row_num, column=4).number_format='₹#,##0'
            ws4.cell(row=row_num, column=5, value=safe_str(r.get('ATC Spec',''))).border=border
            ws4.cell(row=row_num, column=6, value=safe_str(r.get('Compatibility',''))).border=border
            row_num+=1

    if not df_other.empty:
        for _, r in df_other.iterrows():
            ws4.cell(row=row_num, column=1, value="Other Product").border=border
            ws4.cell(row=row_num, column=2, value=safe_str(r.get('Other Product',''))).border=border
            ws4.cell(row=row_num, column=3, value=safe_str(r.get('Available Model',''))).border=border
            ws4.cell(row=row_num, column=4, value=r.get('Price (₹)',0)).border=border
            ws4.cell(row=row_num, column=4).number_format='₹#,##0'
            ws4.cell(row=row_num, column=5, value=safe_str(r.get('Specs',''))).border=border
            ws4.cell(row=row_num, column=6, value="Optional Mention").border=border
            row_num+=1

    for col, w in zip(['A','B','C','D','E','F'], [15,20,30,15,35,18]): ws4.column_dimensions[col].width=w

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer

# UI
st.markdown('<div class="hero"><div style="font-size:20px; font-weight:800;">🇮🇳 GeM — Proper Excel Fixed ✅</div><div style="font-size:11px; opacity:0.7;">Float-safe + Proper Excel with 4 sheets</div></div><div class="tricolor"></div>', unsafe_allow_html=True)

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
            st.error("❌ Could not read ATC - try clearer image or text PDF")
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
            # FIX: Clean NaN immediately
            df_master = df_master.fillna("")
            st.success(f"✅ {len(df_master)} models loaded (NaN cleaned)")
            st.dataframe(df_master.head(2), use_container_width=True)
        except Exception as e:
            st.error(f"{e}")
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

if atc_file and bid_file and master_file and df_master is not None and not df_master.empty:

    # FIX: Clean master fully - remove float NaN
    df_master = df_master.fillna("")
    for col in df_master.columns:
        df_master[col] = df_master[col].apply(lambda x: "" if pd.isna(x) else x)

    df_master.columns = [safe_str(c).strip().lower() for c in df_master.columns]
    prod_col = next((c for c in df_master.columns if 'product' in c or 'component' in c), df_master.columns[0])
    model_col = next((c for c in df_master.columns if 'model' in c), df_master.columns[1] if len(df_master.columns)>1 else prod_col)
    price_col = next((c for c in df_master.columns if 'price' in c or 'rate' in c), df_master.columns[2] if len(df_master.columns)>2 else prod_col)
    specs_col = next((c for c in df_master.columns if 'spec' in c), None)

    if len(atc_products)==0:
        # FIX: Use safe_str
        unique_prods = [safe_str(x) for x in df_master[prod_col].unique().tolist() if safe_str(x).strip()!=""]
        atc_products = unique_prods[:15]

    fresh_rows=[]; other_rows=[]

    for comp in atc_products:
        comp_safe = safe_str(comp)
        if not comp_safe.strip():
            continue
        # FIX: Safe lower comparison
        mask = df_master[prod_col].apply(lambda x: safe_lower(x).find(safe_lower(comp_safe).split()[0])!=-1 if safe_lower(comp_safe).split() else False)
        df_filtered = df_master[mask] if mask.any() else pd.DataFrame()

        if df_filtered.empty:
            for kw in KEYWORDS.get(comp_safe, [safe_lower(comp_safe)]):
                kw_safe = safe_lower(kw)
                mask = df_master[prod_col].apply(lambda x: kw_safe in safe_lower(x)) | df_master[model_col].apply(lambda x: kw_safe in safe_lower(x))
                if mask.any():
                    df_filtered = df_master[mask]
                    break

        if df_filtered.empty:
            fresh_rows.append({"Product": comp_safe, "ATC Spec": safe_str(atc_spec_map.get(comp_safe, "")), "Compatible Model": "Not in Master", "Price": 0, "Compatibility": "❌ Missing", "Reason": "Add"})
            continue

        found=False
        for _, row in df_filtered.iterrows():
            try:
                model=safe_str(row[model_col]); specs=safe_str(row[specs_col]) if specs_col and specs_col in row else ""; price=row[price_col]
                # price can be float/string - convert
                try: price_val = float(price) if price!="" else 0
                except: price_val = price

                ok,reason=is_compatible(atc_spec_map.get(comp_safe, ""),model,specs)
                if ok:
                    fresh_rows.append({"Product": comp_safe, "ATC Spec": safe_str(atc_spec_map.get(comp_safe, "")), "Compatible Model": model, "Price": price_val, "Specs": specs, "Compatibility": "✅ Compatible", "Reason": reason})
                    found=True; break
            except: continue

        if not found:
            try:
                row=df_filtered.iloc[0]
                model=safe_str(row[model_col]); specs=safe_str(row[specs_col]) if specs_col and specs_col in df_filtered.columns else ""
                price=row[price_col]
                try: price_val = float(price) if price!="" else 0
                except: price_val = price
                fresh_rows.append({"Product": comp_safe, "ATC Spec": safe_str(atc_spec_map.get(comp_safe, "")), "Compatible Model": model, "Price": price_val, "Specs": specs, "Compatibility": "❌ Not Compatible", "Reason": "Check spec"})
            except: pass

    # Other products - FIX float issue here too
    all_master_products = [safe_str(x) for x in df_master[prod_col].unique().tolist() if safe_str(x).strip()!=""]
    atc_lower = [safe_lower(p) for p in atc_products]

    for prod in all_master_products:
        prod_lower = safe_lower(prod)
        if prod_lower not in atc_lower and (prod_lower.split()[0] not in [p.split()[0] for p in atc_lower if p.split()] if prod_lower.split() else True):
            df_other_temp = df_master[df_master[prod_col].apply(lambda x: safe_str(x)==prod)]
            if not df_other_temp.empty:
                try:
                    # Sort by price - handle non-numeric
                    df_other_temp[price_col] = pd.to_numeric(df_other_temp[price_col], errors='coerce').fillna(0)
                    df_other_sorted = df_other_temp.sort_values(by=price_col, ascending=True)
                    row=df_other_sorted.iloc[0]
                    other_rows.append({"Other Product": prod, "Available Model": safe_str(row[model_col]), "Price (₹)": row[price_col], "Specs": safe_str(row[specs_col]) if specs_col and specs_col in row else ""})
                except:
                    row=df_other_temp.iloc[0]
                    other_rows.append({"Other Product": prod, "Available Model": safe_str(row[model_col]), "Price (₹)": row[price_col], "Specs": ""})

    df_fresh = pd.DataFrame(fresh_rows) if fresh_rows else pd.DataFrame(columns=["Product","ATC Spec","Compatible Model","Price","Compatibility","Reason"])
    df_other = pd.DataFrame(other_rows) if other_rows else pd.DataFrame(columns=["Other Product","Available Model","Price (₹)","Specs"])
    df_comp = df_fresh[df_fresh["Compatibility"]=="✅ Compatible"] if "Compatibility" in df_fresh.columns and not df_fresh.empty else pd.DataFrame()

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)

    tab1,tab2,tab3 = st.tabs(["✅ ATC Compatible", "📦 Other Products", "📊 Proper Excel Download"])

    with tab1:
        if not df_comp.empty: st.dataframe(df_comp, use_container_width=True)
        else: st.dataframe(df_fresh, use_container_width=True)

    with tab2:
        if not df_other.empty: st.dataframe(df_other, use_container_width=True)
        else: st.info("No other products")

    with tab3:
        st.markdown("### 📊 Proper Excel File — 4 Sheets Formatted")

        if not df_comp.empty or not df_other.empty:
            excel_buffer = create_proper_excel(bid_meta, df_comp, df_other, atc_products, atc_type)
            st.success("✅ Proper Excel Generated — Float-safe!")

            st.download_button(
                label="📥 Download PROPER EXCEL FILE (4 Sheets, Formatted)",
                data=excel_buffer,
                file_name=f"GeM_Proper_{safe_str(bid_meta.get('bid_no','Bid')).replace('/','_')}_{datetime.now().strftime('%d%m%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary"
            )
        else:
            st.warning("No data to generate Excel")

    st.markdown('</div>', unsafe_allow_html=True)

elif atc_file or bid_file or master_file:
    st.info("⬆️ Upload all 3 files")