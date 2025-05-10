"""
Document Routes
This module provides routes for accessing PDF documents and other resources
"""

import os
from flask import Blueprint, send_from_directory, render_template, current_app

# Create blueprint
docs_bp = Blueprint('docs', __name__, url_prefix='/documents')

@docs_bp.route('/')
def index():
    """List available documents"""
    documents = [
        {
            'name': 'NVC Banking Platform Exchange Whitepaper',
            'description': 'Comprehensive overview of the NVC Banking Platform Exchange and how it transforms global currency conversion and payment settlement.',
            'filename': 'NVC_Banking_Platform_Exchange.pdf',
            'date': 'May 2025',
            'type': 'PDF',
            'size': '1.2 MB'
        }
    ]
    
    return render_template(
        'documents/index.html',
        documents=documents,
        title="NVC Banking Platform Documents"
    )

@docs_bp.route('/view/<filename>')
def view_document(filename):
    """View a specific document"""
    return send_from_directory(
        os.path.join(current_app.root_path, 'static', 'docs'),
        filename
    )