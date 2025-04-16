import os
import logging
import secrets
import string
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, session, redirect, url_for, flash
from flask_jwt_extended import create_access_token, verify_jwt_in_request, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from models import User, UserRole
from blockchain_utils import generate_ethereum_account

logger = logging.getLogger(__name__)

# Authentication decorators
def login_required(f):
    """Decorator to require login for route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('web.main.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role for route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('web.main.login', next=request.url))
        
        user = User.query.get(session['user_id'])
        if not user or user.role != UserRole.ADMIN:
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
