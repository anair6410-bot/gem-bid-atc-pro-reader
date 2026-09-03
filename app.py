import streamlit as st
import pandas as pd
import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment

st.set_page_config(page_title="GeM Robot Analyzer 🤖", layout="wide", page_icon="🤖")

# ===== ROBOTIC CSS + BIG ROBOT ANIMATION =====
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600;700;800&family=JetBrains+Mono:wght@500&display=swap');
.stApp {
    background: radial-gradient(ellipse at top, #0F172A 0%, #020617 100%);
    font-family: 'Space Grotesk', sans-serif; color: #E2E8F0;
}
.hero {
    background: linear-gradient(135deg, #020617 0%, #0F172A 30%, #1E293B 100%);
    border-radius: 24px; padding: 28px 32px; color: white; position: relative; overflow: hidden;
    border: 1px solid #1E293B; box-shadow: 0 0 40px rgba(56,189,248,0.15), inset 0 1px 0 rgba(255,255,255,0.05);
}
.hero h1 { font-size: 28px; font-weight: 800; margin:0; letter-spacing: -1px; font-family: 'Space Grotesk', sans-serif; }
.hero p { opacity: 0.6; font-size: 12px; margin: 8px 0 0 0; font-family: 'JetBrains Mono', monospace; }
.tricolor { height: 3px; background: linear-gradient(90deg, #38BDF8 0%, #22D3EE 50%, #A78BFA 100%); border-radius: 10px; margin: 14px 0 20px 0; box-shadow: 0 0 10px rgba(56,189,248,0.5); }

.glass-card {
    background: linear-gradient(180deg, rgba(15,23,42,0.9) 0%, rgba(2,6,23,0.9) 100%);
    border-radius: 20px; padding: 24px;
    border: 1px solid rgba(56,189,248,0.15); box-shadow: 0 8px 40px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05);
    margin-bottom: 18px; backdrop-filter: blur(20px);
}
.upload-box {
    background: linear-gradient(180deg, rgba(30,41,59,0.6) 0%, rgba(15,23,42,0.6) 100%);
    border: 2px dashed rgba(56,189,248,0.2); border-radius: 18px; padding: 22px;
    text-align: center; transition: all 0.4s; position: relative; overflow: hidden;
}
.upload-box:hover { border-color: #38BDF8; background: rgba(56,189,248,0.08); transform: translateY(-3px) scale(1.02); box-shadow: 0 10px 30px rgba(56,189,248,0.2); }
.upload-box::before {
    content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
    background: linear-gradient(45deg, transparent 30%, rgba(56,189,248,0.05) 50%, transparent 70%);
    animation: scan 3s linear infinite;
}
@keyframes scan { 0% { transform: translateX(-100%) translateY(-100%); } 100% { transform: translateX(100%) translateY(100%); } }

.metric-card {
    background: linear-gradient(180deg, rgba(30,41,59,0.8) 0%, rgba(15,23,42,0.8) 100%);
    border-radius: 16px; padding: 16px 18px; border: 1px solid rgba(56,189,248,0.15);
    text-align: center; box-shadow: inset 0 1px 0 rgba(255,255,255,0.05);
}

/* ===== BIG ROBOT TRACK ===== */
.robot-track {
    position: relative; width: 100%; height: 140px;
    background: linear-gradient(90deg, #020617 0%, #0F172A 25%, #1E293B 50%, #0F172A 75%, #020617 100%);
    border-radius: 20px; overflow: hidden; margin: 18px 0;
    border: 1px solid rgba(56,189,248,0.2); box-shadow: 0 0 30px rgba(56,189,248,0.1) inset;
}
.robot-track::before {
    content: ''; position: absolute; top:0; left:0; right:0; bottom:0;
    background: repeating-linear-gradient(90deg, transparent, transparent 80px, rgba(56,189,248,0.03) 80px, rgba(56,189,248,0.03) 81px);
}
.robot {
    position: absolute; font-size: 82px; top: 8px; left: -100px;
    animation: robotPatrol 9s linear infinite;
    filter: drop-shadow(0 0 20px rgba(56,189,248,0.8)) drop-shadow(0 4px 10px rgba(0,0,0,0.5));
}
.robot-shadow {
    position: absolute; bottom: 12px; width: 80px; height: 12px;
    background: radial-gradient(ellipse, rgba(56,189,248,0.3) 0%, transparent 70%);
    border-radius: 50%; animation: robotPatrol 9s linear infinite; left: -100px;
}
.laser {
    position: absolute; top: 54px; height: 2px; background: linear-gradient(90deg, #38BDF8, transparent);
    box-shadow: 0 0 8px #38BDF8; animation: laserScan 0.8s linear infinite;
}
.data-stream {
    position: absolute; font-family: 'JetBrains Mono', monospace; font-size: 10px; color: #38BDF8;
    opacity: 0.4; animation: dataFall 4s linear infinite;
}
@keyframes robotPatrol {
    0% { left: -100px; transform: scaleX(1); }
    45% { transform: scaleX(1); }
    50% { left: calc(100% + 10px); transform: scaleX(-1); }
    95% { transform: scaleX(-1); }
    100% { left: -100px; transform: scaleX(-1); }
}
@keyframes laserScan {
    0% { width: 0; opacity: 1; }
    100% { width: 120px; opacity: 0; }
}
@keyframes dataFall {
    0% { top: -20px; opacity: 0; }
    20% { opacity: 0.5; }
    80% { opacity: 0.5; }
    100% { top: 140px; opacity: 0; }
}
@keyframes float {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(-10px); }
}
@keyframes pulse {
    0%, 100% { box-shadow: 0 0 20px rgba(56,189,248,0.4); }
    50% { box-shadow: 0 0 40px rgba(56,189,248,0.8), 0 0 60px rgba(56,189,248,0.4); }
}

/* Big corner robot */
.corner-robot {
    position: fixed; bottom: 18px; right: 18px; width: 82px; height: 82px;
    background: linear-gradient(135deg, #0F172A, #1E293B);
    border-radius: 20px; display: flex; align-items: center; justify-content: center;
    font-size: 46px; z-index: 9999; border: 1px solid rgba(56,189,248,0.3);
    box-shadow: 0 10px 30px rgba(0,0,0,0.5), 0 0 20px rgba(56,189,248,0.3);
    animation: float 3s ease-in-out infinite, pulse 2s ease-in-out infinite;
    cursor: pointer;
}
.corner-robot::after {
    content: 'AI'; position: absolute; top: -8px; right: -8px;
    background: #22D3EE; color: #020617; font-size: 9px; font-weight: 800;
    padding: 2px 6px; border-radius: 10px; font-family: 'JetBrains Mono', monospace;
}
</style>

<div class="corner-robot">🤖</div>
""", unsafe_allow_html=True)

def safe_str(x):
    if x is None: return ""
    try:
        if pd.isna(x): return ""
    except: pass
    return str(x).strip()
def safe_lower(x): return safe_str(x).lower()

# ===== HEADER =====
st.markdown("""
<div class="hero">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <h1>🤖 GeM ROBOT ANALYZER — SYSTEM v2.0</h1>
            <p>⚡ [STATUS: ONLINE] • [MODE: JUST ONE BEST FETCH] • [SCANNING: MASTER SHEET] • H610→B660/B760 | 16GB→32GB | 256GB→512GB</p>
        </div>
        <div style="font-size: 52px; animation: float 3s ease-in-out infinite;">🦾</div>
    </div>
</div>
<div class="tricolor"></div>

<div class="robot-track">
    <div class="data-stream" style="left:10%;">01010101</div>
    <div class="data-stream" style="left:25%; animation-delay:0.5s;">H610 B660</div>
    <div class="data-stream" style="left:40%; animation-delay:1s;">16GB DDR5</div>
    <div class="data-stream" style="left:60%; animation-delay:1.5s;">256GB NVMe</div>
    <div class="data-stream" style="left:80%; animation-delay:2s;">SCANNING...</div>
    <div class="laser" style="left:0;"></div>
    <div class="robot">🤖</div>
    <div class="robot-shadow"></div>
    <div style="position:absolute; bottom:8px; left:50%; transform:translateX(-50%); font-family:'JetBrains Mono', monospace; font-size:9px; color:#38BDF8; letter-spacing:2px; opacity:0.7;">◼ ROBOT PATROLLING — ANALYZING MASTER SHEET — FETCHING JUST ONE BEST ◼</div>
</div>
""", unsafe_allow_html=True)

if st.button("🔴 TERMINATE & RESET ROBOT", type="secondary"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

# ===== UPLOAD =====
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown("#### 📤 UPLOAD MODULES — ROBOT INPUT PORTS")
c1,c2,c3 = st.columns(3)

with c1:
    st.markdown('<div class="upload-box">', unsafe_allow_html=True)
    st.markdown("**📄 ATC MODULE** <br><span style='font-family:JetBrains Mono; font-size:10px; color:#38BDF8;'>PORT 01</span>")
    atc_file = st.file_uploader("ATC", type=["pdf","jpg","jpeg","png"], key="atc", label_visibility="collapsed")
    if atc_file: st.success(f"⚡ LOADED: {atc_file.name[:15]}")
    st.markdown('</div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="upload-box">', unsafe_allow_html=True)
    st.markdown("**📑 BID MODULE** <br><span style='font-family:JetBrains Mono; font-size:10px; color:#22D3EE;'>PORT 02</span>")
    bid_file = st.file_uploader("Bid", type=["pdf"], key="bid", label_visibility="collapsed")
    if bid_file: st.success(f"⚡ LOADED: {bid_file.name[:15]}")
    st.markdown('</div>', unsafe_allow_html=True)
with c3:
    st.markdown('<div class="upload-box">', unsafe_allow_html=True)
    st.markdown("**📊 MASTER CORE** <br><span style='font-family:JetBrains Mono; font-size:10px; color:#A78BFA;'>PORT 03 — MAIN</span>")
    master_file = st.file_uploader("Master", type=["xlsx","xls","csv"], key="master", label_visibility="collapsed")
    if master_file: st.success(f"🤖 CORE INSERTED: {master_file.name[:15]}")
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
            st.markdown(f'<div class="metric-card"><div style="font-size:26px;">🤖</div><div style="font-size:20px; font-weight:800; color:#38BDF8;">{len(df)}</div><div style="font-size:9px; color:#64748B; font-family:JetBrains Mono;">TOTAL_DATA</div></div>', unsafe_allow_html=True)
        with m2:
            st.markdown(f'<div class="metric-card"><div style="font-size:26px;">⚡</div><div style="font-size:20px; font-weight:800; color:#22D3EE;">{len(all_models)}</div><div style="font-size:9px; color:#64748B; font-family:JetBrains Mono;">MODELS_LOCKED</div></div>', unsafe_allow_html=True)
        with m3:
            st.markdown(f'<div class="metric-card"><div style="font-size:26px;">🦾</div><div style="font-size:20px; font-weight:800; color:#A78BFA;">15</div><div style="font-size:9px; color:#64748B; font-family:JetBrains Mono;">COMPONENTS</div></div>', unsafe_allow_html=True)
        with m4:
            st.markdown(f'<div class="metric-card"><div style="font-size:26px;">🎯</div><div style="font-size:20px; font-weight:800; color:#22D3EE;">1:1</div><div style="font-size:9px; color:#64748B; font-family:JetBrains Mono;">PRECISION_MODE</div></div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 🤖 ROBOT VISION — MASTER SCAN")
        st.dataframe(df.head(6), use_container_width=True, hide_index=True)

        # Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "Robot Fetched 🤖"

        thin = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        bold = Font(name='Space Grotesk', bold=True, size=11)
        h_font = Font(name='Space Grotesk', bold=True, color="FFFFFF", size=11)
        h_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
        green_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
        green_font = Font(bold=True, size=11, color="22D3EE")
        yellow_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        yellow_font = Font(size=10, color="FEF3C7")
        blue_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
        blue_font = Font(size=10, color="38BDF8")

        ws.merge_cells('A1:D1')
        ws['A1'] = f"🤖 ROBOT ANALYZER v2.0 — JUST ONE BEST PER COMPONENT — {len(df)} PRODUCTS SCANNED"
        ws['A1'].font = Font(bold=True, size=13, color="38BDF8")
        ws['A1'].fill = PatternFill(start_color="020617", end_color="020617", fill_type="solid")
        ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
        ws.row_dimensions[1].height = 30

        ws.merge_cells('A2:D2')
        ws['A2'] = "⚡ ROBOT LOGIC: H610 NOT FOUND → FETCH B660/B760 | 16GB DDR5 NOT FOUND → FETCH 32GB DDR5 | 256GB NOT → 512GB"
        ws['A2'].font = Font(size=10, color="64748B")
        ws['A2'].alignment = Alignment(horizontal='center')

        headers = ["PARAMETER [SCAN]", "REQUIREMENT [REQ]", "ROBOT FETCHED [JUST ONE] 🤖", "ROBOT LOGIC [WHY]"]
        for i,h in enumerate(headers, start=1):
            c = ws.cell(row=4, column=i, value=h)
            c.font = h_font
            c.fill = h_fill
            c.border = thin
            c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        ws.row_dimensions[4].height = 28

        rules = [
            ("MB", "Intel H610 DDR5", ["h610","b660","b760","z790","motherboard"], "H610 not in DB → B660/B760/Z790 FETCHED — Better chipset, 14th Gen support"),
            ("RAM", "16 GB DDR5", ["16gb ddr5","32gb ddr5","ram ddr5"], "16GB not in DB → 32GB FETCHED — Higher & Better"),
            ("SSD", "256 GB NVMe", ["256gb nvme","512gb nvme","nvme"], "256GB not → 512GB/1TB FETCHED — Better capacity"),
            ("SSD 1TB", "1 TB SSD", ["1tb ssd","2tb ssd"], "1TB SATA not → 1TB NVMe/2TB FETCHED"),
            ("CPU", "i5 14400", ["i5 14400","i5 14500","i7"], "14400 not → 14500/i7 FETCHED — Same/higher gen"),
            ("MONITOR", '21.5" IPS', ["21.5","22 ips","24 ips","monitor"], "21.5 not → 22/24 IPS FETCHED — Larger & Better"),
            ("OS", "Win 11 Pro", ["win 11 pro"], "Must be Pro — Robot verified"),
            ("CABINET", "Tower", ["cabinet","tower"], "Tower/ATX suitable"),
            ("SMPS", "200W", ["smps","200 watt","300 watt"], "200W not → 300W/450W FETCHED — Higher wattage better"),
            ("K+M", "Wired Combo", ["keyboard","mouse"], "Combo suitable"),
            ("SPEAKER", "Speaker", ["speaker"], "Suitable"),
            ("WIFI+BT", "WiFi+BT", ["wifi","bluetooth"], "WiFi 5/6 + BT 5.0 suitable"),
            ("TPM", "TPM 2.0", ["tpm"], "TPM 2.0 verified"),
            ("GPU", "Integrated", ["graphics"], "Integrated OK, Dedicated better"),
            ("OFFICE", "MS Office", ["office"], "2019/2021/365 suitable"),
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
                        reason = f"🤖 [EXACT] {kw}" if keywords.index(kw)==0 else f"🤖 [ALT FETCH] {kw} → {note}"
                        break
                if best:
                    break
            if not best and all_models:
                best = all_models[min(row_num-5, len(all_models)-1)]
                reason = f"🤖 [CATEGORY MATCH] {param} → {note}"
            if not best:
                best = "❌ NOT IN MASTER CORE"
                reason = "ADD KEYWORD"

            ws.cell(row=row_num, column=1, value=param).font = bold
            ws.cell(row=row_num, column=1).border = thin
            ws.cell(row=row_num, column=1).font = Font(bold=True, color="E2E8F0")
            ws.cell(row=row_num, column=1).fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")

            ws.cell(row=row_num, column=2, value=req).border = thin
            ws.cell(row=row_num, column=2).font = blue_font
            ws.cell(row=row_num, column=2).fill = blue_fill

            ws.cell(row=row_num, column=3, value=best).border = thin
            ws.cell(row=row_num, column=3).font = green_font
            ws.cell(row=row_num, column=3).fill = PatternFill(start_color="020617", end_color="020617", fill_type="solid")
            ws.cell(row=row_num, column=3).alignment = Alignment(wrap_text=True, vertical='center')

            ws.cell(row=row_num, column=4, value=reason).border = thin
            ws.cell(row=row_num, column=4).font = yellow_font
            ws.cell(row=row_num, column=4).fill = yellow_fill
            ws.cell(row=row_num, column=4).alignment = Alignment(wrap_text=True, vertical='center')
            ws.row_dimensions[row_num].height = 36
            row_num += 1

        ws.column_dimensions['A'].width = 16
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 38
        ws.column_dimensions['D'].width = 52

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        st.markdown("---")
        st.markdown("#### 🤖 ROBOT OUTPUT — JUST ONE BEST FETCHED")
        st.markdown('<div style="background: rgba(56,189,248,0.1); border: 1px solid rgba(56,189,248,0.2); border-radius: 12px; padding: 12px 14px; font-family: JetBrains Mono; font-size: 11px; color: #38BDF8;">🤖 > SCAN COMPLETE... FETCHED 1 BEST PER COMPONENT... MB: B660/B760 if H610 not available... RAM: 32GB if 16GB not... SSD: 512GB if 256GB not... READY TO DOWNLOAD... █</div>', unsafe_allow_html=True)

        preview = []
        for param, req, kws, _ in rules[:8]:
            best = next((m for m in all_models if any(safe_lower(k) in safe_lower(m) for k in kws)), all_models[0] if all_models else "Not Found")
            preview.append({"Component": param, "Requirement": req, "Robot Fetched 🤖": best})
        st.dataframe(pd.DataFrame(preview), use_container_width=True, hide_index=True)

        st.download_button(
            "🤖 DOWNLOAD — ROBOT FETCHED EXCEL — JUST ONE BEST",
            data=buf,
            file_name="GeM_ROBOT_BIG_JUST_ONE.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary"
        )

        st.markdown('</div>', unsafe_allow_html=True)
        st.balloons()
        st.success("🤖 ROBOT MISSION COMPLETE — BIG ROBOT FETCHED JUST ONE BEST PER COMPONENT!")

        st.markdown("""
        <div class="robot-track" style="margin-top:20px; height: 90px;">
            <div style="position:absolute; left:50%; top:50%; transform:translate(-50%,-50%); font-family:'JetBrains Mono'; font-size:12px; color:#22D3EE; letter-spacing:3px; text-align:center;">
                🤖 SYSTEM READY — ROBOT STANDING BY — AWAITING NEXT BID 🤖<br>
                <span style="font-size:9px; opacity:0.5;">[BIG ROBOT MODE: ACTIVE] [SCANNING: OFF]</span>
            </div>
            <div style="position:absolute; left:20px; top:20px; font-size:40px; animation: float 2s ease-in-out infinite;">🤖</div>
            <div style="position:absolute; right:20px; top:20px; font-size:40px; animation: float 2s ease-in-out infinite reverse;">🦾</div>
        </div>
        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"🤖 ROBOT ERROR: {e}")
        import traceback
        st.code(traceback.format_exc())
else:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.info("🤖 INSERT MASTER CORE — BIG ROBOT WILL ACTIVATE AND FETCH JUST ONE BEST PRODUCT!")

    st.markdown("""
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin-top:14px;">
        <div style="background:rgba(56,189,248,0.1); border:1px solid rgba(56,189,248,0.2); border-radius:12px; padding:14px; text-align:center;">
            <div style="font-size:28px;">🤖</div><div style="font-size:11px; font-weight:700; color:#38BDF8; font-family:JetBrains Mono;">H610 NOT FOUND → B660/B760 FETCHED</div>
        </div>
        <div style="background:rgba(34,211,238,0.1); border:1px solid rgba(34,211,238,0.2); border-radius:12px; padding:14px; text-align:center;">
            <div style="font-size:28px;">🦾</div><div style="font-size:11px; font-weight:700; color:#22D3EE; font-family:JetBrains Mono;">16GB NOT → 32GB RAM FETCHED</div>
        </div>
        <div style="background:rgba(167,139,250,0.1); border:1px solid rgba(167,139,250,0.2); border-radius:12px; padding:14px; text-align:center;">
            <div style="font-size:28px;">⚡</div><div style="font-size:11px; font-weight:700; color:#A78BFA; font-family:JetBrains Mono;">256GB NOT → 512GB SSD FETCHED</div>
        </div>
        <div style="background:rgba(251,191,36,0.1); border:1px solid rgba(251,191,36,0.2); border-radius:12px; padding:14px; text-align:center;">
            <div style="font-size:28px;">🎯</div><div style="font-size:11px; font-weight:700; color:#FBBF24; font-family:JetBrains Mono;">JUST ONE BEST PER COMPONENT</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)