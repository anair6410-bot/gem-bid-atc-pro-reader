import streamlit as st
import pandas as pd
import re
from pypdf import PdfReader
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
import streamlit.components.v1 as components
import io, os

st.set_page_config(page_title="GeM 3-Row Exact - Built-in Master", layout="wide", page_icon="🤖")

# FIXED PATH - checks all possible locations
POSSIBLE_PATHS = [
    "Intel_Motherboard_All_Vendors_Technical_Compliance_v2.xlsx",
    "/mnt/data/Intel_Motherboard_All_Vendors_Technical_Compliance_v2.xlsx",
    "./Intel_Motherboard_All_Vendors_Technical_Compliance_v2.xlsx"
]
MASTER_FILE_PATH = None
for p in POSSIBLE_PATHS:
    if os.path.exists(p):
        MASTER_FILE_PATH = p
        break
if not MASTER_FILE_PATH:
    MASTER_FILE_PATH = POSSIBLE_PATHS[0]

st.markdown("""
<style>
.stApp { background: radial-gradient(ellipse at top, #0F172A 0%, #020617 100%); color: #E2E8F0; }
.hero { background: linear-gradient(135deg, #020617, #1E293B); border-radius: 20px; padding: 18px 24px; border: 1px solid #334155; }
.glass-card { background: rgba(15,23,42,0.9); border-radius: 18px; padding: 20px; border: 1px solid rgba(56,189,248,0.15); margin-bottom: 14px; }
.robot-track { position: relative; height: 90px; background: #020617; border-radius: 14px; overflow: hidden; border: 1px solid rgba(56,189,248,0.2); margin: 10px 0; }
.robot { position: absolute; font-size: 58px; top: 6px; left: -70px; animation: patrol 6s linear infinite; }
@keyframes patrol { 0%{left:-70px} 50%{left:calc(100% - 60px)} 100%{left:-70px} }
.corner-robot { position: fixed; bottom: 14px; right: 14px; width: 66px; height: 66px; background: #0F172A; border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 36px; z-index: 9999; border: 1px solid #38BDF8; }
</style>
<div class="corner-robot">🤖</div>
""", unsafe_allow_html=True)

def safe_str(x):
    try:
        if pd.isna(x): return ""
    except: pass
    return str(x).strip() if x else ""
def safe_lower(x): return safe_str(x).lower()

def read_pdf(file):
    file.seek(0)
    r = PdfReader(file)
    return "\n".join([(p.extract_text() or "") for p in r.pages])

def extract_components(text):
    comps = []
    keywords = ["processor","ram","ssd","hdd","motherboard","chipset","monitor","display","operating system","windows","cabinet","smps","keyboard","mouse","graphics","warranty","tpm","wifi","bluetooth","office","speaker"]
    lines = [l.strip() for l in text.split('\n') if 10 < len(l.strip()) < 220]
    for line in lines:
        low = line.lower()
        for kw in keywords:
            if kw in low:
                if not any(line[:45] in c[1][:45] for c in comps):
                    cat = kw.upper()
                    if "processor" in low: cat="PROCESSOR"
                    elif "ram" in low: cat="RAM"
                    elif "ssd" in low or "nvme" in low: cat="SSD"
                    elif "motherboard" in low or "chipset" in low: cat="MOTHERBOARD"
                    elif "monitor" in low: cat="MONITOR"
                    elif "windows" in low: cat="OS"
                    elif "cabinet" in low: cat="CABINET"
                    elif "smps" in low: cat="SMPS"
                    elif "keyboard" in low or "mouse" in low: cat="KBD/MOUSE"
                    elif "graphics" in low: cat="GRAPHICS"
                    elif "warranty" in low: cat="WARRANTY"
                    comps.append((cat, line[:180]))
                break
    return comps

@st.cache_data
def read_master_all_sheets():
    all_models = []
    try:
        xls = pd.ExcelFile(MASTER_FILE_PATH)
        for sheet in xls.sheet_names:
            try:
                for header_row in [3, 0]:
                    try:
                        df = pd.read_excel(MASTER_FILE_PATH, sheet_name=sheet, header=header_row)
                        df = df.fillna("")
                        model_col = None
                        for c in df.columns:
                            if 'model' in str(c).lower():
                                model_col = c
                                break
                        if model_col:
                            for _, row in df.iterrows():
                                model = safe_str(row.get(model_col, ""))
                                if model and len(model)>2 and model.lower() not in ["s.no.", "nan", "model"]:
                                    full_text = safe_lower(" ".join([safe_str(row[c]) for c in df.columns]))
                                    all_models.append({"model": model, "sheet": sheet, "full_text": full_text})
                            break
                    except:
                        continue
            except:
                pass
    except Exception as e:
        return []
    return all_models

def find_two_compatible(req_text, all_models):
    req = safe_lower(req_text)
    found = []
    for m in all_models:
        ft = m["full_text"]
        model = m["model"]
        match=False
        note=""
        if "h610" in req:
            if "h610" in ft or "b660" in ft or "b760" in ft:
                match=True
                note="H610 asked → B660/B760 from Master — Suitable & Better" if "b660" in ft or "b760" in ft else "Exact H610 match"
        elif "ddr5" in req:
            if "ddr5" in ft:
                match=True; note="DDR5 model from Master"
        else:
            score = sum(1 for w in req.split() if len(w)>3 and w in ft)
            if score>=1:
                match=True; note=f"Compatible — {score} keywords"
        if match and model not in [f[0] for f in found]:
            found.append((model, note, m["sheet"]))
            if len(found)>=2: break
    if len(found)<2:
        for m in all_models:
            if m["model"] not in [f[0] for f in found]:
                found.append((m["model"], "Available in Master", m["sheet"]))
                if len(found)>=2: break
    return found[:2]

st.markdown('<div class="hero"><h1>🤖 GeM 3-Row Exact — Built-in Master</h1><p>Upload only ATC + BID → Row1: ATC Exact | Row2: BID Exact | Row3: 2 Compatible Models</p></div>', unsafe_allow_html=True)

all_models = read_master_all_sheets()
if all_models:
    st.markdown(f'<div class="glass-card">✅ Built-in Master Loaded: <b>{len(all_models)} Models</b> — Path: {MASTER_FILE_PATH}</div>', unsafe_allow_html=True)
else:
    st.error(f"Master not found at {MASTER_FILE_PATH}. Please upload your Master file to /mnt/data/ or same folder as app.py")
    st.info("For Streamlit Cloud: Put Intel_Motherboard_All_Vendors_Technical_Compliance_v2.xlsx in same GitHub repo as app.py")
    st.stop()

c1,c2 = st.columns(2)
with c1: atc_file = st.file_uploader("📄 ATC File", type=["pdf"])
with c2: bid_file = st.file_uploader("📑 BID File", type=["pdf"])

if atc_file and bid_file:
    atc_text = read_pdf(atc_file)
    bid_text = read_pdf(bid_file)
    atc_comps = extract_components(atc_text)
    bid_comps = extract_components(bid_text)
    all_cats = {}
    for cat, txt in atc_comps: all_cats[cat] = {"atc": txt, "bid": ""}
    for cat, txt in bid_comps:
        if cat in all_cats: all_cats[cat]["bid"] = txt
        else: all_cats[cat] = {"atc": "", "bid": txt}
    if not all_cats: all_cats["MOTHERBOARD"] = {"atc": "H610 DDR4", "bid": "H610 DDR5 14th Gen"}

    preview = []
    for cat, vals in list(all_cats.items())[:8]:
        search = vals["bid"] if vals["bid"] else vals["atc"]
        compat = find_two_compatible(search, all_models)
        m1 = compat[0][0] if len(compat)>0 else "Not found"
        m2 = compat[1][0] if len(compat)>1 else "Not found"
        preview.append({"Category": cat, "ATC Row1": vals["atc"][:50], "BID Row2": vals["bid"][:50], "Model1 Row3": m1, "Model2 Row3": m2})
    st.dataframe(pd.DataFrame(preview), use_container_width=True, hide_index=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "3-Row Exact"
    thin = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    h_font = Font(bold=True, color="FFFFFF", size=11)
    h_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    ws.merge_cells('A1:F1')
    ws['A1']=f"GeM 3-ROW EXACT — {len(all_models)} Models"
    ws['A1'].font=Font(bold=True, size=12, color="38BDF8")
    ws['A1'].fill=PatternFill(start_color="020617", end_color="020617", fill_type="solid")
    ws['A1'].alignment=Alignment(horizontal='center', vertical='center')
    headers=["CATEGORY","ROW1: ATC Exact","ROW2: BID Exact","ROW3: Master Model 1","ROW3: Master Model 2","WHY Compatible?"]
    for i,h in enumerate(headers, start=1):
        c=ws.cell(row=3, column=i, value=h)
        c.font=h_font; c.fill=h_fill; c.border=thin; c.alignment=Alignment(horizontal='center', wrap_text=True, vertical='center')
    rnum=4
    for cat, vals in all_cats.items():
        search = vals["bid"] if vals["bid"] else vals["atc"]
        compat = find_two_compatible(search, all_models)
        m1 = compat[0][0] if len(compat)>0 else "❌ Not in Master"
        n1 = compat[0][1] if len(compat)>0 else "Add product"
        m2 = compat[1][0] if len(compat)>1 else "❌ Not in Master"
        n2 = compat[1][1] if len(compat)>1 else "Add product"
        note = f"{n1} | {n2}"
        ws.cell(row=rnum, column=1, value=cat).border=thin
        ws.cell(row=rnum, column=2, value=vals["atc"]).border=thin
        ws.cell(row=rnum, column=3, value=vals["bid"]).border=thin
        ws.cell(row=rnum, column=4, value=m1).border=thin
        ws.cell(row=rnum, column=5, value=m2).border=thin
        ws.cell(row=rnum, column=6, value=note).border=thin
        rnum+=1
    ws.column_dimensions['A'].width=16
    ws.column_dimensions['B'].width=30
    ws.column_dimensions['C'].width=30
    ws.column_dimensions['D'].width=26
    ws.column_dimensions['E'].width=26
    ws.column_dimensions['F'].width=40
    buf=io.BytesIO(); wb.save(buf); buf.seek(0)
    st.download_button("📥 DOWNLOAD 3 ROW EXCEL", data=buf, file_name="GeM_3Row_Exact.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, type="primary")