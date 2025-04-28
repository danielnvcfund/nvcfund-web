"""
Admin Tools Routes

This module contains routes for administrative tasks, including populating
reference data like financial institutions.
"""

import json
import logging
from datetime import datetime

from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user

from app import db
from models import FinancialInstitution, FinancialInstitutionType, UserRole
from auth import admin_required
from blockchain_utils import generate_ethereum_account
from financial_institutions_reference import FINANCIAL_INSTITUTIONS

# Create the blueprint
admin_tools_bp = Blueprint('admin_tools', __name__)
logger = logging.getLogger(__name__)


@admin_tools_bp.route('/admin/tools/financial-institutions', methods=['GET'])
@login_required
@admin_required
def financial_institutions_tool():
    """
    Admin tool to view and manage the financial institutions reference data
    """
    # Get financial institutions grouped by category
    institutions_by_category = {}
    for institution_data in FINANCIAL_INSTITUTIONS:
        category = institution_data.get('category', 'Other')
        if category not in institutions_by_category:
            institutions_by_category[category] = []
        
        # Check if institution exists in database
        existing = FinancialInstitution.query.filter_by(name=institution_data['name']).first()
        
        # Add status to the institution data for display
        institution_data_copy = institution_data.copy()
        institution_data_copy['exists'] = existing is not None
        institution_data_copy['id'] = existing.id if existing else None
        
        institutions_by_category[category].append(institution_data_copy)
    
    # Count how many exist vs total
    existing_count = sum(1 for inst in FINANCIAL_INSTITUTIONS 
                        if FinancialInstitution.query.filter_by(name=inst['name']).first())
    total_count = len(FINANCIAL_INSTITUTIONS)
    
    return render_template(
        'admin/financial_institutions_tool.html',
        institutions_by_category=institutions_by_category,
        existing_count=existing_count,
        total_count=total_count,
        FinancialInstitutionType=FinancialInstitutionType
    )


@admin_tools_bp.route('/admin/tools/add-financial-institution', methods=['POST'])
@login_required
@admin_required
def add_financial_institution():
    """
    Add a single financial institution to the database
    """
    institution_name = request.form.get('name')
    
    # Find the institution in the reference data
    institution_data = None
    for inst in FINANCIAL_INSTITUTIONS:
        if inst['name'] == institution_name:
            institution_data = inst
            break
    
    if not institution_data:
        flash(f"Institution '{institution_name}' not found in reference data", "danger")
        return redirect(url_for('admin_tools.financial_institutions_tool'))
    
    # Check if institution already exists
    existing_institution = FinancialInstitution.query.filter_by(name=institution_data["name"]).first()
    if existing_institution:
        flash(f"Institution '{institution_data['name']}' already exists (ID: {existing_institution.id})", "warning")
        return redirect(url_for('admin_tools.financial_institutions_tool'))

    try:
        # Generate Ethereum address for the institution
        eth_address, _ = generate_ethereum_account()
        if not eth_address:
            flash(f"Failed to generate Ethereum address for {institution_data['name']}", "danger")
            return redirect(url_for('admin_tools.financial_institutions_tool'))

        # Prepare metadata with country, RTGS information, and category
        metadata = {
            "country": institution_data["country"],
            "rtgs_system": institution_data["rtgs_system"],
            "category": institution_data.get("category", "Other"),
            "added_at": datetime.utcnow().isoformat(),
            "added_by": current_user.username
        }

        # Add SWIFT info if available
        if institution_data["swift_code"]:
            metadata["swift"] = {"bic": institution_data["swift_code"]}

        # Create new institution
        institution = FinancialInstitution(
            name=institution_data["name"],
            institution_type=institution_data["institution_type"],
            ethereum_address=eth_address,
            swift_code=institution_data["swift_code"],
            rtgs_enabled=institution_data["rtgs_enabled"],
            s2s_enabled=institution_data["s2s_enabled"],
            is_active=institution_data["is_active"],
            metadata_json=json.dumps(metadata)
        )

        db.session.add(institution)
        db.session.commit()
        
        flash(f"Successfully added {institution_data['name']} (ID: {institution.id})", "success")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding {institution_data['name']}: {str(e)}")
        flash(f"Error adding {institution_data['name']}: {str(e)}", "danger")
    
    return redirect(url_for('admin_tools.financial_institutions_tool'))


@admin_tools_bp.route('/admin/tools/add-all-financial-institutions', methods=['POST'])
@login_required
@admin_required
def add_all_financial_institutions():
    """
    Add all missing financial institutions to the database
    """
    # Get all missing institutions
    missing_institutions = []
    for institution_data in FINANCIAL_INSTITUTIONS:
        existing = FinancialInstitution.query.filter_by(name=institution_data['name']).first()
        if not existing:
            missing_institutions.append(institution_data)
    
    # Add institutions one by one
    added_count = 0
    error_count = 0
    
    for institution_data in missing_institutions:
        try:
            # Generate Ethereum address for the institution
            eth_address, _ = generate_ethereum_account()
            if not eth_address:
                logger.error(f"Failed to generate Ethereum address for {institution_data['name']}")
                error_count += 1
                continue

            # Prepare metadata with country, RTGS information, and category
            metadata = {
                "country": institution_data["country"],
                "rtgs_system": institution_data["rtgs_system"],
                "category": institution_data.get("category", "Other"),
                "added_at": datetime.utcnow().isoformat(),
                "added_by": current_user.username
            }

            # Add SWIFT info if available
            if institution_data["swift_code"]:
                metadata["swift"] = {"bic": institution_data["swift_code"]}

            # Create new institution
            institution = FinancialInstitution(
                name=institution_data["name"],
                institution_type=institution_data["institution_type"],
                ethereum_address=eth_address,
                swift_code=institution_data["swift_code"],
                rtgs_enabled=institution_data["rtgs_enabled"],
                s2s_enabled=institution_data["s2s_enabled"],
                is_active=institution_data["is_active"],
                metadata_json=json.dumps(metadata)
            )

            db.session.add(institution)
            db.session.commit()
            added_count += 1
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding {institution_data['name']}: {str(e)}")
            error_count += 1
    
    if added_count > 0 and error_count == 0:
        flash(f"Successfully added {added_count} financial institutions", "success")
    elif added_count > 0 and error_count > 0:
        flash(f"Added {added_count} financial institutions with {error_count} errors", "warning")
    elif added_count == 0 and error_count > 0:
        flash(f"Failed to add any financial institutions ({error_count} errors)", "danger")
    else:
        flash("No financial institutions to add", "info")
    
    return redirect(url_for('admin_tools.financial_institutions_tool'))