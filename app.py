import streamlit as st
import pandas as pd
import re
try:
    from pypdf import PdfReader
except:
    from PyPDF2 import PdfReader

st.set_page_config(page_title="GeM Compatibility Price List", layout="wide", page_icon="🇮🇳")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800&display=swap');
* { font-family: 'Outfit', sans-serif; }
.stApp { background: #F8FAFF; }
.hero { background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); border-radius: 18px; padding: 18px 24px; color: white; }
.tricolor { height:4px; background: linear-gradient(90deg, #FF9933 0%, #FFF 50%, #138808 100%); border-radius:10px; margin:10px 0; }
.glass-card { background: white; border-radius: 16px; padding: 18px; border: 1px solid #E2E8F0; box-shadow: 0 4px 20px rgba(0,0,0,0.05); margin-bottom:14px; }
.upload-card { background: #F8FAFC; border: 1.5px dashed #CBD5E1; border-radius: 14px; padding: 16px; text-align:center; }
.prod-card { background:white; border-radius:12px; padding:12px; border:1px solid #E2E8F0; border-left:4px solid #10B981; }
.compatible { background:#ECFDF5; border:1px solid #86EFAC; }
.not-compatible { background:#FEF2F2; border:1px solid #FCA5A5; }
</style>
""", unsafe_allow_html=True)

def read_pdf(file):
    reader = PdfReader(file)
    return "\n".join([(p.extract_text() or "") for p in reader.pages])

def extract_bid_requirements(text):
    """Extract exact requirements from Bid"""
    tl = text.lower()
    req = {}

    # Extract all specs
    patterns = {
        "processor": r'processor\s*[:\-]?\s*([^\n]+i[3579][^\n]*|ryzen[^\n]*|intel[^\n]*core[^\n]*)',
        "ram": r'ram\s*[:\-]?\s*(\d+\s*gb[^\n]*ddr[45]?[^\n]*)',
        "ssd": r'ssd\s*[:\-]?\s*(\d+\s*gb[^\n]*nvme[^\n]*|\d+\s*tb[^\n]*)',
        "monitor": r'monitor\s*[:\-]?\s*(\d+.*?inch[^\n]*)',
        "os": r'operating system\s*[:\-]?\s*([^\n]+)',
        "graphics": r'graphics\s*[:\-]?\s*([^\n]+)',
    }
    for k, pat in patterns.items():
        m = re.search(pat, text, re.I)
        req[k] = m.group(1).strip() if m else "As per ATC"

    # Generic bid meta
    m = re.search(r'GEM\/\d{4}\/B\/\d+', text.replace(" ","").upper())
    req['bid_no'] = m.group(0) if m else ""
    m = re.search(r'Organisation\s*Name\s*[:\-]?\s*([^\n]+)', text, re.I)
    req['org'] = m.group(1).strip()[:80] if m else ""
    m = re.search(r'Quantity\s*[:\-]?\s*(\d+)', text, re.I)
    req['qty'] = int(m.group(1)) if m else 65
    req['full_text'] = text
    return req

def check_compatibility(component_name, component_model, component_specs, bid_requirements_text):
    """Check if component is compatible with bid"""
    text = bid_requirements_text.lower()
    comp = f"{component_name} {component_model} {component_specs}".lower()

    # Basic compatibility logic
    # If bid mentions i5 and component has i3, not compatible
    if "i5" in text and "i3" in comp and "processor" in component_name.lower():
        return False, "Bid requires i5, model is i3"
    if "16 gb" in text and "8 gb" in comp and "ram" in component_name.lower():
        return False, "Bid requires 16GB, model is 8GB"
    if "512 gb" in text and "256 gb" in comp and "ssd" in component_name.lower():
        return False, "Bid requires 512GB, model is 256GB"

    return True, "Compatible as per Bid"

# HEADER
st.markdown('<div class="hero"><div style="font-size:20px; font-weight:800;">🇮🇳 GeM Compatibility Price List Generator</div><div style="font-size:12px; opacity:0.7;">Upload Bid + Your Component Master List → Fresh Compatible List with Price</div></div><div class="tricolor"></div>', unsafe_allow_html=True)

st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown("#### 📂 Step 1 • Upload 2 Files")

c1,c2 = st.columns(2)
with c1:
    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    st.markdown("**📄 1. Bid Document (Full GeM Bid PDF)**")
    bid_file = st.file_uploader("Bid PDF", type=["pdf"], key="bid", label_visibility="collapsed")
    bid_req = None
    bid_text = ""
    if bid_file:
        bid_text = read_pdf(bid_file)
        bid_req = extract_bid_requirements(bid_text)
        st.success(f"✅ Bid Read: {bid_req.get('bid_no','')} | Qty: {bid_req.get('qty')}")
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    st.markdown("**📊 2. Your Components Master List (Excel)**")
    st.caption("Format: Product | Model | Price | Specs")
    comp_file = st.file_uploader("Component List", type=["xlsx","xls","csv"], key="comp", label_visibility="collapsed")
    df_comp = None
    if comp_file:
        try:
            if comp_file.name.endswith('.csv'):
                df_comp = pd.read_csv(comp_file)
            else:
                df_comp = pd.read_excel(comp_file)
            st.success(f"✅ {len(df_comp)} components loaded")
            st.dataframe(df_comp.head(3), use_container_width=True)
        except Exception as e:
            st.error(f"Error: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# SAMPLE FORMAT
with st.expander("📋 See Sample Component Master List Format (Required)"):
    sample = pd.DataFrame([
        ["Processor CPU", "Intel i5 14400", 14200, "14th Gen, 10 Cores, LGA1700"],
        ["Processor CPU", "Intel i3 14100", 8500, "14th Gen, 4 Cores"],
        ["RAM", "Crucial 16GB DDR4", 5200, "16GB DDR4 3200MHz"],
        ["RAM", "Crucial 8GB DDR4", 2800, "8GB DDR4 3200MHz"],
        ["SSD", "WD 512GB NVMe", 3100, "512GB NVMe Gen4"],
        ["SSD", "Samsung 1TB NVMe", 5400, "1TB NVMe Gen4"],
        ["MONITOR", "Dell 21.5 Inch", 7200, "21.5 Inch FHD"],
        ["MONITOR", "Dell 24 Inch", 8500, "24 Inch FHD"],
        ["SMPS WATT", "550W 80+ Bronze", 1800, "550 Watt"],
    ], columns=["Product", "Model", "Price", "Specs"])
    st.dataframe(sample, use_container_width=True)
    st.download_button("📥 Download Sample Excel Template", sample.to_csv(index=False).encode(), "Sample_Component_List.csv")

# GENERATE FRESH LIST
if bid_file and comp_file and df_comp is not None:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown(f"#### ✅ Step 2 • Fresh Compatible List for Bid: {bid_req.get('bid_no','')}")

    # Normalize column names
    df_comp.columns = [c.strip().lower() for c in df_comp.columns]
    # Find columns
    prod_col = next((c for c in df_comp.columns if 'product' in c or 'component' in c or 'item' in c), df_comp.columns[0])
    model_col = next((c for c in df_comp.columns if 'model' in c), df_comp.columns[1] if len(df_comp.columns)>1 else prod_col)
    price_col = next((c for c in df_comp.columns if 'price' in c or 'cost' in c or 'rate' in c), df_comp.columns[2] if len(df_comp.columns)>2 else prod_col)
    specs_col = next((c for c in df_comp.columns if 'spec' in c or 'desc' in c or 'detail' in c), None)

    fresh_list = []
    for idx, row in df_comp.iterrows():
        product = str(row[prod_col])
        model = str(row[model_col])
        price = row[price_col]
        specs = str(row[specs_col]) if specs_col else ""

        is_compat, reason = check_compatibility(product, model, specs, bid_text)

        fresh_list.append({
            "Product": product,
            "Compatible Model (As per Bid)": model,
            "Price (₹)": price,
            "Specs": specs,
            "Compatibility": "✅ Compatible" if is_compat else "❌ Not Compatible",
            "Reason": reason,
            "Bid Requirement": bid_req.get(product.lower().split()[0], "") if product.lower().split()[0] in bid_req else "Check ATC"
        })

    df_fresh = pd.DataFrame(fresh_list)

    # Filter only compatible
    df_compatible = df_fresh[df_fresh['Compatibility'].str.contains('Compatible')].copy()

    tab1, tab2, tab3 = st.tabs(["✅ Compatible Only (Fresh Final List)", "📋 All Components Check", "💰 Final Price Summary"])

    with tab1:
        st.markdown(f"**Fresh List — Only Models Compatible with Bid Requirement** — {len(df_compatible)} items")
        st.dataframe(df_compatible[["Product","Compatible Model (As per Bid)","Price (₹)","Specs","Reason"]], use_container_width=True)

        total = pd.to_numeric(df_compatible["Price (₹)"], errors='coerce').sum()
        qty = bid_req.get('qty',65)
        st.metric("Total Base Price (Compatible Models)", f"₹{total:,.0f}")
        st.metric(f"Total for {qty} Units", f"₹{total*qty:,.0f}")

        st.download_button("📥 Download Fresh Compatible List (Excel)", df_compatible.to_csv(index=False).encode(), f"Compatible_List_{bid_req.get('bid_no','')}.csv", type="primary", use_container_width=True)

    with tab2:
        st.dataframe(df_fresh, use_container_width=True)

    with tab3:
        if len(df_compatible) > 0:
            total = pd.to_numeric(df_compatible["Price (₹)"], errors='coerce').sum()
            margin = st.number_input("Margin per PC ₹", value=4000, key="margin")
            gst = int((total+margin)*0.18)
            grand = total+margin+gst
            total_bid = grand * qty

            st.markdown(f"""
            <div style="background:#0F172A; color:white; padding:16px; border-radius:12px; text-align:center;">
            <div>Base: ₹{total:,.0f} + Margin: ₹{margin:,} + GST: ₹{gst:,}</div>
            <h3 style="margin:8px 0 0 0; color:white;">Grand per PC: ₹{grand:,.0f} | Total Bid ({qty} Units): ₹{total_bid:,.0f}</h3>
            </div>
            """, unsafe_allow_html=True)

            final_summary = pd.DataFrame([
                ["Bid Number", bid_req.get('bid_no','')],
                ["Organisation", bid_req.get('org','')],
                ["Quantity", qty],
                ["Compatible Products", len(df_compatible)],
                ["Base Price", total],
                ["Margin", margin],
                ["GST", gst],
                ["Grand per PC", grand],
                ["Total Bid Value", total_bid]
            ], columns=["Field","Value"])
            st.dataframe(final_summary, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

else:
    st.info("⬆️ Upload both files — Bid PDF + Component Master Excel — to generate fresh compatible list")

st.markdown("""
---
**How this compatibility works:**

1. I read your Bid PDF and extract exact requirement: like *i5 14th Gen, 16GB RAM, 512GB SSD, 21.5 inch Monitor*
2. I read your Master List Excel — which has many different models (i3, i5, i7, 8GB, 16GB etc. with prices)
3. I filter and keep **only those models which match Bid's requirement**
4. Final Fresh List = **Product + Compatible Model + Price** (ready to submit)

**Share your 2 files now and I will generate the fresh list instantly.**
""")