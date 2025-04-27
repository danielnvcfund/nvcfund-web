"""
Script to add government agencies as vendors in the payment system
"""

import os
import sys
from datetime import datetime
import json
import secrets

from app import create_app, db
from models import Vendor
from utils import generate_random_id

def add_government_agencies():
    """Add government agencies as vendors"""
    
    # List of government agencies to add
    agencies = [
        {
            "name": "Internal Revenue Service (IRS)",
            "contact_name": "Taxpayer Service",
            "email": "tax.support@irs.gov",
            "phone": "800-829-1040",
            "address": "Internal Revenue Service Center, Austin, TX 73301",
            "website": "https://www.irs.gov",
            "payment_terms": "Due on Receipt",
            "bank_name": "U.S. Treasury",
            "payment_method": "ach",
            "tax_id": "53-0204542"
        },
        {
            "name": "United States Treasury",
            "contact_name": "Treasury Department",
            "email": "treasury.support@ustreas.gov",
            "phone": "202-622-2000",
            "address": "1500 Pennsylvania Avenue, NW, Washington, D.C. 20220",
            "website": "https://home.treasury.gov",
            "payment_terms": "Due on Receipt",
            "bank_name": "Federal Reserve Bank",
            "payment_method": "wire",
            "tax_id": "53-0204542"
        },
        {
            "name": "Texas Secretary of State",
            "contact_name": "Business Filing Department",
            "email": "secretary@sos.texas.gov",
            "phone": "512-463-5555",
            "address": "P.O. Box 13697, Austin, TX 78711",
            "website": "https://www.sos.state.tx.us",
            "payment_terms": "Due on Receipt",
            "bank_name": "State Treasury Bank",
            "payment_method": "ach",
            "tax_id": "74-6000089"
        },
        {
            "name": "Texas Comptroller of Public Accounts",
            "contact_name": "Tax Payment Processing",
            "email": "tax.help@cpa.texas.gov",
            "phone": "800-252-5555",
            "address": "111 E. 17th Street, Austin, TX 78774",
            "website": "https://comptroller.texas.gov",
            "payment_terms": "Due on Receipt",
            "bank_name": "Texas State Treasury",
            "payment_method": "ach",
            "tax_id": "74-6000089"
        }
    ]
    
    app = create_app()
    
    with app.app_context():
        # Check if agencies already exist
        for agency_data in agencies:
            existing_vendor = Vendor.query.filter_by(name=agency_data["name"]).first()
            
            if existing_vendor:
                print(f"Agency '{agency_data['name']}' already exists. Skipping.")
                continue
            
            # Generate a vendor ID
            vendor_id = generate_random_id("GOV")
            
            # Create vendor object
            vendor = Vendor(
                vendor_id=vendor_id,
                name=agency_data["name"],
                contact_name=agency_data["contact_name"],
                email=agency_data["email"],
                phone=agency_data["phone"],
                address=agency_data["address"],
                website=agency_data["website"],
                payment_terms=agency_data["payment_terms"],
                bank_name=agency_data["bank_name"],
                payment_method=agency_data["payment_method"],
                tax_id=agency_data["tax_id"],
                is_active=True
            )
            
            # Add metadata
            metadata = {"vendor_type": "government_agency"}
            vendor.metadata_json = json.dumps(metadata)
            
            # Add to database
            db.session.add(vendor)
            print(f"Added government agency: {agency_data['name']}")
        
        # Commit changes
        db.session.commit()
        print("Government agencies added successfully.")

if __name__ == "__main__":
    add_government_agencies()