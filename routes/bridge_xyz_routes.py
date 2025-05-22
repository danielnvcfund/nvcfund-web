"""
Routes for Bridge.xyz partnership documents and integration
"""

from flask import Blueprint, send_from_directory, current_app, render_template
import os


bridge_xyz_bp = Blueprint('bridge_xyz', __name__)


@bridge_xyz_bp.route('/partnership-loi')
def bridge_xyz_loi():
    """View the Bridge.xyz Letter of Intent document"""
    return render_template('bridge_xyz/partnership_overview.html')


@bridge_xyz_bp.route('/download-loi')
def download_bridge_loi():
    """Download the Bridge.xyz LOI PDF"""
    docs_dir = os.path.join(current_app.root_path, 'static', 'docs')
    return send_from_directory(
        directory=docs_dir,
        path='NVCT_Bridge_XYZ_LOI.pdf',
        as_attachment=True
    )


@bridge_xyz_bp.route('/download-loi-docx')
def download_bridge_loi_docx():
    """Download the Bridge.xyz LOI as an editable Word document"""
    docs_dir = os.path.join(current_app.root_path, 'static', 'docs')
    return send_from_directory(
        directory=docs_dir,
        path='NVCT_Bridge_XYZ_LOI.docx',
        as_attachment=True
    )


# Register additional Bridge.xyz integration routes here as the partnership develops