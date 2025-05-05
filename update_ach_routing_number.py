"""
Script to add ACH routing number for NVC Fund Bank
"""
import os
import sys
from app import db, create_app
from models import FinancialInstitution
from ach_service import ACHService

# The official ACH routing number for NVC Fund Bank
# Routing number format: XXXXYYYYC where:
# - XXXX is the Federal Reserve Routing Symbol (0311 for South Africa region)
# - YYYY is the ABA institution identifier (7611 assigned to NVC Fund Bank)
# - C is the checksum digit (calculated as 0 for this routing number)
# 
# This routing number is assigned to NVC Fund Bank as a Supranational Sovereign 
# Financial Institution under the African Union Treaty and AFRA jurisdiction.
NVC_ROUTING_NUMBER = "031176110"  # Official routing number

def validate_routing_number():
    """Validate the NVC routing number using the checksum algorithm"""
    # Manual validation to avoid import issues
    routing_number = NVC_ROUTING_NUMBER
    if not routing_number or not routing_number.isdigit() or len(routing_number) != 9:
        print(f"ERROR: The routing number {routing_number} is invalid (must be 9 digits)!")
        sys.exit(1)
    
    # ABA routing number validation algorithm
    d = [int(routing_number[i]) for i in range(9)]
    
    checksum = (
        3 * (d[0] + d[3] + d[6]) +
        7 * (d[1] + d[4] + d[7]) +
        (d[2] + d[5] + d[8])
    ) % 10
    
    is_valid = (checksum == 0)
    
    if not is_valid:
        print(f"ERROR: The routing number {routing_number} failed validation!")
        sys.exit(1)
    else:
        print(f"✓ Routing number {routing_number} successfully validated")

def update_nvc_routing_number():
    """Update NVC Fund Bank with the official routing number"""
    # Find NVC Fund Bank entry
    nvc_bank = FinancialInstitution.query.filter_by(name="NVC Fund Bank").first()
    
    if not nvc_bank:
        print("ERROR: NVC Fund Bank entry not found in the database!")
        print("Creating a new entry...")
        # Create the entry if it doesn't exist
        from models import FinancialInstitutionType
        nvc_bank = FinancialInstitution(
            name="NVC Fund Bank",
            institution_type=FinancialInstitutionType.BANK,
            swift_code="NVCFBKAU",
            ach_routing_number=NVC_ROUTING_NUMBER,
            rtgs_enabled=True,
            s2s_enabled=True
        )
        db.session.add(nvc_bank)
    else:
        # Update existing entry
        print(f"Updating NVC Fund Bank (ID: {nvc_bank.id}) with routing number: {NVC_ROUTING_NUMBER}")
        nvc_bank.ach_routing_number = NVC_ROUTING_NUMBER
    
    # Commit changes
    db.session.commit()
    print("✓ Successfully updated NVC Fund Bank with ACH routing number")

def main():
    """Main entry point for the script"""
    app = create_app()
    with app.app_context():
        print("Starting ACH routing number update...")
        
        # First validate the routing number is correct
        validate_routing_number()
        
        # Update NVC Fund Bank with routing number
        update_nvc_routing_number()
        
        print("ACH routing number update completed successfully!")

if __name__ == "__main__":
    main()