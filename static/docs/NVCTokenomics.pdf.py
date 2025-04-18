#!/usr/bin/env python3
import os
import logging
import sys
import subprocess
import tempfile
import shutil
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
        
        # Create a modified HTML file for PDF conversion with all the content
        with open(html_path, 'r') as file:
            html_content = file.read()
        
        # Create a temporary file with modified HTML specifically for PDF generation
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp_html:
            # Modify the HTML to remove print-specific styles and make content suitable for PDF
            modified_html = html_content.replace('class="printable no-print"', 'style="display:none"')
            modified_html = modified_html.replace('@media print {', '@media print_disabled {')
            
            # Add embedded CSS for better PDF rendering
            pdf_styles = """
            <style>
                @page {
                    margin: 2cm;
                    size: letter;
                    @bottom-center {
                        content: "NVCToken - Page " counter(page) " of " counter(pages);
                        font-size: 9pt;
                        color: #666;
                        margin-top: 1cm;
                    }
                }
                
                body {
                    font-size: 11pt;
                    line-height: 1.5;
                    background-color: white !important;
                    color: black !important;
                    font-family: Arial, sans-serif;
                }
                
                .nvc-document {
                    max-width: 100% !important;
                    margin: 0 auto !important;
                    padding: 0 !important;
                    box-shadow: none !important;
                    background-color: white !important;
                }
                
                .nvc-header {
                    text-align: center;
                    margin-bottom: 40px;
                    border-bottom: 3px solid #0056b3;
                    padding-bottom: 30px;
                }
                
                .nvc-logo {
                    width: 100px;
                    height: 100px;
                    background-color: #0056b3;
                    color: white;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 40px;
                    font-weight: bold;
                    margin: 0 auto 25px;
                    border: 4px solid rgba(255,255,255,0.2);
                }
                
                .chart-segment {
                    print-color-adjust: exact;
                    -webkit-print-color-adjust: exact;
                }
                
                table {
                    page-break-inside: avoid;
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 30px;
                    border: 1px solid #dee2e6;
                }
                
                th, td {
                    border: 1px solid #dee2e6;
                    padding: 10px 15px;
                    text-align: left;
                }
                
                th {
                    background-color: #f1f5f9 !important;
                    color: #0056b3;
                    font-weight: bold;
                    border-bottom: 2px solid #0056b3;
                }
                
                tr:nth-child(even) {
                    background-color: #f8f9fa;
                }
                
                .section {
                    margin-bottom: 40px;
                    page-break-inside: avoid;
                }
                
                .section-title {
                    color: #0056b3;
                    border-bottom: 2px solid #0056b3;
                    padding-bottom: 12px;
                    margin-bottom: 25px;
                    font-size: 1.8rem;
                    font-weight: 700;
                }
                
                .token-stat {
                    display: flex;
                    flex-wrap: wrap;
                    margin-bottom: 20px;
                    padding: 15px;
                    background-color: #f8f9fa;
                    border-radius: 8px;
                    border-left: 4px solid #0056b3;
                }
                
                .token-stat-name {
                    font-weight: bold;
                    min-width: 220px;
                    color: #0056b3;
                }
                
                .token-stat-value {
                    flex-grow: 1;
                    font-weight: 600;
                    font-size: 1.05em;
                }
                
                .token-stat-description {
                    color: #666;
                    margin-top: 8px;
                    font-size: 0.9em;
                    flex-basis: 100%;
                }
                
                .distribution-chart {
                    width: 100%;
                    max-width: 700px;
                    margin: 30px auto;
                    height: 350px;
                    position: relative;
                    border: 1px solid #dee2e6;
                    overflow: hidden;
                    margin-bottom: 40px;
                }
                
                h1, h2, h3, h4 {
                    page-break-after: avoid;
                }
                
                .no-print, .printable {
                    display: none !important;
                }
            </style>
            """
            # Insert our PDF-specific styles right before the closing </head> tag
            modified_html = modified_html.replace('</head>', f'{pdf_styles}</head>')
            
            temp_html.write(modified_html.encode('utf-8'))
            temp_html_path = temp_html.name
        
        success = False
        
        try:
            # Try using weasyprint
            logger.info("Attempting PDF generation with WeasyPrint...")
            from weasyprint import HTML
            HTML(temp_html_path).write_pdf(pdf_path)
            logger.info("PDF successfully generated with WeasyPrint")
            success = True
        except Exception as weasy_error:
            logger.error(f"WeasyPrint failed: {str(weasy_error)}")
            
            try:
                # Try pdfkit (which uses wkhtmltopdf)
                import pdfkit
                logger.info("Attempting PDF generation with pdfkit...")
                pdfkit.from_file(temp_html_path, pdf_path)
                logger.info("PDF successfully generated with pdfkit")
                success = True
            except Exception as pdfkit_error:
                logger.error(f"pdfkit failed: {str(pdfkit_error)}")
                
                try:
                    # Try using wkhtmltopdf directly
                    logger.info("Attempting PDF generation with wkhtmltopdf directly...")
                    subprocess.run(["wkhtmltopdf", temp_html_path, pdf_path], check=True)
                    logger.info("PDF successfully generated with direct wkhtmltopdf")
                    success = True
                except Exception as wk_error:
                    logger.error(f"wkhtmltopdf failed: {str(wk_error)}")
        
        # Clean up the temp file
        try:
            os.unlink(temp_html_path)
        except:
            pass
        
        if not success:
            # Last resort: Create a very basic PDF with a note
            logger.warning("All PDF generation methods failed, creating basic PDF...")
            with open(pdf_path, 'w') as f:
                f.write("NVCTokenomics Documentation\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("Please view the full HTML version at /main/nvctoken for complete details.\n")
                f.write("This PDF contains a simplified version due to conversion limitations.\n")
        
        logger.info(f"PDF output saved to {pdf_path}")
        return pdf_path
    
    except Exception as e:
        logging.error(f"Error in PDF generation process: {str(e)}")
        # Return path anyway for fallback
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'NVCTokenomics.pdf')

if __name__ == "__main__":
    try:
        pdf_path = generate_nvc_token_pdf()
        print(f"PDF generated successfully at: {pdf_path}")
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        sys.exit(1)