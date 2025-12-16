import streamlit as st
from openai import OpenAI
from PIL import Image
import base64, io, zipfile, csv, re

st.set_page_config(page_title="SiteMorph Pro", layout="wide")
st.title("SiteMorph Pro – Exact Design SEO Pages")

# ----------------------
# HELPERS
# ----------------------

def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")

def img_to_b64(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

MASTER_PROMPT = """
You are a senior front-end engineer.

TASK:
- Convert homepage screenshot into FULL HTML + FULL CSS
- This is a MASTER TEMPLATE
- Use placeholders like:
  {{H1}}, {{INTRO}}, {{SECTION_1}}, {{FAQ}}, {{CTA}}, {{SCHEMA}}
- DO NOT hardcode content
- DO NOT explain
- DO NOT change layout later
- Mobile + desktop responsive
- Keep images, icons, CTAs exactly same

Return ONLY HTML with embedded CSS.
"""

CONTENT_PROMPT = """
You are an SEO content strategist.

Fill ONLY the placeholders in the provided HTML.
Do NOT touch CSS, layout, images or structure.

SEO REQUIREMENTS:
- NLP optimized
- Semantic SEO
- Local SEO
- Meta title & description
- FAQ + JSON-LD schema

Keyword: {kw}
City: {city}
Language: {lang}

Return FULL HTML.
"""

# ----------------------
# UI
# ----------------------

api_key = st.text_input("OpenAI API Key", type="password")
language = st.selectbox("Language", ["English","Urdu","Arabic","Spanish","Korean","Filipino"])

homepage_img = st.file_uploader("Upload Homepage Screenshot", type=["png","jpg","jpeg"])

csv_file = st.file_uploader("Upload CSV (keyword,city)", type=["csv"])
manual_kw = st.text_area("Or paste keywords (keyword | city)")

generate = st.button("Generate Pages")

# ----------------------
# ENGINE
# ----------------------

if generate:
    if not api_key or not homepage_img:
        st.error("API key & homepage required")
        st.stop()

    client = OpenAI(api_key=api_key)

    img = Image.open(homepage_img)
    img_b64 = img_to_b64(img)

    # STEP 1: MASTER TEMPLATE
    with st.spinner("Locking master design..."):
        master = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role":"user",
                "content":[
                    {"type":"text","text":MASTER_PROMPT},
                    {"type":"image_url","image_url":{"url":f"data:image/png;base64,{img_b64}"}}
                ]
            }],
            temperature=0.1
        ).choices[0].message.content

    rows = []

    if csv_file:
        reader = csv.DictReader(io.StringIO(csv_file.getvalue().decode()))
        for r in reader:
            rows.append((r["keyword"], r["city"]))
    else:
        for line in manual_kw.splitlines():
            if "|" in line:
                k,c = line.split("|")
                rows.append((k.strip(), c.strip()))

    zip_buf = io.BytesIO()

    # STEP 2: CONTENT INJECTION
    with zipfile.ZipFile(zip_buf,"w") as zipf:
        for kw, city in rows:
            html = client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role":"user",
                    "content": master + CONTENT_PROMPT.format(
                        kw=kw, city=city, lang=language
                    )
                }],
                temperature=0.4
            ).choices[0].message.content

            zipf.writestr(f"{slugify(kw)}-{slugify(city)}.html", html)

    st.success("Exact design pages generated.")
    st.download_button("Download ZIP", zip_buf.getvalue(), "pages.zip")
