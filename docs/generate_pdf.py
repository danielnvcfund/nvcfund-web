#!/usr/bin/env python3
"""
PDF Generator for NVC Banking Platform Documentation
This script converts HTML files to PDF format using WeasyPrint.
"""

import os
import sys
import weasyprint

def generate_pdf(html_file, pdf_file):
    """
    Generate a PDF file from an HTML file.
    
    Args:
        html_file (str): Path to the HTML file
        pdf_file (str): Path to the output PDF file
    """
    print(f"Converting {html_file} to {pdf_file}...")
    html = weasyprint.HTML(filename=html_file)
    html.write_pdf(pdf_file)
    print(f"PDF generated successfully: {pdf_file}")

if __name__ == "__main__":
    # Ensure we're in the docs directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Check if specific files are passed as arguments
    if len(sys.argv) > 2:
        html_file = sys.argv[1]
        pdf_file = sys.argv[2]
        generate_pdf(html_file, pdf_file)
    else:
        # Generate default PDFs
        generate_pdf("blockchain_vs_swift.html", "blockchain_vs_swift.pdf")
        generate_pdf("payment_operations_guide.html", "payment_operations_guide.pdf")
    
    print("All PDFs generated successfully.")