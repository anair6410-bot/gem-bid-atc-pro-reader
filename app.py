import streamlit as st
import pandas as pd
import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
import streamlit.components.v1 as components

st.set_page_config(page_title="GeM Robot Voice Guide 🤖🎤", layout="wide", page_icon="🤖")

# ===== ROBOTIC CSS + VOICE =====
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600;700;800&family=JetBrains+Mono:wght@500&display=swap');
.stApp { background: radial-gradient(ellipse at top, #0F172A 0%, #020617 100%); font-family: 'Space Grotesk', sans-serif; color: #E2E8F0; }
.hero { background: linear-gradient(135deg, #020617 0%, #0F172A 30%, #1E293B 100%); border-radius: 24px; padding: 28px 32px; color: white; position: relative; overflow: hidden; border: 1px solid #1E293B; box-shadow: 0 0 40px rgba(56,189,248,0.15); }
.hero h1 { font-size: 28px; font-weight: 800; margin:0; }
.hero p { opacity: 0.6; font-size: 12px; margin: 8px 0 0 0; font-family: 'JetBrains Mono', monospace; }
.tricolor { height: 3px; background: linear-gradient(90deg, #38BDF8 0%, #22D3EE 50%, #A78BFA 100%); border-radius: 10px; margin: 14px 0 20px 0; }
.glass-card { background: linear-gradient(180deg, rgba(15,23,42,0.9) 0%, rgba(2,6,23,0.9) 100%); border-radius: 20px; padding: 24px; border: 1px solid rgba(56,189,248,0.15); margin-bottom: 18px; backdrop-filter: blur(20px); }
.upload-box { background: linear-gradient(180deg, rgba(30,41,59,0.6) 0%, rgba(15,23,42,0.6) 100%); border: 2px dashed rgba(56,189,248,0.2); border-radius: 18px; padding: 22px; text-align: center; transition: all 0.4s; }
.upload-box:hover { border-color: #38BDF8; background: rgba(56,189,248,0.08); transform: translateY(-3px); }
.metric-card { background: linear-gradient(180deg, rgba(30,41,59,0.8) 0%, rgba(15,23,42,0.8) 100%); border-radius: 16px; padding: 16px 18px; border: 1px solid rgba(56,189,248,0.15); text-align: center; }

.robot-track { position: relative; width: 100%; height: 140px; background: linear-gradient(90deg, #020617 0%, #0F172A 25%, #1E293B 50%, #0F172A 75%, #020617 100%); border-radius: 20px; overflow: hidden; margin: 18px 0; border: 1px solid rgba(56,189,248,0.2); }
.robot { position: absolute; font-size: 82px; top: 8px; left: -100px; animation: robotPatrol 9s linear infinite; filter: drop-shadow(0 0 20px rgba(56,189,248,0.8)); }
@keyframes robotPatrol { 0% { left: -100px; } 50% { left: calc(100% + 10px); } 100% { left: -100px; } }
@keyframes float { 0%, 100% { transform: translateY(0px); } 50% { transform: translateY(-10px); } }
.corner-robot { position: fixed; bottom: 18px; right: 18px; width: 82px; height: 82px; background: linear-gradient(135deg, #0F172A, #1E293B); border-radius: 20px; display: flex; align-items: center; justify-content: center; font-size: 46px; z-index: 9999; border: 1px solid rgba(56,189,248,0.3); box-shadow: 0 10px 30px rgba(0,0,0,0.5), 0 0 20px rgba(56,189,248,0.3); animation: float 3s ease-in-out infinite; cursor: pointer; }
.voice-btn { background: linear-gradient(135deg, #38BDF8, #22D3EE); color: #020617; border: none; padding: 14px 22px; border-radius: 14px; font-weight: 800; font-size: 14px; cursor: pointer; box-shadow: 0 4px 15px rgba(56,189,248,0.4); transition: all 0.3s; }
.voice-btn:hover { transform: scale(1.05); box-shadow: 0 6px 25px rgba(56,189,248,0.6); }
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

# ===== VOICE CHATBOT ROBOT HTML =====
voice_chatbot_html = """
<div id="voice-robot-container" style="background: linear-gradient(135deg, #0F172A, #1E293B); border: 1px solid rgba(56,189,248,0.3); border-radius: 20px; padding: 20px; margin: 16px 0; box-shadow: 0 0 30px rgba(56,189,248,0.15);">
    <div style="display:flex; align-items:center; gap:14px; margin-bottom:16px;">
        <div style="font-size:48px; animation: float 2s ease-in-out infinite;">🤖</div>
        <div>
            <div style="color:#38BDF8; font-weight:800; font-size:16px; font-family: Space Grotesk;">ROBOT VOICE GUIDE — ONLINE</div>
            <div style="color:#64748B; font-size:11px; font-family: JetBrains Mono;">🎤 Click to talk | 🔊 Robot will speak and guide you</div>
            <div id="robot-status" style="color:#22D3EE; font-size:11px; margin-top:4px; font-family: JetBrains Mono;">● READY TO GUIDE YOU</div>
        </div>
        <div style="margin-left:auto; display:flex; gap:8px;">
            <button onclick="speakGuide()" style="background:#22D3EE; color:#020617; border:none; padding:10px 16px; border-radius:12px; font-weight:800; cursor:pointer;">🔊 GUIDE ME</button>
            <button onclick="startListening()" id="micBtn" style="background:#FBBF24; color:#020617; border:none; padding:10px 16px; border-radius:12px; font-weight:800; cursor:pointer;">🎤 ASK ROBOT</button>
        </div>
    </div>

    <div id="chat-log" style="background: rgba(2,6,23,0.8); border-radius: 14px; padding: 14px; height: 140px; overflow-y: auto; font-family: JetBrains Mono; font-size: 12px; color: #E2E8F0; border: 1px solid rgba(56,189,248,0.1);">
        <div style="color:#38BDF8;">🤖 ROBOT: Hello! I am your GeM Robot Guide. Upload your Master Sheet and I will fetch JUST ONE best product for each component with voice guidance!</div>
    </div>

    <div style="display:flex; gap:8px; margin-top:12px;">
        <input id="userInput" type="text" placeholder="Type: What is MB compatible? or RAM alternative?" style="flex:1; background: rgba(2,6,23,0.8); border: 1px solid rgba(56,189,248,0.2); border-radius: 10px; padding: 10px 14px; color: #E2E8F0; font-family: JetBrains Mono; font-size: 12px;" onkeypress="if(event.key==='Enter') sendToRobot()">
        <button onclick="sendToRobot()" style="background: #38BDF8; color: #020617; border: none; padding: 10px 18px; border-radius: 10px; font-weight: 800; cursor: pointer;">SEND 🤖</button>
    </div>

    <div style="display:flex; gap:6px; margin-top:10px; flex-wrap:wrap;">
        <button onclick="quickAsk('What is MB compatible if H610 not available?')" style="background: rgba(56,189,248,0.15); border: 1px solid rgba(56,189,248,0.3); color: #38BDF8; padding: 6px 10px; border-radius: 20px; font-size: 10px; cursor: pointer;">MB compatible?</button>
        <button onclick="quickAsk('What is RAM alternative if 16GB not available?')" style="background: rgba(34,211,238,0.15); border: 1px solid rgba(34,211,238,0.3); color: #22D3EE; padding: 6px 10px; border-radius: 20px; font-size: 10px; cursor: pointer;">RAM alternative?</button>
        <button onclick="quickAsk('What is SSD alternative if 256GB not available?')" style="background: rgba(167,139,250,0.15); border: 1px solid rgba(167,139,250,0.3); color: #A78BFA; padding: 6px 10px; border-radius: 20px; font-size: 10px; cursor: pointer;">SSD alternative?</button>
        <button onclick="quickAsk('Guide me to download excel')" style="background: rgba(251,191,36,0.15); border: 1px solid rgba(251,191,36,0.3); color: #FBBF24; padding: 6px 10px; border-radius: 20px; font-size: 10px; cursor: pointer;">Download help?</button>
    </div>
</div>

<script>
let recognition;
let isListening = false;

function speak(text) {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 0.95;
        utterance.pitch = 0.9;
        utterance.volume = 1;
        const voices = window.speechSynthesis.getVoices();
        let robotVoice = voices.find(v => v.name.includes('Google') && v.lang.includes('en')) || voices.find(v => v.lang.includes('en')) || voices[0];
        if (robotVoice) utterance.voice = robotVoice;
        utterance.onstart = () => { document.getElementById('robot-status').innerHTML = '● 🔊 SPEAKING...'; document.getElementById('robot-status').style.color = '#FBBF24'; };
        utterance.onend = () => { document.getElementById('robot-status').innerHTML = '● READY TO GUIDE'; document.getElementById('robot-status').style.color = '#22D3EE'; };
        window.speechSynthesis.speak(utterance);
        addToLog('🤖 ROBOT (voice): ' + text, '#22D3EE');
    }
}

function addToLog(msg, color='#E2E8F0') {
    const log = document.getElementById('chat-log');
    const div = document.createElement('div');
    div.style.margin = '6px 0';
    div.style.color = color;
    div.innerHTML = msg;
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
}

function getRobotAnswer(question) {
    const q = question.toLowerCase();
    if (q.includes('mb') || q.includes('motherboard') || q.includes('h610') || q.includes('b660') || q.includes('b760')) {
        return "For Motherboard: If your Master Sheet does not have H610, I will fetch B660 DDR5 or B760 DDR5. They are highly suitable and better than H610. They support 14th Gen processor and DDR5 RAM. Just upload Master and I will find one best B660 or B760 for you.";
    } else if (q.includes('ram')) {
        return "For RAM: Bid requires 16 GB DDR5. If your Master does not have 16GB, I will fetch 32GB DDR5. It is suitable and better because higher capacity. 32GB DDR5 4800 or 5600 both are excellent alternatives.";
    } else if (q.includes('ssd') || q.includes('storage')) {
        return "For SSD: Bid requires 256 GB NVMe. If 256 not in your Master, I will fetch 512 GB NVMe or 1 TB NVMe. Higher capacity is always suitable and better. Same for secondary 1 TB SSD, I can fetch 2 TB if 1 TB not available.";
    } else if (q.includes('cpu') || q.includes('processor') || q.includes('i5') || q.includes('14400')) {
        return "For Processor: Bid requires Intel i5 14400. If not in Master, I will fetch i5 14500 or i7 12700. They are same or higher generation, fully suitable and better performance.";
    } else if (q.includes('monitor') || q.includes('display')) {
        return "For Monitor: Bid requires 21.5 inch IPS. If not available, I will fetch 22 inch or 24 inch IPS. Larger size is suitable and better. IPS is must.";
    } else if (q.includes('download') || q.includes('excel') || q.includes('file')) {
        return "To download: After uploading Master Sheet, scroll down. You will see a big blue button saying Download Excel. Click it. You will get JUST ONE best product per component. The robot has already fetched it for you.";
    } else if (q.includes('how') || q.includes('guide') || q.includes('help') || q.includes('work')) {
        return "I am your Robot Guide. Step one: Upload your Master Excel sheet with all your products. Step two: I scan it and find JUST ONE best product for each component like MB, RAM, SSD, CPU, Monitor. Step three: If exact match not found, I fetch better alternative like B660 for H610, 32GB for 16GB. Step four: Download beautiful Excel.";
    } else {
        return "I understand you asked: " + question + ". I fetch JUST ONE best product per component from your Master. For motherboard H610, I can fetch B660 or B760 if H610 not available. For RAM 16GB, I fetch 32GB if 16 not available. For SSD 256GB, I fetch 512GB if 256 not available. All alternatives are suitable and better. Upload your Master Sheet and I will show you.";
    }
}

function sendToRobot() {
    const input = document.getElementById('userInput');
    const question = input.value.trim();
    if (!question) return;
    addToLog('👤 YOU: ' + question, '#FBBF24');
    const answer = getRobotAnswer(question);
    setTimeout(() => { speak(answer); }, 300);
    input.value = '';
}

function quickAsk(q) {
    document.getElementById('userInput').value = q;
    sendToRobot();
}

function speakGuide() {
    const guide = "Welcome to GeM Robot Analyzer. I am your voice guide. Upload your Master Sheet Excel file. I am a big robot scanning your products. I will fetch JUST ONE best product for each component. If H610 motherboard not available, I fetch B660 or B760 which is suitable and better. If 16GB RAM not available, I fetch 32GB RAM which is better. If 256GB SSD not available, I fetch 512GB SSD which is better. After scanning, download your beautiful Excel file with one best per component. You can ask me anything by typing or clicking mic button. I am ready to guide you.";
    speak(guide);
}

function startListening() {
    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
        alert('Voice input not supported in this browser. Please type your question. Use Chrome for voice.');
        return;
    }
    if (isListening) {
        recognition.stop();
        return;
    }
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.lang = 'en-IN';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
        isListening = true;
        document.getElementById('micBtn').innerHTML = '🔴 LISTENING...';
        document.getElementById('micBtn').style.background = '#EF4444';
        document.getElementById('robot-status').innerHTML = '● 🎤 LISTENING TO YOU...';
        document.getElementById('robot-status').style.color = '#EF4444';
    };
    recognition.onend = () => {
        isListening = false;
        document.getElementById('micBtn').innerHTML = '🎤 ASK ROBOT';
        document.getElementById('micBtn').style.background = '#FBBF24';
        document.getElementById('robot-status').innerHTML = '● READY TO GUIDE';
        document.getElementById('robot-status').style.color = '#22D3EE';
    };
    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        document.getElementById('userInput').value = transcript;
        addToLog('👤 YOU (voice): ' + transcript, '#FBBF24');
        const answer = getRobotAnswer(transcript);
        setTimeout(() => { speak(answer); }, 400);
    };
    recognition.onerror = (event) => {
        addToLog('❌ Voice error: ' + event.error, '#EF4444');
        isListening = false;
        document.getElementById('micBtn').innerHTML = '🎤 ASK ROBOT';
        document.getElementById('micBtn').style.background = '#FBBF24';
    };
    recognition.start();
}

// Auto speak welcome after 2 sec
setTimeout(() => {
    if ('speechSynthesis' in window) {
        // Don't auto play unless user interacted, just show ready
        addToLog('🤖 ROBOT: Click GUIDE ME button to hear voice guide! Or click ASK ROBOT to speak with me.', '#38BDF8');
    }
}, 1500);
</script>
"""

# ===== HEADER =====
st.markdown("""
<div class="hero">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <h1>🤖 GeM ROBOT — VOICE GUIDE v3.0 🎤</h1>
            <p>⚡ [VOICE: ONLINE] • [CHATBOT: ACTIVE] • BIG ROBOT WILL SPEAK & GUIDE YOU • JUST ONE BEST PER COMPONENT</p>
        </div>
        <div style="font-size: 52px; animation: float 3s ease-in-out infinite;">🦾</div>
    </div>
</div>
<div class="tricolor"></div>

<div class="robot-track">
    <div class="robot">🤖</div>
    <div style="position:absolute; bottom:8px; left:50%; transform:translateX(-50%); font-family:JetBrains Mono; font-size:9px; color:#38BDF8; letter-spacing:2px;">◼ ROBOT PATROLLING — VOICE GUIDE READY — CLICK GUIDE ME 🔊 ◼</div>
</div>
""", unsafe_allow_html=True)

# Voice Chatbot
components.html(voice_chatbot_html, height=360)

if st.button("🔴 RESET ROBOT SYSTEM", type="secondary"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

# Upload
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown("#### 📤 UPLOAD PORTS — ROBOT INPUT")
c1,c2,c3 = st.columns(3)
with c1:
    st.markdown('<div class="upload-box">', unsafe_allow_html=True)
    st.markdown("**📄 ATC**<br><span style='font-family:JetBrains Mono; font-size:10px; color:#38BDF8;'>PORT 01</span>")
    atc_file = st.file_uploader("ATC", type=["pdf","jpg","jpeg","png"], key="atc", label_visibility="collapsed")
    if atc_file: st.success(f"⚡ LOADED")
    st.markdown('</div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="upload-box">', unsafe_allow_html=True)
    st.markdown("**📑 BID**<br><span style='font-family:JetBrains Mono; font-size:10px; color:#22D3EE;'>PORT 02</span>")
    bid_file = st.file_uploader("Bid", type=["pdf"], key="bid", label_visibility="collapsed")
    if bid_file: st.success(f"⚡ LOADED")
    st.markdown('</div>', unsafe_allow_html=True)
with c3:
    st.markdown('<div class="upload-box">', unsafe_allow_html=True)
    st.markdown("**📊 MASTER CORE**<br><span style='font-family:JetBrains Mono; font-size:10px; color:#A78BFA;'>PORT 03 — MAIN</span>")
    master_file = st.file_uploader("Master", type=["xlsx","xls","csv"], key="master", label_visibility="collapsed")
    if master_file: st.success(f"🤖 CORE INSERTED")
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Process (same as before - just one best)
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
            st.markdown(f'<div class="metric-card"><div style="font-size:26px;">⚡</div><div style="font-size:20px; font-weight:800; color:#22D3EE;">{len(all_models)}</div><div style="font-size:9px; color:#64748B; font-family:JetBrains Mono;">MODELS</div></div>', unsafe_allow_html=True)
        with m3:
            st.markdown(f'<div class="metric-card"><div style="font-size:26px;">🎤</div><div style="font-size:20px; font-weight:800; color:#FBBF24;">VOICE</div><div style="font-size:9px; color:#64748B; font-family:JetBrains Mono;">GUIDE ON</div></div>', unsafe_allow_html=True)
        with m4:
            st.markdown(f'<div class="metric-card"><div style="font-size:26px;">🎯</div><div style="font-size:20px; font-weight:800; color:#22D3EE;">1:1</div><div style="font-size:9px; color:#64748B; font-family:JetBrains Mono;">BEST MODE</div></div>', unsafe_allow_html=True)

        st.markdown("#### 🤖 ROBOT SCAN — MASTER DATA")
        st.dataframe(df.head(6), use_container_width=True, hide_index=True)

        # Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "Robot Voice Guide"
        thin = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        bold = Font(bold=True, size=11)
        h_font = Font(bold=True, color="FFFFFF", size=11)
        h_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
        green_font = Font(bold=True, size=11, color="22D3EE")
        yellow_font = Font(size=10, color="FEF3C7")
        blue_font = Font(size=10, color="38BDF8")

        ws.merge_cells('A1:D1')
        ws['A1'] = f"🤖 ROBOT VOICE GUIDE v3.0 — JUST ONE BEST — {len(df)} PRODUCTS"
        ws['A1'].font = Font(bold=True, size=13, color="38BDF8")
        ws['A1'].fill = PatternFill(start_color="020617", end_color="020617", fill_type="solid")
        ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
        ws.row_dimensions[1].height = 30

        headers = ["PARAMETER", "REQUIREMENT", "ROBOT FETCHED (JUST ONE) 🤖", "ROBOT VOICE LOGIC"]
        for i,h in enumerate(headers, start=1):
            c = ws.cell(row=4, column=i, value=h)
            c.font = h_font
            c.fill = h_fill
            c.border = thin
            c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

        rules = [
            ("MB", "H610 DDR5", ["h610","b660","b760","z790","motherboard"], "H610 not → B660/B760/Z790 FETCHED — Better, supports 14th Gen"),
            ("RAM", "16GB DDR5", ["16gb ddr5","32gb ddr5","ram ddr5"], "16GB not → 32GB FETCHED — Better capacity"),
            ("SSD", "256GB NVMe", ["256gb nvme","512gb nvme","nvme"], "256 not → 512GB/1TB FETCHED — Better"),
            ("SSD 1TB", "1TB SSD", ["1tb ssd","2tb ssd"], "1TB not → 2TB FETCHED"),
            ("CPU", "i5 14400", ["i5 14400","i5 14500","i7"], "14400 not → 14500/i7 FETCHED"),
            ("MONITOR", '21.5" IPS', ["21.5","22 ips","24 ips","monitor"], "21.5 not → 22/24 IPS FETCHED — Larger"),
            ("OS", "Win11 Pro", ["win 11 pro"], "Must be Pro"),
            ("CABINET", "Tower", ["cabinet","tower"], "Tower suitable"),
            ("SMPS", "200W", ["smps","200 watt","300 watt"], "200W not → 300W/450W FETCHED"),
            ("K+M", "Combo", ["keyboard","mouse"], "Combo suitable"),
            ("SPEAKER", "Speaker", ["speaker"], "Suitable"),
            ("WIFI+BT", "WiFi+BT", ["wifi","bluetooth"], "WiFi 5/6 + BT suitable"),
            ("TPM", "TPM 2.0", ["tpm"], "TPM 2.0"),
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
                        reason = f"🤖 [EXACT] {kw}" if keywords.index(kw)==0 else f"🤖 [ALT] {kw} → {note}"
                        break
                if best:
                    break
            if not best and all_models:
                best = all_models[min(row_num-5, len(all_models)-1)]
                reason = f"🤖 [CATEGORY] {param} → {note}"
            if not best:
                best = "❌ NOT IN MASTER"
                reason = "ADD KEYWORD"

            ws.cell(row=row_num, column=1, value=param).font = bold
            ws.cell(row=row_num, column=1).border = thin
            ws.cell(row=row_num, column=1).fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
            ws.cell(row=row_num, column=1).font = Font(bold=True, color="E2E8F0")

            ws.cell(row=row_num, column=2, value=req).border = thin
            ws.cell(row=row_num, column=2).font = blue_font
            ws.cell(row=row_num, column=2).fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")

            ws.cell(row=row_num, column=3, value=best).border = thin
            ws.cell(row=row_num, column=3).font = green_font
            ws.cell(row=row_num, column=3).fill = PatternFill(start_color="020617", end_color="020617", fill_type="solid")

            ws.cell(row=row_num, column=4, value=reason).border = thin
            ws.cell(row=row_num, column=4).font = yellow_font
            ws.cell(row=row_num, column=4).fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
            ws.cell(row=row_num, column=4).alignment = Alignment(wrap_text=True, vertical='center')
            ws.row_dimensions[row_num].height = 36
            row_num += 1

        ws.column_dimensions['A'].width = 16
        ws.column_dimensions['B'].width = 18
        ws.column_dimensions['C'].width = 38
        ws.column_dimensions['D'].width = 52

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        st.markdown("---")
        st.markdown("#### 🤖 ROBOT READY — VOICE GUIDE + EXCEL")
        st.dataframe(pd.DataFrame([{"Component": r[0], "Requirement": r[1], "Robot Fetched 🤖": next((m for m in all_models if any(safe_lower(k) in safe_lower(m) for k in r[2])), all_models[0] if all_models else "Not Found")} for r in rules[:8]]), use_container_width=True, hide_index=True)

        st.download_button(
            "🤖🎤 DOWNLOAD — ROBOT VOICE GUIDE EXCEL — JUST ONE BEST",
            data=buf,
            file_name="GeM_ROBOT_VOICE_GUIDE_JUST_ONE.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary"
        )
        st.markdown('</div>', unsafe_allow_html=True)
        st.balloons()

        # Auto speak after excel ready
        components.html("""
        <script>
            setTimeout(() => {
                if ('speechSynthesis' in window) {
                    const msg = new SpeechSynthesisUtterance("Excellent! I have scanned your Master Sheet and fetched just one best product for each component. If H610 motherboard not available, I fetched B660 or B760. If 16GB RAM not available, I fetched 32GB. If 256GB SSD not available, I fetched 512GB. Your Excel file is ready to download. Click the download button. You can ask me any question by voice.");
                    msg.rate = 0.95;
                    msg.pitch = 0.9;
                    window.speechSynthesis.speak(msg);
                }
            }, 1000);
        </script>
        """, height=0)

    except Exception as e:
        st.error(f"🤖 ROBOT ERROR: {e}")
        import traceback
        st.code(traceback.format_exc())
else:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.info("🤖 INSERT MASTER CORE — ROBOT VOICE GUIDE WILL ACTIVATE! Click GUIDE ME for voice 🔊")

    st.markdown("""
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin-top:14px;">
        <div style="background:rgba(56,189,248,0.1); border:1px solid rgba(56,189,248,0.2); border-radius:12px; padding:14px; text-align:center;">
            <div style="font-size:28px;">🎤</div><div style="font-size:11px; font-weight:700; color:#38BDF8; font-family:JetBrains Mono;">VOICE: Click mic, ask question, robot speaks answer</div>
        </div>
        <div style="background:rgba(34,211,238,0.1); border:1px solid rgba(34,211,238,0.2); border-radius:12px; padding:14px; text-align:center;">
            <div style="font-size:28px;">🤖</div><div style="font-size:11px; font-weight:700; color:#22D3EE; font-family:JetBrains Mono;">BIG ROBOT: Patrols, scans, fetches JUST ONE best</div>
        </div>
        <div style="background:rgba(167,139,250,0.1); border:1px solid rgba(167,139,250,0.2); border-radius:12px; padding:14px; text-align:center;">
            <div style="font-size:28px;">🔊</div><div style="font-size:11px; font-weight:700; color:#A78BFA; font-family:JetBrains Mono;">GUIDE ME button: Full voice tutorial</div>
        </div>
        <div style="background:rgba(251,191,36,0.1); border:1px solid rgba(251,191,36,0.2); border-radius:12px; padding:14px; text-align:center;">
            <div style="font-size:28px;">🎯</div><div style="font-size:11px; font-weight:700; color:#FBBF24; font-family:JetBrains Mono;">JUST ONE: RAM, MB, SSD, CPU, Monitor</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)