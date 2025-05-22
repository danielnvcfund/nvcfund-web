"""
Generate a PDF prospectus using ReportLab (more reliable than FPDF for Unicode)
"""

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.platypus import PageBreak
import os
from datetime import datetime

def generate_prospectus():
    """Generate investment prospectus PDF using ReportLab"""
    
    # Create directory if it doesn't exist
    pdf_dir = 'static/docs'
    if not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir)
        
    # Output path
    pdf_path = os.path.join(pdf_dir, 'nvc_investment_prospectus.pdf')
    
    # Create document
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=LETTER,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Container for elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    styles.add(ParagraphStyle(
        name='DocTitle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=1,  # Center
        spaceAfter=12
    ))
    
    styles.add(ParagraphStyle(
        name='DocSubtitle',
        parent=styles['Heading2'],
        fontSize=13,
        alignment=1,  # Center
        spaceAfter=12
    ))
    
    styles.add(ParagraphStyle(
        name='SectionTitle',
        parent=styles['Heading2'],
        fontSize=12,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.navy
    ))
    
    styles.add(ParagraphStyle(
        name='Note',
        parent=styles['Normal'],
        fontSize=9,
        backColor=colors.lightgrey,
        borderColor=colors.grey,
        borderWidth=1,
        borderPadding=5
    ))
    
    # Document title
    elements.append(Paragraph('NVC BANKING PLATFORM', styles['DocTitle']))
    elements.append(Paragraph('$100 Million Debt Instrument Offering', styles['DocSubtitle']))
    elements.append(Paragraph('24-Month Term • 20% Annual Coupon • Convertible to Equity', styles['DocSubtitle']))
    elements.append(Paragraph(f'Confidential Offering Prospectus - {datetime.now().strftime("%B %Y")}', styles['Italic']))
    elements.append(Spacer(1, 0.25*inch))
    
    # Executive Summary
    elements.append(Paragraph('EXECUTIVE SUMMARY', styles['SectionTitle']))
    elements.append(Paragraph(
        'NVC Banking Platform is offering a $100 million debt instrument with a 24-month term and 20% annual coupon ' +
        'to accelerate the expansion of its established global financial infrastructure. This debt offering includes ' +
        'an equity conversion option held by NVC Fund Holding and is secured by over $10 trillion in assets under management.',
        styles['Normal']
    ))
    elements.append(Spacer(1, 0.25*inch))
    
    # Key Metrics
    elements.append(Paragraph('INVESTMENT HIGHLIGHTS', styles['SectionTitle']))
    
    # Metrics table
    metrics_data = [
        ['$10T+', '$1T+', '$289B', '20%'],
        ['Total Assets', 'Market Cap', 'Annual Revenue', 'Annual Coupon Rate']
    ]
    
    metrics_table = Table(metrics_data, colWidths=[1.1*inch]*4)
    metrics_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('FONTSIZE', (0, 1), (-1, 1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
    ]))
    
    elements.append(metrics_table)
    elements.append(Spacer(1, 0.25*inch))
    
    # Company Overview
    elements.append(Paragraph('COMPANY OVERVIEW', styles['SectionTitle']))
    elements.append(Paragraph(
        'NVC Banking Platform is a sophisticated blockchain-powered financial institution offering comprehensive ' +
        'multi-gateway payment processing and advanced financial services. The platform serves as a bridge between ' +
        'traditional banking and next-generation financial technologies, with a specialized focus on:',
        styles['Normal']
    ))
    
    # Bullet points
    elements.append(Paragraph('• Financial institution recapitalization', styles['Normal']))
    elements.append(Paragraph('• Treasury management', styles['Normal']))
    elements.append(Paragraph('• Global settlement infrastructure', styles['Normal']))
    elements.append(Paragraph('• Multi-currency transaction processing', styles['Normal']))
    elements.append(Paragraph('• Standby Letter of Credit (SBLC) issuance', styles['Normal']))
    elements.append(Spacer(1, 0.25*inch))
    
    # Investment Security
    elements.append(Paragraph('INVESTMENT SECURITY', styles['SectionTitle']))
    elements.append(Paragraph(
        'This investment opportunity offers exceptional security through multiple institutional safeguards:',
        styles['Normal']
    ))
    
    security_data = [
        ['Security Factor', 'Details'],
        ['Asset Backing', '$10+ trillion in high-quality assets and cash equivalents held by NVC Fund Holding Trust'],
        ['Regulatory Compliance', 'SEC-registered securities with CUSIP/ISIN identifiers and independent verification'],
        ['Bloomberg Verification', 'Listed on Bloomberg (3387420Z US, BBGID: BBG000P6FW5)'],
        ['Corporate Governance', 'Independent board oversight, regular audits, and transparent financial reporting'],
        ['Risk Management', 'Sophisticated treasury controls, diversified asset allocation, and compliance frameworks']
    ]
    
    security_table = Table(security_data, colWidths=[1.5*inch, 4*inch])
    security_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    
    elements.append(security_table)
    elements.append(Spacer(1, 0.25*inch))
    
    # Debt Instrument Structure
    elements.append(Paragraph('DEBT INSTRUMENT STRUCTURE', styles['SectionTitle']))
    elements.append(Paragraph(
        'This offering is structured as a secured debt instrument with the following key terms:',
        styles['Normal']
    ))
    
    debt_terms = [
        ['Term', 'Details'],
        ['Instrument Type', 'Secured Senior Debt with Equity Conversion Option'],
        ['Amount', '$100,000,000 USD'],
        ['Term', '24 months from date of issuance'],
        ['Coupon Rate', '20% per annum (5% paid quarterly)'],
        ['Security', 'Asset-backed by NVC Fund Holding Trust\'s $10+ trillion balance sheet'],
        ['Conversion Option', 'NVC Fund Holding may elect to convert debt to equity at predetermined terms'],
        ['Minimum Investment', '$5,000,000 USD']
    ]
    
    debt_table = Table(debt_terms, colWidths=[1.5*inch, 4*inch])
    debt_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    
    elements.append(debt_table)
    elements.append(PageBreak())
    
    # Strategic Use of Investment Capital
    elements.append(Paragraph('STRATEGIC USE OF INVESTMENT CAPITAL', styles['SectionTitle']))
    elements.append(Paragraph(
        'The $100 million debt proceeds will be strategically allocated to accelerate growth and enhance infrastructure:',
        styles['Normal']
    ))
    
    elements.append(Paragraph('<b>Technology Infrastructure (35%)</b>', styles['Normal']))
    elements.append(Paragraph(
        '$35 million to expand technical capabilities, enhance blockchain integration, and scale systems architecture',
        styles['Normal']
    ))
    elements.append(Spacer(1, 0.1*inch))
    
    elements.append(Paragraph('<b>Global Banking Licenses (25%)</b>', styles['Normal']))
    elements.append(Paragraph(
        '$25 million to secure additional banking licenses in key jurisdictions worldwide',
        styles['Normal']
    ))
    elements.append(Spacer(1, 0.1*inch))
    
    elements.append(Paragraph('<b>Settlement Network Expansion (20%)</b>', styles['Normal']))
    elements.append(Paragraph(
        '$20 million to build out global settlement networks and correspondent banking relationships',
        styles['Normal']
    ))
    elements.append(Spacer(1, 0.1*inch))
    
    elements.append(Paragraph('<b>Security & Compliance Systems (10%)</b>', styles['Normal']))
    elements.append(Paragraph(
        '$10 million to implement advanced security protocols and regulatory compliance mechanisms',
        styles['Normal']
    ))
    elements.append(Spacer(1, 0.1*inch))
    
    elements.append(Paragraph('<b>Strategic Reserve & Contingency (10%)</b>', styles['Normal']))
    elements.append(Paragraph(
        '$10 million maintained as contingency funds for unexpected opportunities or challenges',
        styles['Normal']
    ))
    elements.append(Spacer(1, 0.25*inch))
    
    # Investment Participation Levels
    elements.append(Paragraph('INVESTMENT PARTICIPATION LEVELS', styles['SectionTitle']))
    
    participation_levels = [
        ['Participation Level', 'Investment Amount', 'Special Benefits'],
        ['Lead Investor', '$25,000,000+', 'Board Observer Rights, Executive Briefings, Custom Treasury Services'],
        ['Institutional Investor', '$10,000,000 - $24,999,999', 'Advisory Committee Invitation, Quarterly Strategy Calls, Priority Services'],
        ['Qualified Investor', '$5,000,000 - $9,999,999', 'Investor Relations Portal, Quarterly Updates, Enhanced Banking Services']
    ]
    
    participation_table = Table(participation_levels, colWidths=[1.5*inch, 1.5*inch, 2.5*inch])
    participation_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('WORDWRAP', (0, 0), (-1, -1), True),
    ]))
    
    elements.append(participation_table)
    elements.append(Spacer(1, 0.25*inch))
    
    # Note on Return Structure
    elements.append(Paragraph(
        'Note on Return Structure: All investors receive the same 20% annual coupon rate, paid quarterly at 5% per quarter, ' +
        'regardless of investment amount. The benefits above represent additional value-added services beyond the financial return.',
        styles['Note']
    ))
    elements.append(Spacer(1, 0.25*inch))
    
    # Platform Capabilities & Achievements
    elements.append(Paragraph('PLATFORM CAPABILITIES & ACHIEVEMENTS', styles['SectionTitle']))
    elements.append(Paragraph(
        'The NVC Banking Platform has established a robust financial infrastructure with diverse capabilities:',
        styles['Normal']
    ))
    
    elements.append(Paragraph('• Multi-Gateway Payment Processing - Integrated Stripe, PayPal, SWIFT, ACH, Wire Transfer, and Mojoloop', styles['Normal']))
    elements.append(Paragraph('• Correspondent Banking Network - Global banking relationships with real-time settlement capabilities', styles['Normal']))
    elements.append(Paragraph('• NVCT Stablecoin Ecosystem - 1:1 USD-pegged stablecoin with multi-currency exchange capabilities', styles['Normal']))
    elements.append(Paragraph('• SBLC Issuance System - Comprehensive Standby Letter of Credit issuance platform', styles['Normal']))
    elements.append(Paragraph('• Financial Institution Recapitalization - Specialized capital injection programs', styles['Normal']))
    elements.append(Paragraph('• Blockchain Settlement Infrastructure - Multi-blockchain architecture with smart contract capabilities', styles['Normal']))
    
    elements.append(PageBreak())
    
    # Implementation Timeline
    elements.append(Paragraph('IMPLEMENTATION TIMELINE', styles['SectionTitle']))
    
    timeline_data = [
        ['Timeline', 'Milestone', 'Key Activities'],
        ['Q3 2025', 'Capital Raise Completion', 'Close $100M investment and finalize deployment strategy'],
        ['Q4 2025', 'Infrastructure Expansion', 'Scale platform infrastructure, enhance security protocols'],
        ['Q1 2026', 'Regulatory Framework', 'Secure additional licenses, expand compliance framework'],
        ['Q2 2026', 'Global Market Entry', 'Launch in strategic new markets, expand banking network'],
        ['Q3-Q4 2026', 'Integration & Scale', 'Complete system integrations, achieve operational scale']
    ]
    
    timeline_table = Table(timeline_data, colWidths=[1*inch, 1.5*inch, 3*inch])
    timeline_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    
    elements.append(timeline_table)
    elements.append(Spacer(1, 0.25*inch))
    
    # Institutional Credibility
    elements.append(Paragraph('INSTITUTIONAL CREDIBILITY', styles['SectionTitle']))
    elements.append(Paragraph(
        'NVC Banking Platform maintains the highest levels of institutional credibility through:',
        styles['Normal']
    ))
    
    elements.append(Paragraph('• Unit Investment Trust - CUSIP# 67074B105, ISIN# US67074B1052', styles['Normal']))
    elements.append(Paragraph('• NVC Fund Bond - CUSIP# 62944AAA4, ISIN# US62944AAA43', styles['Normal']))
    elements.append(Paragraph('• Bloomberg Listings - Bloomberg Identifier: 3387420Z US, BBGID: BBG000P6FW5', styles['Normal']))
    elements.append(Paragraph('• SEC Registered Transfer Agent - Transferonline Inc. (since 2009)', styles['Normal']))
    elements.append(Spacer(1, 0.25*inch))
    
    # Contact Information
    elements.append(Paragraph('CONTACT INFORMATION', styles['SectionTitle']))
    elements.append(Paragraph(
        'To discuss this investment opportunity in more detail, please contact our Investor Relations team:',
        styles['Normal']
    ))
    
    contact_data = [
        ['Phone:', '+1 (XXX) XXX-XXXX'],
        ['Email:', 'investors@nvcbanking.com'],
        ['Website:', 'www.nvcbanking.com/investors'],
        ['Address:', '[Corporate Headquarters Address]']
    ]
    
    contact_table = Table(contact_data, colWidths=[1*inch, 4.5*inch])
    contact_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(contact_table)
    elements.append(Spacer(1, 0.5*inch))
    
    # Disclaimer
    elements.append(Paragraph('<b>DISCLAIMER:</b>', styles['Normal']))
    elements.append(Paragraph(
        'This document is for informational purposes only and does not constitute an offer to sell or a solicitation ' +
        'of an offer to buy any securities. The information contained herein is subject to change without notice. ' +
        'NVC Banking Platform does not make any representation or warranty as to the accuracy or completeness of the ' +
        'information contained herein. Investments involve risk and are not guaranteed. Prospective investors should ' +
        'consult with their financial, legal, and tax advisors before investing.',
        styles['Italic']
    ))
    
    # Build PDF
    doc.build(elements)
    
    return pdf_path
    
    
if __name__ == "__main__":
    pdf_path = generate_prospectus()
    print(f"Investment prospectus PDF generated successfully at: {pdf_path}")