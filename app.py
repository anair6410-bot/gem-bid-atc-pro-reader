import streamlit as st
import pandas as pd
import re
from PIL import Image
import io

try:
    from pypdf import PdfReader
except:
    from PyPDF2 import PdfReader

# Try OCR - optional, if not available will fallback
try:
    import pytesseract
    OCR_AVAILABLE = True
except:
    OCR_AVAILABLE = False

st.set_page_config(page_title="GeM ATC Image Support", layout="wide", page_icon="🇮🇳")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800&display=swap');
* { font-family: 'Outfit', sans-serif; }
.stApp { background: #F8FAFF; }
.hero { background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); border-radius: 18px; padding: 18px 24px; color: white; }
.tricolor { height:4px; background: linear-gradient(90deg, #FF9933 0%, #FFF 50%, #138808 100%); border-radius:10px; margin:10px 0; }
.glass-card { background: white; border-radius: 16px; padding: 18px; border: 1px solid #E2E8F0; box-shadow: 0 4px 20px rgba(0,0,0,0.05); margin-bottom:14px; }
.upload-card { background: #F8FAFC; border: 1.5px dashed #CBD5E1; border-radius: 14px; padding: 16px; text-align:center; min-height: 190px; }
.upload-card:hover { border-color: #6366F1; background: #EEF2FF; }
.badge-atc { background:#DBEAFE; color:#1E40AF; padding:3px 10px; border-radius:20px; font-size:10px; font-weight:700; }
.badge-bid { background:#FEF3C7; color:#92400E; padding:3px 10px; border-radius:20px; font-size:10px; font-weight:700; }
.badge-master { background:#D1FAE5; color:#065F46; padding:3px 10px; border-radius:20px; font-size:10px; font-weight:700; }
</style>
""", unsafe_allow_html=True)

KEYWORDS = {
    "Processor CPU": ["processor", "cpu", "i3", "i5", "i7", "ryzen"],
    "MB": ["motherboard"], "Graphics CARD": ["graphics", "gpu"], "OS": ["windows", "linux", "operating system"],
    "RAM": ["ram", "memory"], "SSD": ["ssd", "nvme"], "SSD (SECONDARY)": ["secondary hdd", "1 tb", "2 tb", "secondary"],
    "Cabinet LTR": ["cabinet", "chassis"], "SMPS WATT": ["smps", "power supply"], "MONITOR": ["monitor", "inch", "display"],
    "SPEAKER": ["speaker"], "WIRELESS + BLUETOOTH": ["wifi", "wireless", "bluetooth"], "MS OFFICE": ["ms office"],
    "CHASSIS SWITCH": ["chassis intrusion"], "TPM 2.0": ["tpm"], "CAMERA": ["camera", "webcam"], "ANTIVIRUS": ["antivirus"],
    "DP PORT": ["display port", "dp port"], "SERIAL COM PORT+PARALLEL": ["serial", "com port"], "Keyboard & Mouse": ["keyboard", "mouse"]
}

def read_pdf_text(file):
    try:
        r = PdfReader(file)
        text = ""
        for p in r.pages:
            text += (p.extract_text() or "") + "\n"
        return text
    except:
        return ""

def read_image_ocr(image_file):
    """OCR from image file"""
    try:
        if not OCR_AVAILABLE:
            return ""
        img = Image.open(image_file)
        text = pytesseract.image_to_string(img)
        return text
    except Exception as e:
        return ""

def read_atc_any(file):
    """
    NEW: ATC can be PDF, JPG, PNG, JPEG, Scanned PDF
    Returns text + type
    """
    filename = file.name.lower()

    # Case 1: Image file - JPG/PNG
    if filename.endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp')):
        st.info(f"📸 Image ATC detected: {file.name} - Using OCR to read...")
        text = read_image_ocr(file)
        if len(text.strip()) < 20:
            # Try with enhancement
            try:
                img = Image.open(file).convert('L')
                text = pytesseract.image_to_string(img) if OCR_AVAILABLE else ""
            except:
                text = ""
        return text, "image"

    # Case 2: PDF file
    elif filename.endswith('.pdf'):
        text = read_pdf_text(file)
        # If PDF has very little text, it's scanned - try OCR
        if len(text.strip()) < 100:
            st.warning("📄 Scanned PDF detected - Text extraction low, trying OCR...")
            if OCR_AVAILABLE:
                try:
                    # Try to convert PDF pages to images and OCR
                    # Fallback: use fitz if available
                    try:
                        import fitz # PyMuPDF
                        doc = fitz.open(stream=file.read(), filetype="pdf")
                        ocr_text = ""
                        for page in doc:
                            pix = page.get_pixmap(dpi=200)
                            img_data = pix.tobytes("png")
                            img = Image.open(io.BytesIO(img_data))
                            ocr_text += pytesseract.image_to_string(img) + "\n"
                        if len(ocr_text) > len(text):
                            text = ocr_text
                    except:
                        # If fitz not available, keep original text
                        pass
                except:
                    pass
            else:
                st.warning("⚠️ OCR library not available. For image ATC, add pytesseract to requirements.")
        return text, "pdf"

    else:
        return "", "unknown"

def parse_atc_components(atc_text):
    if not atc_text:
        return [], {}
    low = atc_text.lower()
    required = []
    spec_map = {}
    for prod, kws in KEYWORDS.items():
        for kw in kws:
            if kw in low:
                for line in atc_text.split("\n"):
                    if kw in line.lower() and 5 < len(line) < 250:
                        if prod not in spec_map:
                            spec_map[prod] = line.strip()
                if prod not in required:
                    required.append(prod)
                break
    return required, spec_map

def parse_bid_meta(bid_text):
    data = {}
    try:
        m = re.search(r'GEM\/\d{4}\/B\/\d{4,10}', bid_text.replace(" ","").upper())
        data['bid_no'] = m.group(0) if m else ""
        m = re.search(r'Organisation\s*Name\s*[:\-]?\s*([^\n]+)', bid_text, re.I)
        data['org'] = m.group(1).strip()[:100] if m else ""
        m = re.search(r'Ministry\s*Name\s*[:\-]?\s*([^\n]+)|Department\s*Name\s*[:\-]?\s*([^\n]+)', bid_text, re.I)
        data['dept'] = (m.group(1) or m.group(2) or "").strip()[:100] if m else ""
        m = re.search(r'Item\s*Category\s*[:\-]?\s*([^\n]+)', bid_text, re.I)
        data['item'] = m.group(1).strip()[:100] if m else "Desktop Computer"
        m = re.search(r'Quantity\s*[:\-]?\s*(\d+)', bid_text, re.I)
        data['qty'] = int(m.group(1)) if m else 65
    except:
        data = {'bid_no':"", 'org':"", 'dept':"", 'item':"Desktop Computer", 'qty':65}
    return data

def is_compatible(atc_spec_line, model_name, model_specs):
    atc = (atc_spec_line or "").lower()
    model = f"{model_name} {model_specs}".lower()
    if "i5" in atc and "i3" in model: return False, "ATC needs i5, model i3"
    if "i7" in atc and ("i3" in model or "i5" in model): return False, "ATC needs i7"
    if "16 gb" in atc and "8 gb" in model: return False, "ATC needs 16GB"
    if "32 gb" in atc and ("8 gb" in model or "16 gb" in model): return False, "ATC needs 32GB"
    if "512" in atc and "256" in model and "ssd" in atc: return False, "ATC needs 512GB"
    if "24 inch" in atc and "21.5" in model: return False, "ATC needs 24 inch"
    if "ddr5" in atc and "ddr4" in model: return False, "ATC needs DDR5"
    return True, "Matches ATC"

# HEADER
st.markdown('<div class="hero"><div><div style="font-size:21px; font-weight:800;">🇮🇳 GeM 3-Doc — ATC Image Supported 📸</div><div style="font-size:12px; opacity:0.7;">ATC = PDF or IMAGE (JPG/PNG) + Scanned PDF with OCR • Bid = PDF • Master = Excel</div></div><div style="font-size:11px; opacity:0.5;">V8 Image</div></div><div class="tricolor"></div>', unsafe_allow_html=True)

if st.button("🗑️ Clear All", type="primary"):
    for k in list(st.session_state.keys()): del st.session_state[k]
    st.rerun()

# 3 UPLOADS - ATC NOW SUPPORTS IMAGE
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown("#### 📂 Upload Documents — ATC Now Supports IMAGE")

c1,c2,c3 = st.columns(3)

with c1:
    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    st.markdown(f'**📄 ATC Document** <span class="badge-atc">PDF + IMAGE 📸</span>')
    st.caption("PDF, JPG, PNG, Scanned PDF all allowed")
    atc_file = st.file_uploader("ATC PDF/Image", type=["pdf","jpg","jpeg","png","bmp","webp"], key="atc", label_visibility="collapsed")
    atc_products = []; atc_spec_map = {}; atc_text=""; atc_type=""
    if atc_file:
        atc_text, atc_type = read_atc_any(atc_file)
        if atc_text:
            atc_products, atc_spec_map = parse_atc_components(atc_text)
            st.success(f"✅ {len(atc_products)} components ({atc_type})")
            if atc_products:
                st.caption(", ".join(atc_products[:8]))
            with st.expander("See extracted text from image/PDF"):
                st.text(atc_text[:3000])
        else:
            st.error("❌ Could not read text. If image, make sure it's clear. Add pytesseract to requirements.")
            if not OCR_AVAILABLE:
                st.warning("OCR not installed. Add to requirements.txt: pytesseract, Pillow, PyMuPDF")
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    st.markdown(f'**📑 Full Bid Doc** <span class="badge-bid">PDF</span>')
    bid_file = st.file_uploader("Bid PDF", type=["pdf"], key="bid", label_visibility="collapsed")
    bid_meta = {"bid_no":"","org":"","dept":"","item":"Desktop Computer","qty":65}
    bid_text = ""
    if bid_file:
        bid_text = read_pdf_text(bid_file)
        bid_meta = parse_bid_meta(bid_text)
        st.success(f"✅ {bid_meta['bid_no'] or 'Bid read'} | Qty {bid_meta['qty']}")
    st.markdown('</div>', unsafe_allow_html=True)

with c3:
    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    st.markdown(f'**📊 Master List** <span class="badge-master">Excel</span>')
    master_file = st.file_uploader("Master Excel", type=["xlsx","xls","csv"], key="master", label_visibility="collapsed")
    df_master = None
    if master_file:
        try:
            df_master = pd.read_excel(master_file) if not master_file.name.endswith('.csv') else pd.read_csv(master_file)
            st.success(f"✅ {len(df_master)} models")
            st.dataframe(df_master.head(2), use_container_width=True)
        except Exception as e:
            st.error(f"{e}")
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# GENERATE
if atc_file and bid_file and master_file and df_master is not None and len(df_master) > 0:

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown(f"### ✅ Fresh List — ATC ({atc_type.upper()}) + Bid Compatibility")

    if len(atc_products) == 0:
        st.warning("ATC has 0 products detected - Showing fallback. Try clearer image.")
        atc_products = list(df_master.iloc[:,0].astype(str).unique())[:20]

    st.info(f"ATC ({atc_type}): {len(atc_products)} → {', '.join(atc_products)} | Bid: {bid_meta['bid_no']} | Qty: {bid_meta['qty']}")

    df_master.columns = [str(c).strip().lower() for c in df_master.columns]
    prod_col = next((c for c in df_master.columns if 'product' in c or 'component' in c or 'item' in c), df_master.columns[0])
    model_col = next((c for c in df_master.columns if 'model' in c), df_master.columns[1] if len(df_master.columns)>1 else prod_col)
    price_col = next((c for c in df_master.columns if 'price' in c or 'rate' in c or 'cost' in c), df_master.columns[2] if len(df_master.columns)>2 else prod_col)
    specs_col = next((c for c in df_master.columns if 'spec' in c or 'desc' in c), None)

    fresh_rows = []
    for comp in atc_products:
        mask = df_master[prod_col].astype(str).str.lower().str.contains(comp.lower().split()[0], na=False)
        df_filtered = df_master[mask] if mask.any() else pd.DataFrame()
        if df_filtered.empty:
            for kw in KEYWORDS.get(comp, [comp.lower()]):
                mask = df_master[prod_col].astype(str).str.lower().str.contains(kw, na=False) | df_master[model_col].astype(str).str.lower().str.contains(kw, na=False)
                if mask.any():
                    df_filtered = df_master[mask]
                    break
        if df_filtered.empty:
            fresh_rows.append({"Product": comp, "ATC Spec": atc_spec_map.get(comp, "As per ATC"), "Compatible Model": "❌ Not in Master", "Price": 0, "Specs": "", "Compatibility": "❌ Missing", "Reason": "Add to master"})
            continue

        found = False
        for _, row in df_filtered.iterrows():
            try:
                model = str(row[model_col])
                specs = str(row[specs_col]) if specs_col and specs_col in row else ""
                price = row[price_col]
                atc_spec = atc_spec_map.get(comp, "")
                ok, reason = is_compatible(atc_spec, model, specs)
                if ok:
                    fresh_rows.append({"Product": comp, "ATC Spec": atc_spec, "Compatible Model": model, "Price": price, "Specs": specs, "Compatibility": "✅ Compatible", "Reason": reason})
                    found = True
                    break
            except:
                continue
        if not found:
            try:
                row = df_filtered.iloc[0]
                model = str(row[model_col])
                specs = str(row[specs_col]) if specs_col and specs_col in df_filtered.columns else ""
                price = row[price_col]
                atc_spec = atc_spec_map.get(comp, "")
                ok, reason = is_compatible(atc_spec, model, specs)
                fresh_rows.append({"Product": comp, "ATC Spec": atc_spec, "Compatible Model": model, "Price": price, "Specs": specs, "Compatibility": "❌ Not Compatible", "Reason": reason})
            except:
                pass

    if len(fresh_rows) == 0:
        df_fresh = pd.DataFrame(columns=["Product","ATC Spec","Compatible Model","Price","Specs","Compatibility","Reason"])
    else:
        df_fresh = pd.DataFrame(fresh_rows)

    if "Compatibility" in df_fresh.columns and not df_fresh.empty:
        df_compatible_only = df_fresh[df_fresh["Compatibility"] == "✅ Compatible"].copy()
    else:
        df_compatible_only = pd.DataFrame(columns=df_fresh.columns if not df_fresh.empty else ["Product","ATC Spec","Compatible Model","Price","Specs","Compatibility","Reason"])

    tab1, tab2 = st.tabs(["✅ Final Fresh List", "📋 All Check"])

    with tab1:
        if not df_compatible_only.empty:
            st.dataframe(df_compatible_only[["Product","ATC Spec","Compatible Model","Price","Reason"]], use_container_width=True)
            try:
                total = pd.to_numeric(df_compatible_only["Price"], errors='coerce').fillna(0).sum()
            except:
                total = 0
            qty = bid_meta.get('qty',65)
            margin = st.number_input("Margin per PC ₹", value=4000, step=500, key="margin_final")
            gst = int((total+margin)*0.18)
            grand = total+margin+gst
            total_bid = grand*qty
            st.markdown(f"""
            <div style="background:#0F172A; color:white; padding:16px; border-radius:12px; text-align:center;">
            <div style="font-size:11px; opacity:0.7;">BID: {bid_meta.get('bid_no','')} | Qty: {qty} | ATC Type: {atc_type.upper()} | Products: {len(atc_products)}</div>
            <div style="margin-top:6px;">Base: ₹{total:,.0f} + Margin: ₹{margin:,} + GST: ₹{gst:,}</div>
            <h3 style="margin:8px 0 0 0; color:white;">Grand/PC: ₹{grand:,.0f} | Total: ₹{total_bid:,.0f}</h3>
            </div>
            """, unsafe_allow_html=True)
            st.download_button("📥 Download Compatible CSV", df_compatible_only.to_csv(index=False).encode(), f"Compatible_{bid_meta.get('bid_no','bid')}.csv", use_container_width=True, type="primary")
        else:
            st.warning("No compatible models — showing all")
            if not df_fresh.empty:
                st.dataframe(df_fresh, use_container_width=True)

    with tab2:
        if not df_fresh.empty:
            st.dataframe(df_fresh, use_container_width=True)
            st.download_button("📥 Download Full Check", df_fresh.to_csv(index=False).encode(), f"FullCheck_{bid_meta.get('bid_no','bid')}.csv", use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

elif atc_file or bid_file or master_file:
    st.info("⬆️ Upload all 3: ATC (PDF/Image) + Bid PDF + Master Excel")

st.markdown("""
---
**Now ATC Supports:**

✅ PDF Text
✅ Scanned PDF (OCR)
✅ JPG / JPEG
✅ PNG / WEBP / BMP

Just upload ATC as photo — it will read with OCR and detect components.
""")