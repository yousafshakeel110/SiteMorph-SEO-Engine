import streamlit as st
import zipfile
import os
import tempfile
import pandas as pd
from io import BytesIO
from PIL import Image
import base64
from openai import OpenAI

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Premium AI SEO Page Generator", layout="wide")
st.title("Premium AI SEO Page Generator (Exact Design Reuse)")

# ---------------- INPUTS ----------------
project_name = st.text_input("Project / Website Name")

screenshots = st.file_uploader(
    "Upload Homepage Screenshots (Desktop + Mobile allowed)",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)

keyword_input = st.text_area("Paste Keywords (one per line)", height=150)

keyword_file = st.file_uploader(
    "Or upload CSV (column name: keyword)",
    type=["csv"]
)

language = st.selectbox(
    "Language",
    ["English", "Urdu", "Arabic", "Spanish"]
)

seo_type = st.selectbox(
    "SEO Type",
    ["Local", "Global", "Hybrid"]
)

country = st.text_input("Country")
city = st.text_input("City")

content_length = st.selectbox(
    "Content Length",
    ["800", "1200", "1800"]
)

openai_key = st.text_input("OpenAI API Key", type="password")

generate = st.button("Generate Premium SEO Pages")

# ---------------- HELPERS ----------------
def get_keywords():
    if keyword_file:
        df = pd.read_csv(keyword_file)
        return df["keyword"].dropna().tolist()
    return [k.strip() for k in keyword_input.split("\n") if k.strip()]

def image_to_base64(img):
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()

# ---------------- PROMPTS ----------------
def layout_prompt():
    return """
You are a senior UI/UX + Frontend architect.

TASK:
- Analyze homepage screenshots
- Extract EXACT layout
- Extract colors, fonts, spacing, CTA placement
- Create:
  1) base.html (semantic HTML5)
  2) style.css (all colors, fonts, responsive rules)

RULES:
- Layout must be reusable
- Mobile + Desktop responsive
- No dummy redesign
- Clean professional SaaS look

OUTPUT FORMAT:
---HTML---
(full html without content)
---CSS---
(full css)
"""

def page_prompt(keyword, base_html):
    return f"""
You are an expert SEO content strategist.

STRICT RULE:
- DO NOT change layout, classes, or structure
- Only replace text content

SEO DATA:
Keyword: {keyword}
Language: {language}
SEO Type: {seo_type}
Country: {country}
City: {city}
Length: {content_length} words

Include:
- Meta title & description
- H1–H3
- NLP entities
- FAQ section
- JSON-LD FAQ schema
- Local signals if applicable

BASE TEMPLATE:
{base_html}

OUTPUT:
Return full final HTML only.
"""

# ---------------- MAIN ----------------
if generate:
    if not openai_key or not screenshots:
        st.error("API key and screenshots required")
    else:
        client = OpenAI(api_key=openai_key)
        keywords = get_keywords()

        image_payload = []
        for img in screenshots:
            image = Image.open(img)
            image_payload.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_to_base64(image)}"
                }
            })

        with st.spinner("Analyzing homepage design..."):
            layout_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": layout_prompt()},
                        *image_payload
                    ]
                }],
                temperature=0.2
            )

        raw_output = layout_response.choices[0].message.content

        html_part = raw_output.split("---CSS---")[0].replace("---HTML---", "").strip()
        css_part = raw_output.split("---CSS---")[1].strip()

        with tempfile.TemporaryDirectory() as tmpdir:
            assets_dir = os.path.join(tmpdir, "assets")
            pages_dir = os.path.join(tmpdir, "pages")
            os.makedirs(assets_dir)
            os.makedirs(pages_dir)

            with open(os.path.join(assets_dir, "style.css"), "w", encoding="utf-8") as f:
                f.write(css_part)

            for kw in keywords:
                with st.spinner(f"Generating page for: {kw}"):
                    page_response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{
                            "role": "user",
                            "content": page_prompt(kw, html_part)
                        }],
                        temperature=0.6
                    )

                final_html = page_response.choices[0].message.content
                filename = kw.lower().replace(" ", "-") + ".html"

                with open(os.path.join(pages_dir, filename), "w", encoding="utf-8") as f:
                    f.write(final_html)

            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zipf:
                for folder, _, files in os.walk(tmpdir):
                    for file in files:
                        full_path = os.path.join(folder, file)
                        arc = full_path.replace(tmpdir + "/", "")
                        zipf.write(full_path, arc)

            st.success("Pages generated successfully")
            st.download_button(
                "Download ZIP",
                zip_buffer.getvalue(),
                f"{project_name}_seo_pages.zip",
                "application/zip"
            )
