#!/usr/bin/env python3
"""
Generate a PDF Letter of Intent (LOI) for NVC Fund and Bridge.xyz partnership
"""

import os
import sys
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from datetime import datetime

# Ensure UTF-8 encoding is properly handled for output
# Python 3 uses UTF-8 by default so no explicit encoding is needed

def generate_bridge_xyz_loi():
    """Generate a PDF document for NVC Fund and Bridge.xyz Letter of Intent."""
    
    # Set up the document
    pdf_path = "static/docs/NVCT_Bridge_XYZ_LOI.pdf"
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=LETTER,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Create our custom styles
    justify_style = ParagraphStyle(
        name='Justify',
        alignment=TA_JUSTIFY,
        fontName='Helvetica',
        fontSize=11,
        leading=14
    )
    
    center_style = ParagraphStyle(
        name='CenterBold',
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        fontSize=12
    )
    
    title_style = ParagraphStyle(
        name='LOITitle',
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        fontSize=16,
        spaceBefore=12,
        spaceAfter=12
    )
    
    heading1_style = ParagraphStyle(
        name='LOIHeading1',
        alignment=TA_LEFT,
        fontName='Helvetica-Bold',
        fontSize=14,
        spaceBefore=10,
        spaceAfter=6
    )
    
    heading2_style = ParagraphStyle(
        name='LOIHeading2',
        alignment=TA_LEFT,
        fontName='Helvetica-Bold',
        fontSize=12,
        spaceBefore=8,
        spaceAfter=4
    )
    
    right_style = ParagraphStyle(
        name='RightAlign',
        alignment=TA_RIGHT,
        fontName='Helvetica',
        fontSize=11
    )
    
    # Content elements
    elements = []
    
    # Logo placeholder - you would need to replace with actual path to logo
    # logo_path = "static/images/nvc_logo.png"
    # if os.path.exists(logo_path):
    #     elements.append(Image(logo_path, width=2*inch, height=0.75*inch))
    #     elements.append(Spacer(1, 0.25*inch))
    
    # Title
    elements.append(Paragraph("LETTER OF INTENT", title_style))
    elements.append(Spacer(1, 0.1*inch))
    elements.append(Paragraph("STRATEGIC PARTNERSHIP BETWEEN", center_style))
    elements.append(Paragraph("NVC FUND HOLDING TRUST AND BRIDGE.XYZ", center_style))
    elements.append(Spacer(1, 0.25*inch))
    
    # Date
    today = datetime.now().strftime("%B %d, %Y")
    elements.append(Paragraph(f"Date: {today}", right_style))
    elements.append(Spacer(1, 0.25*inch))
    
    # Addressee
    elements.append(Paragraph("Bridge.xyz", styles['Normal']))
    elements.append(Paragraph("San Francisco, CA", styles['Normal']))
    elements.append(Paragraph("United States", styles['Normal']))
    elements.append(Spacer(1, 0.25*inch))
    
    # Salutation
    elements.append(Paragraph("Re: Letter of Intent - $5 Billion Strategic Liquidity Partnership", heading2_style))
    elements.append(Spacer(1, 0.15*inch))
    elements.append(Paragraph("Dear Bridge.xyz Leadership Team:", styles['Normal']))
    elements.append(Spacer(1, 0.15*inch))
    
    # Introduction paragraph
    intro_text = """
    This Letter of Intent ("LOI") sets forth the principal terms and conditions under which NVC Fund Holding Trust 
    ("NVC Fund") proposes to enter into a strategic liquidity partnership with Bridge.xyz ("Bridge") to establish 
    a $5 billion liquidity facility leveraging NVC Fund's NVCToken ("NVCT"). This non-binding LOI outlines the
    framework for our proposed partnership and serves as the basis for the preparation of definitive agreements.
    """
    elements.append(Paragraph(intro_text, justify_style))
    elements.append(Spacer(1, 0.15*inch))
    
    # 1. Partnership Structure
    elements.append(Paragraph("1. PARTNERSHIP STRUCTURE", heading1_style))
    
    structure_text = """
    1.1 Strategic Liquidity Partnership: NVC Fund and Bridge.xyz propose to establish a multi-tiered liquidity 
    provision agreement with the following parameters:
    
    a) Initial Phase: $500 million liquidity provision against NVCToken collateral with a loan-to-value 
    ratio of 75%.
    
    b) Scaling Phases: Incremental increases to the full $5 billion facility based on predetermined 
    transaction volume and performance metrics over a 24-month period.
    
    c) Term: Initial 36-month arrangement with automatic renewal options upon mutual agreement.
    
    1.2 Technical Integration: The parties will collaborate to develop:
    
    a) Direct API connections between NVC Banking Platform and Bridge.xyz infrastructure
    
    b) Stablecoin settlement layer utilizing Bridge's existing stablecoin infrastructure
    
    c) Cross-chain bridge solutions to support NVCToken liquidity across multiple blockchain networks
    """
    elements.append(Paragraph(structure_text, justify_style))
    elements.append(Spacer(1, 0.15*inch))
    
    # 2. Commercial Terms
    elements.append(Paragraph("2. COMMERCIAL TERMS", heading1_style))
    
    commercial_text = """
    2.1 Fee Structure: A tiered transaction fee model based on volume:
    
    a) Tier 1 (0-$500M): 0.40% per transaction
    
    b) Tier 2 ($500M-$2B): 0.30% per transaction
    
    c) Tier 3 ($2B-$5B): 0.25% per transaction
    
    2.2 Revenue Sharing: 70% to NVC Fund and 30% to Bridge.xyz for all new transaction revenue generated 
    through the partnership.
    
    2.3 Minimum Volume Commitments: 
    
    a) Year 1: $2 billion in transaction volume
    
    b) Year 2: $5 billion in transaction volume
    
    c) Year 3: $8 billion in transaction volume
    """
    elements.append(Paragraph(commercial_text, justify_style))
    elements.append(Spacer(1, 0.15*inch))
    
    # 3. Security and Compliance
    elements.append(Paragraph("3. SECURITY AND COMPLIANCE", heading1_style))
    
    security_text = """
    3.1 Collateral Management: Establishment of a programmatic treasury management system with 
    transparent reporting and automated collateral adjustments.
    
    3.2 Smart Contract Governance: Formation of a joint oversight committee for contract modifications
    with representation from both parties.
    
    3.3 Regulatory Framework: Development of clear jurisdictional parameters and compliance requirements
    in accordance with relevant financial regulations and blockchain governance standards.
    """
    elements.append(Paragraph(security_text, justify_style))
    elements.append(Spacer(1, 0.15*inch))
    
    # 4. Growth Incentives
    elements.append(Paragraph("4. GROWTH INCENTIVES", heading1_style))
    
    incentives_text = """
    4.1 Transaction Volume Bonuses: Automatic credit facility increases upon exceeding volume targets:
    
    a) 10% additional credit for exceeding quarterly targets by 15%
    
    b) 20% additional credit for exceeding quarterly targets by 25%
    
    4.2 Market Expansion: Preferential terms for entering new geographic markets, with specific focus on
    emerging markets in Africa, Southeast Asia, and Latin America.
    
    4.3 Technology Collaboration: Joint development of new liquidity products with intellectual property
    sharing arrangements to be detailed in the definitive agreements.
    """
    elements.append(Paragraph(incentives_text, justify_style))
    elements.append(Spacer(1, 0.15*inch))
    
    # 5. Mutual Benefits
    elements.append(Paragraph("5. MUTUAL BENEFITS", heading1_style))
    
    benefits_text = """
    5.1 Benefits to NVC Fund:
    
    a) Immediate access to global stablecoin infrastructure
    
    b) Enhanced liquidity for NVCToken
    
    c) New distribution channels for NVC Fund services
    
    5.2 Benefits to Bridge.xyz:
    
    a) Access to NVC Fund's $10+ trillion asset base as backing collateral
    
    b) Enhanced credibility through partnership with an established financial institution
    
    c) Expanded transaction volume through NVC Fund's existing global networks
    """
    elements.append(Paragraph(benefits_text, justify_style))
    elements.append(Spacer(1, 0.25*inch))
    
    # 6. Non-Binding Nature
    elements.append(Paragraph("6. NON-BINDING NATURE", heading1_style))
    
    nonbinding_text = """
    This LOI is non-binding and subject to the execution of definitive agreements between the parties.
    The parties agree to work in good faith to negotiate and execute such agreements within 60 days from
    the date of this LOI.
    """
    elements.append(Paragraph(nonbinding_text, justify_style))
    elements.append(Spacer(1, 0.25*inch))
    
    # 7. Confidentiality
    elements.append(Paragraph("7. CONFIDENTIALITY", heading1_style))
    
    confidentiality_text = """
    The parties agree to maintain the confidentiality of this LOI and all discussions and information
    exchanged in connection with the proposed partnership, except as required by law or regulatory authorities.
    """
    elements.append(Paragraph(confidentiality_text, justify_style))
    elements.append(Spacer(1, 0.25*inch))
    
    # 8. Governing Law
    elements.append(Paragraph("8. GOVERNING LAW", heading1_style))
    
    law_text = """
    This LOI shall be governed by and construed in accordance with the laws of the jurisdiction to be
    determined in the definitive agreements.
    """
    elements.append(Paragraph(law_text, justify_style))
    elements.append(Spacer(1, 0.5*inch))
    
    # Signature blocks
    elements.append(Paragraph("If the terms outlined in this LOI are acceptable, please indicate your acceptance by signing below.", justify_style))
    elements.append(Spacer(1, 0.5*inch))
    
    # Create a more professional signature block
    elements.append(Spacer(1, 0.5*inch))
    
    # Create two-column layout for signatures
    signature_data = [
        # Headers
        [Paragraph('<b>FOR NVC FUND HOLDING TRUST:</b>', justify_style), 
         Paragraph('<b>FOR BRIDGE.XYZ:</b>', justify_style)],
         
        # Spacing
        [Spacer(1, 0.6*inch), Spacer(1, 0.6*inch)],
        
        # Signature lines
        [Paragraph('__________________________________', justify_style),
         Paragraph('__________________________________', justify_style)],
         
        # Name lines
        [Paragraph('Name: ___________________________', justify_style),
         Paragraph('Name: ___________________________', justify_style)],
         
        # Title lines
        [Paragraph('Title: ____________________________', justify_style),
         Paragraph('Title: ____________________________', justify_style)],
         
        # Date lines
        [Paragraph('Date: ____________________________', justify_style),
         Paragraph('Date: ____________________________', justify_style)],
    ]
    
    # Create signature table with better spacing and formatting
    signature_table = Table(signature_data, colWidths=[2.75*inch, 2.75*inch], spaceBefore=20, spaceAfter=20)
    signature_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(signature_table)
    
    # Build the document
    doc.build(elements)
    
    print(f"Generated LOI PDF at: {pdf_path}")
    return pdf_path

if __name__ == "__main__":
    generate_bridge_xyz_loi()