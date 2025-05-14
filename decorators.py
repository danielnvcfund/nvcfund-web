"""
Decorators for the NVC Financial Platform
Provides various decorators for route security, permission checking, etc.
"""

import functools
from flask import flash, redirect, url_for, current_app
from flask_login import current_user


def roles_required(roles):
    """
    Decorator that checks if the current user has any of the specified roles.
    
    Args:
        roles (list): List of role names that are authorized to access the route
        
    Returns:
        function: The decorated function
    """
    def decorator(view_function):
        @functools.wraps(view_function)
        def decorated_view(*args, **kwargs):
            # Anonymous users can't have roles
            if not current_user.is_authenticated:
                flash("Please log in to access this page", "warning")
                return redirect(url_for('web.main.login'))
            
            # Check if the user has any of the required roles
            if current_user.role and current_user.role.name in roles:
                return view_function(*args, **kwargs)
            
            # Not authorized
            flash("You don't have permission to access this page", "danger")
            return redirect(url_for('web.main.dashboard'))
        
        return decorated_view
    
    return decorator


def api_roles_required(roles):
    """
    Decorator that checks if the API user has any of the specified roles.
    
    Args:
        roles (list): List of role names that are authorized to access the route
        
    Returns:
        function: The decorated function that returns JSON errors when unauthorized
    """
    def decorator(view_function):
        @functools.wraps(view_function)
        def decorated_view(*args, **kwargs):
            # Anonymous users can't have roles
            if not current_user.is_authenticated:
                return {"error": "Authentication required"}, 401
            
            # Check if the user has any of the required roles
            if current_user.role and current_user.role.name in roles:
                return view_function(*args, **kwargs)
            
            # Not authorized
            return {"error": "You don't have permission to access this resource"}, 403
        
        return decorated_view
    
    return decorator