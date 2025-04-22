import os
import inspect
import logging
import secrets
import string
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, session, redirect, url_for, flash, current_app
from flask_jwt_extended import create_access_token, verify_jwt_in_request, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import current_user, login_required as flask_login_required
from app import db
from models import User, UserRole
from blockchain_utils import generate_ethereum_account

logger = logging.getLogger(__name__)

# We'll use Flask-Login's built-in login_required decorator
login_required = flask_login_required

def admin_required(f):
    """Decorator to require admin role for route"""
    @wraps(f)
    @flask_login_required
    def decorated_function(*args, **kwargs):
        # User is already authenticated due to @flask_login_required
        # Now check if they have admin role
        if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
            flash('You do not have permission to access this page', 'danger')
            return redirect(url_for('web.main.index'))
        
        return f(*args, **kwargs)
    return decorated_function

def api_key_required(f):
    """Decorator to require API key for route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'API key is required'}), 401
        
        user = User.query.filter_by(api_key=api_key, is_active=True).first()
        if not user:
            return jsonify({'error': 'Invalid API key'}), 401
        
        return f(user, *args, **kwargs)
    return decorated_function

def jwt_required(f):
    """Decorator to require JWT token for route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            
            if not user or not user.is_active:
                return jsonify({'error': 'Invalid or inactive user'}), 401
                
            return f(user, *args, **kwargs)
        except Exception as e:
            return jsonify({'error': str(e)}), 401
    return decorated_function

def api_test_access(f):
    """Decorator to allow API access for testing without authentication"""
    import inspect
    from flask_login import current_user, login_user
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for special test header or proceed with logged-in user
        test_header = request.headers.get('X-API-Test')
        if test_header == 'true':
            # For API endpoints that need a user, create or get a test user
            # to avoid authentication errors when user information is needed
            
            # Check if the function accepts 'user' as a parameter
            sig = inspect.signature(f)
            accepts_user = 'user' in sig.parameters
            
            if accepts_user:
                test_user = User.query.filter_by(username='test_api_user').first()
                if not test_user:
                    logger.info("Creating test API user for testing")
                    test_user = User(
                        username='test_api_user',
                        email='test_api@example.com',
                        password_hash='test_password_hash',
                        role=UserRole.ADMIN,
                        is_active=True
                    )
                    db.session.add(test_user)
                    db.session.commit()
                
                # Add test user to kwargs only if the function accepts it
                kwargs['user'] = test_user
                
                # Also log in the test user for Flask-Login
                login_user(test_user)
            
            logger.info(f"API test header detected, bypassing authentication for {request.path}")
            return f(*args, **kwargs)
        
        # Check if user is authenticated with Flask-Login
        if not current_user.is_authenticated:
            # Also check session for backward compatibility
            if 'user_id' not in session:
                if request.path.startswith('/api/'):
                    # Return JSON error for API routes instead of redirecting
                    return jsonify({'error': 'Authentication required'}), 401
                else:
                    flash('Please log in to access this page', 'warning')
                    return redirect(url_for('web.main.login', next=request.url))
            else:
                # User is in session but not logged in with Flask-Login
                user = User.query.get(session['user_id'])
                if user:
                    # Log in the user with Flask-Login
                    login_user(user)
        
        # If user is logged in, add the user to kwargs only if endpoint accepts it
        sig = inspect.signature(f)
        if 'user' in sig.parameters:
            # If Flask-Login's current_user is authenticated, use it
            if current_user.is_authenticated:
                kwargs['user'] = current_user
            # Fallback to session (legacy compatibility)
            elif 'user_id' in session:
                user = User.query.get(session['user_id'])
                if user:
                    kwargs['user'] = user
                    
        return f(*args, **kwargs)
    return decorated_function


# User authentication functions
def authenticate_user(username, password):
    """Authenticate user with username and password"""
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return None
    
    if not user.is_active:
        return None
    
    if not check_password_hash(user.password_hash, password):
        return None
    
    return user

def register_user(username, email, password, role=UserRole.USER):
    """Register a new user"""
    try:
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            return None, "Username already exists"
        
        if User.query.filter_by(email=email).first():
            return None, "Email already exists"
        
        # Generate Ethereum account
        eth_address, eth_private_key = generate_ethereum_account()
        
        if not eth_address:
            return None, "Failed to generate Ethereum account"
        
        # Generate API key
        api_key = generate_api_key()
        
        # Create user
        user = User(
            username=username,
            email=email,
            role=role,
            api_key=api_key,
            ethereum_address=eth_address,
            ethereum_private_key=eth_private_key
        )
        
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Send welcome email to the new user
        try:
            from email_service import send_welcome_email
            send_welcome_email(user)
        except Exception as email_error:
            logger.error(f"Failed to send welcome email: {str(email_error)}")
            # Continue even if email fails - user is registered
        
        return user, None
    
    except Exception as e:
        logger.error(f"Error registering user: {str(e)}")
        db.session.rollback()
        return None, str(e)

def generate_api_key():
    """Generate a secure API key"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(64))

def generate_jwt_token(user_id):
    """Generate a JWT token for a user"""
    expires = timedelta(hours=1)
    return create_access_token(identity=user_id, expires_delta=expires)

def verify_reset_token(token):
    """Verify a password reset token"""
    try:
        from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
        from flask import current_app
        
        serializer = URLSafeTimedSerializer(current_app.secret_key)
        data = serializer.loads(
            token,
            max_age=3600,  # 1 hour
            salt='reset-password'
        )
        
        user_id = data['user_id']
        user = User.query.get(user_id)
        
        if not user:
            return None
        
        return user
    
    except (SignatureExpired, BadSignature):
        return None
    except Exception as e:
        logger.error(f"Error verifying reset token: {str(e)}")
        return None

def generate_reset_token(user):
    """Generate a password reset token for a user"""
    try:
        from itsdangerous import URLSafeTimedSerializer
        from flask import current_app
        
        serializer = URLSafeTimedSerializer(current_app.secret_key)
        token = serializer.dumps(
            {'user_id': user.id},
            salt='reset-password'
        )
        
        # Send password reset email
        from email_service import send_password_reset_email
        send_password_reset_email(user, token)
        
        return token
    
    except Exception as e:
        logger.error(f"Error generating reset token: {str(e)}")
        return None

def create_php_test_user():
    """Create or update a test user for PHP integration"""
    try:
        # Check if the test user already exists
        php_test_user = User.query.filter_by(username="php_test_integration").first()
        
        if php_test_user:
            # Update existing user
            php_test_user.api_key = "php_test_api_key"
            php_test_user.role = UserRole.API
            php_test_user.is_active = True
            db.session.commit()
            logger.info("Updated PHP test integration user")
            return php_test_user
        else:
            # Create new user
            new_user = User(
                username="php_test_integration",
                email="php_test@example.com",
                password_hash=generate_password_hash("PhpTest123!"),
                role=UserRole.API,
                api_key="php_test_api_key"
            )
            
            db.session.add(new_user)
            db.session.commit()
            logger.info("Created new PHP test integration user")
            return new_user
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating PHP test user: {str(e)}")
        return None
