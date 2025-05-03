"""
Script to check for Telex code in database
"""
from main import app
from models import FinancialInstitution

def check_telex_code():
    """Check Telex code for our bank"""
    with app.app_context():
        # Try to find our institution
        institution = FinancialInstitution.query.filter_by(name='NVC Fund Bank').first()
        if institution:
            print(f"Institution: {institution.name}")
            print(f"SWIFT/BIC Code: {institution.swift_code}")
            print(f"Routing number: {institution.routing_number}")
            print(f"Type: {institution.institution_type}")
            print(f"Country: {institution.country}")
        else:
            print("NVC Fund Bank not found. Looking for other institutions...")
            institutions = FinancialInstitution.query.all()
            for inst in institutions:
                print(f"- {inst.name}: SWIFT Code: {inst.swift_code}")

if __name__ == "__main__":
    check_telex_code()