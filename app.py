import streamlit as st
import pandas as pd
import re
import io

try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader

try:
    import pytesseract
    from PIL import Image, ImageEnhance
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment


# =========================================================
# BASIC HELPERS
# =========================================================

def safe_str(x):
    if x is None:
        return ""
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    return str(x).strip()


def safe_lower(x):
    return safe_str(x).lower()


def read_pdf_text(file):
    try:
        file.seek(0)
        r = PdfReader(file)
        return "\n".join([(p.extract_text() or "") for p in r.pages])
    except Exception:
        return ""


def read_atc_any(file):
    filename = safe_lower(file.name)
    file.seek(0)
    if filename.endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp')):
        if not OCR_AVAILABLE:
            return "", "image", "OCR library (pytesseract) not available in this environment"
        try:
            pil_img = Image.open(file)
            img = pil_img.convert('L')
            w, h = img.size
            if w < 1800:
                img = img.resize((w * 2, h * 2), Image.LANCZOS)
            img = ImageEnhance.Contrast(img).enhance(2.5)
            text = pytesseract.image_to_string(img, config=r'--oem 3 --psm 6')
            return text, "image", "success"
        except Exception as e:
            return "", "image", str(e)
    elif filename.endswith('.pdf'):
        text = read_pdf_text(file)
        return text, "pdf", "text pdf"
    return "", "unknown", "unsupported file type"


# =========================================================
# ATC EXTRACTION
# Parses a "Feature | Minimum Required Specification" style table.
# Works off OCR / PDF text lines. Because layout is lost in text
# extraction, this keys off known feature labels rather than trying
# to reconstruct table columns blindly.
# =========================================================

ATC_FEATURE_KEYS = [
    ("Processor", ["processor"]),
    ("RAM Type", ["ram type"]),
    ("RAM Capacity", ["ram capacity"]),
    ("RAM Expandability", ["ram expandability", "expandab"]),
    ("SSD", ["ssd"]),
    ("HDD", ["hdd"]),
    ("Network Connectivity", ["ethernet", "network connectivity"]),
    ("USB Ports", ["usb ort", "usb port"]),
    ("Audio-in/Mic", ["audio-in", "audio in", "mic"]),
    ("Audio-out", ["audio-out", "audio out"]),
    ("HDMI Port (CPU)", ["number of hdmi"]),
    ("DP/VGA Port (CPU)", ["number of dp", "dp or vga"]),
    ("Monitor Size", ["size inches", "monitor size"]),
    ("Monitor Technology", ["technology"]),
    ("Monitor Resolution", ["resolution"]),
    ("Webcam", ["webcam"]),
    ("Speakers & MIC (Monitor)", ["speakers", "mic integrated"]),
    ("Monitor HDMI Port", ["hdmi port inbuilt"]),
    ("Monitor DP Port", ["dp or vga port inbuilt", "dp port inbuilt"]),
    ("Keyboard", ["keyboard"]),
    ("Mouse", ["mouse"]),
    ("Operating System", ["operating system"]),
    ("SMPS", ["smps"]),
    ("Certificate (PC)", ["bee or equivalent"]),
    ("Certificate (Monitor)", ["rohs or equivalent"]),
    ("Certificate (General)", ["bis or equivalent"]),
    ("TPM / Security Feature", ["tpm"]),
    ("Onsite Warranty", ["onsite warranty", "warranty"]),
]


def extract_atc_requirements(atc_text):
    """
    Returns dict: {feature_label: requirement_text}
    Line-based heuristic: for each line, if it matches a known feature key,
    take the remainder of that line (after stripping the label) as the value.
    If the value looks empty (label-only line, common when OCR splits a
    table row across two lines), fall back to the NEXT non-empty line.
    """
    requirements = {}
    if not atc_text:
        return requirements

    lines = [l.strip() for l in atc_text.split("\n") if l.strip()]

    for i, line in enumerate(lines):
        ll = safe_lower(line)
        for label, keywords in ATC_FEATURE_KEYS:
            if label in requirements:
                continue
            matched_kw = next((kw for kw in keywords if kw in ll), None)
            if matched_kw:
                value = ""
                # 1) prefer a 2+space/tab column split (typical of table OCR)
                parts = re.split(r'\s{2,}|\t', line.strip())
                if len(parts) >= 2:
                    value = parts[-1].strip()
                # 2) else take whatever follows the matched keyword on the same line
                if not value or safe_lower(value) == ll:
                    pos = ll.find(matched_kw)
                    remainder = line[pos + len(matched_kw):].strip(" :-\t")
                    if remainder and len(remainder) >= 2:
                        value = remainder
                # 3) only fall back to the next line if this line was label-only
                if not value:
                    if i + 1 < len(lines):
                        nxt = lines[i + 1].strip()
                        # don't steal a line that itself starts a different known feature
                        if not any(other_kw in safe_lower(nxt) for _, kws in ATC_FEATURE_KEYS for other_kw in kws):
                            value = nxt
                requirements[label] = value if value else "(present, value unclear from OCR/text — verify manually)"
    return requirements


# =========================================================
# BID EXTRACTION
# GeM's "High End Desktop Computer" category has a fixed set of
# specification labels defined by the MeitY model spec. We search
# for those exact labels in the extracted Bid PDF text and capture
# the value that follows, up to the next known label.
# =========================================================

BID_SPEC_LABELS = [
    "Base Processor Number",
    "Higher Processor Number",
    "Trusted Platform Module",
    "Factory Pre-loaded Operating System",
    "RAM Size (Memory Card/Module) (in GB) (Capacity to be Installed in the System)",
    "Primary Storage Capacity (in GB)",
    "Availability of Secondary Storage",
    "Secondary Storage Capacity (in GB)",
    "Availibility of Monitor",
    "Panel Type",
    "Screen Size (in CMs)",
    "On Site OEM Warranty (In year)",
]

# shorter aliases actually likely to appear cleanly in extracted text
BID_SPEC_LABELS_SHORT = [
    "Base Processor Number",
    "Higher Processor Number",
    "Trusted Platform Module",
    "Factory Pre-loaded",
    "RAM Size",
    "Primary Storage Capacity",
    "Availability of Secondary",
    "Secondary Storage Capacity",
    "Availibility of Monitor",
    "Panel Type",
    "Screen Size",
    "On Site OEM Warranty",
]


def extract_bid_requirements(bid_text):
    """
    Returns dict: {label: value}
    Bid PDFs (as extracted to text) tend to lose the table structure but
    keep label and value as adjacent lines/tokens. We scan for each known
    label and grab the text immediately following it up to the next label
    or a sane stop point.
    """
    requirements = {}
    if not bid_text:
        return requirements

    text = bid_text.replace("\r", "\n")
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    value_pattern = re.compile(r'(or higher|or equivalent|or better|discrete|yes|no|dos)', re.IGNORECASE)

    for idx, label in enumerate(BID_SPEC_LABELS_SHORT):
        for i, line in enumerate(lines):
            if label.lower() in line.lower():
                # value is usually on the same line after the label, or wraps
                # across several following lines in the PDF's extracted text
                # (GeM's PDF table cells wrap label and value across lines).
                after = line.lower().split(label.lower(), 1)[-1].strip(" :-")
                collected = after
                window = []
                j = i + 1
                grabbed_lines = 0
                found_value_marker = bool(value_pattern.search(after))
                while j < len(lines) and grabbed_lines < 8:
                    nxt = lines[j]
                    if any(other.lower() in nxt.lower() for other in BID_SPEC_LABELS_SHORT if other != label):
                        break
                    window.append(nxt)
                    grabbed_lines += 1
                    if value_pattern.search(nxt):
                        found_value_marker = True
                        j += 1
                        break
                    j += 1
                collected = (collected + " " + " ".join(window)).strip()
                if collected:
                    requirements[BID_SPEC_LABELS[idx]] = collected[:400]
                break  # first occurrence only

    # bid number, quantity
    m = re.search(r'GEM\/\d{4}\/B\/\d{4,10}', text.replace(" ", "").upper())
    requirements["_bid_no"] = m.group(0) if m else ""
    m_qty = re.search(r'Total Quantity[^\d]{0,20}(\d+)', text, re.IGNORECASE)
    requirements["_total_qty"] = m_qty.group(1) if m_qty else ""

    return requirements


# =========================================================
# MERGE ATC + BID
# Rule: for anything the Bid explicitly specifies, Bid wins (GeM's own
# rules prohibit ATC from overriding predefined category specs).
# ATC is used to fill gaps the Bid table doesn't cover (e.g. RAM slot
# expandability, which isn't a Bid-schema field).
# =========================================================

def merge_requirements(atc_req, bid_req):
    merged = {}

    def add(category, label, value, source):
        merged.setdefault(category, []).append({"label": label, "value": value, "source": source})

    # Processor — Bid authoritative (explicit allowed SKU list)
    if bid_req.get("Higher Processor Number"):
        add("Processor", "Higher Processor Number (allowed list)", bid_req["Higher Processor Number"], "Bid")
    if bid_req.get("Base Processor Number"):
        add("Processor", "Base Processor Number", bid_req["Base Processor Number"], "Bid")
    if atc_req.get("Processor") and "Processor" not in merged:
        add("Processor", "Processor (ATC)", atc_req["Processor"], "ATC")

    # Motherboard / TPM — Bid authoritative
    if bid_req.get("Trusted Platform Module"):
        add("Motherboard/TPM", "Trusted Platform Module", bid_req["Trusted Platform Module"], "Bid")
    if atc_req.get("TPM / Security Feature"):
        add("Motherboard/TPM", "Security Feature (ATC)", atc_req["TPM / Security Feature"], "ATC")

    # RAM — merge both; ATC has slot-expandability detail Bid lacks
    if bid_req.get("RAM Size (Memory Card/Module) (in GB) (Capacity to be Installed in the System)"):
        add("RAM", "RAM Size (GB)", bid_req["RAM Size (Memory Card/Module) (in GB) (Capacity to be Installed in the System)"], "Bid")
    if atc_req.get("RAM Type"):
        add("RAM", "RAM Type (ATC)", atc_req["RAM Type"], "ATC")
    if atc_req.get("RAM Capacity"):
        add("RAM", "RAM Capacity (ATC)", atc_req["RAM Capacity"], "ATC")
    if atc_req.get("RAM Expandability"):
        add("RAM", "RAM Expandability - slots (ATC only, Bid has no equivalent field)", atc_req["RAM Expandability"], "ATC")

    # Storage
    if bid_req.get("Primary Storage Capacity (in GB)"):
        add("Storage", "Primary Storage Capacity (GB)", bid_req["Primary Storage Capacity (in GB)"], "Bid")
    if bid_req.get("Availability of Secondary Storage"):
        add("Storage", "Secondary Storage Type", bid_req["Availability of Secondary Storage"], "Bid")
    if bid_req.get("Secondary Storage Capacity (in GB)"):
        add("Storage", "Secondary Storage Capacity (GB)", bid_req["Secondary Storage Capacity (in GB)"], "Bid")
    if atc_req.get("SSD"):
        add("Storage", "SSD (ATC)", atc_req["SSD"], "ATC")
    if atc_req.get("HDD"):
        add("Storage", "HDD (ATC)", atc_req["HDD"], "ATC")

    # Monitor
    if bid_req.get("Availibility of Monitor"):
        add("Monitor", "Availability", bid_req["Availibility of Monitor"], "Bid")
    if bid_req.get("Panel Type"):
        add("Monitor", "Panel Type", bid_req["Panel Type"], "Bid")
    if bid_req.get("Screen Size (in CMs)"):
        add("Monitor", "Screen Size (cm)", bid_req["Screen Size (in CMs)"], "Bid")
    if atc_req.get("Monitor Size"):
        add("Monitor", "Monitor Size (ATC, inches)", atc_req["Monitor Size"], "ATC")
    if atc_req.get("Monitor Resolution"):
        add("Monitor", "Resolution (ATC)", atc_req["Monitor Resolution"], "ATC")

    # Warranty
    if bid_req.get("On Site OEM Warranty (In year)"):
        add("Warranty", "Onsite OEM Warranty", bid_req["On Site OEM Warranty (In year)"], "Bid")
    elif atc_req.get("Onsite Warranty"):
        add("Warranty", "Onsite Warranty (ATC)", atc_req["Onsite Warranty"], "ATC")

    # Everything else from ATC that has no Bid-schema equivalent
    other_atc_only = ["SMPS", "Keyboard", "Mouse", "Operating System",
                       "Certificate (PC)", "Certificate (Monitor)", "Certificate (General)",
                       "USB Ports", "Network Connectivity", "Webcam"]
    for key in other_atc_only:
        if atc_req.get(key):
            add("Other (ATC only)", key, atc_req[key], "ATC")

    return merged


# =========================================================
# MASTER WORKBOOK — MOTHERBOARD SHEETS ONLY
# =========================================================

PLACEHOLDER_MARKERS = ["verify exact model page", "verify model", "n/a - verify", "—", ""]


def is_placeholder(value):
    v = safe_lower(value)
    return v in PLACEHOLDER_MARKERS or "verify" in v


def load_master_motherboards(master_file):
    """
    Reads every sheet whose name contains 'Compliance' AND has the standard
    18-column header (S.No, Model, Form Factor, CPU Socket/CPU Support,
    Chipset, Memory, Max Memory, Expansion, M.2 Storage, SATA, Graphics,
    LAN, Wi-Fi/BT, USB, TPM, OS, Official Source, Status).
    Returns one combined DataFrame with a Vendor + Chipset column derived
    from the sheet name, since not every sheet has an explicit Vendor column.
    """
    master_file.seek(0)
    wb = load_workbook(master_file, data_only=True)
    rows = []

    for sheet_name in wb.sheetnames:
        if "compliance" not in sheet_name.lower():
            continue
        ws = wb[sheet_name]
        data = list(ws.iter_rows(values_only=True))
        if not data:
            continue

        # find header row (the one starting with 'S.No.' or containing 'Model')
        header_idx = None
        for i, row in enumerate(data[:6]):
            row_vals = [safe_lower(c) for c in row]
            if any("model" in c for c in row_vals) and any("s.no" in c or "sno" in c for c in row_vals):
                header_idx = i
                break
        if header_idx is None:
            continue

        headers = [safe_str(c) for c in data[header_idx]]
        # normalize variant headers like "ASRock Model" / "MSI Model" -> "Model"
        headers = ["Model" if ("model" in h.lower() and h.lower() != "model index") else h for h in headers]
        # normalize variant CPU socket header naming
        headers = ["CPU Socket / CPU Support" if "cpu socket" in h.lower() else h for h in headers]
        # derive vendor/chipset from sheet name, e.g. "MSI H610 Compliance"
        name_parts = sheet_name.replace("Compliance", "").strip().split()
        if len(name_parts) >= 2:
            vendor_guess = " ".join(name_parts[:-1])
            chipset_guess = name_parts[-1]
        elif len(name_parts) == 1:
            vendor_guess, chipset_guess = "ASRock", name_parts[0]  # base H610 sheet has no vendor prefix
        else:
            vendor_guess, chipset_guess = "Unknown", "Unknown"

        for r in data[header_idx + 1:]:
            if not r or all(c is None for c in r):
                continue
            row_dict = {headers[i]: safe_str(r[i]) for i in range(min(len(headers), len(r)))}
            if not row_dict.get("Model") and not any(row_dict.values()):
                continue
            row_dict["Vendor"] = vendor_guess
            row_dict["Chipset (from sheet)"] = chipset_guess
            row_dict["Source Sheet"] = sheet_name
            rows.append(row_dict)

    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    return df


# =========================================================
# COMPATIBILITY LOGIC — MOTHERBOARD ONLY
# =========================================================

def cpu_family_flags(processor_req_text):
    """From the Bid's Higher Processor Number list, determine which CPU
    families/sockets are actually required so we can check board support."""
    t = safe_lower(processor_req_text)
    needs_lga1700 = any(g in t for g in ["12th", "13th", "14th", "i7-14700", "i9-12900",
                                          "i9-13900", "i9-14900", "12900", "13900", "14700", "14900"])
    needs_lga1851 = "ultra" in t
    return needs_lga1700, needs_lga1851


def check_row_compatibility(row, needs_lga1700, needs_lga1851, ram_min_gb, ram_types_allowed):
    """
    Returns (status, reasons[]) where status in
    {"Compatible", "Not Compatible", "Unverified"}.
    """
    socket_text = safe_lower(row.get("CPU Socket / CPU Support", "") or row.get("CPU Socket", ""))
    memory_text = safe_lower(row.get("Memory", ""))
    max_memory_text = safe_lower(row.get("Max Memory", ""))
    tpm_text = safe_lower(row.get("TPM", ""))

    reasons = []
    unverified = False

    # --- Socket / CPU family check ---
    if is_placeholder(socket_text):
        reasons.append("CPU socket/support data unverified")
        unverified = True
        socket_ok = None
    else:
        board_lga1700 = "lga1700" in socket_text
        board_lga1851 = "lga1851" in socket_text
        socket_ok = (needs_lga1700 and board_lga1700) or (needs_lga1851 and board_lga1851)
        if not socket_ok:
            reasons.append(f"Board socket ({socket_text[:40]}) does not match required CPU family")

    # --- RAM type check (DDR4/DDR5 allowed either) ---
    if is_placeholder(memory_text):
        reasons.append("RAM type/config data unverified")
        unverified = True
        ram_type_ok = None
    else:
        ram_type_ok = any(t in memory_text for t in ram_types_allowed)
        if not ram_type_ok:
            reasons.append(f"RAM type ({memory_text[:40]}) does not match DDR4/DDR5 requirement")

    # --- RAM capacity check ---
    if is_placeholder(max_memory_text):
        reasons.append("Max memory data unverified")
        unverified = True
        ram_cap_ok = None
    else:
        nums = [int(n) for n in re.findall(r'(\d+)\s*gb', max_memory_text)]
        ram_cap_ok = bool(nums) and max(nums) >= ram_min_gb
        if nums and not ram_cap_ok:
            reasons.append(f"Max memory ({max(nums)}GB) below required {ram_min_gb}GB")
        elif not nums:
            reasons.append("Could not parse max memory value")
            unverified = True

    # --- TPM check ---
    if is_placeholder(tpm_text):
        reasons.append("TPM data unverified")
        unverified = True
        tpm_ok = None
    else:
        tpm_ok = "tpm" in tpm_text
        if tpm_ok and "header" in tpm_text:
            reasons.append("Board has TPM HEADER only — a discrete TPM 2.0 module must be fitted separately to meet 'Discrete TPM 2.0' requirement; not shipped compliant by default")
        if not tpm_ok:
            reasons.append("No TPM support indicated")

    if unverified:
        return "Unverified — needs manual spec check", reasons

    all_ok = all(x is True for x in [socket_ok, ram_type_ok, ram_cap_ok, tpm_ok] if x is not None)
    if all_ok:
        return "Compatible", reasons if reasons else ["Meets socket, RAM type/capacity, and TPM requirements"]
    else:
        return "Not Compatible", reasons


def build_compatibility_table(df_master, merged_reqs):
    if df_master.empty:
        return pd.DataFrame()

    proc_reqs = merged_reqs.get("Processor", [])
    proc_text = " ".join([p["value"] for p in proc_reqs])
    needs_lga1700, needs_lga1851 = cpu_family_flags(proc_text)

    ram_reqs = merged_reqs.get("RAM", [])
    ram_min_gb = 32
    for r in ram_reqs:
        nums = [int(n) for n in re.findall(r'(\d+)', r["value"]) if n.isdigit() or True]
    nums_all = []
    for r in ram_reqs:
        nums_all += [int(n) for n in re.findall(r'\d+', r["value"])]
    if nums_all:
        ram_min_gb = min([n for n in nums_all if n >= 8], default=32)  # smallest realistic capacity mentioned

    ram_types_allowed = ["ddr4", "ddr5"]

    results = []
    for _, row in df_master.iterrows():
        status, reasons = check_row_compatibility(row, needs_lga1700, needs_lga1851, ram_min_gb, ram_types_allowed)
        results.append({
            "Vendor": row.get("Vendor", ""),
            "Chipset": row.get("Chipset", row.get("Chipset (from sheet)", "")),
            "Model": row.get("Model", ""),
            "Form Factor": row.get("Form Factor", ""),
            "CPU Socket / Support": row.get("CPU Socket / CPU Support", ""),
            "Memory": row.get("Memory", ""),
            "Max Memory": row.get("Max Memory", ""),
            "TPM": row.get("TPM", ""),
            "Status": status,
            "Reason(s)": "; ".join(reasons),
            "Source Sheet": row.get("Source Sheet", ""),
            "Official Source": row.get("Official Source", ""),
        })

    return pd.DataFrame(results)


# =========================================================
# EXCEL EXPORT
# =========================================================

def export_excel(atc_req, bid_req, merged_reqs, compat_df, bid_no):
    wb = Workbook()

    thin = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    ok_fill = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid")
    bad_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    unv_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")

    def write_header(ws, headers, row=1):
        for i, h in enumerate(headers, start=1):
            c = ws.cell(row=row, column=i, value=h)
            c.font = header_font
            c.fill = header_fill
            c.border = thin
            c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    # Sheet 1: ATC Requirements
    ws1 = wb.active
    ws1.title = "ATC Requirements"
    write_header(ws1, ["Feature", "Minimum Required Spec (ATC)"])
    r = 2
    for label, _ in ATC_FEATURE_KEYS:
        if label in atc_req:
            ws1.cell(row=r, column=1, value=label).border = thin
            ws1.cell(row=r, column=2, value=atc_req[label]).border = thin
            r += 1
    ws1.column_dimensions['A'].width = 28
    ws1.column_dimensions['B'].width = 60

    # Sheet 2: Bid Requirements
    ws2 = wb.create_sheet("Bid Requirements")
    write_header(ws2, ["Parameter", "Bid Allowed Value"])
    r = 2
    for label in BID_SPEC_LABELS:
        if label in bid_req:
            ws2.cell(row=r, column=1, value=label).border = thin
            ws2.cell(row=r, column=2, value=bid_req[label]).border = thin
            r += 1
    ws2.column_dimensions['A'].width = 40
    ws2.column_dimensions['B'].width = 70

    # Sheet 3: Merged requirement (per category, with source)
    ws3 = wb.create_sheet("Merged Requirements (ATC+Bid)")
    write_header(ws3, ["Category", "Requirement Label", "Value", "Source"])
    r = 2
    for cat, items in merged_reqs.items():
        for item in items:
            ws3.cell(row=r, column=1, value=cat).border = thin
            ws3.cell(row=r, column=2, value=item["label"]).border = thin
            ws3.cell(row=r, column=3, value=item["value"]).border = thin
            src_cell = ws3.cell(row=r, column=4, value=item["source"])
            src_cell.border = thin
            src_cell.fill = PatternFill(start_color="DBEAFE" if item["source"] == "Bid" else "FEF3C7", fill_type="solid")
            r += 1
    ws3.column_dimensions['A'].width = 20
    ws3.column_dimensions['B'].width = 35
    ws3.column_dimensions['C'].width = 60
    ws3.column_dimensions['D'].width = 10

    # Sheet 4: Motherboard Compatibility (the core deliverable)
    ws4 = wb.create_sheet("Motherboard Compatibility")
    ws4.merge_cells('A1:K1')
    ws4['A1'] = f"BID: {bid_no} | Motherboard compatibility vs Master Sheet (only category currently covered by Master)"
    ws4['A1'].font = Font(bold=True, size=11)
    ws4['A1'].fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")

    cols = ["Vendor", "Chipset", "Model", "Form Factor", "CPU Socket / Support", "Memory",
            "Max Memory", "TPM", "Status", "Reason(s)", "Source Sheet"]
    write_header(ws4, cols, row=3)
    r = 4
    if not compat_df.empty:
        for _, row in compat_df.iterrows():
            for ci, col in enumerate(cols, start=1):
                cell = ws4.cell(row=r, column=ci, value=row.get(col, ""))
                cell.border = thin
                cell.alignment = Alignment(wrap_text=True, vertical='top')
            status = row.get("Status", "")
            fill = ok_fill if status == "Compatible" else (bad_fill if status == "Not Compatible" else unv_fill)
            for ci in range(1, len(cols) + 1):
                ws4.cell(row=r, column=ci).fill = fill
            r += 1
    for i, col in enumerate(cols, start=1):
        ws4.column_dimensions[chr(64 + i) if i <= 26 else 'A'].width = 22

    # Sheet 5: Other categories — not covered by this Master
    ws5 = wb.create_sheet("Other Categories (No Data)")
    write_header(ws5, ["Category", "Bid/ATC Requirement", "Status"])
    r = 2
    covered = {"Processor", "Motherboard/TPM"}
    for cat, items in merged_reqs.items():
        if cat in covered:
            continue
        for item in items:
            ws5.cell(row=r, column=1, value=cat).border = thin
            ws5.cell(row=r, column=2, value=f'{item["label"]}: {item["value"]}').border = thin
            c = ws5.cell(row=r, column=3, value="No master data uploaded for this category yet")
            c.border = thin
            c.fill = unv_fill
            r += 1
    ws5.column_dimensions['A'].width = 20
    ws5.column_dimensions['B'].width = 70
    ws5.column_dimensions['C'].width = 35

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


# =========================================================


# UI
# =========================================================

st.markdown("""
<div style="background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); border-radius: 18px; padding: 18px 24px; color: white;">
<div style="font-size:20px; font-weight:800;">🇮🇳 GeM — ATC + Bid Requirement Extraction & Motherboard Compatibility</div>
<div style="font-size:11px; opacity:0.7;">Step 1: ATC required list · Step 2: Bid required list · Step 3: Compatible motherboards from Master (other categories flagged as no-data until their master sheets are added)</div>
</div>
<div style="height:4px; background: linear-gradient(90deg, #FF9933 0%, #FFF 50%, #138808 100%); border-radius:10px; margin:10px 0;"></div>
""", unsafe_allow_html=True)

if st.button("🗑️ Clear All", type="primary"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("**📄 ATC — PDF/Image**")
    atc_file = st.file_uploader("ATC", type=["pdf", "jpg", "jpeg", "png", "bmp", "webp"], key="atc", label_visibility="collapsed")
    atc_text, atc_req = "", {}
    if atc_file:
        atc_text, atc_type, atc_msg = read_atc_any(atc_file)
        if atc_text:
            atc_req = extract_atc_requirements(atc_text)
            st.success(f"✅ ATC parsed: {len(atc_req)} features found")
        else:
            st.warning(atc_msg)

with c2:
    st.markdown("**📑 Bid PDF**")
    bid_file = st.file_uploader("Bid", type=["pdf"], key="bid", label_visibility="collapsed")
    bid_req = {}
    if bid_file:
        bid_text = read_pdf_text(bid_file)
        bid_req = extract_bid_requirements(bid_text)
        bid_no = bid_req.get("_bid_no", "Unknown")
        st.success(f"✅ Bid parsed: {bid_no}")

with c3:
    st.markdown("**📊 Master Excel (Motherboard workbook)**")
    master_file = st.file_uploader("Master", type=["xlsx", "xls"], key="master", label_visibility="collapsed")
    df_master = pd.DataFrame()
    if master_file:
        try:
            df_master = load_master_motherboards(master_file)
            st.success(f"✅ {len(df_master)} motherboard rows loaded from {df_master['Source Sheet'].nunique() if not df_master.empty else 0} sheets")
        except Exception as e:
            st.error(f"Could not read master workbook: {e}")

if atc_req:
    st.markdown("### 1️⃣ ATC Required Products")
    st.dataframe(pd.DataFrame([{"Feature": k, "Minimum Required Spec": v} for k, v in atc_req.items()]), use_container_width=True)

if bid_req:
    st.markdown("### 2️⃣ Bid Required Products")
    bid_display = {k: v for k, v in bid_req.items() if not k.startswith("_")}
    st.dataframe(pd.DataFrame([{"Parameter": k, "Bid Allowed Value": v} for k, v in bid_display.items()]), use_container_width=True)

if atc_file and bid_file and master_file and not df_master.empty:
    st.markdown("### 3️⃣ Compatible Motherboards (Master vs merged ATC+Bid requirement)")
    merged = merge_requirements(atc_req, bid_req)
    compat_df = build_compatibility_table(df_master, merged)

    status_filter = st.multiselect("Filter by status", options=["Compatible", "Not Compatible", "Unverified — needs manual spec check"],
                                    default=["Compatible", "Unverified — needs manual spec check"])
    shown = compat_df[compat_df["Status"].isin(status_filter)] if status_filter else compat_df
    st.dataframe(shown, use_container_width=True, height=500)

    n_compat = (compat_df["Status"] == "Compatible").sum()
    n_unver = (compat_df["Status"] == "Unverified — needs manual spec check").sum()
    n_not = (compat_df["Status"] == "Not Compatible").sum()
    st.info(f"**{n_compat}** compatible · **{n_unver}** unverified (master sheet data incomplete for that row) · **{n_not}** not compatible — out of {len(compat_df)} total motherboard rows in Master.")

    excel_buffer = export_excel(atc_req, bid_req, merged, compat_df, bid_req.get("_bid_no", ""))

    st.download_button(
        label="📥 Download Full Excel Report (ATC list, Bid list, Merged requirements, Motherboard compatibility, Other categories)",
        data=excel_buffer,
        file_name=f"GeM_Compliance_Report_{safe_str(bid_req.get('_bid_no','')).replace('/','_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        type="primary"
    )
elif atc_file or bid_file or master_file:
    st.info("⬆️ Upload all 3 files (ATC, Bid, Master) to generate the compatibility report.")