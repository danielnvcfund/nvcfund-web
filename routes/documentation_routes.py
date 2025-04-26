"""
Documentation Routes
This module provides routes for accessing platform documentation.
"""

import os
import logging
from flask import Blueprint, send_from_directory, render_template, abort, current_app
from flask_login import login_required, current_user
from auth import admin_required

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
documentation_bp = Blueprint('documentation', __name__, url_prefix='/documentation')

@documentation_bp.route('/')
@login_required
def documentation_index():
    """Documentation index page listing all available documents"""
    # Get list of PDF files in docs directory
    docs_dir = os.path.join(current_app.root_path, 'docs')
    pdf_files = []
    md_files = []
    html_guides = []
    
    # Add HTML guides from static/docs directory
    html_guides.append({
        'name': 'Server-to-Server Integration Guide',
        'url': '/static/docs/server_to_server_integration_guide.html',
        'description': 'Comprehensive guide for integrating with the Server-to-Server transfer system'
    })
    
    html_guides.append({
        'name': 'NVC Banking Platform Capabilities',
        'url': '/static/docs/nvc_mainnet_readiness_assessment.html',
        'description': 'Current capabilities and mainnet readiness assessment for the NVC Banking Platform'
    })
    
    # Add PDF versions of the HTML guides
    if os.path.exists(os.path.join(docs_dir, 'server_to_server_integration_guide.pdf')):
        pdf_files.append({
            'name': 'Server-to-Server Integration Guide (PDF)',
            'filename': 'server_to_server_integration_guide.pdf',
            'url': '/documentation/pdf/server_to_server_integration_guide.pdf'
        })
        
    if os.path.exists(os.path.join(docs_dir, 'nvc_banking_platform_capabilities.pdf')):
        pdf_files.append({
            'name': 'NVC Banking Platform Capabilities (PDF)',
            'filename': 'nvc_banking_platform_capabilities.pdf',
            'url': '/documentation/pdf/nvc_banking_platform_capabilities.pdf'
        })
    
    try:
        for filename in os.listdir(docs_dir):
            if filename.endswith('.pdf'):
                # Custom name for NVC EDI Guide
                if filename == 'nvc_electronic_data_interchange_guide.pdf':
                    name = 'NVC Electronic Data Interchange Guide'
                else:
                    name = filename[:-4].replace('_', ' ').title()
                
                pdf_files.append({
                    'name': name,
                    'filename': filename,
                    'url': f'/documentation/pdf/{filename}'
                })
            elif filename.endswith('.md') and not filename.startswith('README'):
                name = filename[:-3].replace('_', ' ').title()
                md_files.append({
                    'name': name,
                    'filename': filename,
                    'url': f'/documentation/view/{filename}'
                })
    except FileNotFoundError:
        logger.error("Documentation directory not found")
        pdf_files = []
        md_files = []
    
    # Sort files alphabetically by name
    pdf_files.sort(key=lambda x: x['name'])
    md_files.sort(key=lambda x: x['name'])
    
    return render_template(
        'documentation/index.html', 
        pdf_files=pdf_files,
        md_files=md_files,
        html_guides=html_guides,
        is_admin=current_user.is_admin if hasattr(current_user, 'is_admin') else False
    )

@documentation_bp.route('/pdf/<filename>')
@login_required
def get_pdf_document(filename):
    """Serve PDF document from docs directory"""
    # Validate filename to prevent directory traversal
    if '..' in filename or '/' in filename:
        abort(404)
    
    docs_dir = os.path.join(current_app.root_path, 'docs')
    try:
        return send_from_directory(docs_dir, filename, as_attachment=False)
    except FileNotFoundError:
        logger.error(f"PDF document not found: {filename}")
        abort(404)

@documentation_bp.route('/view/<filename>')
@login_required
def view_markdown_document(filename):
    """View markdown document content"""
    # Validate filename to prevent directory traversal
    if '..' in filename or '/' in filename:
        abort(404)
    
    # Only allow .md files
    if not filename.endswith('.md'):
        abort(404)
    
    docs_dir = os.path.join(current_app.root_path, 'docs')
    try:
        with open(os.path.join(docs_dir, filename), 'r') as f:
            content = f.read()
        
        title = filename[:-3].replace('_', ' ').title()
        return render_template(
            'documentation/markdown_view.html',
            title=title,
            content=content,
            is_admin=current_user.is_admin if hasattr(current_user, 'is_admin') else False
        )
    except FileNotFoundError:
        logger.error(f"Markdown document not found: {filename}")
        abort(404)

@documentation_bp.route('/admin')
@login_required
@admin_required
def admin_documentation():
    """Admin-specific documentation"""
    # Get list of admin-specific PDF files
    docs_dir = os.path.join(current_app.root_path, 'docs')
    admin_pdf_files = []
    admin_md_files = []
    
    try:
        for filename in os.listdir(docs_dir):
            if filename.startswith('admin_') and filename.endswith('.pdf'):
                name = filename[6:-4].replace('_', ' ').title()
                admin_pdf_files.append({
                    'name': name,
                    'filename': filename,
                    'url': f'/documentation/pdf/{filename}'
                })
            elif filename.startswith('admin_') and filename.endswith('.md'):
                name = filename[6:-3].replace('_', ' ').title()
                admin_md_files.append({
                    'name': name,
                    'filename': filename,
                    'url': f'/documentation/view/{filename}'
                })
    except FileNotFoundError:
        logger.error("Documentation directory not found")
        admin_pdf_files = []
        admin_md_files = []
    
    # Sort files alphabetically by name
    admin_pdf_files.sort(key=lambda x: x['name'])
    admin_md_files.sort(key=lambda x: x['name'])
    
    # Add technical documents that aren't prefixed with admin_
    technical_docs = [
        'blockchain_vs_swift.pdf', 
        'payment_operations_guide.pdf',
        'nvc_banking_platform_capabilities.pdf',
        'server_to_server_integration_guide.pdf'
    ]
    for filename in technical_docs:
        if os.path.exists(os.path.join(docs_dir, filename)):
            # Custom names for some documents
            if filename == 'nvc_banking_platform_capabilities.pdf':
                name = 'NVC Banking Platform Capabilities'
            elif filename == 'server_to_server_integration_guide.pdf':
                name = 'Server-to-Server Integration Guide'
            else:
                name = filename[:-4].replace('_', ' ').title()
            
            admin_pdf_files.append({
                'name': name,
                'filename': filename,
                'url': f'/documentation/pdf/{filename}'
            })
    
    return render_template(
        'documentation/admin_docs.html',
        pdf_files=admin_pdf_files,
        md_files=admin_md_files
    )