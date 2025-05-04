#!/usr/bin/env python3
"""
Generate PDF for NVC Acquisition Strategy
"""
import os
import sys
from weasyprint import HTML
import weasyprint.text.fonts

def generate_pdf():
    print("Generating NVC Acquisition Strategy PDF...")
    
    # Define input and output paths - adjust paths based on current working directory
    html_path = "../static/docs/nvc_acquisition_strategy.html"
    pdf_path = "../static/docs/nvc_acquisition_strategy.pdf"
    
    # Check if HTML file exists
    if not os.path.exists(html_path):
        print(f"ERROR: HTML file not found at {html_path}")
        return False
    
    try:
        # Create pdf directory if it doesn't exist
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        
        # Generate PDF from HTML
        HTML(html_path).write_pdf(pdf_path)
        
        # Verify PDF was created
        if os.path.exists(pdf_path):
            print(f"SUCCESS: PDF generated successfully at {pdf_path}")
            return True
        else:
            print(f"ERROR: PDF generation failed. File not found at {pdf_path}")
            return False
            
    except Exception as e:
        print(f"ERROR: Failed to generate PDF: {str(e)}")
        return False

if __name__ == "__main__":
    generate_pdf()