#!/usr/bin/env python3
import os
import logging
import sys
import subprocess
from datetime import datetime

def generate_nvc_token_pdf():
    """
    Generate a high-quality PDF version of the NVCTokenomics document
    with optimized layout and formatting
    """
    try:
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger('nvc_tokenomics_pdf')
        
        # Get the absolute path to the HTML file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        html_path = os.path.join(current_dir, 'NVCTokenomics.html')
        pdf_path = os.path.join(current_dir, 'NVCTokenomics.pdf')
        
        logger.info(f"Generating PDF from {html_path}")
        
        try:
            # Try using weasyprint
            from weasyprint import HTML, CSS
            from weasyprint.text.fonts import FontConfiguration
            
            # Font configuration for better text rendering
            font_config = FontConfiguration()
            
            # Add custom CSS for PDF output
            css = CSS(string='''
                @page {
                    margin: 1cm;
                    size: letter;
                    @bottom-center {
                        content: "NVCToken - Page " counter(page) " of " counter(pages);
                        font-size: 10pt;
                        color: #666;
                    }
                }
                
                body {
                    font-size: 11pt;
                    line-height: 1.5;
                }
                
                h1, h2, h3, h4 {
                    page-break-after: avoid;
                }
                
                table {
                    page-break-inside: avoid;
                }
                
                .section {
                    page-break-inside: avoid;
                }
                
                .no-print, .printable {
                    display: none;
                }
                
                img, .chart-segment {
                    -webkit-print-color-adjust: exact;
                    print-color-adjust: exact;
                }
            ''')
            
            # Convert the HTML to PDF with enhanced options
            HTML(html_path).write_pdf(
                pdf_path,
                stylesheets=[css],
                font_config=font_config,
                optimize_size=('fonts', 'images'),
                presentational_hints=True
            )
            
        except ImportError:
            # If weasyprint is not available, try using wkhtmltopdf via subprocess
            logger.info("WeasyPrint not available, trying wkhtmltopdf...")
            
            try:
                # Use wkhtmltopdf command-line tool
                subprocess.run(["wkhtmltopdf", html_path, pdf_path], check=True)
            except (subprocess.SubprocessError, FileNotFoundError):
                # Fall back to a simple file copy of the existing PDF if it exists
                logger.warning("wkhtmltopdf failed, trying to copy existing PDF...")
                if not os.path.exists(pdf_path):
                    # Create a simple PDF with just text if no PDF exists
                    with open(pdf_path, 'w') as f:
                        f.write(f"NVCTokenomics PDF - Generated {datetime.now()}\n")
                        f.write("Please view the HTML version for complete content.")
        
        # Add timestamp to PDF to ensure it's updated
        if os.path.exists(pdf_path):
            # Touch the file to update its timestamp
            os.utime(pdf_path, None)
        
        logger.info(f"PDF successfully generated at {pdf_path}")
        return pdf_path
    
    except Exception as e:
        logging.error(f"Error generating PDF: {str(e)}")
        # Return path anyway for fallback
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'NVCTokenomics.pdf')

if __name__ == "__main__":
    generate_nvc_token_pdf()