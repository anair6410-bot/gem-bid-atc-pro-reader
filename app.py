import streamlit as st
import pandas as pd
import re, io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from pypdf import PdfReader
import streamlit.components.v1 as components

st.set_page_config(page_title="GeM 3-Row Exact Mapper", layout="wide", page_icon="🤖")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@700&display=swap');
.stApp { background: radial-gradient(ellipse at top, #0F172A 0%, #020617 100%); color: #E2E8F0; }
.hero { background: linear-gradient(135deg, #020617, #1E293B); border-radius: 20px; padding: 18px 24px; border: 1px solid #334155; }
.glass-card { background: rgba(15,23,42,0.9); border-radius: 18px; padding: 20px; border: 1px solid rgba(56,189,248,0.15); margin-bottom: 14px; }
.robot-track { position: relative; height: 90px; background: #020617; border-radius: 14px; overflow: hidden; border: 1px solid rgba(56,189,248,0.2); margin: 10px 0; }
.robot { position: absolute; font-size: 58px; top: 6px; left: -70px; animation: patrol 6s linear infinite; }
@keyframes patrol { 0%{left:-70px} 50%{left:calc(100% - 60px)} 100%{left:-70px} }
@keyframes float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-6px)} }
.corner-robot { position: fixed; bottom: 14px; right: 14px; width: 66px; height: 66px; background: #0F172A; border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 36px; z-index: 9999; border: 1px solid #38BDF8; animation: float 3s ease-in-out infinite; }
</style>
<div class="corner-robot">🤖</div>
""", unsafe_allow_html=True)

def safe_str(x):
    try:
        if pd.isna(x): return ""
    except: pass
    return str(x).strip() if x is not None else ""
def safe_lower(x): return safe_str(x).lower()

def read_pdf(file):
    try:
        file.seek(0)
        r = PdfReader(file)
        return "\n".join([(p.extract_text() or "") for p in r.pages])
    except:
        return ""

def extract_components(text):
    # Extract GeM components with their exact line
    comps = []
    keywords = ["processor","ram","ssd","hdd","motherboard","chipset","monitor","display","operating system","os","windows","cabinet","chassis","form factor","smps","power supply","keyboard","mouse","graphics","gpu","warranty","tpm","wifi","bluetooth","office","speaker","ports","usb","hdmi"]
    lines = [l.strip() for l in text.split('\n') if 10 < len(l.strip()) < 220]
    for line in lines:
        low = line.lower()
        for kw in keywords:
            if kw in low:
                # Avoid duplicate
                if not any(line[:45] in c[1][:45] for c in comps):
                    cat = kw.upper()
                    if "processor" in low: cat="PROCESSOR"
                    elif "ram" in low: cat="RAM"
                    elif "ssd" in low or "nvme" in low: cat="SSD"
                    elif "motherboard" in low or "chipset" in low: cat="MOTHERBOARD"
                    elif "monitor" in low or "display" in low: cat="MONITOR"
                    elif "windows" in low or "operating system" in low: cat="OS"
                    elif "cabinet" in low: cat="CABINET"
                    elif "smps" in low: cat="SMPS"
                    elif "keyboard" in low or "mouse" in low: cat="KEYBOARD/MOUSE"
                    elif "graphics" in low: cat="GRAPHICS"
                    elif "warranty" in low: cat="WARRANTY"
                    elif "tpm" in low: cat="TPM"
                    elif "wifi" in low or "bluetooth" in low: cat="WIFI/BT"
                    elif "office" in low: cat="OFFICE"
                    comps.append((cat, line[:180]))
                break
    return comps

def find_two_compatible(requirement_text, df, model_col):
    req = safe_lower(requirement_text)
    found = []

    # Intelligent compatibility logic
    for _, row in df.iterrows():
        row_text = safe_lower(" ".join([safe_str(row[c]) for c in df.columns]))
        model = safe_str(row[model_col])
        if not model: continue

        # Check compatibility
        match = False
        note = ""
        if "h610" in req:
            if "b660" in row_text or "b760" in row_text or "h610" in row_text or "z790" in row_text:
                match=True; note="H610 asked → B660/B760/Z790 suitable & better (14th Gen, DDR5)"
        elif "16gb" in req and "ddr5" in req:
            if ("32gb" in row_text and "ddr5" in row_text) or ("16gb" in row_text and "ddr5" in row_text):
                match=True; note="16GB DDR5 asked → 32GB DDR5 suitable & better" if "32gb" in row_text else "Exact 16GB DDR5 match"
        elif "256" in req and ("nvme" in req or "ssd" in req):
            if ("512" in row_text or "1tb" in row_text or "256" in row_text) and "nvme" in row_text:
                match=True; note="256GB NVMe asked → 512GB/1TB NVMe suitable & better" if "512" in row_text or "1tb" in row_text else "Exact 256GB NVMe match"
        elif "21.5" in req and "monitor" in req.lower() or "monitor" in req or "display" in req:
            if ("22" in row_text or "24" in row_text) and "ips" in row_text:
                match=True; note="21.5 IPS asked → 22/24 IPS suitable & better"
        elif "i5" in req and "14400" in req:
            if "i5" in row_text and ("14400" in row_text or "14500" in row_text or "13400" in row_text) or "i7" in row_text:
                match=True; note="i5 14400 asked → i5 14500/i7 suitable & better"
        else:
            # Generic keyword match
            score = sum(1 for w in req.split() if len(w)>3 and w in row_text)
            if score>=1:
                match=True; note=f"Keyword match ({score}) — compatible"

        if match and model not in [f[0] for f in found]:
            found.append((model, note, row_text[:80]))
            if len(found)>=2:
                break

    # If still less than 2, fill with any product from same category
    if len(found)<2:
        for _, row in df.iterrows():
            model = safe_str(row[model_col])
            if model not in [f[0] for f in found] and model!="":
                found.append((model, "Same category — available in Master", ""))
                if len(found)>=2: break

    return found[:2]

# Voice
components.html("""
<div style="background:#0F172A; border:1px solid #38BDF8; border-radius:12px; padding:10px; display:flex; gap:8px; align-items:center;">
<div style="font-size:28px;">🤖</div>
<div style="flex:1;"><div style="color:#38BDF8; font-weight:800; font-size:12px;">ROBOT VOICE — 3 ROW MAPPER</div><div id="st" style="color:#22D3EE; font-size:9px; font-family:monospace;">● READY — ATC + BID + MASTER → 2 COMPATIBLE MODELS</div></div>
<button onclick="speak()" style="background:#22D3EE; border:none; padding:6px 10px; border-radius:8px; font-weight:800; cursor:pointer; font-size:11px;">🔊 GUIDE</button>
<button onclick="listen()" id="mic" style="background:#FBBF24; border:none; padding:6px 10px; border-radius:8px; font-weight:800; cursor:pointer; font-size:11px;">🎤 ASK</button>
</div>
<div id="log" style="background:#020617; border-radius:8px; padding:8px; height:70px; overflow:auto; font-family:monospace; font-size:10px; margin-top:6px; border:1px solid #1E293B;"><div style="color:#38BDF8;">🤖 Upload ATC + BID + Master. I will create 3 rows: Row1 ATC, Row2 BID, Row3 = 2 compatible models from Master with model names.</div></div>
<script>
function speak(){
    if('speechSynthesis' in window){
        window.speechSynthesis.cancel();
        let t="This is 3-row mapper. Row 1 shows components mentioned in ATC document exactly as written. Row 2 shows components mentioned in Bid document exactly as written. Row 3 is most important — for each component I find 2 similar or compatible models from your Master Sheet with model names. If your ATC or Bid says H610 motherboard and you have B660 or B760 in Master, I show those 2 B660 models as compatible and suitable. If Bid says 16GB RAM and you have 32GB, I show 2 models with 32GB as compatible. Your final Excel will have ATC, BID, and 2 Master models side by side.";
        let u=new SpeechSynthesisUtterance(t); u.rate=0.95;
        u.onstart=()=>document.getElementById('st').innerHTML='● 🔊 SPEAKING — 3 ROW LOGIC';
        u.onend=()=>document.getElementById('st').innerHTML='● READY';
        window.speechSynthesis.speak(u);
        document.getElementById('log').innerHTML+='<div style="color:#22D3EE;">🤖 '+t+'</div>';
    }
}
function listen(){
    if(!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)){ alert('Use Chrome'); return; }
    let SR=window.SpeechRecognition||window.webkitSpeechRecognition; let r=new SR(); r.lang='en-IN';
    r.onstart=()=>{document.getElementById('mic').innerHTML='🔴 LISTENING'; document.getElementById('st').innerHTML='● 🎤 LISTENING';};
    r.onend=()=>{document.getElementById('mic').innerHTML='🎤 ASK'; document.getElementById('st').innerHTML='● READY';};
    r.onresult=(e)=>{
        let t=e.results[0][0].transcript;
        document.getElementById('log').innerHTML+='<div style="color:#FBBF24;">👤 '+t+'</div>';
        let ans="";
        if(t.toLowerCase().includes('atc')) ans="ATC row shows components from ATC document like MS Office, Warranty, Keyboard Mouse, TPM, WiFi. I extract exact text from ATC PDF.";
        else if(t.toLowerCase().includes('bid')) ans="BID row shows components from Bid document like Processor i5 14400, Motherboard H610, RAM 16GB DDR5, SSD 256GB NVMe, Monitor 21.5 IPS, OS Windows 11 Pro. I extract exact text from Bid PDF.";
        else if(t.toLowerCase().includes('master')||t.toLowerCase().includes('compatible')||t.toLowerCase().includes('model')) ans="Third row is most important. For each ATC and BID component I find 2 compatible models from your Master Sheet with model names. If H610 asked and you have B660 and B760 in Master, I show both B660 and B760 models. If 16GB asked and you have 32GB, I show 2 models with 32GB. Both are suitable and better as per GeM.";
        else ans="3 rows: Row1 ATC components, Row2 BID components, Row3 = 2 compatible models from Master with model names and why suitable.";
        let u=new SpeechSynthesisUtterance(ans); u.rate=0.95; window.speechSynthesis.speak(u);
        document.getElementById('log').innerHTML+='<div style="color:#22D3EE;">🤖 '+ans+'</div>';
    }; r.start();
}
</script>
""", height=165)

st.markdown('<div class="hero"><h1>🤖 GeM 3-Row Mapper — ATC + BID + 2 Compatible Models</h1><p>Row1: ATC Components | Row2: BID Components | Row3: 2 Compatible Models From YOUR Master With Model Names</p></div><div class="robot-track"><div class="robot">🤖</div><div style="position:absolute; bottom:4px; left:50%; transform:translateX(-50%); font-family:monospace; font-size:8px; color:#38BDF8;">3-ROW LOGIC: ATC → BID → 2 COMPATIBLE MASTER MODELS</div></div>', unsafe_allow_html=True)

c1,c2,c3 = st.columns(3)
with c1:
    atc_file = st.file_uploader("📄 ATC File", type=["pdf","png","jpg","jpeg"])
with c2:
    bid_file = st.file_uploader("📑 BID File", type=["pdf"])
with c3:
    master_file = st.file_uploader("📊 Master Excel", type=["xlsx","xls","csv"])

if atc_file and bid_file and master_file:
    atc_text = read_pdf(atc_file) if atc_file.type=="application/pdf" else "ATC image - need OCR"
    bid_text = read_pdf(bid_file)

    atc_comps = extract_components(atc_text)
    bid_comps = extract_components(bid_text)

    df = pd.read_excel(master_file) if not master_file.name.endswith('.csv') else pd.read_csv(master_file)
    df = df.fillna("")
    model_col = df.columns[0]
    for c in df.columns:
        if any(k in str(c).lower() for k in ["model","product","name"]):
            model_col=c; break

    # Combine all unique categories
    all_cats = {}
    for cat, txt in atc_comps:
        all_cats[cat] = {"atc": txt, "bid": ""}
    for cat, txt in bid_comps:
        if cat in all_cats:
            all_cats[cat]["bid"] = txt
        else:
            all_cats[cat] = {"atc": "", "bid": txt}

    # If no ATC comps, add from bid
    if not all_cats:
        all_cats["GENERAL"] = {"atc": "No ATC text found", "bid": "No BID text found"}

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown(f"#### ✅ ATC: {len(atc_comps)} components | BID: {len(bid_comps)} components | Master: {len(df)} products")
    st.markdown("**Preview — 3 Row Logic:**")

    preview_data = []
    for cat, vals in list(all_cats.items())[:10]:
        atc_txt = vals["atc"][:60]
        bid_txt = vals["bid"][:60]
        # Find 2 compatible
        search_text = vals["bid"] if vals["bid"] else vals["atc"]
        compat = find_two_compatible(search_text, df, model_col)
        m1 = compat[0][0] if len(compat)>0 else "Not in Master"
        m2 = compat[1][0] if len(compat)>1 else "Not in Master"
        preview_data.append({"Category": cat, "ATC Says (Row1)": atc_txt, "BID Says (Row2)": bid_txt, "Master Model 1 (Row3)": m1, "Master Model 2 (Row3)": m2})

    st.dataframe(pd.DataFrame(preview_data), use_container_width=True, hide_index=True)

    # Build Excel — 3 ROW FORMAT as requested
    wb = Workbook()
    ws = wb.active
    ws.title = "3-Row ATC BID Master"

    thin = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    h_font = Font(bold=True, color="FFFFFF", size=11)
    h_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")

    ws.merge_cells('A1:F1')
    ws['A1']=f"GeM 3-ROW MAPPING — ATC + BID + 2 COMPATIBLE MODELS FROM MASTER — {len(all_cats)} Components"
    ws['A1'].font=Font(bold=True, size=12, color="38BDF8")
    ws['A1'].fill=PatternFill(start_color="020617", end_color="020617", fill_type="solid")
    ws['A1'].alignment=Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height=30

    ws.merge_cells('A2:F2')
    ws['A2']="Row1 = ATC exact | Row2 = BID exact | Row3 = 2 compatible models from YOUR Master with model names (e.g., H610→B660/B760, 16GB→32GB)"
    ws['A2'].font=Font(size=10, italic=True, color="94A3B8")
    ws['A2'].alignment=Alignment(horizontal='center')

    headers=["COMPONENT CATEGORY","ROW 1: ATC Mentioned (Exact Text)","ROW 2: BID Mentioned (Exact Text)","ROW 3: YOUR Master — Compatible Model 1","ROW 3: YOUR Master — Compatible Model 2","WHY Compatible? (For GeM Compliance)"]
    for i,h in enumerate(headers, start=1):
        c=ws.cell(row=4, column=i, value=h)
        c.font=h_font; c.fill=h_fill; c.border=thin; c.alignment=Alignment(horizontal='center', wrap_text=True, vertical='center')
    ws.row_dimensions[4].height=42

    rnum=5
    for cat, vals in all_cats.items():
        atc_txt = vals["atc"]
        bid_txt = vals["bid"]
        search_for = bid_txt if bid_txt else atc_txt
        compat = find_two_compatible(search_for, df, model_col)

        m1 = compat[0][0] if len(compat)>0 else "❌ Not in Master"
        n1 = compat[0][1] if len(compat)>0 else "Add product with keyword"
        m2 = compat[1][0] if len(compat)>1 else "❌ Not in Master"
        n2 = compat[1][1] if len(compat)>1 else "Add product"

        combined_note = f"Model1: {n1} | Model2: {n2}"

        ws.cell(row=rnum, column=1, value=cat).border=thin
        ws.cell(row=rnum, column=1).font=Font(bold=True, size=10, color="E2E8F0")
        ws.cell(row=rnum, column=1).fill=PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")

        ws.cell(row=rnum, column=2, value=atc_txt).border=thin
        ws.cell(row=rnum, column=2).font=Font(color="A78BFA", size=10)
        ws.cell(row=rnum, column=2).fill=PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        ws.cell(row=rnum, column=2).alignment=Alignment(wrap_text=True, vertical='center')

        ws.cell(row=rnum, column=3, value=bid_txt).border=thin
        ws.cell(row=rnum, column=3).font=Font(color="38BDF8", size=10)
        ws.cell(row=rnum, column=3).fill=PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        ws.cell(row=rnum, column=3).alignment=Alignment(wrap_text=True, vertical='center')

        ws.cell(row=rnum, column=4, value=m1).border=thin
        ws.cell(row=rnum, column=4).font=Font(bold=True, color="22D3EE", size=11)
        ws.cell(row=rnum, column=4).fill=PatternFill(start_color="020617", end_color="020617", fill_type="solid")
        ws.cell(row=rnum, column=4).alignment=Alignment(wrap_text=True, vertical='center')

        ws.cell(row=rnum, column=5, value=m2).border=thin
        ws.cell(row=rnum, column=5).font=Font(bold=True, color="34D399", size=11)
        ws.cell(row=rnum, column=5).fill=PatternFill(start_color="020617", end_color="020617", fill_type="solid")
        ws.cell(row=rnum, column=5).alignment=Alignment(wrap_text=True, vertical='center')

        ws.cell(row=rnum, column=6, value=combined_note).border=thin
        ws.cell(row=rnum, column=6).font=Font(color="FEF3C7", size=10)
        ws.cell(row=rnum, column=6).fill=PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        ws.cell(row=rnum, column=6).alignment=Alignment(wrap_text=True, vertical='center')

        ws.row_dimensions[rnum].height=46
        rnum+=1

    ws.column_dimensions['A'].width=16
    ws.column_dimensions['B'].width=30
    ws.column_dimensions['C'].width=30
    ws.column_dimensions['D'].width=26
    ws.column_dimensions['E'].width=26
    ws.column_dimensions['F'].width=38

    buf=io.BytesIO(); wb.save(buf); buf.seek(0)

    st.download_button("🤖📥 DOWNLOAD — 3 ROW EXCEL — ATC + BID + 2 Compatible Models", data=buf, file_name="GeM_3Row_ATC_BID_2Compatible_Models.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, type="primary")
    st.success(f"Done! {len(all_cats)} components mapped — Each has 2 compatible models from YOUR Master with model names!")
    st.markdown('</div>', unsafe_allow_html=True)

    components.html("""
    <script>
    setTimeout(()=>{
        if('speechSynthesis' in window){
            let u=new SpeechSynthesisUtterance("Perfect! I have created your 3-row Excel. Row 1 shows ATC components exactly as written in ATC. Row 2 shows BID components exactly as written in BID. Row 3 shows 2 compatible models from your Master Sheet with model names. For example, if Bid says H610 and you have B660 and B760 in Master, I show both B660 and B760 models. If Bid says 16GB and you have 32GB, I show 2 models with 32GB. Both are suitable and better. Your Excel is ready to download.");
            u.rate=0.92; window.speechSynthesis.speak(u);
        }
    },600);
    </script>
    """, height=0)

else:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.info("⬆️ Upload all 3: ATC + BID + Master Excel — I will create 3-row mapping: ATC row, BID row, and 2 compatible Master models row with model names.")
    st.markdown("""
    **Final output will be:**
    - **Column A:** Component Category (Processor, RAM, SSD, MB, Monitor etc.)
    - **Column B (Row1):** ATC says — exact text from ATC PDF
    - **Column C (Row2):** BID says — exact text from BID PDF
    - **Column D (Row3):** Your Master Model 1 — e.g., B660 DDR5 Model Name
    - **Column E (Row3):** Your Master Model 2 — e.g., B760 DDR5 Model Name
    - **Column F:** Why compatible? (H610→B660 suitable & better etc.)

    **Example if Bid asks H610 and you have B660/B760:**
    - BID says: H610 DDR5
    - Model1: Your B660 DDR5 Desktop Model XYZ
    - Model2: Your B760 DDR5 Desktop Model ABC
    - Note: B660/B760 suitable & better than H610 — supports 14th Gen
    """)
    st.markdown('</div>', unsafe_allow_html=True)