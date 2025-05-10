#!/usr/bin/env python3
"""
Generate a PDF document about the NVC Banking Platform Exchange
"""
import markdown
import os
from weasyprint import HTML, CSS
from datetime import datetime

# Configuration
OUTPUT_DIR = 'static/docs'
MD_FILE = 'docs/nvc_exchange_whitepaper.md'
PDF_FILENAME = 'NVC_Banking_Platform_Exchange.pdf'
STATIC_DIR = 'static'

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Read markdown content
with open(MD_FILE, 'r') as f:
    md_content = f.read()

# Convert Markdown to HTML
html_content = markdown.markdown(
    md_content, 
    extensions=['tables', 'fenced_code', 'codehilite', 'nl2br']
)

# Add CSS styling
css_content = """
@page {
    margin: 1.5cm;
    @top-center {
        content: "NVC Banking Platform Exchange";
        font-family: Arial, sans-serif;
        font-size: 9pt;
        color: #666;
    }
    @bottom-center {
        content: "Page " counter(page) " of " counter(pages);
        font-family: Arial, sans-serif;
        font-size: 9pt;
        color: #666;
    }
}
body {
    font-family: Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.5;
    color: #333;
}
h1 {
    font-size: 24pt;
    color: #0052b4;
    text-align: center;
    margin-top: 2cm;
    margin-bottom: 0.5cm;
}
h2 {
    font-size: 16pt;
    color: #0052b4;
    margin-top: 1cm;
    margin-bottom: 0.5cm;
    padding-bottom: 0.2cm;
    border-bottom: 1pt solid #ddd;
}
h3 {
    font-size: 13pt;
    color: #333;
    margin-top: 0.8cm;
    margin-bottom: 0.3cm;
}
hr {
    border: none;
    border-top: 1pt solid #ddd;
    margin: 1cm 0;
}
p {
    margin-bottom: 0.5cm;
    text-align: justify;
}
li {
    margin-bottom: 0.2cm;
}
a {
    color: #0052b4;
    text-decoration: none;
}
.footer {
    text-align: center;
    font-size: 9pt;
    color: #666;
    margin-top: 1cm;
}
"""

# Create full HTML document
full_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>NVC Banking Platform Exchange</title>
    <style>
    {css_content}
    </style>
</head>
<body>
    {html_content}
    <div class="footer">
        <p>Document generated on {datetime.now().strftime('%B %d, %Y')}</p>
        <p>© 2025 NVC Fund Bank. All rights reserved.</p>
    </div>
</body>
</html>
"""

# Generate PDF
pdf_path = os.path.join(OUTPUT_DIR, PDF_FILENAME)
HTML(string=full_html).write_pdf(
    pdf_path,
    stylesheets=[CSS(string=css_content)],
    optimize_size=('fonts', 'images')
)

print(f"PDF generated successfully: {pdf_path}")