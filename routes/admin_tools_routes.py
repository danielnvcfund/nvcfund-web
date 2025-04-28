"""
Admin Tools Routes

This module contains routes for administrative tasks, including populating
reference data like financial institutions.
"""

import os
import logging
import json
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import and_, or_

from auth import admin_required
from models import FinancialInstitution, FinancialInstitutionType, db
from financial_institutions_reference import FINANCIAL_INSTITUTIONS_REFERENCE

logger = logging.getLogger(__name__)

# Create the blueprint
admin_tools_bp = Blueprint('admin_tools', __name__, url_prefix='/admin-tools')


@admin_tools_bp.route('/financial-institutions', methods=['GET'])
@login_required
@admin_required
def financial_institutions_tool():
    """
    Admin tool to view and manage the financial institutions reference data
    """
    # Retrieve all financial institutions from the database for comparison
    existing_institutions = FinancialInstitution.query.all()
    existing_swift_codes = {inst.swift_code for inst in existing_institutions if inst.swift_code}
    
    # Transform reference data for the template
    institutions_by_category = {}
    total_count = 0
    
    for category, institutions in FINANCIAL_INSTITUTIONS_REFERENCE.items():
        category_institutions = []
        
        for inst_data in institutions:
            total_count += 1
            
            # Check if this institution exists in the database
            exists = inst_data.get('swift_code') in existing_swift_codes
            
            # Find the DB ID if it exists
            db_id = None
            if exists:
                for db_inst in existing_institutions:
                    if db_inst.swift_code == inst_data.get('swift_code'):
                        db_id = db_inst.id
                        break
            
            # Add to the list for display
            category_institutions.append({
                'name': inst_data.get('name'),
                'swift_code': inst_data.get('swift_code'),
                'rtgs_system': inst_data.get('rtgs_system'),
                'country': inst_data.get('country'),
                'institution_type': FinancialInstitutionType[inst_data.get('type', 'BANK')],
                'exists': exists,
                'id': db_id
            })
        
        institutions_by_category[category] = category_institutions
    
    existing_count = len(existing_swift_codes)
    
    return render_template(
        'admin/financial_institutions_tool.html',
        institutions_by_category=institutions_by_category,
        total_count=total_count,
        existing_count=existing_count,
        FinancialInstitutionType=FinancialInstitutionType
    )


@admin_tools_bp.route('/financial-institutions/add', methods=['POST'])
@login_required
@admin_required
def add_financial_institution():
    """
    Add a single financial institution to the database
    """
    institution_name = request.form.get('name')
    
    # Find the institution in the reference data
    institution_data = None
    for category, institutions in FINANCIAL_INSTITUTIONS_REFERENCE.items():
        for inst in institutions:
            if inst.get('name') == institution_name:
                institution_data = inst
                break
        if institution_data:
            break
    
    if not institution_data:
        flash('Institution not found in reference data.', 'danger')
        return redirect(url_for('admin_tools.financial_institutions_tool'))
    
    try:
        # Check if it already exists
        existing = FinancialInstitution.query.filter_by(swift_code=institution_data.get('swift_code')).first()
        if existing:
            flash(f'Institution {institution_name} already exists.', 'warning')
            return redirect(url_for('admin_tools.financial_institutions_tool'))
        
        # Create the new institution
        new_institution = FinancialInstitution(
            name=institution_data.get('name'),
            swift_code=institution_data.get('swift_code'),
            institution_type=FinancialInstitutionType[institution_data.get('type', 'BANK')],
            rtgs_enabled=True,
            rtgs_system=institution_data.get('rtgs_system'),
            ethereum_address=institution_data.get('ethereum_address', ''),
            api_endpoint=institution_data.get('api_endpoint', ''),
            metadata_json=json.dumps({
                'country': institution_data.get('country', ''),
                'added_on': datetime.utcnow().isoformat()
            })
        )
        
        db.session.add(new_institution)
        db.session.commit()
        
        flash(f'Successfully added {institution_name} to the database.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding institution: {str(e)}', 'danger')
        logger.error(f"Error adding institution {institution_name}: {str(e)}", exc_info=True)
    
    return redirect(url_for('admin_tools.financial_institutions_tool'))


@admin_tools_bp.route('/financial-institutions/add-all', methods=['POST'])
@login_required
@admin_required
def add_all_financial_institutions():
    """
    Add all missing financial institutions to the database
    """
    # Get existing institutions to avoid duplicates
    existing_institutions = FinancialInstitution.query.all()
    existing_swift_codes = {inst.swift_code for inst in existing_institutions if inst.swift_code}
    
    added_count = 0
    error_count = 0
    
    for category, institutions in FINANCIAL_INSTITUTIONS_REFERENCE.items():
        for inst_data in institutions:
            swift_code = inst_data.get('swift_code')
            
            # Skip if it already exists
            if swift_code in existing_swift_codes:
                continue
            
            try:
                # Create the new institution
                new_institution = FinancialInstitution(
                    name=inst_data.get('name'),
                    swift_code=swift_code,
                    institution_type=FinancialInstitutionType[inst_data.get('type', 'BANK')],
                    rtgs_enabled=True,
                    rtgs_system=inst_data.get('rtgs_system'),
                    ethereum_address=inst_data.get('ethereum_address', ''),
                    api_endpoint=inst_data.get('api_endpoint', ''),
                    metadata_json=json.dumps({
                        'country': inst_data.get('country', ''),
                        'added_on': datetime.utcnow().isoformat()
                    })
                )
                
                db.session.add(new_institution)
                added_count += 1
                
                # Commit every 5 institutions to avoid long transactions
                if added_count % 5 == 0:
                    db.session.commit()
                
            except Exception as e:
                error_count += 1
                logger.error(f"Error adding institution {inst_data.get('name')}: {str(e)}", exc_info=True)
    
    # Final commit for any remaining institutions
    try:
        db.session.commit()
        flash(f'Successfully added {added_count} institutions to the database.', 'success')
        if error_count > 0:
            flash(f'There were {error_count} errors. Check the logs for details.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Error committing transaction: {str(e)}', 'danger')
        logger.error(f"Error committing transaction: {str(e)}", exc_info=True)
    
    return redirect(url_for('admin_tools.financial_institutions_tool'))