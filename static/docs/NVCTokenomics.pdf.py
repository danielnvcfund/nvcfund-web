import os
from weasyprint import HTML
import tempfile

def generate_nvc_token_pdf():
    """
    Generate a PDF version of the NVCTokenomics document
    """
    # Get the absolute path to the HTML file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(current_dir, 'NVCTokenomics.html')
    pdf_path = os.path.join(current_dir, 'NVCTokenomics.pdf')
    
    # Convert the HTML to PDF
    HTML(html_path).write_pdf(pdf_path)
    
    print(f"PDF generated at {pdf_path}")
    return pdf_path

if __name__ == "__main__":
    generate_nvc_token_pdf()