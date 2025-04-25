import os
import markdown
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

def convert_markdown_to_pdf(markdown_file, output_pdf):
    """
    Convert a Markdown file to PDF
    
    Args:
        markdown_file: Path to the markdown file
        output_pdf: Path where the PDF will be saved
    """
    # Read the markdown file
    with open(markdown_file, 'r') as f:
        md_text = f.read()
    
    # Convert markdown to HTML
    html = markdown.markdown(md_text, extensions=['tables', 'nl2br', 'fenced_code'])
    
    # Add some styling
    styled_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <title>NVC Electronic Data Interchange Guide</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 2cm;
            color: #333;
        }}
        h1, h2, h3, h4 {{
            color: #1a3b5d;
            margin-top: 1.5em;
        }}
        h1 {{
            border-bottom: 2px solid #1a3b5d;
            padding-bottom: 10px;
            text-align: center;
            font-size: 24pt;
        }}
        h2 {{
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
        }}
        code {{
            background-color: #f5f5f5;
            padding: 2px 4px;
            border-radius: 4px;
            font-family: monospace;
        }}
        pre {{
            background-color: #f5f5f5;
            padding: 1em;
            border-radius: 5px;
            overflow-x: auto;
            font-family: monospace;
            font-size: 9pt;
            page-break-inside: avoid;
            width: 100%;
            text-align: center;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
        }}
        th {{
            background-color: #f0f0f0;
            text-align: left;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        a {{
            color: #0066cc;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        .footer {{
            margin-top: 2em;
            border-top: 1px solid #ddd;
            padding-top: 1em;
            text-align: center;
            font-size: 0.9em;
            color: #666;
        }}
        @page {{
            size: letter;
            margin: 1.5cm;
            @bottom-center {{
                content: "Page " counter(page) " of " counter(pages);
                font-size: 9pt;
            }}
        }}
        /* Specific style for the architecture diagram */
        .architecture-diagram {{
            page-break-inside: avoid;
            text-align: center;
            margin: 0 auto;
        }}
    </style>
    </head>
    <body>
    {html.replace('### NVC Global EDI Architecture Overview', '<h3 class="architecture-diagram">NVC Global EDI Architecture Overview</h3>')}
    <div class="footer">
        © 2025 NVC Global Banking Platform. All rights reserved.
    </div>
    </body>
    </html>
    """
    
    # Configure fonts
    font_config = FontConfiguration()
    
    # Convert HTML to PDF
    HTML(string=styled_html).write_pdf(
        output_pdf,
        stylesheets=[],
        font_config=font_config
    )
    
    print(f"Successfully converted {markdown_file} to {output_pdf}")

if __name__ == "__main__":
    # Set file paths
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    markdown_file = os.path.join(current_dir, 'docs', 'edi_guide.md')
    output_pdf = os.path.join(current_dir, 'docs', 'nvc_electronic_data_interchange_guide.pdf')
    
    # Convert markdown to PDF
    convert_markdown_to_pdf(markdown_file, output_pdf)