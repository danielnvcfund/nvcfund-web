#!/usr/bin/env python3
"""
Script to convert HTML documents to PDF
"""
import os
import sys
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

def convert_html_to_pdf(html_file, pdf_file):
    """
    Convert HTML file to PDF
    
    Args:
        html_file (str): Path to HTML file
        pdf_file (str): Path to output PDF file
    """
    print(f"Converting {html_file} to {pdf_file}...")
    
    # Ensure parent directory exists
    os.makedirs(os.path.dirname(pdf_file), exist_ok=True)
    
    # Configure fonts
    font_config = FontConfiguration()
    
    # Create PDF
    html = HTML(filename=html_file)
    
    # CSS for print
    css = CSS(string='''
        @page {
            size: A4;
            margin: 1.5cm;
        }
        body {
            font-family: Arial, sans-serif;
        }
        h1, h2, h3, h4 {
            margin-top: 1.5em;
            margin-bottom: 0.8em;
        }
        .d-print-none {
            display: none !important;
        }
    ''', font_config=font_config)
    
    # Write PDF
    html.write_pdf(pdf_file, stylesheets=[css], font_config=font_config)
    print(f"PDF created successfully: {pdf_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_html_to_pdf.py <html_file> <pdf_file>")
        sys.exit(1)
    
    html_file = sys.argv[1]
    pdf_file = sys.argv[2]
    
    convert_html_to_pdf(html_file, pdf_file)