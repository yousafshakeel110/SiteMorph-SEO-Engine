import streamlit as st
import openai
import zipfile
import os
import tempfile
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Design Lock SEO Generator", layout="wide")
st.title("Premium Design-Lock SEO Page Generator")

# ---------------- BASIC INPUTS ---------------- #

project_name = st.text_input("Project / Website Name")

homepage_html = st.file_uploader(
    "Upload Homepage HTML file (index.html)",
    type=["html"]
)

homepage_css = st.file_uploader(
    "Upload Homepage CSS file (style.css)",
    type=["css"]
)

keyword_input = st.text_area(
    "Paste Keywords (one per line)",
    height=150
)

keyword_file = st.file_uploader(
    "Or upload keyword CSV (column name: keyword)",
    type=["csv"]
)

language = st.selectbox(
    "Language",
    ["English", "Urdu", "Arabic", "Spanish", "Korean", "Filipino"]
)

seo_type = st.selectbox(
    "SEO Type",
    ["Local", "Global", "Hybrid"]
)

country = st.text_input("Country")
city = st.text_input("City")

openai_key = st.text_input(
    "OpenAI API Key",
    type="password"
)

generate = st.button("Generate SEO Pages")

# ---------------- FUNCTIONS ---------------- #

def get_keywords():
    if keyword_file:
        df = pd.read_csv(keyword_file)
        return df["keyword"].dropna().tolist()
    return [k.strip() for k in keyword_input.split("\n") if k.strip()]

def build_page_prompt(base_html, keyword):
    return f"""
You are an expert SEO developer.

STRICT RULES (DO NOT BREAK):
- Do NOT change layout
- Do NOT change HTML structure
- Do NOT change CSS classes
- Do NOT change images
- Do NOT change colors or fonts

TASK:
Replace ONLY text content inside the HTML.

SEO DATA:
Language: {language}
SEO Type: {seo_type}
Primary Keyword: {keyword}
Country: {country}
City: {city}

REQUIREMENTS:
- SEO optimized headings
- NLP semantic content
- Natural language
- FAQ section
- JSON-LD FAQ schema
- Meta title & description

OUTPUT:
Return FULL HTML ONLY.
"""

# ---------------- MAIN LOGIC ---------------- #

if generate:
    if not homepage_html or not homepage_css or not openai_key:
        st.error("Homepage HTML, CSS and OpenAI key are required.")
    else:
        openai.api_key = openai_key
        keywords = get_keywords()

        base_html = homepage_html.read().decode("utf-8")
        base_css = homepage_css.read().decode("utf-8")

        with tempfile.TemporaryDirectory() as tmpdir:

            # Save CSS
            css_dir = os.path.join(tmpdir, "css")
            os.makedirs(css_dir, exist_ok=True)

            with open(os.path.join(css_dir, "style.css"), "w", encoding="utf-8") as f:
                f.write(base_css)

            pages_dir = os.path.join(tmpdir, "pages")
            os.makedirs(pages_dir, exist_ok=True)

            for kw in keywords:
                prompt = build_page_prompt(base_html, kw)

                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You generate production-ready SEO HTML pages."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.6
                )

                page_html = response.choices[0].message.content
                filename = kw.lower().replace(" ", "-") + ".html"

                with open(os.path.join(pages_dir, filename), "w", encoding="utf-8") as f:
                    f.write(page_html)

            # ZIP CREATION
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                for folder, _, files in os.walk(tmpdir):
                    for file in files:
                        file_path = os.path.join(folder, file)
                        zipf.write(
                            file_path,
                            arcname=file_path.replace(tmpdir, "")
                        )

            st.success("Design-locked SEO pages generated successfully.")
            st.download_button(
                "Download ZIP",
                data=zip_buffer.getvalue(),
                file_name=f"{project_name}_seo_pages.zip",
                mime="application/zip"
            )
