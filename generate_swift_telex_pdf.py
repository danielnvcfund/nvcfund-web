"""
Generate a PDF document describing SWIFT and Telex messaging capabilities
"""
import os
from datetime import datetime
import weasyprint
from flask import render_template_string
from main import app
from models import FinancialInstitution

# HTML Template for the PDF
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SWIFT and KTT Telex Messaging Capabilities</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #1a5276;
            padding-bottom: 10px;
        }
        .logo {
            max-width: 200px;
            height: auto;
            margin-bottom: 20px;
        }
        h1 {
            color: #1a5276;
            font-size: 28px;
            margin-bottom: 10px;
        }
        h2 {
            color: #2874a6;
            font-size: 22px;
            margin-top: 25px;
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
        }
        h3 {
            color: #2874a6;
            font-size: 18px;
            margin-top: 20px;
        }
        p {
            margin-bottom: 15px;
        }
        .footer {
            margin-top: 50px;
            border-top: 1px solid #ddd;
            padding-top: 10px;
            font-size: 12px;
            color: #777;
            text-align: center;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px 12px;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
            font-weight: bold;
        }
        .section {
            margin-bottom: 25px;
        }
        .info-box {
            background-color: #f8f9fa;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 15px;
            margin: 15px 0;
        }
        .code {
            font-family: monospace;
            background-color: #f5f5f5;
            padding: 2px 4px;
            border-radius: 3px;
        }
        .important {
            color: #d35400;
            font-weight: bold;
        }
        .code-block {
            background-color: #f5f5f5;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 10px;
            font-family: monospace;
            white-space: pre-wrap;
            margin: 15px 0;
        }
        .note {
            background-color: #e8f4f8;
            border-left: 4px solid #2874a6;
            padding: 10px 15px;
            margin: 15px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>SWIFT and KTT Telex Messaging Capabilities</h1>
            <p>NVC Fund Bank</p>
            <p>{{ current_date }}</p>
        </div>

        <div class="section">
            <h2>Executive Summary</h2>
            <p>This document provides comprehensive information about NVC Fund Bank's SWIFT and KTT Telex messaging capabilities, including identification codes, supported message types, and integration protocols. These systems enable secure financial messaging for international funds transfers, payment confirmations, and other banking communications.</p>
        </div>

        <div class="section">
            <h2>Institutional Information</h2>
            <div class="info-box">
                <p><strong>Institution Name:</strong> {{ bank_name }}</p>
                <p><strong>SWIFT/BIC Code:</strong> <span class="code important">{{ swift_code }}</span></p>
                <p><strong>Regulatory Status:</strong> Expressed Trust Bank pursuant to African Union Treaty, Laws and Jurisdictions under AFRA, ACB, Article XIV 1(e) of ECO-6 Treaty, and ADCB</p>
            </div>
        </div>

        <div class="section">
            <h2>SWIFT Messaging Capabilities</h2>
            
            <h3>Supported SWIFT Message Types</h3>
            <table>
                <thead>
                    <tr>
                        <th>Message Type</th>
                        <th>Description</th>
                        <th>Support Status</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>MT103</td>
                        <td>Single Customer Credit Transfer</td>
                        <td>Fully Supported</td>
                    </tr>
                    <tr>
                        <td>MT202</td>
                        <td>General Financial Institution Transfer</td>
                        <td>Fully Supported</td>
                    </tr>
                    <tr>
                        <td>MT199</td>
                        <td>Free Format Message</td>
                        <td>Fully Supported</td>
                    </tr>
                    <tr>
                        <td>MT299</td>
                        <td>Free Format Message - Treasury</td>
                        <td>Fully Supported</td>
                    </tr>
                    <tr>
                        <td>MT700</td>
                        <td>Issue of a Documentary Credit</td>
                        <td>Supported</td>
                    </tr>
                    <tr>
                        <td>MT760</td>
                        <td>Guarantee/Standby Letter of Credit</td>
                        <td>Supported</td>
                    </tr>
                    <tr>
                        <td>MT798</td>
                        <td>Proprietary Message</td>
                        <td>Supported</td>
                    </tr>
                </tbody>
            </table>
            
            <h3>SWIFT Integration Protocols</h3>
            <p>Our SWIFT messaging infrastructure supports both FIN (Financial Information Network) and InterAct messaging services, enabling secure communication with correspondent banks and financial institutions worldwide.</p>
            
            <div class="note">
                <p><strong>Note:</strong> For high-value transfers and treasury operations, we recommend using MT202 message types for institution-to-institution transfers to ensure optimal processing.</p>
            </div>
        </div>

        <div class="section">
            <h2>KTT Telex Messaging Capabilities</h2>
            
            <h3>About KTT Telex</h3>
            <p>Our institution utilizes the KTT Telex system for secure financial messaging, particularly for transactions with partner institutions in regions where SWIFT access may be limited. KTT Telex provides an alternative secure channel for financial communications.</p>
            
            <h3>KTT Telex Identification</h3>
            <div class="info-box">
                <p><strong>Telex Code:</strong> <span class="code important">{{ swift_code }}</span> (Same as our SWIFT/BIC code)</p>
                <p><strong>Webhook Endpoint:</strong> <span class="code">/telex/api/webhook</span></p>
            </div>
            
            <h3>Supported KTT Telex Message Types</h3>
            <table>
                <thead>
                    <tr>
                        <th>Code</th>
                        <th>Message Type</th>
                        <th>Description</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>FT</td>
                        <td>Funds Transfer</td>
                        <td>Request to transfer funds between financial institutions</td>
                    </tr>
                    <tr>
                        <td>FTC</td>
                        <td>Funds Transfer Confirmation</td>
                        <td>Confirmation of a completed funds transfer</td>
                    </tr>
                    <tr>
                        <td>PO</td>
                        <td>Payment Order</td>
                        <td>Instruction to make a payment</td>
                    </tr>
                    <tr>
                        <td>PC</td>
                        <td>Payment Confirmation</td>
                        <td>Confirmation of a completed payment</td>
                    </tr>
                    <tr>
                        <td>BI</td>
                        <td>Balance Inquiry</td>
                        <td>Request for account balance information</td>
                    </tr>
                    <tr>
                        <td>BR</td>
                        <td>Balance Response</td>
                        <td>Response with account balance information</td>
                    </tr>
                    <tr>
                        <td>GM</td>
                        <td>General Message</td>
                        <td>Free-format message for general communications</td>
                    </tr>
                </tbody>
            </table>
            
            <h3>Sample KTT Telex Message Structure</h3>
            <div class="code-block">{
  "message_id": "KTT-a1b2c3d4-e5f6-7890-abcd-1234567890ab",
  "sender_reference": "REF1683924765",
  "sender_bic": "SOMEBANK123",
  "recipient_bic": "{{ swift_code }}",
  "message_type": "FT",
  "content": {
    "reference": "FT-TX123456789",
    "amount": 100000.00,
    "currency": "USD",
    "sender_name": "Sending Bank Name",
    "sender_account": "123456789",
    "recipient_name": "{{ bank_name }}",
    "recipient_account": "987654321",
    "value_date": "2025-05-03",
    "details": "Invoice payment #INV-2025-001",
    "timestamp": "2025-05-03T10:15:30Z"
  },
  "priority": "HIGH"
}</div>
        </div>

        <div class="section">
            <h2>Integration Guidelines</h2>
            
            <h3>For SWIFT Integration</h3>
            <p>To send SWIFT messages to our institution:</p>
            <ol>
                <li>Use our BIC code <span class="code">{{ swift_code }}</span> as the recipient identifier</li>
                <li>Follow SWIFT standards for message formatting and field requirements</li>
                <li>For MT103 messages, ensure field 59 (Beneficiary) contains complete and accurate account information</li>
                <li>For foreign exchange transactions, include conversion details in field 72</li>
            </ol>
            
            <h3>For KTT Telex Integration</h3>
            <p>To send KTT Telex messages to our institution:</p>
            <ol>
                <li>Use our Telex code <span class="code">{{ swift_code }}</span> as the recipient identifier</li>
                <li>Send webhook requests to our endpoint with proper authentication</li>
                <li>Include all required fields specific to the message type</li>
                <li>For sensitive transactions, use HIGH priority and request acknowledgment</li>
            </ol>
            
            <div class="note">
                <p><strong>Security Note:</strong> All API communications require proper authentication with API keys and signature verification. Contact our integration team to obtain the necessary credentials for secure message exchange.</p>
            </div>
        </div>

        <div class="section">
            <h2>Contact Information</h2>
            <p>For technical support or integration assistance:</p>
            <ul>
                <li><strong>Technical Support:</strong> technical.support@nvcfundbank.example.com</li>
                <li><strong>Integration Team:</strong> integration@nvcfundbank.example.com</li>
                <li><strong>SWIFT Help Desk:</strong> swift.desk@nvcfundbank.example.com</li>
            </ul>
        </div>

        <div class="footer">
            <p>© {{ current_year }} NVC Fund Bank. All rights reserved.</p>
            <p>This document is confidential and intended solely for the use of the individual or entity to whom it is addressed.</p>
        </div>
    </div>
</body>
</html>
"""

def generate_pdf():
    """Generate the SWIFT and Telex capabilities PDF"""
    
    # Get institution data
    with app.app_context():
        institution = FinancialInstitution.query.filter_by(name='NVC BANK').first()
        if not institution:
            # Try alternate name
            institution = FinancialInstitution.query.filter(FinancialInstitution.swift_code == 'NVCGLOBAL').first()
        
        # Use default values if institution not found
        if institution:
            bank_name = institution.name
            swift_code = institution.swift_code
        else:
            bank_name = "NVC Fund Bank"
            swift_code = "NVCGLOBAL"
    
    # Prepare template context
    context = {
        'bank_name': bank_name,
        'swift_code': swift_code,
        'current_date': datetime.now().strftime('%B %d, %Y'),
        'current_year': datetime.now().year
    }
    
    # Render HTML
    with app.app_context():
        html_content = render_template_string(TEMPLATE, **context)
    
    # Define output file path
    output_file = 'static/documents/swift_telex_capabilities.pdf'
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Generate PDF
    weasyprint.HTML(string=html_content).write_pdf(output_file)
    
    print(f"PDF generated at: {output_file}")
    return output_file

if __name__ == "__main__":
    generate_pdf()