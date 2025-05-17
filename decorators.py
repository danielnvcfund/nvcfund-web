"""
Custom decorators for route protection and user role verification.
"""
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user


def admin_required(f):
    """
    Decorator for routes that require admin privileges.
    Redirects to home page if user is not an admin.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not hasattr(current_user, 'is_admin') or not current_user.is_admin:
            flash('This page requires administrator privileges', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


def analyst_required(f):
    """
    Decorator for routes that require analyst privileges.
    Redirects to home page if user is not an analyst or admin.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Admins also have analyst privileges
        is_admin = hasattr(current_user, 'is_admin') and current_user.is_admin
        is_analyst = hasattr(current_user, 'is_analyst') and current_user.is_analyst
        
        if not current_user.is_authenticated or not (is_admin or is_analyst):
            flash('This page requires analyst privileges', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


def roles_required(*role_names):
    """
    Decorator for routes that require specific roles.
    Redirects to home page if user doesn't have any of the specified roles.
    
    Usage example:
        @roles_required('admin', 'manager')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('You need to be logged in to access this page', 'danger')
                return redirect(url_for('main.index'))
            
            if not hasattr(current_user, 'roles'):
                flash('You do not have the required roles to access this page', 'danger')
                return redirect(url_for('main.index'))
            
            # Check if the user has any of the required roles
            user_roles = current_user.roles.split(',') if isinstance(current_user.roles, str) else current_user.roles
            if not any(role in user_roles for role in role_names):
                flash('You do not have the required roles to access this page', 'danger')
                return redirect(url_for('main.index'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator