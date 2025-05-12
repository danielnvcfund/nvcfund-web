"""
Routes for document downloads
"""

from flask import Blueprint, send_from_directory, render_template
import os
import datetime
from generate_custody_agreement import generate_custody_agreement

document_download_bp = Blueprint('document_download', __name__, url_prefix='')


@document_download_bp.route('/download-center')
def download_center():
    """Render the document download center page"""
    
    # Ensure the Custody Agreement exists
    custody_agreement_path = "static/documents/NVC_Fund_Bank_Custody_Agreement.pdf"
    if not os.path.exists(custody_agreement_path):
        generate_custody_agreement()
    
    documents = [
        {
            "name": "Correspondent Banking Agreement (PDF)",
            "description": "Official agreement template for establishing correspondent banking relationships (PDF format)",
            "path": "/download/pdf/correspondent-banking-agreement",
            "size": os.path.getsize("static/documents/NVC_Fund_Bank_Correspondent_Banking_Agreement.pdf") if os.path.exists("static/documents/NVC_Fund_Bank_Correspondent_Banking_Agreement.pdf") else 0,
            "date": datetime.datetime.fromtimestamp(os.path.getmtime("static/documents/NVC_Fund_Bank_Correspondent_Banking_Agreement.pdf")).strftime("%Y-%m-%d") if os.path.exists("static/documents/NVC_Fund_Bank_Correspondent_Banking_Agreement.pdf") else datetime.datetime.now().strftime("%Y-%m-%d")
        },
        {
            "name": "Correspondent Banking Agreement (Word)",
            "description": "Editable version of the correspondent banking agreement template (Microsoft Word format)",
            "path": "/download/docx/correspondent-banking-agreement",
            "size": os.path.getsize("static/documents/NVC_Fund_Bank_Correspondent_Banking_Agreement.docx") if os.path.exists("static/documents/NVC_Fund_Bank_Correspondent_Banking_Agreement.docx") else 0,
            "date": datetime.datetime.fromtimestamp(os.path.getmtime("static/documents/NVC_Fund_Bank_Correspondent_Banking_Agreement.docx")).strftime("%Y-%m-%d") if os.path.exists("static/documents/NVC_Fund_Bank_Correspondent_Banking_Agreement.docx") else datetime.datetime.now().strftime("%Y-%m-%d")
        },
        {
            "name": "Custody Services Agreement (PDF)",
            "description": "Official agreement template for digital and traditional asset custody services (PDF format)",
            "path": "/download/pdf/custody-agreement",
            "size": os.path.getsize(custody_agreement_path) if os.path.exists(custody_agreement_path) else 0,
            "date": datetime.datetime.fromtimestamp(os.path.getmtime(custody_agreement_path)).strftime("%Y-%m-%d") if os.path.exists(custody_agreement_path) else datetime.datetime.now().strftime("%Y-%m-%d")
        }
    ]
    
    return render_template('document_download.html', documents=documents)


@document_download_bp.route('/download/pdf/correspondent-banking-agreement')
def download_correspondent_agreement_pdf():
    """Download the Correspondent Banking Agreement PDF"""
    return send_from_directory('static/documents', 'NVC_Fund_Bank_Correspondent_Banking_Agreement.pdf')


@document_download_bp.route('/download/docx/correspondent-banking-agreement')
def download_correspondent_agreement_docx():
    """Download the Correspondent Banking Agreement Word document"""
    return send_from_directory('static/documents', 'NVC_Fund_Bank_Correspondent_Banking_Agreement.docx')


@document_download_bp.route('/download/pdf/custody-agreement')
def download_custody_agreement_pdf():
    """Download the Custody Services Agreement PDF"""
    # Ensure the file exists
    custody_agreement_path = "static/documents/NVC_Fund_Bank_Custody_Agreement.pdf"
    if not os.path.exists(custody_agreement_path):
        generate_custody_agreement()
    
    return send_from_directory('static/documents', 'NVC_Fund_Bank_Custody_Agreement.pdf')