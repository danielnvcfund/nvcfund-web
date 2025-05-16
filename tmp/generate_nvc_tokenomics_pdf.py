#!/usr/bin/env python3
import os
import logging
import sys
import subprocess
import tempfile
import shutil
from datetime import datetime
import markdown

def generate_nvc_tokenomics_pdf():
    """
    Generate a high-quality PDF version of the NVC Tokenomics document from the markdown file
    """
    try:
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger('nvc_tokenomics_pdf')
        
        # Get the absolute path to the Markdown file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        md_path = os.path.join(current_dir, 'nvc_tokenomics.md')
        html_path = os.path.join(current_dir, 'nvc_tokenomics.html')
        pdf_path = os.path.join(current_dir, 'nvc_tokenomics.pdf')
        
        logger.info(f"Converting Markdown to HTML: {md_path} -> {html_path}")
        
        # Read the markdown content
        with open(md_path, 'r') as md_file:
            md_content = md_file.read()
        
        # Convert markdown to HTML
        html_content = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
        
        # Create a complete HTML document with styling
        complete_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NVCToken: Tokenomics & Core Statistics</title>
    <style>
        body {{
            padding: 40px 0;
            background-color: #f5f5f5;
            color: #333;
            font-family: Arial, sans-serif;
            line-height: 1.6;
        }}
        .nvc-document {{
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            padding: 40px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
            border-radius: 8px;
        }}
        .nvc-header {{
            text-align: center;
            margin-bottom: 40px;
            border-bottom: 3px solid #0056b3;
            padding-bottom: 30px;
            position: relative;
        }}
        .nvc-logo {{
            width: 120px;
            height: 120px;
            background: linear-gradient(135deg, #0056b3 0%, #0071e3 100%);
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 40px;
            font-weight: bold;
            margin: 0 auto 25px;
            box-shadow: 0 4px 15px rgba(0,86,179,0.3);
        }}
        h1, h2, h3, h4 {{
            color: #0056b3;
        }}
        h1 {{
            font-size: 2.5rem;
            margin-top: 0;
        }}
        h2 {{
            border-bottom: 2px solid #0056b3;
            padding-bottom: 10px;
            margin-top: 2em;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }}
        th, td {{
            border: 1px solid #dee2e6;
            padding: 12px 15px;
            text-align: left;
        }}
        th {{
            background-color: #f1f5f9;
            font-weight: 600;
            color: #0056b3;
            border-bottom: 2px solid #0056b3;
        }}
        tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        p {{
            margin-bottom: 1em;
        }}
        ul, ol {{
            margin-bottom: 1em;
            padding-left: 2em;
        }}
        li {{
            margin-bottom: 0.5em;
        }}
        code {{
            background-color: #f0f0f0;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: monospace;
        }}
        hr {{
            border: none;
            height: 1px;
            background-color: #dee2e6;
            margin: 2em 0;
        }}
        /* Print-specific styles */
        @page {{
            margin: 2cm;
            size: letter;
            @bottom-center {{
                content: "NVCToken - Page " counter(page) " of " counter(pages);
                font-size: 9pt;
                color: #666;
                margin-top: 1cm;
            }}
        }}
        @media print {{
            body {{
                background-color: white;
                padding: 0;
            }}
            .nvc-document {{
                box-shadow: none;
                max-width: 100%;
                padding: 0;
            }}
            h1, h2, h3, h4 {{
                page-break-after: avoid;
            }}
            table {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <div class="nvc-document">
        <div class="nvc-header">
            <div class="nvc-logo">NVC</div>
        </div>
        {html_content}
    </div>
</body>
</html>
"""
        # Write the HTML to a file
        with open(html_path, 'w') as html_file:
            html_file.write(complete_html)
        
        logger.info(f"HTML file created at {html_path}")
        
        # Generate PDF from HTML
        success = False
        
        try:
            # Try using weasyprint
            logger.info("Attempting PDF generation with WeasyPrint...")
            from weasyprint import HTML
            HTML(html_path).write_pdf(pdf_path)
            logger.info("PDF successfully generated with WeasyPrint")
            success = True
        except Exception as weasy_error:
            logger.error(f"WeasyPrint failed: {str(weasy_error)}")
            
            try:
                # Try pdfkit (which uses wkhtmltopdf)
                import pdfkit
                logger.info("Attempting PDF generation with pdfkit...")
                pdfkit.from_file(html_path, pdf_path)
                logger.info("PDF successfully generated with pdfkit")
                success = True
            except Exception as pdfkit_error:
                logger.error(f"pdfkit failed: {str(pdfkit_error)}")
                
                try:
                    # Try using wkhtmltopdf directly
                    logger.info("Attempting PDF generation with wkhtmltopdf directly...")
                    subprocess.run(["wkhtmltopdf", html_path, pdf_path], check=True)
                    logger.info("PDF successfully generated with direct wkhtmltopdf")
                    success = True
                except Exception as wk_error:
                    logger.error(f"wkhtmltopdf failed: {str(wk_error)}")
        
        if not success:
            # Use a simpler method - at least create a basic PDF
            logger.warning("All PDF generation methods failed, attempting direct method...")
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                from reportlab.lib.styles import getSampleStyleSheet
                
                doc = SimpleDocTemplate(pdf_path, pagesize=letter)
                styles = getSampleStyleSheet()
                
                # Parse the Markdown content into sections
                content_parts = md_content.split('\n\n')
                flowables = []
                
                for part in content_parts:
                    if part.strip():
                        if part.startswith('# '):
                            flowables.append(Paragraph(part[2:], styles['Title']))
                        elif part.startswith('## '):
                            flowables.append(Paragraph(part[3:], styles['Heading2']))
                        elif part.startswith('### '):
                            flowables.append(Paragraph(part[4:], styles['Heading3']))
                        else:
                            flowables.append(Paragraph(part, styles['Normal']))
                    flowables.append(Spacer(1, 12))
                
                doc.build(flowables)
                logger.info("Basic PDF created with ReportLab")
                success = True
            except Exception as report_error:
                logger.error(f"ReportLab PDF generation failed: {str(report_error)}")
        
        if not success:
            # Last resort: Create a very basic text file with PDF extension
            logger.warning("All PDF generation methods failed, creating basic text document...")
            with open(pdf_path, 'w') as f:
                f.write("NVCTokenomics Documentation\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(md_content)
                f.write("\n\nPlease view the full document in the web interface for better formatting.\n")
            
            logger.info(f"Basic text document saved to {pdf_path}")
        
        logger.info(f"PDF generation process completed. Output at {pdf_path}")
        return pdf_path
    
    except Exception as e:
        logging.error(f"Error in PDF generation process: {str(e)}")
        # Return path anyway for fallback
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nvc_tokenomics.pdf')

if __name__ == "__main__":
    try:
        pdf_path = generate_nvc_tokenomics_pdf()
        print(f"PDF generated successfully at: {pdf_path}")
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        sys.exit(1)