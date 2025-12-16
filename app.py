import streamlit as st
import zipfile
import pandas as pd
from io import BytesIO
from openai import OpenAI

st.set_page_config(page_title="Inline HTML SEO Generator", layout="wide")
st.title("Premium Inline HTML SEO Page Generator")

# ---------------- UI ---------------- #

st.markdown("### *Paste HTML Template (Inline CSS Required)*")
html_template = st.text_area(
    "HTML Template",
    height=300,
    placeholder="Paste FULL HTML here (with <style> inside)"
)

st.markdown("### *Keywords Input*")
keyword_text = st.text_area(
    "Paste keywords (one per line)",
    height=120
)

keyword_file = st.file_uploader(
    "Or upload CSV (column name: keyword)",
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

generate = st.button("Generate Pages")

# ---------------- HELPERS ---------------- #

def get_keywords():
    if keyword_file:
        df = pd.read_csv(keyword_file)
        return df["keyword"].dropna().tolist()
    return [k.strip() for k in keyword_text.split("\n") if k.strip()]

def build_prompt(html, keyword):
    return f"""
You are an expert SEO content editor.

STRICT RULES (ABSOLUTE):
- DO NOT change HTML structure
- DO NOT change CSS
- DO NOT change images
- DO NOT change buttons or CTA
- DO NOT add new sections
- ONLY replace existing text content

HTML TEMPLATE:
{html}

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
- Add meta title & description IF already present
- Add FAQ schema ONLY if FAQ section exists

OUTPUT:
Return FULL HTML ONLY.
NO explanations.
"""

# ---------------- MAIN ---------------- #

if generate:
    if not html_template or not api_key:
        st.error("HTML template and API key are required.")
    else:
        keywords = get_keywords()
        if not keywords:
            st.error("Please add at least one keyword.")
        else:
            client = OpenAI(api_key=api_key)

            zip_buffer = BytesIO()

            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                for kw in keywords:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You strictly preserve HTML layout."},
                            {"role": "user", "content": build_prompt(html_template, kw)}
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
