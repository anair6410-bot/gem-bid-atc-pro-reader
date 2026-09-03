import streamlit as st
import pandas as pd
import re
from PIL import Image, ImageEnhance, ImageFilter
import io
import cv2
import numpy as np

try:
    from pypdf import PdfReader
except:
    from PyPDF2 import PdfReader

try:
    import pytesseract
    OCR_AVAILABLE = True
    # Test if binary exists
    try:
        pytesseract.get_tesseract_version()
    except:
        OCR_AVAILABLE = False
except:
    OCR_AVAILABLE = False

st.set_page_config(page_title="GeM ATC Image OCR Fixed", layout="wide", page_icon="🇮🇳")

st.markdown("""
<style>
.stApp { background: #F8FAFF; }
.hero { background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); border-radius: 18px; padding: 18px 24px; color: white; }
.tricolor { height:4px; background: linear-gradient(90deg, #FF9933 0%, #FFF 50%, #138808 100%); border-radius:10px; margin:10px 0; }
.glass-card { background: white; border-radius: 16px; padding: 18px; border: 1px solid #E2E8F0; box-shadow: 0 4px 20px rgba(0,0,0,0.05); margin-bottom:14px; }
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
    "DP PORT": ["display port"], "SERIAL COM PORT+PARALLEL": ["serial", "com port"], "Keyboard & Mouse": ["keyboard", "mouse"]
}

def enhance_image_for_ocr(pil_image):
    """Enhance image to make OCR clear"""
    try:
        # Convert PIL to CV2
        img = np.array(pil_image.convert('RGB'))
        img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

        # Upscale 2x for small images
        h, w = img.shape
        if w < 1500:
            img = cv2.resize(img, (w*2, h*2), interpolation=cv2.INTER_CUBIC)

        # Denoise + Threshold
        img = cv2.medianBlur(img, 1)
        img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

        # Back to PIL
        return Image.fromarray(img)
    except:
        # Fallback PIL only
        try:
            img = pil_image.convert('L')
            img = img.filter(ImageFilter.MedianFilter())
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)
            w, h = img.size
            if w < 1500:
                img = img.resize((w*2, h*2), Image.LANCZOS)
            return img
        except:
            return pil_image

def read_pdf_text(file):
    try:
        file.seek(0)
        r = PdfReader(file)
        text = ""
        for p in r.pages:
            text += (p.extract_text() or "") + "\n"
        return text
    except:
        return ""

def read_image_ocr_fixed(image_file):
    if not OCR_AVAILABLE:
        return "", "OCR binary not found - add packages.txt"

    try:
        image_file.seek(0)
        pil_img = Image.open(image_file)

        # Show original for debug
        st.image(pil_img, caption="Uploaded ATC Image", width=300)

        enhanced = enhance_image_for_ocr(pil_img)

        # OCR with custom config for documents
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(enhanced, config=custom_config)

        # If still low, try psm 3
        if len(text.strip()) < 50:
            custom_config2 = r'--oem 3 --psm 3'
            text2 = pytesseract.image_to_string(enhanced, config=custom_config2)
            if len(text2) > len(text):
                text = text2

        return text, "success"
    except Exception as e:
        return "", f"OCR Error: {str(e)}"

def read_atc_any(file):
    filename = file.name.lower()
    file.seek(0)

    if filename.endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp')):
        text, status = read_image_ocr_fixed(file)
        return text, "image", status

    elif filename.endswith('.pdf'):
        text = read_pdf_text(file)
        if len(text.strip()) < 100: # Scanned PDF
            if OCR_AVAILABLE:
                try:
                    import fitz
                    file.seek(0)
                    doc = fitz.open(stream=file.read(), filetype="pdf")
                    ocr_full = ""
                    for i, page in enumerate(doc):
                        pix = page.get_pixmap(dpi=300)
                        img_data = pix.tobytes("png")
                        pil_img = Image.open(io.BytesIO(img_data))
                        enhanced = enhance_image_for_ocr(pil_img)
                        custom_config = r'--oem 3 --psm 6'
                        page_text = pytesseract.image_to_string(enhanced, config=custom_config)
                        ocr_full += page_text + "\n"
                    if len(ocr_full.strip()) > 50:
                        return ocr_full, "scanned_pdf", "success OCR from scanned PDF"
                    else:
                        return text, "pdf", "Scanned PDF but OCR got low text"
                except Exception as e:
                    return text, "pdf", f"Scanned PDF OCR failed: {e}"
            else:
                return text, "pdf", "Scanned PDF - OCR binary missing"
        return text, "pdf", "text pdf"
    else:
        return "", "unknown", "unsupported"

def parse_atc_components(atc_text):
    if not atc_text: return [], {}
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
    data = {'bid_no':"", 'org':"", 'dept':"", 'item':"Desktop Computer", 'qty':65}
    try:
        m = re.search(r'GEM\/\d{4}\/B\/\d{4,10}', bid_text.replace(" ","").upper())
        data['bid_no'] = m.group(0) if m else ""
        m = re.search(r'Organisation\s*Name\s*[:\-]?\s*([^\n]+)', bid_text, re.I)
        data['org'] = m.group(1).strip()[:100] if m else ""
        m = re.search(r'Quantity\s*[:\-]?\s*(\d+)', bid_text, re.I)
        data['qty'] = int(m.group(1)) if m else 65
    except: pass
    return data

def is_compatible(atc_spec_line, model_name, model_specs):
    atc = (atc_spec_line or "").lower()
    model = f"{model_name} {model_specs}".lower()
    if "i5" in atc and "i3" in model: return False, "ATC i5 vs i3"
    if "i7" in atc and ("i3" in model or "i5" in model): return False, "ATC i7 needed"
    if "16 gb" in atc and "8 gb" in model: return False, "ATC 16GB needed"
    if "512" in atc and "256" in model: return False, "ATC 512GB needed"
    return True, "Matches ATC"

# UI
st.markdown('<div class="hero"><div style="font-size:20px; font-weight:800;">🇮🇳 ATC Image OCR — FIXED ✅</div><div style="font-size:11px; opacity:0.7;">Now supports JPG/PNG + Scanned PDF with enhanced OCR</div></div><div class="tricolor"></div>', unsafe_allow_html=True)

if not OCR_AVAILABLE:
    st.error("⚠️ Tesseract OCR binary NOT FOUND. Please add `packages.txt` with `tesseract-ocr` and reboot app. Then image ATC will work.")
    st.info("Steps: Add file `packages.txt` in GitHub repo root → Write 3 lines: tesseract-ocr, tesseract-ocr-eng, libgl1 → Commit → Reboot app from Streamlit Cloud")

if st.button("🗑️ Clear All", type="primary"):
    for k in list(st.session_state.keys()): del st.session_state[k]
    st.rerun()

st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown("#### 📂 Upload 3 Files — ATC now IMAGE allowed")

c1,c2,c3 = st.columns(3)
with c1:
    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    st.markdown('**📄 ATC — PDF + JPG/PNG 📸**')
    atc_file = st.file_uploader("ATC", type=["pdf","jpg","jpeg","png","bmp","webp"], key="atc", label_visibility="collapsed")
    atc_products=[]; atc_spec_map={}; atc_text=""; atc_type=""; status_msg=""
    if atc_file:
        atc_text, atc_type, status_msg = read_atc_any(atc_file)
        st.caption(f"Status: {status_msg}")
        if atc_text and len(atc_text.strip()) > 10:
            atc_products, atc_spec_map = parse_atc_components(atc_text)
            st.success(f"✅ Read: {len(atc_text)} chars | {len(atc_products)} components")
            if atc_products: st.caption(", ".join(atc_products))
            with st.expander("📄 Extracted Text from Image/PDF"):
                st.text_area("OCR Text", atc_text[:5000], height=200)
        else:
            st.error(f"❌ Could not read: {status_msg}")
            st.warning("Try: 1. Clear photo, 2. Crop to text only, 3. Check packages.txt added")
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

if atc_file and bid_file and master_file and df_master is not None:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown(f"### ✅ Fresh List — ATC ({atc_type})")

    if len(atc_products)==0:
        atc_products = list(df_master.iloc[:,0].astype(str).unique())[:20]
        st.warning(f"ATC 0 products — fallback to master first 20")

    df_master.columns = [str(c).strip().lower() for c in df_master.columns]
    prod_col = next((c for c in df_master.columns if 'product' in c or 'component' in c), df_master.columns[0])
    model_col = next((c for c in df_master.columns if 'model' in c), df_master.columns[1] if len(df_master.columns)>1 else prod_col)
    price_col = next((c for c in df_master.columns if 'price' in c or 'rate' in c), df_master.columns[2] if len(df_master.columns)>2 else prod_col)
    specs_col = next((c for c in df_master.columns if 'spec' in c), None)

    fresh_rows=[]
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
            fresh_rows.append({"Product": comp, "ATC Spec": atc_spec_map.get(comp, ""), "Compatible Model": "Not in Master", "Price": 0, "Compatibility": "❌ Missing", "Reason": "Add to master"})
            continue
        found=False
        for _, row in df_filtered.iterrows():
            try:
                model=str(row[model_col]); specs=str(row[specs_col]) if specs_col and specs_col in row else ""; price=row[price_col]
                atc_spec=atc_spec_map.get(comp, ""); ok,reason=is_compatible(atc_spec,model,specs)
                if ok:
                    fresh_rows.append({"Product": comp, "ATC Spec": atc_spec, "Compatible Model": model, "Price": price, "Compatibility": "✅ Compatible", "Reason": reason})
                    found=True; break
            except: continue
        if not found:
            try:
                row=df_filtered.iloc[0]; model=str(row[model_col]); specs=str(row[specs_col]) if specs_col and specs_col in df_filtered.columns else ""; price=row[price_col]
                atc_spec=atc_spec_map.get(comp, ""); ok,reason=is_compatible(atc_spec,model,specs)
                fresh_rows.append({"Product": comp, "ATC Spec": atc_spec, "Compatible Model": model, "Price": price, "Compatibility": "❌ Not Compatible", "Reason": reason})
            except: pass

    df_fresh = pd.DataFrame(fresh_rows) if fresh_rows else pd.DataFrame(columns=["Product","ATC Spec","Compatible Model","Price","Compatibility","Reason"])
    df_comp = df_fresh[df_fresh["Compatibility"]=="✅ Compatible"] if "Compatibility" in df_fresh.columns else pd.DataFrame()

    if not df_comp.empty:
        st.dataframe(df_comp, use_container_width=True)
        total = pd.to_numeric(df_comp["Price"], errors='coerce').fillna(0).sum()
        qty=bid_meta.get('qty',65); margin=st.number_input("Margin ₹", value=4000, step=500)
        gst=int((total+margin)*0.18); grand=total+margin+gst
        st.success(f"Grand/PC: ₹{grand:,.0f} | Total {qty} Units: ₹{grand*qty:,.0f}")
        st.download_button("📥 Download Compatible List", df_comp.to_csv(index=False).encode(), f"Compatible_{bid_meta.get('bid_no','')}.csv", use_container_width=True, type="primary")
    else:
        st.warning("No compatible found")
        st.dataframe(df_fresh, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)