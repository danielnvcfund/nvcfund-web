#!/usr/bin/env python3
"""
Generate PDF version of the SWIFT BIC Registration Guide
"""
import os
import sys
import logging
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_pdf():
    """Generate PDF from HTML file"""
    try:
        # Set up file paths
        current_dir = os.path.dirname(os.path.abspath(__file__))
        html_path = os.path.join(current_dir, 'swift_bic_registration_guide.html')
        pdf_path = os.path.join(current_dir, 'swift_bic_registration_guide.pdf')
        
        # Check if HTML file exists
        if not os.path.exists(html_path):
            logger.error(f"HTML file not found: {html_path}")
            return False
        
        # Set up font configuration
        font_config = FontConfiguration()
        
        # Generate PDF
        logger.info(f"Generating PDF from {html_path}")
        html = HTML(filename=html_path)
        css = CSS(string='''
            @page {
                size: letter;
                margin: 1.5cm;
                @top-center {
                    content: "SWIFT BIC Registration Guide";
                    font-size: 9pt;
                    color: #666;
                }
                @bottom-center {
                    content: "Page " counter(page) " of " counter(pages);
                    font-size: 9pt;
                    color: #666;
                }
            }
        ''', font_config=font_config)
        
        html.write_pdf(pdf_path, stylesheets=[css], font_config=font_config)
        
        # Check if PDF was created
        if os.path.exists(pdf_path):
            logger.info(f"PDF successfully generated: {pdf_path}")
            return True
        else:
            logger.error("PDF generation failed")
            return False
            
    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        return False

if __name__ == "__main__":
    success = generate_pdf()
    sys.exit(0 if success else 1)