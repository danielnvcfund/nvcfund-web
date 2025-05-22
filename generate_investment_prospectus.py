"""
Generate a professional PDF investment prospectus for the NVC Banking Platform.
"""

from fpdf import FPDF
import sys

# Set encoding to utf-8
sys.setdefaultencoding = 'utf-8'
import os
from datetime import datetime

class PDF(FPDF):
    """Custom PDF class with header and footer"""
    
    def header(self):
        # Logo - if available
        logo_path = 'static/images/logo.png'
        if os.path.exists(logo_path):
            self.image(logo_path, 10, 8, 30)
            
        # Arial bold 15
        self.set_font('Arial', 'B', 15)
        # Move to the right
        self.cell(30)
        # Title
        self.cell(130, 10, 'NVC BANKING PLATFORM', 0, 0, 'C')
        # Line break
        self.ln(20)
        
    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Arial italic 8
        self.set_font('Arial', 'I', 8)
        # Page number
        self.cell(0, 10, 'Page ' + str(self.page_no()) + ' | CONFIDENTIAL - FOR QUALIFIED INVESTORS ONLY', 0, 0, 'C')
        
    def chapter_title(self, title):
        # Arial 12
        self.set_font('Arial', 'B', 12)
        # Background color
        self.set_fill_color(200, 220, 255)
        # Title
        self.cell(0, 6, title, 0, 1, 'L', 1)
        # Line break
        self.ln(4)
        
    def chapter_body(self, body):
        # Times 12
        self.set_font('Times', '', 12)
        # Output text
        self.multi_cell(0, 5, body)
        # Line break
        self.ln()
        
    def section_title(self, title):
        # Arial 12
        self.set_font('Arial', 'B', 11)
        # Title
        self.cell(0, 6, title, 0, 1, 'L')
        # Line break
        self.ln(2)
        
    def data_table(self, headers, data, column_widths=None):
        # Set column widths based on page width
        if column_widths is None:
            width = self.w - 2 * self.l_margin
            column_widths = [width / len(headers)] * len(headers)
            
        # Headers
        self.set_font('Arial', 'B', 10)
        self.set_fill_color(200, 220, 255)
        for i, header in enumerate(headers):
            self.cell(column_widths[i], 7, header, 1, 0, 'C', 1)
        self.ln()
        
        # Data
        self.set_font('Arial', '', 10)
        self.set_fill_color(255, 255, 255)
        for row in data:
            for i, cell in enumerate(row):
                self.cell(column_widths[i], 6, str(cell), 1, 0, 'L')
            self.ln()
        self.ln(4)

def generate_prospectus():
    """Generate the investment prospectus PDF"""
    
    # Create PDF instance
    pdf = PDF()
    pdf.set_author('NVC Banking Platform')
    pdf.set_title('$100M Debt Instrument Offering - Investment Prospectus')
    pdf.set_subject('24-Month Term • 20% Annual Coupon • Convertible to Equity')
    pdf.add_page()
    
    # Document Title
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, '$100 Million Debt Instrument Offering', 0, 1, 'C')
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, '24-Month Term • 20% Annual Coupon • Convertible to Equity', 0, 1, 'C')
    pdf.set_font('Arial', 'I', 10)
    pdf.cell(0, 5, f'Confidential Offering Prospectus - {datetime.now().strftime("%B %Y")}', 0, 1, 'C')
    pdf.ln(10)
    
    # Executive Summary
    pdf.chapter_title('EXECUTIVE SUMMARY')
    pdf.chapter_body('NVC Banking Platform is offering a $100 million debt instrument with a 24-month term and 20% annual coupon to accelerate the expansion of its established global financial infrastructure. This debt offering includes an equity conversion option held by NVC Fund Holding and is secured by over $10 trillion in assets under management.')
    pdf.ln(5)
    
    # Key Metrics
    pdf.chapter_title('INVESTMENT HIGHLIGHTS')
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(50, 10, '$10T+', 0, 0, 'C')
    pdf.cell(50, 10, '$1T+', 0, 0, 'C')
    pdf.cell(50, 10, '$289B', 0, 0, 'C')
    pdf.cell(50, 10, '20%', 0, 1, 'C')
    
    pdf.set_font('Arial', '', 10)
    pdf.cell(50, 5, 'Total Assets', 0, 0, 'C')
    pdf.cell(50, 5, 'Market Capitalization', 0, 0, 'C')
    pdf.cell(50, 5, 'Annual Revenue', 0, 0, 'C')
    pdf.cell(50, 5, 'Annual Coupon Rate', 0, 1, 'C')
    pdf.ln(10)
    
    # Company Overview
    pdf.chapter_title('COMPANY OVERVIEW')
    pdf.chapter_body('NVC Banking Platform is a sophisticated blockchain-powered financial institution offering comprehensive multi-gateway payment processing and advanced financial services. The platform serves as a bridge between traditional banking and next-generation financial technologies, with a specialized focus on:')
    
    pdf.set_font('Times', '', 12)
    pdf.ln(2)
    pdf.cell(10, 5, '•', 0, 0)
    pdf.cell(0, 5, 'Financial institution recapitalization', 0, 1)
    pdf.cell(10, 5, '•', 0, 0)
    pdf.cell(0, 5, 'Treasury management', 0, 1)
    pdf.cell(10, 5, '•', 0, 0)
    pdf.cell(0, 5, 'Global settlement infrastructure', 0, 1)
    pdf.cell(10, 5, '•', 0, 0)
    pdf.cell(0, 5, 'Multi-currency transaction processing', 0, 1)
    pdf.cell(10, 5, '•', 0, 0)
    pdf.cell(0, 5, 'Standby Letter of Credit (SBLC) issuance', 0, 1)
    pdf.ln(5)
    
    # Investment Security
    pdf.chapter_title('INVESTMENT SECURITY')
    pdf.chapter_body('This investment opportunity offers exceptional security through multiple institutional safeguards:')
    pdf.ln(2)
    
    security_data = [
        ['Asset Backing', '$10+ trillion in high-quality assets and cash equivalents held by NVC Fund Holding Trust'],
        ['Regulatory Compliance', 'SEC-registered securities with CUSIP/ISIN identifiers and independent verification'],
        ['Bloomberg Verification', 'Listed on Bloomberg (3387420Z US, BBGID: BBG000P6FW5)'],
        ['Corporate Governance', 'Independent board oversight, regular audits, and transparent financial reporting'],
        ['Risk Management', 'Sophisticated treasury controls, diversified asset allocation, and compliance frameworks']
    ]
    
    pdf.data_table(['Security Factor', 'Details'], security_data, [50, 140])
    
    # Debt Instrument Structure
    pdf.chapter_title('DEBT INSTRUMENT STRUCTURE')
    pdf.chapter_body('This offering is structured as a secured debt instrument with the following key terms:')
    
    debt_terms = [
        ['Instrument Type', 'Secured Senior Debt with Equity Conversion Option'],
        ['Amount', '$100,000,000 USD'],
        ['Term', '24 months from date of issuance'],
        ['Coupon Rate', '20% per annum (5% paid quarterly)'],
        ['Security', 'Asset-backed by NVC Fund Holding Trust\'s $10+ trillion balance sheet'],
        ['Conversion Option', 'NVC Fund Holding may elect to convert debt to equity at predetermined terms'],
        ['Minimum Investment', '$5,000,000 USD']
    ]
    
    pdf.data_table(['Term', 'Details'], debt_terms, [60, 130])
    
    # Strategic Use of Investment Capital
    pdf.add_page()
    pdf.chapter_title('STRATEGIC USE OF INVESTMENT CAPITAL')
    pdf.chapter_body('The $100 million debt proceeds will be strategically allocated to accelerate growth and enhance infrastructure:')
    
    pdf.set_font('Times', 'B', 12)
    pdf.ln(2)
    pdf.cell(0, 6, 'Technology Infrastructure (35%)', 0, 1)
    pdf.set_font('Times', '', 12)
    pdf.cell(10, 5, '', 0, 0)
    pdf.cell(0, 5, '$35 million to expand technical capabilities, enhance blockchain integration,', 0, 1)
    pdf.cell(10, 5, '', 0, 0)
    pdf.cell(0, 5, 'and scale systems architecture', 0, 1)
    pdf.ln(2)
    
    pdf.set_font('Times', 'B', 12)
    pdf.cell(0, 6, 'Global Banking Licenses (25%)', 0, 1)
    pdf.set_font('Times', '', 12)
    pdf.cell(10, 5, '', 0, 0)
    pdf.cell(0, 5, '$25 million to secure additional banking licenses in key jurisdictions worldwide', 0, 1)
    pdf.ln(2)
    
    pdf.set_font('Times', 'B', 12)
    pdf.cell(0, 6, 'Settlement Network Expansion (20%)', 0, 1)
    pdf.set_font('Times', '', 12)
    pdf.cell(10, 5, '', 0, 0)
    pdf.cell(0, 5, '$20 million to build out global settlement networks and correspondent banking relationships', 0, 1)
    pdf.ln(2)
    
    pdf.set_font('Times', 'B', 12)
    pdf.cell(0, 6, 'Security & Compliance Systems (10%)', 0, 1)
    pdf.set_font('Times', '', 12)
    pdf.cell(10, 5, '', 0, 0)
    pdf.cell(0, 5, '$10 million to implement advanced security protocols and regulatory compliance mechanisms', 0, 1)
    pdf.ln(2)
    
    pdf.set_font('Times', 'B', 12)
    pdf.cell(0, 6, 'Strategic Reserve & Contingency (10%)', 0, 1)
    pdf.set_font('Times', '', 12)
    pdf.cell(10, 5, '', 0, 0)
    pdf.cell(0, 5, '$10 million maintained as contingency funds for unexpected opportunities or challenges', 0, 1)
    pdf.ln(5)
    
    # Investment Participation Levels
    pdf.chapter_title('INVESTMENT PARTICIPATION LEVELS')
    
    participation_levels = [
        ['Lead Investor', '$25,000,000+', 'Board Observer Rights, Executive Briefings, Custom Treasury Services'],
        ['Institutional Investor', '$10,000,000 - $24,999,999', 'Advisory Committee Invitation, Quarterly Strategy Calls, Priority Services'],
        ['Qualified Investor', '$5,000,000 - $9,999,999', 'Investor Relations Portal, Quarterly Updates, Enhanced Banking Services']
    ]
    
    pdf.data_table(['Participation Level', 'Investment Amount', 'Special Benefits'], participation_levels, [50, 60, 80])
    
    # Note on Return Structure
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(pdf.l_margin, pdf.get_y(), pdf.w - 2*pdf.l_margin, 20, 'F')
    
    pdf.set_font('Arial', 'B', 11)
    pdf.set_xy(pdf.l_margin + 5, pdf.get_y() + 2)
    pdf.cell(0, 6, 'Note on Return Structure:', 0, 1)
    
    pdf.set_font('Times', '', 11)
    pdf.set_x(pdf.l_margin + 5)
    pdf.multi_cell(0, 5, 'All investors receive the same 20% annual coupon rate, paid quarterly at 5% per quarter, regardless of investment amount. The benefits above represent additional value-added services beyond the financial return.')
    pdf.ln(5)
    
    # Platform Capabilities & Achievements
    pdf.chapter_title('PLATFORM CAPABILITIES & ACHIEVEMENTS')
    pdf.chapter_body('The NVC Banking Platform has established a robust financial infrastructure with diverse capabilities:')
    
    pdf.set_font('Times', '', 12)
    pdf.ln(2)
    pdf.cell(10, 5, '•', 0, 0)
    pdf.cell(0, 5, 'Multi-Gateway Payment Processing - Integrated Stripe, PayPal, SWIFT, ACH, Wire Transfer, and Mojoloop', 0, 1)
    pdf.cell(10, 5, '•', 0, 0)
    pdf.cell(0, 5, 'Correspondent Banking Network - Global banking relationships with real-time settlement capabilities', 0, 1)
    pdf.cell(10, 5, '•', 0, 0)
    pdf.cell(0, 5, 'NVCT Stablecoin Ecosystem - 1:1 USD-pegged stablecoin with multi-currency exchange capabilities', 0, 1)
    pdf.cell(10, 5, '•', 0, 0)
    pdf.cell(0, 5, 'SBLC Issuance System - Comprehensive Standby Letter of Credit issuance platform', 0, 1)
    pdf.cell(10, 5, '•', 0, 0)
    pdf.cell(0, 5, 'Financial Institution Recapitalization - Specialized capital injection programs', 0, 1)
    pdf.cell(10, 5, '•', 0, 0)
    pdf.cell(0, 5, 'Blockchain Settlement Infrastructure - Multi-blockchain architecture with smart contract capabilities', 0, 1)
    
    # Implementation Timeline
    pdf.add_page()
    pdf.chapter_title('IMPLEMENTATION TIMELINE')
    
    timeline_data = [
        ['Q3 2025', 'Capital Raise Completion', 'Close $100M investment and finalize deployment strategy'],
        ['Q4 2025', 'Infrastructure Expansion', 'Scale platform infrastructure, enhance security protocols'],
        ['Q1 2026', 'Regulatory Framework', 'Secure additional licenses, expand compliance framework'],
        ['Q2 2026', 'Global Market Entry', 'Launch in strategic new markets, expand banking network'],
        ['Q3-Q4 2026', 'Integration & Scale', 'Complete system integrations, achieve operational scale']
    ]
    
    pdf.data_table(['Timeline', 'Milestone', 'Key Activities'], timeline_data, [30, 50, 110])
    
    # Institutional Credibility
    pdf.chapter_title('INSTITUTIONAL CREDIBILITY')
    pdf.chapter_body('NVC Banking Platform maintains the highest levels of institutional credibility through:')
    
    pdf.set_font('Times', '', 12)
    pdf.ln(2)
    pdf.cell(10, 5, '•', 0, 0)
    pdf.cell(0, 5, 'Unit Investment Trust - CUSIP# 67074B105, ISIN# US67074B1052', 0, 1)
    pdf.cell(10, 5, '•', 0, 0)
    pdf.cell(0, 5, 'NVC Fund Bond - CUSIP# 62944AAA4, ISIN# US62944AAA43', 0, 1)
    pdf.cell(10, 5, '•', 0, 0)
    pdf.cell(0, 5, 'Bloomberg Listings - Bloomberg Identifier: 3387420Z US, BBGID: BBG000P6FW5', 0, 1)
    pdf.cell(10, 5, '•', 0, 0)
    pdf.cell(0, 5, 'SEC Registered Transfer Agent - Transferonline Inc. (since 2009)', 0, 1)
    pdf.ln(10)
    
    # Contact Information
    pdf.chapter_title('CONTACT INFORMATION')
    pdf.chapter_body('To discuss this investment opportunity in more detail, please contact our Investor Relations team:')
    
    pdf.set_font('Times', 'B', 12)
    pdf.cell(30, 6, 'Phone:', 0, 0)
    pdf.set_font('Times', '', 12)
    pdf.cell(0, 6, '+1 (XXX) XXX-XXXX', 0, 1)
    
    pdf.set_font('Times', 'B', 12)
    pdf.cell(30, 6, 'Email:', 0, 0)
    pdf.set_font('Times', '', 12)
    pdf.cell(0, 6, 'investors@nvcbanking.com', 0, 1)
    
    pdf.set_font('Times', 'B', 12)
    pdf.cell(30, 6, 'Website:', 0, 0)
    pdf.set_font('Times', '', 12)
    pdf.cell(0, 6, 'www.nvcbanking.com/investors', 0, 1)
    
    pdf.set_font('Times', 'B', 12)
    pdf.cell(30, 6, 'Address:', 0, 0)
    pdf.set_font('Times', '', 12)
    pdf.cell(0, 6, '[Corporate Headquarters Address]', 0, 1)
    pdf.ln(15)
    
    # Disclaimer
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 5, 'DISCLAIMER:', 0, 1)
    pdf.set_font('Arial', 'I', 8)
    pdf.multi_cell(0, 4, 'This document is for informational purposes only and does not constitute an offer to sell or a solicitation of an offer to buy any securities. The information contained herein is subject to change without notice. NVC Banking Platform does not make any representation or warranty as to the accuracy or completeness of the information contained herein. Investments involve risk and are not guaranteed. Prospective investors should consult with their financial, legal, and tax advisors before investing.')
    
    # Output PDF
    pdf_dir = 'static/docs'
    if not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir)
        
    pdf_path = os.path.join(pdf_dir, 'nvc_investment_prospectus.pdf')
    pdf.output(pdf_path, 'F')
    
    return pdf_path

if __name__ == "__main__":
    generate_prospectus()
    print("Investment prospectus PDF generated successfully!")