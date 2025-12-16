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
Convert the homepage screenshot into FULL HTML + CSS.
This is a LOCKED MASTER TEMPLATE.

Rules:
- Use semantic HTML5
- Use embedded CSS
- Add placeholders: {{H1}}, {{INTRO}}, {{SECTION1}}, {{FAQ}}, {{CTA}}, {{SCHEMA}}
- Do not add real content
- Keep layout, colors, fonts, images same
- Mobile + desktop responsive

Return ONLY HTML.
"""

CONTENT_PROMPT = """
Fill ONLY placeholders in the given HTML.
Do NOT change layout, CSS, images.

SEO:
- NLP optimized
- Local SEO
- Meta title & description
- JSON-LD schema

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
csv_file = st.file_uploader("CSV (keyword,city)", type=["csv"])

generate = st.button("Generate Pages")

# ----------------------
# ENGINE
# ----------------------

if generate:
    if not api_key or not homepage_img:
        st.error("API key & homepage screenshot required")
        st.stop()

    client = OpenAI(api_key=api_key)

    # STEP 1: MASTER TEMPLATE
    try:
        img = Image.open(homepage_img)
        img_b64 = img_to_b64(img)

        with st.spinner("Creating master template..."):
            master_res = client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role":"user",
                    "content":[
                        {"type":"text","text":MASTER_PROMPT},
                        {"type":"image_url","image_url":{"url":f"data:image/png;base64,{img_b64}"}}
                    ]
                }],
                temperature=0.1
            )

        master_html = master_res.choices[0].message.content.strip()

        if len(master_html) < 500:
            st.error("Master template generation failed.")
            st.stop()

        st.subheader("Master Template Preview")
        st.code(master_html[:2000], language="html")

    except Exception as e:
        st.error(f"Template error: {e}")
        st.stop()

    # STEP 2: READ CSV
    rows = []
    try:
        reader = csv.DictReader(io.StringIO(csv_file.getvalue().decode()))
        for r in reader:
            rows.append((r["keyword"], r["city"]))
    except:
        st.error("Invalid CSV. Required columns: keyword, city")
        st.stop()

    if not rows:
        st.error("No keywords found.")
        st.stop()

    zip_buf = io.BytesIO()

    # STEP 3: GENERATE PAGES
    with zipfile.ZipFile(zip_buf,"w") as zipf:
        for kw, city in rows:
            try:
                page_res = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{
                        "role":"user",
                        "content": master_html + CONTENT_PROMPT.format(
                            kw=kw, city=city, lang=language
                        )
                    }],
                    temperature=0.4
                )

                page_html = page_res.choices[0].message.content.strip()

                if len(page_html) < 500:
                    st.warning(f"Skipped: {kw} ({city}) – empty content")
                    continue

                zipf.writestr(f"{slugify(kw)}-{slugify(city)}.html", page_html)

            except Exception as e:
                st.warning(f"Failed: {kw} ({city}) – {e}")

    if zip_buf.getbuffer().nbytes < 100:
        st.error("ZIP is empty. No pages generated.")
        st.stop()

    st.success("Pages generated successfully.")
    st.download_button("Download ZIP", zip_buf.getvalue(), "pages.zip")
