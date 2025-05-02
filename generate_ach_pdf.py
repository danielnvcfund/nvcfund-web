import os
from weasyprint import HTML

def generate_pdf():
    print("Generating ACH capabilities PDF...")
    
    # Define input and output paths
    html_path = "static/docs/ach_capabilities.html"
    pdf_path = "static/docs/ach_capabilities.pdf"
    
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