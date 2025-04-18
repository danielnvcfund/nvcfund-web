import os
import logging
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

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
        
        logger.info(f"PDF successfully generated at {pdf_path}")
        return pdf_path
    
    except Exception as e:
        logging.error(f"Error generating PDF: {str(e)}")
        raise

if __name__ == "__main__":
    generate_nvc_token_pdf()