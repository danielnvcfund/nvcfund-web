"""
Generate NVC Fund Bank Custody Services Agreement

This module generates a PDF document for the NVC Fund Bank Custody Services Agreement.
"""

import os
from fpdf import FPDF
import datetime


class PDFWithPageNumbers(FPDF):
    """Custom PDF class that adds page numbers to each page"""
    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", 0, 0, "C")


def generate_custody_agreement():
    """Generate a PDF for the NVC Fund Bank Custody Services Agreement."""
    # Initialize PDF with page numbers
    pdf = PDFWithPageNumbers()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Set document information
    pdf.set_title("NVC Fund Bank Custody Services Agreement")
    pdf.set_author("NVC Fund Bank")
    
    # Add title
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "CUSTODY SERVICES AGREEMENT", 0, 1, "C")
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "NVC FUND BANK", 0, 1, "C")
    
    # Introduction
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "AGREEMENT", 0, 1)
    
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "THIS CUSTODY SERVICES AGREEMENT (the \"Agreement\") is made and entered into as of the Effective Date set forth below, by and between:")
    
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 6, "NVC Fund Bank", 0, 1)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "a Supranational Sovereign Financial Institution established under the African Union Treaty framework with SWIFT code NVCFBKAU and ACH Routing Number 031176110, (hereinafter referred to as \"Custodian\")")
    
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 6, "AND", 0, 1, "C")
    
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 6, "[CLIENT NAME]", 0, 1)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "a [legal entity type] organized and existing under the laws of [jurisdiction], with its principal place of business at [address], (hereinafter referred to as \"Client\")")
    
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 6, "(each a \"Party\" and collectively the \"Parties\")", 0, 1, "C")
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "RECITALS", 0, 1)
    
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "WHEREAS, the Client wishes to engage the Custodian to provide custody services for its assets, including but not limited to financial assets, digital assets, and cryptocurrencies;")
    
    pdf.multi_cell(0, 6, "WHEREAS, the Custodian is willing to provide such custody services to the Client in accordance with the terms and conditions set forth in this Agreement;")
    
    pdf.multi_cell(0, 6, "NOW, THEREFORE, in consideration of the mutual covenants and agreements contained herein, and for other good and valuable consideration, the receipt and sufficiency of which are hereby acknowledged, the Parties hereby agree as follows:")
    
    # Definitions
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "1. DEFINITIONS", 0, 1)
    
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "In this Agreement, unless the context otherwise requires, the following terms shall have the following meanings:")
    
    pdf.set_font("Arial", "B", 11)
    pdf.cell(60, 6, "\"Assets\"", 0, 0)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "means the financial assets, digital assets, cryptocurrencies, and other property of the Client that are held in custody by the Custodian pursuant to this Agreement.")
    
    pdf.set_font("Arial", "B", 11)
    pdf.cell(60, 6, "\"Applicable Law\"", 0, 0)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "means all laws, regulations, rules, orders, directives, guidelines, and standards applicable to the Parties and the services provided under this Agreement.")
    
    pdf.set_font("Arial", "B", 11)
    pdf.cell(60, 6, "\"Business Day\"", 0, 0)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "means a day (other than a Saturday, Sunday, or public holiday) on which banks are open for general business in the respective jurisdictions of the Parties.")
    
    pdf.set_font("Arial", "B", 11)
    pdf.cell(60, 6, "\"Confidential Information\"", 0, 0)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "means any non-public information disclosed by one Party to the other Party in connection with this Agreement, including but not limited to business information, financial information, customer information, and technical information.")
    
    pdf.set_font("Arial", "B", 11)
    pdf.cell(60, 6, "\"Digital Assets\"", 0, 0)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "means cryptocurrencies, tokens, stablecoins, and other blockchain-based assets, including but not limited to NVCT, BTC, ETH, and other supported digital currencies.")
    
    pdf.set_font("Arial", "B", 11)
    pdf.cell(60, 6, "\"Effective Date\"", 0, 0)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "means the date on which this Agreement is signed by both Parties.")
    
    pdf.set_font("Arial", "B", 11)
    pdf.cell(60, 6, "\"Fees\"", 0, 0)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "means the fees payable by the Client to the Custodian for the provision of the Services, as set forth in Schedule A.")
    
    pdf.set_font("Arial", "B", 11)
    pdf.cell(60, 6, "\"Services\"", 0, 0)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "means the custody services provided by the Custodian to the Client pursuant to this Agreement.")
    
    # Services
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "2. SERVICES", 0, 1)
    
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "2.1 The Custodian shall provide the following Services to the Client:")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "a) Safekeeping of Assets, including secure storage of Digital Assets using cold storage solutions and multi-signature security protocols;")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "b) Settlement of transactions involving the Assets;")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "c) Receipt and delivery of Assets as instructed by the Client;")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "d) Collection of income and other payments with respect to the Assets;")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "e) Recordkeeping and reporting services;")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "f) Private key management for Digital Assets;")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "g) NVCT stablecoin custody services;")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "h) Digital asset transaction processing;")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "i) Blockchain monitoring and reporting services;")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "j) Such other services as may be agreed upon by the Parties from time to time.")
    
    pdf.multi_cell(0, 6, "2.2 The Custodian shall perform the Services with reasonable care, skill, and diligence in accordance with the standards and practices generally accepted in the custody industry and in compliance with Applicable Law.")
    
    # Client Responsibilities
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "3. CLIENT RESPONSIBILITIES", 0, 1)
    
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "3.1 The Client shall:")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "a) Provide the Custodian with complete and accurate information regarding the Assets;")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "b) Issue clear and timely instructions to the Custodian regarding the Assets;")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "c) Pay all Fees and expenses due to the Custodian in accordance with this Agreement;")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "d) Comply with all Applicable Law in connection with this Agreement;")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "e) Provide the Custodian with such information and documentation as the Custodian may reasonably request to fulfill its obligations under this Agreement.")
    
    # Custody of Assets
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "4. CUSTODY OF ASSETS", 0, 1)
    
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "4.1 The Custodian shall hold and segregate the Assets in accordance with Applicable Law and industry standards.")
    
    pdf.multi_cell(0, 6, "4.2 The Custodian shall maintain appropriate records of the Assets held in custody.")
    
    pdf.multi_cell(0, 6, "4.3 The Custodian shall establish and maintain appropriate security measures to safeguard the Assets against unauthorized access, theft, loss, or damage.")
    
    pdf.multi_cell(0, 6, "4.4 For Digital Assets, the Custodian shall:")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "a) Implement cold storage solutions for the storage of private keys;")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "b) Utilize multi-signature security protocols requiring multiple approvals for transactions;")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "c) Employ Hardware Security Module (HSM) integration for enhanced security;")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "d) Maintain backup private keys in secure, geographically distributed locations;")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "e) Conduct regular security audits of its custody systems and protocols.")
    
    # Instructions and Transactions
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "5. INSTRUCTIONS AND TRANSACTIONS", 0, 1)
    
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "5.1 The Custodian shall act only upon Written Instructions from Authorized Persons, except as otherwise expressly provided in this Agreement.")
    
    pdf.multi_cell(0, 6, "5.2 \"Written Instructions\" means instructions in writing received by the Custodian from an Authorized Person, including instructions received by email, secure messaging system, or other electronic means approved by the Custodian.")
    
    pdf.multi_cell(0, 6, "5.3 \"Authorized Persons\" means the individuals designated by the Client as authorized to give instructions to the Custodian on behalf of the Client, as set forth in Schedule B, as may be amended from time to time.")
    
    pdf.multi_cell(0, 6, "5.4 The Custodian may refuse to act upon any instruction that it reasonably believes to be unclear, incomplete, or not given by an Authorized Person.")
    
    pdf.multi_cell(0, 6, "5.5 The Custodian shall use reasonable efforts to execute transactions in accordance with the Client's Written Instructions in a timely manner, subject to market conditions, blockchain network congestion, and other factors beyond the Custodian's reasonable control.")
    
    # Fees and Expenses
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "6. FEES AND EXPENSES", 0, 1)
    
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "6.1 The Client shall pay the Custodian the Fees for the Services as set forth in Schedule A.")
    
    pdf.multi_cell(0, 6, "6.2 The Custodian shall invoice the Client for the Fees on a monthly basis, and the Client shall pay such invoices within thirty (30) days of receipt.")
    
    pdf.multi_cell(0, 6, "6.3 The Client shall reimburse the Custodian for all reasonable out-of-pocket expenses incurred by the Custodian in connection with the provision of the Services.")
    
    pdf.multi_cell(0, 6, "6.4 All Fees and expenses are exclusive of any applicable taxes, which shall be borne by the Client.")
    
    pdf.multi_cell(0, 6, "6.5 The Custodian may revise the Fees from time to time upon ninety (90) days' prior written notice to the Client.")
    
    # Compliance with Applicable Law
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "7. COMPLIANCE WITH APPLICABLE LAW", 0, 1)
    
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "7.1 Each Party shall comply with all Applicable Law in the performance of its obligations under this Agreement, including but not limited to laws and regulations relating to anti-money laundering, counter-terrorism financing, sanctions, and data protection.")
    
    pdf.multi_cell(0, 6, "7.2 The Client shall implement and maintain adequate policies, procedures, and controls to ensure compliance with Applicable Law, including but not limited to customer due diligence and transaction monitoring.")
    
    pdf.multi_cell(0, 6, "7.3 The Client shall provide the Custodian with such information and documentation as the Custodian may reasonably request to fulfill its compliance obligations under Applicable Law.")
    
    pdf.multi_cell(0, 6, "7.4 The Custodian may refuse to process any transaction that it reasonably believes may violate Applicable Law or its internal policies and procedures.")
    
    # Add a new page
    pdf.add_page()
    
    # Confidentiality
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "8. CONFIDENTIALITY", 0, 1)
    
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "8.1 Each Party shall maintain the confidentiality of the Confidential Information of the other Party and shall not disclose such Confidential Information to any third party without the prior written consent of the other Party, except as required by Applicable Law or court order.")
    
    pdf.multi_cell(0, 6, "8.2 Each Party shall use the Confidential Information of the other Party solely for the purpose of performing its obligations under this Agreement.")
    
    pdf.multi_cell(0, 6, "8.3 The confidentiality obligations in this Section 8 shall survive the termination of this Agreement for a period of five (5) years.")
    
    # Data Protection
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "9. DATA PROTECTION", 0, 1)
    
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "9.1 Each Party shall comply with all applicable data protection laws and regulations in the performance of its obligations under this Agreement.")
    
    pdf.multi_cell(0, 6, "9.2 Each Party shall implement appropriate technical and organizational measures to protect personal data processed in connection with this Agreement.")
    
    pdf.multi_cell(0, 6, "9.3 The Custodian shall process personal data only on documented instructions from the Client, unless required to do so by Applicable Law.")
    
    # Liability and Indemnification
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "10. LIABILITY AND INDEMNIFICATION", 0, 1)
    
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "10.1 The Custodian shall be liable to the Client for direct losses, damages, costs, and expenses arising from the Custodian's negligence, willful misconduct, or material breach of this Agreement.")
    
    pdf.multi_cell(0, 6, "10.2 Notwithstanding Section 10.1, the Custodian shall not be liable for:")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "a) Any loss, damage, cost, or expense arising from the acts or omissions of the Client or any third party;")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "b) Any loss, damage, cost, or expense arising from compliance with the Client's instructions;")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "c) Any loss, damage, cost, or expense arising from events beyond the Custodian's reasonable control, including but not limited to natural disasters, acts of war, terrorism, civil unrest, or blockchain network failures;")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "d) Any indirect, special, incidental, consequential, or punitive damages, whether based on contract, tort, or any other legal theory.")
    
    pdf.multi_cell(0, 6, "10.3 The Custodian's maximum aggregate liability under this Agreement shall not exceed the lesser of (i) the value of the Assets held in custody at the time of the event giving rise to the liability, or (ii) the amount of Fees paid by the Client to the Custodian during the twelve (12) months preceding the event giving rise to such liability.")
    
    pdf.multi_cell(0, 6, "10.4 Each Party shall indemnify and hold harmless the other Party from and against any and all third-party claims, liabilities, costs, and expenses (including reasonable attorneys' fees) arising from or in connection with any breach of this Agreement by the indemnifying Party or its negligence or willful misconduct.")
    
    # Term and Termination
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "11. TERM AND TERMINATION", 0, 1)
    
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "11.1 This Agreement shall commence on the Effective Date and shall continue until terminated in accordance with this Section 11.")
    
    pdf.multi_cell(0, 6, "11.2 Either Party may terminate this Agreement by giving ninety (90) days' prior written notice to the other Party.")
    
    pdf.multi_cell(0, 6, "11.3 Either Party may terminate this Agreement with immediate effect by giving written notice to the other Party if:")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "a) The other Party commits a material breach of this Agreement and fails to remedy such breach within thirty (30) days after receiving written notice requiring it to do so;")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "b) The other Party becomes insolvent, bankrupt, or enters into any arrangement with its creditors, or is subject to any similar event or proceeding in any jurisdiction.")
    
    pdf.multi_cell(0, 6, "11.4 Upon termination of this Agreement:")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "a) The Custodian shall deliver the Assets to the Client or as directed by the Client in writing;")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "b) The Client shall pay all outstanding Fees and expenses due to the Custodian;")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "c) The Parties shall cooperate in good faith to ensure an orderly transition of the Assets.")
    
    # Add a new page
    pdf.add_page()
    
    # Force Majeure
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "12. FORCE MAJEURE", 0, 1)
    
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "12.1 Neither Party shall be liable for any delay or failure to perform its obligations under this Agreement to the extent that such delay or failure is caused by events beyond its reasonable control, including but not limited to acts of God, natural disasters, war, terrorism, riots, civil unrest, government actions, power failures, telecommunications failures, or blockchain network failures.")
    
    # Notices
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "13. NOTICES", 0, 1)
    
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "13.1 All notices and other communications under this Agreement shall be in writing and shall be delivered by hand, by courier, by registered mail, or by email to the addresses set forth below or to such other addresses as may be designated by the Parties in writing:")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "If to the Custodian:")
    pdf.set_x(30)
    pdf.multi_cell(0, 6, "NVC Fund Bank")
    pdf.set_x(30)
    pdf.multi_cell(0, 6, "[Address]")
    pdf.set_x(30)
    pdf.multi_cell(0, 6, "Email: [Email]")
    pdf.set_x(30)
    pdf.multi_cell(0, 6, "Attention: [Contact Person]")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "If to the Client:")
    pdf.set_x(30)
    pdf.multi_cell(0, 6, "[Client Name]")
    pdf.set_x(30)
    pdf.multi_cell(0, 6, "[Address]")
    pdf.set_x(30)
    pdf.multi_cell(0, 6, "Email: [Email]")
    pdf.set_x(30)
    pdf.multi_cell(0, 6, "Attention: [Contact Person]")
    
    # Governing Law and Dispute Resolution
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "14. GOVERNING LAW AND DISPUTE RESOLUTION", 0, 1)
    
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "14.1 This Agreement shall be governed by and construed in accordance with the laws of [Jurisdiction], without regard to its conflict of laws principles.")
    
    pdf.multi_cell(0, 6, "14.2 Any dispute, controversy, or claim arising out of or relating to this Agreement, or the breach, termination, or invalidity thereof, shall be settled by arbitration in accordance with the rules of the [Arbitration Institution] by [Number] arbitrator(s) appointed in accordance with said rules.")
    
    pdf.multi_cell(0, 6, "14.3 The place of arbitration shall be [City, Country].")
    
    pdf.multi_cell(0, 6, "14.4 The language of the arbitration shall be English.")
    
    # Miscellaneous
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "15. MISCELLANEOUS", 0, 1)
    
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "15.1 This Agreement constitutes the entire agreement between the Parties with respect to the subject matter hereof and supersedes all prior agreements, understandings, negotiations, and discussions, whether oral or written.")
    
    pdf.multi_cell(0, 6, "15.2 This Agreement may be amended only by a written instrument signed by both Parties.")
    
    pdf.multi_cell(0, 6, "15.3 Neither Party may assign or transfer any of its rights or obligations under this Agreement without the prior written consent of the other Party, except that the Custodian may assign this Agreement to an affiliate without the Client's consent.")
    
    pdf.multi_cell(0, 6, "15.4 If any provision of this Agreement is found to be invalid or unenforceable, the remaining provisions shall remain in full force and effect.")
    
    pdf.multi_cell(0, 6, "15.5 The failure of either Party to enforce any right or provision of this Agreement shall not constitute a waiver of such right or provision.")
    
    pdf.multi_cell(0, 6, "15.6 This Agreement may be executed in counterparts, each of which shall be deemed an original, but all of which together shall constitute one and the same instrument.")
    
    pdf.multi_cell(0, 6, "15.7 The headings in this Agreement are for convenience only and shall not affect its interpretation.")
    
    # Schedules
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "16. SCHEDULES", 0, 1)
    
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "The following Schedules form an integral part of this Agreement:")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "Schedule A: Fees")
    
    pdf.set_x(20)
    pdf.multi_cell(0, 6, "Schedule B: Authorized Persons")
    
    # Signature Block
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "IN WITNESS WHEREOF, the Parties have executed this Agreement as of the Effective Date.", 0, 1)
    
    pdf.set_font("Arial", "B", 11)
    pdf.cell(90, 6, "NVC FUND BANK", 0, 0)
    pdf.cell(90, 6, "CLIENT", 0, 1)
    
    pdf.cell(90, 6, "By: ________________________", 0, 0)
    pdf.cell(90, 6, "By: ________________________", 0, 1)
    
    pdf.cell(90, 6, "Name: _____________________", 0, 0)
    pdf.cell(90, 6, "Name: _____________________", 0, 1)
    
    pdf.cell(90, 6, "Title: ______________________", 0, 0)
    pdf.cell(90, 6, "Title: ______________________", 0, 1)
    
    pdf.cell(90, 6, "Date: ______________________", 0, 0)
    pdf.cell(90, 6, "Date: ______________________", 0, 1)
    
    # Add Schedule A - Fees
    pdf.add_page()
    
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "SCHEDULE A", 0, 1)
    pdf.cell(0, 10, "FEES", 0, 1)
    
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "The Custodian shall charge the following Fees for the Services:")
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "1. Custody Fees", 0, 1)
    
    pdf.set_font("Arial", "", 11)
    pdf.cell(90, 6, "Traditional Assets:", 0, 0)
    pdf.cell(90, 6, "0.XX% per annum of assets under custody", 0, 1)
    
    pdf.cell(90, 6, "Digital Assets:", 0, 0)
    pdf.cell(90, 6, "0.XX% per annum of assets under custody", 0, 1)
    
    pdf.cell(90, 6, "NVCT Stablecoin:", 0, 0)
    pdf.cell(90, 6, "0.XX% per annum of assets under custody", 0, 1)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "2. Transaction Fees", 0, 1)
    
    pdf.set_font("Arial", "", 11)
    pdf.cell(90, 6, "Traditional Asset Transactions:", 0, 0)
    pdf.cell(90, 6, "$XX.XX per transaction", 0, 1)
    
    pdf.cell(90, 6, "Digital Asset Transactions:", 0, 0)
    pdf.cell(90, 6, "$XX.XX per transaction", 0, 1)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "3. Additional Services", 0, 1)
    
    pdf.set_font("Arial", "", 11)
    pdf.cell(90, 6, "Custom Reporting:", 0, 0)
    pdf.cell(90, 6, "$XX.XX per report", 0, 1)
    
    pdf.cell(90, 6, "Tax Reporting:", 0, 0)
    pdf.cell(90, 6, "$XX.XX per report", 0, 1)
    
    pdf.cell(90, 6, "Audit Support:", 0, 0)
    pdf.cell(90, 6, "$XXX.XX per hour", 0, 1)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "4. Minimum Fee", 0, 1)
    
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "The minimum monthly fee for custody services is $X,XXX.XX.")
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "5. Fee Calculation and Payment", 0, 1)
    
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "5.1 Custody fees are calculated based on the average daily value of assets under custody during the billing period.")
    
    pdf.multi_cell(0, 6, "5.2 Fees are invoiced monthly in arrears and are payable within thirty (30) days of receipt of the invoice.")
    
    pdf.multi_cell(0, 6, "5.3 The Client authorizes the Custodian to deduct fees directly from the Client's account if payment is not received within thirty (30) days of the invoice date.")
    
    # Add Schedule B - Authorized Persons
    pdf.add_page()
    
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "SCHEDULE B", 0, 1)
    pdf.cell(0, 10, "AUTHORIZED PERSONS", 0, 1)
    
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "The following individuals are designated by the Client as Authorized Persons who may give instructions to the Custodian on behalf of the Client:")
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "1. Primary Authorized Persons", 0, 1)
    
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "Name: _____________________________")
    pdf.multi_cell(0, 6, "Title: _____________________________")
    pdf.multi_cell(0, 6, "Email: _____________________________")
    pdf.multi_cell(0, 6, "Phone: _____________________________")
    pdf.multi_cell(0, 6, "Specimen Signature: _____________________________")
    
    pdf.ln(5)
    
    pdf.multi_cell(0, 6, "Name: _____________________________")
    pdf.multi_cell(0, 6, "Title: _____________________________")
    pdf.multi_cell(0, 6, "Email: _____________________________")
    pdf.multi_cell(0, 6, "Phone: _____________________________")
    pdf.multi_cell(0, 6, "Specimen Signature: _____________________________")
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "2. Secondary Authorized Persons", 0, 1)
    
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "Name: _____________________________")
    pdf.multi_cell(0, 6, "Title: _____________________________")
    pdf.multi_cell(0, 6, "Email: _____________________________")
    pdf.multi_cell(0, 6, "Phone: _____________________________")
    pdf.multi_cell(0, 6, "Specimen Signature: _____________________________")
    
    pdf.ln(5)
    
    pdf.multi_cell(0, 6, "Name: _____________________________")
    pdf.multi_cell(0, 6, "Title: _____________________________")
    pdf.multi_cell(0, 6, "Email: _____________________________")
    pdf.multi_cell(0, 6, "Phone: _____________________________")
    pdf.multi_cell(0, 6, "Specimen Signature: _____________________________")
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "3. Certification", 0, 1)
    
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, "I, the undersigned, hereby certify that the above individuals have been duly authorized by the Client to give instructions to the Custodian on behalf of the Client in connection with the Custody Services Agreement.")
    
    pdf.ln(10)
    
    pdf.cell(90, 6, "Signature: ________________________", 0, 1)
    pdf.cell(90, 6, "Name: _____________________________", 0, 1)
    pdf.cell(90, 6, "Title: ______________________________", 0, 1)
    pdf.cell(90, 6, "Date: ______________________________", 0, 1)
    
    # Create the directory if it doesn't exist
    os.makedirs("static/documents", exist_ok=True)
    
    # Save the PDF
    pdf_path = "static/documents/NVC_Fund_Bank_Custody_Agreement.pdf"
    pdf.output(pdf_path)
    
    return pdf_path


if __name__ == "__main__":
    print(f"Generating Custody Agreement PDF at: {generate_custody_agreement()}")