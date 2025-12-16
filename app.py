import streamlit as st
from openai import OpenAI
from PIL import Image
import base64, io, zipfile, re

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(
    page_title="SiteMorph SEO Engine",
    layout="wide"
)

st.title("SiteMorph SEO Engine")
st.caption("Clone homepage design → Generate fully optimized SEO pages")

# -----------------------------
# HELPERS
# -----------------------------

def img_to_base64(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

def clean_slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")

def layout_prompt(language):
    return f"""
You are a senior UI/UX designer and front-end engineer.

TASK:
- Analyze the uploaded homepage screenshot
- Recreate the SAME visual design
- Extract colors, fonts, spacing, layout structure
- Reuse visual hierarchy and CTA placement
- Build clean, responsive HTML + embedded CSS
- Mobile-first, then desktop

RULES:
- Use semantic HTML5
- Use inline <style> CSS
- Keep images as placeholders with same layout logic
- No explanations
- No markdown

Language for text placeholders: {language}

Return ONLY HTML + CSS.
"""

def seo_page_prompt(keyword, city, language):
    return f"""
You are an elite SEO content architect.

Create a FULL service page using the SAME design, CSS, fonts, colors and layout.

SEO REQUIREMENTS:
- NLP optimized
- Semantic SEO
- Local intent
- Google EEAT aligned
- Conversion focused

PAGE MUST INCLUDE:
- Meta title (CTR optimized)
- Meta description
- H1 with keyword + city
- H2/H3 semantic clusters
- Internal CTA blocks
- FAQ section
- JSON-LD LocalBusiness schema
- Clean readable HTML

TARGET:
Keyword: {keyword}
Location: {city}
Language: {language}

STRICT:
- Do NOT change layout or CSS
- Only replace content
- No explanations
- Return ONLY HTML
"""

# -----------------------------
# UI
# -----------------------------

api_key = st.text_input("OpenAI API Key", type="password")

language = st.selectbox(
    "Content Language",
    ["English", "Urdu", "Arabic", "Spanish", "Korean", "Filipino"]
)

city = st.text_input("Target City / Location")

homepage_img = st.file_uploader(
    "Upload Homepage Screenshot",
    type=["png", "jpg", "jpeg"]
)

keywords_raw = st.text_area(
    "Paste Keywords (one per line)",
    height=200
)

generate_btn = st.button("Generate SEO Pages")

# -----------------------------
# ENGINE
# -----------------------------

if generate_btn:
    if not api_key or not homepage_img or not keywords_raw:
        st.error("All fields are required.")
        st.stop()

    client = OpenAI(api_key=api_key)

    image = Image.open(homepage_img)
    img_b64 = img_to_base64(image)

    # STEP 1: DESIGN EXTRACTION
    with st.spinner("Cloning homepage design..."):
        layout_res = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": layout_prompt(language)},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_b64}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.2
        )

    base_html = layout_res.choices[0].message.content

    keywords = [k.strip() for k in keywords_raw.splitlines() if k.strip()]
    zip_buffer = io.BytesIO()

    # STEP 2: PAGE GENERATION
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for kw in keywords:
            with st.spinner(f"Generating page: {kw}"):
                page_res = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": "You generate enterprise-level SEO HTML pages."
                        },
                        {
                            "role": "user",
                            "content": base_html + "\n\n" + seo_page_prompt(
                                kw, city, language
                            )
                        }
                    ],
                    temperature=0.6
                )

                html = page_res.choices[0].message.content
                filename = clean_slug(kw) + ".html"
                zipf.writestr(filename, html)

    st.success("Pages generated successfully.")

    st.download_button(
        "Download HTML Pages (ZIP)",
        zip_buffer.getvalue(),
        "sitemorph-seo-pages.zip",
        "application/zip"
    )
