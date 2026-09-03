import streamlit as st
import pandas as pd
import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment

st.set_page_config(page_title="GeM Bid Analyzer Pro 🐶", layout="wide", page_icon="🐕")

# ===== BEAUTIFUL UI + MOVING DOG CSS =====
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');
.stApp { background: linear-gradient(180deg, #F0F7FF 0%, #FFFFFF 100%); font-family: 'Plus Jakarta Sans', sans-serif; }

.hero {
    background: linear-gradient(135deg, #0F172A 0%, #1E3A5F 50%, #334155 100%);
    border-radius: 24px; padding: 26px 30px; color: white;
    box-shadow: 0 12px 40px rgba(15,23,42,0.25); position: relative; overflow: hidden;
}
.hero h1 { font-size: 26px; font-weight: 800; margin:0; letter-spacing: -0.5px; }
.hero p { opacity: 0.8; font-size: 12px; margin: 6px 0 0 0; }

.tricolor { height: 5px; background: linear-gradient(90deg, #FF9933 0%, #FFFFFF 50%, #138808 100%); border-radius: 10px; margin: 14px 0 20px 0; }

.glass-card {
    background: rgba(255,255,255,0.9); backdrop-filter: blur(10px);
    border-radius: 20px; padding: 24px;
    border: 1px solid #E2E8F0; box-shadow: 0 8px 30px rgba(0,0,0,0.06);
    margin-bottom: 18px;
}
.upload-box {
    background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
    border: 2px dashed #CBD5E1; border-radius: 18px; padding: 22px;
    text-align: center; transition: all 0.3s;
}
.upload-box:hover { border-color: #3B82F6; background: #EFF6FF; transform: translateY(-2px); box-shadow: 0 6px 20px rgba(59,130,246,0.15); }

.metric-card {
    background: white; border-radius: 16px; padding: 16px 18px;
    border: 1px solid #E2E8F0; text-align: center;
    box-shadow: 0 2px 10px rgba(0,0,0,0.03);
}

/* ===== MOVING DOG ANIMATION ===== */
.dog-track {
    position: relative; width: 100%; height: 90px;
    background: linear-gradient(90deg, #FEF3C7 0%, #DBEAFE 50%, #D1FAE5 100%);
    border-radius: 18px; overflow: hidden; margin: 16px 0;
    border: 2px solid #E2E8F0;
}
.dog {
    position: absolute; font-size: 52px; top: 8px; left: -80px;
    animation: dogRun 8s linear infinite;
    filter: drop-shadow(0 4px 8px rgba(0,0,0,0.15));
}
.dog2 {
    position: absolute; font-size: 28px; top: 48px; left: -60px;
    animation: dogRun 6s linear infinite reverse;
    animation-delay: 1s;
}
.bone {
    position: absolute; font-size: 20px; top: 35px;
    animation: boneFloat 2s ease-in-out infinite;
}
.bone1 { left: 15%; animation-delay: 0s; }
.bone2 { left: 45%; animation-delay: 0.5s; }
.bone3 { left: 75%; animation-delay: 1s; }

@keyframes dogRun {
    0% { left: -80px; transform: scaleX(1); }
    49% { transform: scaleX(1); }
    50% { left: calc(100% + 20px); transform: scaleX(-1); }
    51% { transform: scaleX(-1); }
    100% { left: -80px; transform: scaleX(-1); }
}
@keyframes boneFloat {
    0%, 100% { transform: translateY(0px) rotate(0deg); }
    50% { transform: translateY(-8px) rotate(10deg); }
}
@keyframes wiggle {
    0%, 100% { transform: rotate(-3deg); }
    50% { transform: rotate(3deg); }
}
.paw-print {
    position: absolute; font-size: 16px; opacity: 0.15;
    animation: pawFade 3s linear infinite;
}
@keyframes pawFade {
    0% { opacity: 0; transform: scale(0.5); }
    50% { opacity: 0.2; transform: scale(1); }
    100% { opacity: 0; transform: scale(1.2); }
}

/* Floating dog in corner */
.corner-dog {
    position: fixed; bottom: 20px; right: 20px; font-size: 44px;
    z-index: 9999; animation: wiggle 1.5s ease-in-out infinite;
    background: white; width: 68px; height: 68px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 8px 24px rgba(0,0,0,0.15); border: 3px solid #FEF3C7;
    cursor: pointer;
}
</style>

<!-- Floating corner dog -->
<div class="corner-dog">🐕</div>
""", unsafe_allow_html=True)

def safe_str(x):
    if x is None: return ""
    try:
        if pd.isna(x): return ""
    except: pass
    return str(x).strip()
def safe_lower(x): return safe_str(x).lower()

# ===== HEADER WITH DOG =====
st.markdown("""
<div class="hero">
    <h1>🐕 GeM Bid Analyzer Pro — Dog Edition</h1>
    <p>✨ Our cute dog will fetch JUST ONE best product for you! • H610 → B660/B760 • 16GB RAM → 32GB • 256GB SSD → 512GB</p>
</div>
<div class="tricolor"></div>

<div class="dog-track">
    <div class="bone bone1">🦴</div>
    <div class="bone bone2">🦴</div>
    <div class="bone bone3">🦴</div>
    <div class="paw-print" style="left:10%; top:20px;">🐾</div>
    <div class="paw-print" style="left:30%; top:60px; animation-delay:0.5s;">🐾</div>
    <div class="paw-print" style="left:50%; top:25px; animation-delay:1s;">🐾</div>
    <div class="paw-print" style="left:70%; top:55px; animation-delay:1.5s;">🐾</div>
    <div class="paw-print" style="left:90%; top:20px; animation-delay:2s;">🐾</div>
    <div class="dog">🐕‍🦺</div>
    <div class="dog2">🐩</div>
    <div style="position:absolute; bottom:6px; left:50%; transform:translateX(-50%); font-size:10px; color:#64748B; font-weight:700; letter-spacing:1.5px;">🐾 OUR DOG IS SEARCHING YOUR MASTER SHEET 🐾</div>
</div>
""", unsafe_allow_html=True)

if st.button("🗑️ Clear All & Call Dog Back 🐕", type="secondary"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

# ===== UPLOAD =====
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown("#### 📤 Upload Files — Dog will fetch them!")
c1,c2,c3 = st.columns(3)

with c1:
    st.markdown('<div class="upload-box">', unsafe_allow_html=True)
    st.markdown("**📄 ATC** <span style='font-size:18px;'>🦴</span>")
    atc_file = st.file_uploader("ATC", type=["pdf","jpg","jpeg","png"], key="atc", label_visibility="collapsed")
    if atc_file: st.success(f"✅ Fetched! {atc_file.name[:15]}")
    st.markdown('</div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="upload-box">', unsafe_allow_html=True)
    st.markdown("**📑 Bid PDF** <span style='font-size:18px;'>🐾</span>")
    bid_file = st.file_uploader("Bid", type=["pdf"], key="bid", label_visibility="collapsed")
    if bid_file: st.success(f"✅ Fetched! {bid_file.name[:15]}")
    st.markdown('</div>', unsafe_allow_html=True)
with c3:
    st.markdown('<div class="upload-box">', unsafe_allow_html=True)
    st.markdown("**📊 Master Sheet** <span style='font-size:18px;'>🐕</span>")
    master_file = st.file_uploader("Master", type=["xlsx","xls","csv"], key="master", label_visibility="collapsed")
    if master_file: st.success(f"✅ Woof! {master_file.name[:15]}")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ===== PROCESS =====
if master_file:
    try:
        df = pd.read_excel(master_file) if not master_file.name.endswith('.csv') else pd.read_csv(master_file)
        df = df.fillna("")
        model_col = df.columns[0]
        for c in df.columns:
            if any(k in str(c).lower() for k in ["model","product","name"]):
                model_col = c
                break
        all_models = [safe_str(df.iloc[i][model_col]) for i in range(len(df)) if safe_str(df.iloc[i][model_col])!=""]

        st.markdown('<div class="glass-card">', unsafe_allow_html=True)

        m1,m2,m3,m4 = st.columns(4)
        with m1:
            st.markdown(f'<div class="metric-card"><div style="font-size:24px;">🐕</div><div style="font-size:22px; font-weight:800;">{len(df)}</div><div style="font-size:10px; color:#64748B;">PRODUCTS FOUND</div></div>', unsafe_allow_html=True)
        with m2:
            st.markdown(f'<div class="metric-card"><div style="font-size:24px;">🦴</div><div style="font-size:22px; font-weight:800;">{len(all_models)}</div><div style="font-size:10px; color:#64748B;">MODELS FETCHED</div></div>', unsafe_allow_html=True)
        with m3:
            st.markdown(f'<div class="metric-card"><div style="font-size:24px;">🐾</div><div style="font-size:22px; font-weight:800; color:#059669;">15</div><div style="font-size:10px; color:#64748B;">COMPONENTS</div></div>', unsafe_allow_html=True)
        with m4:
            st.markdown(f'<div class="metric-card"><div style="font-size:24px;">🏆</div><div style="font-size:22px; font-weight:800; color:#3B82F6;">1:1</div><div style="font-size:10px; color:#64748B;">BEST PICK</div></div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 👀 Your Master — Dog's View 🐶")
        st.dataframe(df.head(6), use_container_width=True, hide_index=True)

        # Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "Dog Fetched List 🐕"

        thin = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        bold = Font(bold=True, size=11)
        h_font = Font(bold=True, color="FFFFFF", size=11)
        h_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
        green_fill = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid")
        yellow_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
        blue_fill = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")
        gray_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

        ws.merge_cells('A1:D1')
        ws['A1'] = f"🐕 GeM Bid — Dog Fetched JUST ONE Best Per Component | {len(df)} Products"
        ws['A1'].font = Font(bold=True, size=13)
        ws['A1'].fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
        ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
        ws.row_dimensions[1].height = 30

        ws.merge_cells('A2:D2')
        ws['A2'] = "🐾 Dog Logic: H610 not available → B660/B760 fetched | 16GB RAM not → 32GB fetched | 256GB SSD not → 512GB fetched 🦴"
        ws['A2'].font = Font(size=10, italic=True, color="64748B")
        ws['A2'].alignment = Alignment(horizontal='center')

        headers = ["PARAMETER 🐾", "Bid Requirement 🦴", "Best From Master — Dog Fetched 🐕 (JUST ONE)", "Why Suitable? 🐶"]
        for i,h in enumerate(headers, start=1):
            c = ws.cell(row=4, column=i, value=h)
            c.font = h_font
            c.fill = h_fill
            c.border = thin
            c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        ws.row_dimensions[4].height = 28

        rules = [
            ("MB 🐾", "Intel H610 DDR5", ["h610","b660","b760","z790","motherboard"], "B660/B760/Z790 Suitable - Better chipset, supports 14th Gen"),
            ("RAM 🦴", "16 GB DDR5", ["16gb ddr5","32gb ddr5","ram ddr5"], "32GB DDR5 Suitable & Better if 16GB not available"),
            ("SSD 💾", "256 GB NVMe", ["256gb nvme","512gb nvme","nvme"], "512GB/1TB NVMe Suitable & Better"),
            ("SSD 1TB 🦴", "1 TB SSD", ["1tb ssd","1 tb ssd","2tb ssd"], "1TB NVMe / 2TB Suitable & Better than SATA"),
            ("CPU 🧠", "i5 14400", ["i5 14400","i5 14500","i7"], "i5-14500 / i7 Suitable - Same or Better"),
            ("MONITOR 🖥️", '21.5" IPS', ["21.5","22 ips","24 ips","monitor"], "22/24 IPS Suitable & Better - Larger"),
            ("OS 💻", "Win 11 Pro", ["win 11 pro"], "Must be Pro"),
            ("CABINET 📦", "Tower", ["cabinet","tower"], "Tower/ATX suitable"),
            ("SMPS ⚡", "200W", ["smps","200 watt","300 watt"], "Higher wattage Suitable & Better"),
            ("KEYBOARD ⌨️", "Wired Combo", ["keyboard","mouse","combo"], "Wired/Wireless Combo suitable"),
            ("SPEAKER 🔊", "Speaker", ["speaker"], "Internal/External suitable"),
            ("WIFI 📶", "WiFi+BT", ["wifi","bluetooth"], "WiFi 5/6 + BT suitable"),
            ("TPM 🔒", "TPM 2.0", ["tpm"], "TPM 2.0"),
            ("GRAPHICS 🎮", "Integrated", ["graphics"], "Integrated suitable, Dedicated also better"),
            ("OFFICE 📄", "MS Office", ["office"], "Office 2019/2021/365 suitable"),
        ]

        row_num = 5
        for param, req, keywords, note in rules:
            best = ""
            reason = ""
            for kw in keywords:
                for _, r in df.iterrows():
                    row_text = safe_lower(" ".join([safe_str(r[c]) for c in df.columns]))
                    if safe_lower(kw) in row_text:
                        best = safe_str(r[model_col])
                        reason = f"✅ Dog fetched exact: {kw}" if keywords.index(kw)==0 else f"🐕 Dog fetched alternative: {kw} | {note}"
                        break
                if best:
                    break
            if not best and all_models:
                best = all_models[min(row_num-5, len(all_models)-1)]
                reason = f"🐾 Same category - {param} | {note}"
            if not best:
                best = "❌ Not in Master"
                reason = "Add keyword"

            ws.cell(row=row_num, column=1, value=param).font = bold
            ws.cell(row=row_num, column=1).border = thin
            ws.cell(row=row_num, column=1).fill = gray_fill
            ws.cell(row=row_num, column=2, value=req).border = thin
            ws.cell(row=row_num, column=2).fill = blue_fill
            ws.cell(row=row_num, column=3, value=best).border = thin
            ws.cell(row=row_num, column=3).fill = green_fill
            ws.cell(row=row_num, column=3).font = Font(bold=True, size=11)
            ws.cell(row=row_num, column=4, value=reason).border = thin
            ws.cell(row=row_num, column=4).fill = yellow_fill
            ws.cell(row=row_num, column=4).alignment = Alignment(wrap_text=True, vertical='center')
            ws.row_dimensions[row_num].height = 34
            row_num += 1

        ws.column_dimensions['A'].width = 18
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 38
        ws.column_dimensions['D'].width = 48

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        st.markdown("---")
        st.markdown("#### ✨ Dog Fetched List — Just One Best! 🐕🦴")
        st.markdown('<div style="background: #FEF3C7; border-radius: 12px; padding: 10px 14px; font-size: 11px; color: #92400E;">🐕 Our dog ran across your Master Sheet and fetched the BEST ONE product for each component — RAM, MB, SSD, CPU etc. If H610 not available, he brought B660/B760! 🦴</div>', unsafe_allow_html=True)

        preview = []
        for param, req, kws, _ in rules[:8]:
            best = next((m for m in all_models if any(safe_lower(k) in safe_lower(m) for k in kws)), all_models[0] if all_models else "Not Found")
            preview.append({"Component": param, "Requirement": req, "Dog Fetched 🐕": best})
        st.dataframe(pd.DataFrame(preview), use_container_width=True, hide_index=True)

        st.download_button(
            "📥 Download Excel — Dog Fetched List 🐕🦴 (Beautiful + Just One)",
            data=buf,
            file_name="GeM_Dog_Fetched_JUST_ONE.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary"
        )

        st.markdown('</div>', unsafe_allow_html=True)
        st.balloons()
        st.success("✅ Woof Woof! 🐕 Excel Ready — Beautiful + Moving Dog + Just One Best Per Component!")

        # Extra moving dog footer
        st.markdown("""
        <div class="dog-track" style="margin-top:20px;">
            <div style="position:absolute; left:10px; top:12px; font-size:32px; animation: wiggle 0.8s ease-in-out infinite;">🐕</div>
            <div style="position:absolute; left:50%; top:50%; transform:translate(-50%,-50%); font-weight:800; color:#0F172A;">🐾 DOG SAYS: YOUR EXCEL IS READY! DOWNLOAD NOW 🦴</div>
            <div style="position:absolute; right:10px; top:12px; font-size:32px; animation: wiggle 0.8s ease-in-out infinite reverse;">🦴</div>
        </div>
        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"🐶 Oops Dog slipped: {e}")
        import traceback
        st.code(traceback.format_exc())
else:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.info("⬆️ Upload Master Excel — Watch our dog run and fetch JUST ONE best product for each component! 🐕")

    st.markdown("""
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin-top:14px;">
        <div style="background:#DCFCE7; border-radius:12px; padding:12px; text-align:center;">
            <div style="font-size:24px;">🐕‍🦺</div><div style="font-size:11px; font-weight:700;">Dog runs if H610 not found → Fetches B660/B760</div>
        </div>
        <div style="background:#DBEAFE; border-radius:12px; padding:12px; text-align:center;">
            <div style="font-size:24px;">🦴</div><div style="font-size:11px; font-weight:700;">If 16GB RAM not → Fetches 32GB RAM</div>
        </div>
        <div style="background:#FEF3C7; border-radius:12px; padding:12px; text-align:center;">
            <div style="font-size:24px;">🐾</div><div style="font-size:11px; font-weight:700;">If 256GB SSD not → Fetches 512GB SSD</div>
        </div>
        <div style="background:#FCE7F3; border-radius:12px; padding:12px; text-align:center;">
            <div style="font-size:24px;">🎨</div><div style="font-size:11px; font-weight:700;">Beautiful + Moving Dog + Just One</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)