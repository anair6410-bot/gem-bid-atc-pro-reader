import streamlit as st
import pandas as pd
import re
try:
    from pypdf import PdfReader
except:
    from PyPDF2 import PdfReader

st.set_page_config(page_title="GeM 3-Doc Compatibility", layout="wide", page_icon="🇮🇳")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800&display=swap');
* { font-family: 'Outfit', sans-serif; }
.stApp { background: #F8FAFF; }
.hero { background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); border-radius: 18px; padding: 18px 24px; color: white; display:flex; justify-content:space-between; align-items:center; }
.tricolor { height:4px; background: linear-gradient(90deg, #FF9933 0%, #FFF 50%, #138808 100%); border-radius:10px; margin:10px 0; }
.glass-card { background: white; border-radius: 16px; padding: 18px; border: 1px solid #E2E8F0; box-shadow: 0 4px 20px rgba(0,0,0,0.05); margin-bottom:14px; }
.upload-card { background: #F8FAFC; border: 1.5px dashed #CBD5E1; border-radius: 14px; padding: 16px; text-align:center; min-height: 180px; }
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

def read_pdf(file):
    r = PdfReader(file)
    return "\n".join([(p.extract_text() or "") for p in r.pages])

def parse_atc_components(atc_text):
    """Extract components required from ATC + their spec lines"""
    low = atc_text.lower()
    required = []
    spec_map = {} # product -> spec line from ATC

    for prod, kws in KEYWORDS.items():
        for kw in kws:
            if kw in low:
                # Find line containing this keyword
                for line in atc_text.split("\n"):
                    if kw in line.lower() and len(line) < 200:
                        if prod not in spec_map:
                            spec_map[prod] = line.strip()
                if prod not in required:
                    required.append(prod)
                break
    return required, spec_map

def parse_bid_meta(bid_text):
    data = {}
    m = re.search(r'GEM\/\d{4}\/B\/\d{4,10}', bid_text.replace(" ","").upper())
    data['bid_no'] = m.group(0) if m else ""
    m = re.search(r'Organisation\s*Name\s*[:\-]?\s*([^\n]+)', bid_text, re.I)
    data['org'] = m.group(1).strip()[:100] if m else ""
    m = re.search(r'Ministry\s*Name\s*[:\-]?\s*([^\n]+)|Department\s*Name\s*[:\-]?\s*([^\n]+)', bid_text, re.I)
    data['dept'] = (m.group(1) or m.group(2)).strip()[:100] if m and (m.group(1) or m.group(2)) else ""
    m = re.search(r'Item\s*Category\s*[:\-]?\s*([^\n]+)', bid_text, re.I)
    data['item'] = m.group(1).strip()[:100] if m else "Desktop Computer"
    m = re.search(r'Quantity\s*[:\-]?\s*(\d+)', bid_text, re.I)
    data['qty'] = int(m.group(1)) if m else 65
    return data

def is_compatible_with_atc(atc_spec_line, model_name, model_specs):
    """Check if model matches ATC spec line"""
    atc = atc_spec_line.lower()
    model = f"{model_name} {model_specs}".lower()

    # Example rules - you can add more
    if "i5" in atc and "i3" in model: return False, f"ATC needs i5, model is i3"
    if "i7" in atc and ("i3" in model or "i5" in model): return False, f"ATC needs i7"
    if "16 gb" in atc and "8 gb" in model: return False, "ATC needs 16GB"
    if "32 gb" in atc and ("8 gb" in model or "16 gb" in model): return False, "ATC needs 32GB"
    if "512" in atc and "256" in model and "ssd" in atc: return False, "ATC needs 512GB"
    if "1 tb" in atc and "512" in model: return False, "ATC needs 1TB"
    if "24 inch" in atc and "21.5" in model: return False, "ATC needs 24 inch"
    if "ddr5" in atc and "ddr4" in model: return False, "ATC needs DDR5"

    return True, "Matches ATC spec"

# HEADER
st.markdown('<div class="hero"><div><div style="font-size:21px; font-weight:800;">🇮🇳 GeM 3-Document Compatibility Engine</div><div style="font-size:12px; opacity:0.7;">ATC = What components needed • Bid = Organisation/Qty • Master List = Your models & prices → Fresh Final List</div></div><div style="text-align:right; font-size:11px; opacity:0.5;">V6 - 3 Uploads</div></div><div class="tricolor"></div>', unsafe_allow_html=True)

top1,top2 = st.columns([5,1])
with top2:
    if st.button("🗑️ Clear All", use_container_width=True, type="primary"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

# 3 UPLOADS
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown("#### 📂 Upload 3 Documents — All Required")

c1,c2,c3 = st.columns(3)

with c1:
    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    st.markdown(f'**📄 ATC Document** <span class="badge-atc">COMPONENTS</span>')
    st.caption("Tells what components needed")
    atc_file = st.file_uploader("ATC PDF", type=["pdf"], key="atc", label_visibility="collapsed")
    atc_products = []; atc_spec_map = {}; atc_text=""
    if atc_file:
        atc_text = read_pdf(atc_file)
        atc_products, atc_spec_map = parse_atc_components(atc_text)
        st.success(f"✅ {len(atc_products)} components found in ATC")
        for p in atc_products[:6]:
            st.markdown(f"<div style='font-size:11px; background:#DBEAFE; margin:2px; padding:2px 6px; border-radius:10px; display:inline-block;'>{p}</div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    st.markdown(f'**📑 Full Bid Document** <span class="badge-bid">META DATA</span>')
    st.caption("Organisation, Bid No, Qty, Item")
    bid_file = st.file_uploader("Bid PDF", type=["pdf"], key="bid", label_visibility="collapsed")
    bid_meta = {"bid_no":"","org":"","dept":"","item":"Desktop Computer","qty":65}
    bid_text = ""
    if bid_file:
        bid_text = read_pdf(bid_file)
        bid_meta = parse_bid_meta(bid_text)
        st.success(f"✅ {bid_meta['bid_no'] or 'Bid'} | Qty: {bid_meta['qty']}")
        st.caption(f"Org: {bid_meta['org'][:30]}")
    st.markdown('</div>', unsafe_allow_html=True)

with c3:
    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    st.markdown(f'**📊 Master Component List** <span class="badge-master">MODELS + PRICE</span>')
    st.caption("Your different models & prices")
    master_file = st.file_uploader("Master Excel", type=["xlsx","xls","csv"], key="master", label_visibility="collapsed")
    df_master = None
    if master_file:
        try:
            df_master = pd.read_excel(master_file) if not master_file.name.endswith('.csv') else pd.read_csv(master_file)
            st.success(f"✅ {len(df_master)} models loaded")
            st.dataframe(df_master.head(2), use_container_width=True)
        except Exception as e:
            st.error(f"{e}")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# SAMPLE FORMAT
with st.expander("📋 Required Master Excel Format - Click to see"):
    sample = pd.DataFrame([
        ["Processor CPU", "Intel i5 14400", 14200, "14th Gen, 10 Cores, up to 4.7GHz"],
        ["Processor CPU", "Intel i3 14100", 8500, "14th Gen, 4 Cores"],
        ["RAM", "16GB DDR4 3200", 5200, "16GB DDR4"],
        ["RAM", "8GB DDR4 3200", 2800, "8GB DDR4"],
        ["SSD", "WD 512GB NVMe", 3100, "512GB NVMe Gen4"],
        ["SSD", "1TB NVMe", 5400, "1TB NVMe Gen4"],
        ["MONITOR", "Dell 21.5 FHD", 7200, "21.5 Inch"],
        ["MONITOR", "Dell 24 FHD", 8500, "24 Inch"],
    ], columns=["Product", "Model", "Price", "Specs"])
    st.dataframe(sample, use_container_width=True)

# GENERATE FRESH LIST
if atc_file and bid_file and master_file and df_master is not None:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown(f"### ✅ Fresh Final List — Compatibility Checked with ATC + Bid")

    st.info(f"ATC says: **{len(atc_products)} products required** → {', '.join(atc_products)} | Bid Qty: **{bid_meta['qty']}** | Org: **{bid_meta['org'][:40]}**")

    # Normalize master columns
    df_master.columns = [c.strip().lower() for c in df_master.columns]
    prod_col = next((c for c in df_master.columns if 'product' in c or 'component' in c), df_master.columns[0])
    model_col = next((c for c in df_master.columns if 'model' in c), df_master.columns[1])
    price_col = next((c for c in df_master.columns if 'price' in c or 'rate' in c), df_master.columns[2])
    specs_col = next((c for c in df_master.columns if 'spec' in c or 'desc' in c), None)

    fresh_rows = []
    for comp in atc_products: # Only products mentioned in ATC
        # Filter master list for this component
        df_filtered = df_master[df_master[prod_col].astype(str).str.lower().str.contains(comp.lower().split()[0], na=False)]

        if df_filtered.empty:
            # Try keyword matching
            for kw in KEYWORDS.get(comp, [comp.lower()]):
                df_filtered = df_master[df_master[prod_col].astype(str).str.lower().str.contains(kw, na=False) |
                                       df_master[model_col].astype(str).str.lower().str.contains(kw, na=False)]
                if not df_filtered.empty:
                    break

        if df_filtered.empty:
            fresh_rows.append({
                "Product": comp,
                "ATC Spec (from ATC doc)": atc_spec_map.get(comp, "As per ATC"),
                "Compatible Model Found": "❌ No model in your master list",
                "Price (₹)": 0,
                "Compatibility": "❌ Missing",
                "Reason": "Add this product to master list"
            })
            continue

        # Find best compatible model from filtered
        best_found = False
        for _, row in df_filtered.iterrows():
            model = str(row[model_col])
            specs = str(row[specs_col]) if specs_col else ""
            price = row[price_col]
            atc_spec = atc_spec_map.get(comp, "")

            is_comp, reason = is_compatible_with_atc(atc_spec, model, specs)

            if is_comp:
                fresh_rows.append({
                    "Product": comp,
                    "ATC Spec (from ATC doc)": atc_spec,
                    "Compatible Model Found": model,
                    "Price (₹)": price,
                    "Specs": specs,
                    "Compatibility": "✅ Compatible",
                    "Reason": reason
                })
                best_found = True
                break # Take first compatible

        if not best_found and not df_filtered.empty:
            # Show first model as not compatible
            row = df_filtered.iloc[0]
            model = str(row[model_col])
            specs = str(row[specs_col]) if specs_col else ""
            price = row[price_col]
            atc_spec = atc_spec_map.get(comp, "")
            is_comp, reason = is_compatible_with_atc(atc_spec, model, specs)
            fresh_rows.append({
                "Product": comp,
                "ATC Spec (from ATC doc)": atc_spec,
                "Compatible Model Found": model,
                "Price (₹)": price,
                "Specs": specs,
                "Compatibility": "❌ Not Compatible",
                "Reason": reason
            })

    df_fresh = pd.DataFrame(fresh_rows)
    df_compatible_only = df_fresh[df_fresh["Compatibility"] == "✅ Compatible"]

    tab1, tab2 = st.tabs(["✅ Final Fresh List (Only Compatible + Price)", "📋 All ATC Products Check"])

    with tab1:
        if len(df_compatible_only) > 0:
            st.dataframe(df_compatible_only[["Product","ATC Spec (from ATC doc)","Compatible Model Found","Price (₹)","Reason"]], use_container_width=True)

            total = pd.to_numeric(df_compatible_only["Price (₹)"], errors='coerce').sum()
            qty = bid_meta['qty']
            margin = st.number_input("Add Margin per PC ₹", value=4000, step=500, key="margin_final")

            gst = int((total+margin)*0.18)
            grand = total+margin+gst
            total_bid = grand*qty

            st.markdown(f"""
            <div style="background:#0F172A; color:white; padding:16px; border-radius:12px; text-align:center; margin-top:10px;">
            <div style="font-size:12px; opacity:0.7;">BID: {bid_meta['bid_no']} | {bid_meta['org'][:30]} | Qty: {qty} | ATC Products: {len(atc_products)}</div>
            <div style="margin-top:6px;">Base (Compatible): ₹{total:,.0f} + Margin: ₹{margin:,} + GST: ₹{gst:,}</div>
            <h2 style="margin:8px 0 0 0; color:white;">Grand/PC: ₹{grand:,.0f} | Total Bid: ₹{total_bid:,.0f}</h2>
            </div>
            """, unsafe_allow_html=True)

            # Final Download
            st.download_button("📥 Download Fresh Final List (Compatible + Price) CSV", df_compatible_only.to_csv(index=False).encode(), f"FINAL_Compatible_{bid_meta['bid_no']}.csv", use_container_width=True, type="primary")

            # Also Excel with all details
            final_summary = pd.DataFrame([
                ["Bid Number (from Bid Doc)", bid_meta['bid_no']],
                ["Organisation (from Bid Doc)", bid_meta['org']],
                ["Department (from Bid Doc)", bid_meta['dept']],
                ["Item Category (from Bid Doc)", bid_meta['item']],
                ["Quantity (from Bid Doc)", qty],
                ["ATC File", atc_file.name],
                ["Bid File", bid_file.name],
                ["Master List File", master_file.name],
                ["Total ATC Products Required", len(atc_products)],
                ["Compatible Models Found", len(df_compatible_only)],
                ["Base Price", total],
                ["Margin", margin],
                ["GST 18%", gst],
                ["Grand per PC", grand],
                ["Total Bid Value", total_bid]
            ], columns=["Field","Value from Docs"])
            st.dataframe(final_summary, use_container_width=True)

        else:
            st.warning("No compatible models found — Check your master list models vs ATC specs")

    with tab2:
        st.dataframe(df_fresh, use_container_width=True)
        st.download_button("📥 Download Full Check (Compatible + Not Compatible)", df_fresh.to_csv(index=False).encode(), f"Full_Check_{bid_meta['bid_no']}.csv", use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

elif atc_file or bid_file or master_file:
    st.warning("⬆️ Please upload all 3 files to generate fresh compatible list: 1) ATC PDF 2) Bid Full PDF 3) Master Excel")

st.markdown("""
---
**Flow now — exactly as you wanted:**

1. **ATC Upload** → I read which components are needed (Processor, RAM, SSD, Monitor etc.) + exact spec from ATC line
2. **Bid Full Doc Upload** → I auto-fill Organisation, Bid No, Qty, Department
3. **Master List Upload** → Your 100 models with different prices

**Output:** Fresh list with **Product (from ATC) + Compatible Model (from your master) + Price (from your master)** — Only compatible with ATC.

Share your 3 files and I will run it live.
""")