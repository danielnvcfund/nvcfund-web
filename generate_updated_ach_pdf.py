#!/usr/bin/env python3
"""
Script to generate an updated PDF version of the ACH Capabilities document
with the enhanced routing number information.
"""

import os
import weasyprint

def generate_pdf_from_html(html_path, pdf_path):
    """
    Generate a PDF from an HTML file
    
    Args:
        html_path (str): Path to the HTML file
        pdf_path (str): Path where the PDF should be saved
    """
    print(f"Generating PDF from {html_path} to {pdf_path}...")
    
    # Read the HTML content
    with open(html_path, 'r') as f:
        html_content = f.read()
    
    # Add page number CSS
    page_number_css = """
    @page {
        @bottom-right {
            content: "Page " counter(page) " of " counter(pages);
            font-family: Arial, sans-serif;
            font-size: 10pt;
            color: #666;
        }
    }
    """
    
    # Create an HTML string with the page number CSS
    html_with_page_numbers = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            {page_number_css}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    
    # Generate PDF
    html = weasyprint.HTML(string=html_with_page_numbers, base_url=os.path.dirname(html_path))
    html.write_pdf(pdf_path)
    
    print(f"PDF generated successfully: {pdf_path}")

def main():
    """Main function"""
    # Define paths
    html_path = "static/docs/ach_capabilities.html"
    pdf_path = "static/docs/ach_capabilities.pdf"
    
    # Ensure the output directory exists
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    
    # Generate the PDF
    generate_pdf_from_html(html_path, pdf_path)

if __name__ == "__main__":
    main()