"""
Portfolio routes for NVC Banking Platform
"""

from flask import Blueprint, render_template

portfolio_bp = Blueprint('portfolio', __name__, url_prefix='/portfolio')

@portfolio_bp.route('/asset-allocation')
def asset_allocation():
    """Display the portfolio asset allocation with improved readability"""
    return render_template('portfolio/asset_allocation.html', title="Asset Allocation")