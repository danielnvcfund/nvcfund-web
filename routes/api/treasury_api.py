"""
Treasury API Routes
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from models import db, FinancialInstitution

# Create the treasury API blueprint
treasury_api_bp = Blueprint('treasury_api', __name__)


@treasury_api_bp.route('/add_institution', methods=['POST'])
@login_required
def add_institution():
    """Add a new financial institution via API"""
    try:
        if request.is_json:
            data = request.get_json()
        else:
            # For non-JSON requests, try to get data from form
            data = {
                'name': request.form.get('name', ''),
                'institution_type': request.form.get('institution_type', 'BANK')
            }
        
        if not data.get('name'):
            return jsonify({
                'success': False,
                'message': 'Institution name is required'
            }), 400
            
        # Create and save the new institution
        institution = FinancialInstitution(
            name=data.get('name'),
            institution_type=data.get('institution_type', 'BANK'),
            is_active=True
        )
        
        db.session.add(institution)
        db.session.commit()
        
        # Return the created institution
        return jsonify({
            'success': True,
            'message': 'Institution created successfully',
            'institution': {
                'id': institution.id,
                'name': institution.name,
                'type': institution.institution_type
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error creating institution: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error creating institution: {str(e)}'
        }), 500