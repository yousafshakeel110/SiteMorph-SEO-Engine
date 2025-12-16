import streamlit as st
import zipfile
import pandas as pd
from io import BytesIO
from openai import OpenAI
import requests
import os
import shutil

st.set_page_config(page_title="SEO Page Generator", layout="wide")
st.title("Advanced SEO Page Generator with Folder Support")

# ---------------- UI ---------------- #

st.markdown("### Upload Template")
template_option = st.radio("Select Template Source:", ["Upload HTML/ZIP File", "Paste URL"])

template_file = None
template_url = None

if template_option == "Upload HTML/ZIP File":
    template_file = st.file_uploader(
        "Upload HTML Template File or ZIP Folder",
        type=["html", "zip"]
    )
elif template_option == "Paste URL":
    template_url = st.text_input("Paste Template URL (HTML or ZIP)")

keyword_text = st.text_area(
    "Paste Keywords (one per line)",
    height=120
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

country = st.text_input("Country (optional)")
city = st.text_input("City (optional)")

st.markdown("### *OpenAI API Key*")
api_key = st.text_input("API Key", type="password")

generate = st.button("Generate SEO Pages")

# ---------------- HELPERS ---------------- #

def get_keywords():
    if keyword_file:
        df = pd.read_csv(keyword_file)
        return df["keyword"].dropna().tolist()
    return [k.strip() for k in keyword_text.split("\n") if k.strip()]

def build_prompt(html_content, keyword):
    return f"""
You are an expert SEO content editor.

STRICT RULES:
- DO NOT change HTML structure
- DO NOT change CSS
- DO NOT change images
- DO NOT change buttons or CTA
- ONLY replace text content

HTML TEMPLATE:
{html_content}

SEO CONTEXT:
Primary Keyword: {keyword}
Language: {language}
SEO Type: {seo_type}
Country: {country}
City: {city}

TASK:
- Replace headings and paragraphs naturally
- Apply NLP semantic optimization
- Update city/location references
- Improve content quality
- Add meta title & description if present
- Add FAQ schema only if template contains FAQ

OUTPUT:
Return FULL HTML ONLY. NO explanations.
"""

def fetch_template_from_url(url):
    response = requests.get(url)
    if response.status_code == 200:
        content_type = response.headers.get("Content-Type", "")
        if "zip" in content_type or url.lower().endswith(".zip"):
            zip_buffer = BytesIO(response.content)
            extract_path = "temp_template"
            if os.path.exists(extract_path):
                shutil.rmtree(extract_path)
            with zipfile.ZipFile(zip_buffer, "r") as zip_ref:
                zip_ref.extractall(extract_path)
            st.success("ZIP template downloaded and extracted.")
            return extract_path
        elif "html" in content_type or url.lower().endswith(".html"):
            st.success("HTML template downloaded successfully.")
            return response.text
    st.error("Failed to download template.")
    return None

def process_html_file(client, html_path, keywords, zipf, base_folder=""):
    with open(html_path, "r", encoding="utf-8") as f:
        template_html = f.read()
    filename_base = os.path.basename(html_path)
    for kw in keywords:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You strictly preserve HTML layout."},
                {"role": "user", "content": build_prompt(template_html, kw)}
            ],
            temperature=0.5
        )
        page_html = response.choices[0].message.content
        zip_filename = os.path.join(base_folder, f"{kw.lower().replace(' ', '-')}-{filename_base}")
        zipf.writestr(zip_filename, page_html)

# ---------------- MAIN ---------------- #

if generate:
    if not api_key:
        st.error("Please enter OpenAI API key.")
    else:
        # Load template
        template_path_or_html = None
        if template_option == "Paste URL" and template_url:
            template_path_or_html = fetch_template_from_url(template_url)
        elif template_option == "Upload HTML/ZIP File" and template_file:
            if template_file.type == "application/zip" or template_file.name.endswith(".zip"):
                extract_path = "temp_template"
                if os.path.exists(extract_path):
                    shutil.rmtree(extract_path)
                with zipfile.ZipFile(template_file, "r") as zip_ref:
                    zip_ref.extractall(extract_path)
                st.success("ZIP template uploaded and extracted.")
                template_path_or_html = extract_path
            else:
                template_path_or_html = template_file.read().decode("utf-8")
        else:
            st.error("Please provide a template file or URL.")
            template_path_or_html = None

        if template_path_or_html:
            keywords = get_keywords()
            if not keywords:
                st.error("Add at least one keyword or CSV.")
            else:
                client = OpenAI(api_key=api_key)
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                    # Folder case
                    if isinstance(template_path_or_html, str) and os.path.isdir(template_path_or_html):
                        for root, dirs, files in os.walk(template_path_or_html):
                            rel_root = os.path.relpath(root, template_path_or_html)
                            for file in files:
                                if file.endswith(".html"):
                                    file_path = os.path.join(root, file)
                                    process_html_file(client, file_path, keywords, zipf, rel_root)
                                else:
                                    # Add other files (CSS/images) as-is
                                    file_path = os.path.join(root, file)
                                    with open(file_path, "rb") as f:
                                        zipf.writestr(os.path.join(rel_root, file), f.read())
                    else:
                        # Single HTML file
                        for kw in keywords:
                            response = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[
                                    {"role": "system", "content": "You strictly preserve HTML layout."},
                                    {"role": "user", "content": build_prompt(template_path_or_html, kw)}
                                ],
                                temperature=0.5
                            )
                            page_html = response.choices[0].message.content
                            filename = kw.lower().replace(" ", "-") + ".html"
                            zipf.writestr(filename, page_html)

                st.success("SEO pages generated successfully.")
                st.download_button(
                    "Download HTML ZIP",
                    data=zip_buffer.getvalue(),
                    file_name="seo_pages.zip",
                    mime="application/zip"
                )
