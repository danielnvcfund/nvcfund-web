#!/usr/bin/env python3
"""
Test script to generate a PDF receipt for a wire transfer
"""

import sys
import os
from main import app
from generate_wire_transfer_pdf import generate_wire_transfer_pdf
from models import db, WireTransfer

def main():
    """
    Main function to test PDF generation
    """
    if len(sys.argv) < 2:
        print("Usage: python test_pdf_generation.py <wire_transfer_id>")
        sys.exit(1)
    
    try:
        wire_transfer_id = int(sys.argv[1])
    except ValueError:
        print("Error: wire_transfer_id must be an integer")
        sys.exit(1)
    
    print(f"Generating PDF for wire transfer ID: {wire_transfer_id}")
    
    with app.app_context():
        # Verify the wire transfer exists
        wire_transfer = WireTransfer.query.get(wire_transfer_id)
        if not wire_transfer:
            print(f"Error: Wire transfer with ID {wire_transfer_id} not found")
            sys.exit(1)
            
        print(f"Found wire transfer: {wire_transfer.reference_number}")
        
        # Generate the PDF
        pdf_bytes, filename = generate_wire_transfer_pdf(wire_transfer_id)
        
        if not pdf_bytes:
            print(f"Error: {filename}")
            sys.exit(1)
        
        output_file = f"./{filename}"
        with open(output_file, 'wb') as f:
            f.write(pdf_bytes)
        
        print(f"PDF successfully generated: {output_file}")
        
        # Get absolute path
        abs_path = os.path.abspath(output_file)
        print(f"Absolute path: {abs_path}")

if __name__ == "__main__":
    main()