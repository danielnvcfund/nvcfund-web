"""
Script to generate a PDF for the NVC API Infrastructure document.
"""

import os
from fpdf import FPDF

def generate_api_infrastructure_pdf():
    """Generate a PDF for the NVC API Infrastructure document."""
    pdf = FPDF()
    pdf.add_page()
    
    # Set document information
    pdf.set_title("NVC Banking Platform API Infrastructure")
    pdf.set_author("NVC Banking Platform")
    
    # Add title
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "NVC Banking Platform API Infrastructure", 0, 1, "C")
    pdf.cell(0, 10, "Strategic Integration with the Financial Ecosystem", 0, 1, "C")
    pdf.ln(5)
    
    # What is an API section
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "What is an API?", 0, 1)
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 8, "API (Application Programming Interface) serves as a structured communication bridge that allows different software systems to interact with each other. In the context of the NVC Banking Platform, APIs enable secure, standardized methods for:")
    
    # bullet points
    pdf.ln(2)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Exchanging financial data", 0, 1)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Processing transactions", 0, 1)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Integrating with external services", 0, 1)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Automating financial operations", 0, 1)
    pdf.ln(5)
    
    # Strategic Importance section
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Strategic Importance of APIs in the NVC Banking Platform", 0, 1)
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 8, "The NVC Banking Platform's API infrastructure is central to its functioning as a global financial hub for several key reasons:")
    pdf.ln(2)
    
    # Section 1
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "1. Interbank Communication", 0, 1)
    pdf.set_font("Arial", "", 12)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Enables direct interaction with correspondent banks worldwide", 0, 1)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Facilitates real-time settlement using standardized messaging formats", 0, 1)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Supports SWIFT message types (MT103, MT202, MT760) for international transfers", 0, 1)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Provides RTGS (Real-Time Gross Settlement) integration with central banks", 0, 1)
    pdf.ln(2)
    
    # Section 2
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "2. Payment System Integration", 0, 1)
    pdf.set_font("Arial", "", 12)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.multi_cell(0, 8, "Creates seamless connections with multiple payment gateways including traditional card processors, digital wallets, ACH networks, SWIFT networks, and blockchain settlement networks")
    pdf.ln(2)
    
    # Section 3
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "3. Stablecoin Ecosystem Support", 0, 1)
    pdf.set_font("Arial", "", 12)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Powers NVCT stablecoin operations with 1:1 USD peg", 0, 1)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Enables currency exchange between NVCT and other currencies (fiat and crypto)", 0, 1)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Supports integration with AFD1 liquidity pool backed by gold value", 0, 1)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Facilitates multi-currency settlement using stablecoins as intermediaries", 0, 1)
    pdf.ln(2)
    
    # Add a new page for the rest of the content
    pdf.add_page()
    
    # Section 4
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "4. Financial Institution Connectivity", 0, 1)
    pdf.set_font("Arial", "", 12)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Provides partner banks with secure access to NVC's settlement infrastructure", 0, 1)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Enables institutional clients to initiate high-value transfers programmatically", 0, 1)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Supports KYC/AML information sharing between trusted institutions", 0, 1)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Ensures regulatory compliance in cross-border transactions", 0, 1)
    pdf.ln(2)
    
    # Section 5
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "5. Enterprise Treasury Integration", 0, 1)
    pdf.set_font("Arial", "", 12)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Allows corporate treasuries to connect directly to banking services", 0, 1)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Supports automated payroll, accounts payable, and accounts receivable functions", 0, 1)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Enables programmatic access to currency exchange and hedging operations", 0, 1)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Provides real-time reporting and reconciliation capabilities", 0, 1)
    pdf.ln(5)
    
    # Technical Implementation section
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Technical Implementation in the NVC Platform", 0, 1)
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 8, "The API architecture in the NVC Banking Platform follows industry best practices:")
    pdf.ln(2)
    
    # Technical sections
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "1. Security-First Design", 0, 1)
    pdf.set_font("Arial", "", 12)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "JWT-based authentication for all API endpoints", 0, 1)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Role-based permissions with granular access controls", 0, 1)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "End-to-end encryption for sensitive data", 0, 1)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "API key rotation and management system", 0, 1)
    pdf.ln(2)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "2. Comprehensive Documentation", 0, 1)
    pdf.set_font("Arial", "", 12)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Detailed API reference guides for integration partners", 0, 1)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Interactive API documentation with request/response examples", 0, 1)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Sandbox environment for testing integrations", 0, 1)
    pdf.ln(2)
    
    # Add a new page for the final section
    pdf.add_page()
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "3. Flexible Integration Methods", 0, 1)
    pdf.set_font("Arial", "", 12)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "RESTful API endpoints for modern integrations", 0, 1)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Support for legacy SOAP interfaces where required", 0, 1)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Webhook capabilities for event-driven architecture", 0, 1)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Server-to-server secure communication channels", 0, 1)
    pdf.ln(2)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "4. High-Availability Infrastructure", 0, 1)
    pdf.set_font("Arial", "", 12)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Distributed API gateway architecture", 0, 1)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Load-balanced endpoints for handling high transaction volumes", 0, 1)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Geographic redundancy for global accessibility", 0, 1)
    pdf.cell(10, 8, chr(127), 0, 0)
    pdf.cell(0, 8, "Rate limiting and throttling to prevent abuse", 0, 1)
    pdf.ln(5)
    
    # Financial Ecosystem Impact
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Financial Ecosystem Impact", 0, 1)
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 8, "The API capabilities of the NVC Banking Platform create a powerful network effect:")
    pdf.ln(2)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(60, 8, "Banking-as-a-Service:", 0, 0)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, "Enables smaller financial institutions to leverage NVC's global infrastructure", 0, 1)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(60, 8, "Open Banking Compliance:", 0, 0)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, "Supports regulatory frameworks for financial data sharing", 0, 1)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(60, 8, "Financial Inclusion:", 0, 0)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, "Allows fintech innovators to build on top of NVC's platform", 0, 1)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(60, 8, "Cross-Border Efficiency:", 0, 0)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, "Reduces friction in international transactions through standardized interfaces", 0, 1)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(60, 8, "Blockchain Integration:", 0, 0)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, "Bridges traditional and decentralized finance through unified API access", 0, 1)
    pdf.ln(5)
    
    # Conclusion
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 8, "By prioritizing robust API infrastructure, the NVC Banking Platform positions itself as a connectivity hub in the global financial ecosystem, enabling seamless interaction between traditional banking systems, emerging fintech solutions, and blockchain networks.")
    
    # Footer
    pdf.ln(15)
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 5, "NVC Banking Platform © 2025 | Confidential Document", 0, 1, "C")
    
    # Create the directory if it doesn't exist
    os.makedirs("static/documents", exist_ok=True)
    
    # Save the PDF
    pdf_path = "static/documents/NVC_API_Infrastructure.pdf"
    pdf.output(pdf_path)
    
    print(f"PDF generated at {pdf_path}")

if __name__ == "__main__":
    generate_api_infrastructure_pdf()