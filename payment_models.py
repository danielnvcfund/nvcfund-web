"""
Payment Models
-------------

Models for payment processors (Stripe, PayPal, POS).
These models track payments made through various payment processors
and support settlement to treasury accounts.
"""

import logging
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from app import db
from models import TransactionStatus

logger = logging.getLogger(__name__)

class Payment(db.Model):
    """Base abstract payment model"""
    __abstract__ = True
    
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default="USD")
    description = db.Column(db.String(256))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Settlement fields
    is_settled = db.Column(db.Boolean, default=False)
    settlement_date = db.Column(db.DateTime)
    settlement_reference = db.Column(db.String(100))  # Reference to the treasury transaction ID
    
    user = db.relationship('User', backref=db.backref('payments', lazy=True))

class StripePayment(Payment):
    """Stripe payment model"""
    __tablename__ = 'stripe_payment'
    
    stripe_payment_id = db.Column(db.String(100), unique=True)
    stripe_customer_id = db.Column(db.String(100))
    payment_method = db.Column(db.String(100))
    status = db.Column(db.String(50), default='pending')
    receipt_url = db.Column(db.String(256))
    metadata_json = db.Column(db.Text)
    
    def __repr__(self):
        return f"<StripePayment {self.id}: {self.amount} {self.currency}>"

class PayPalPayment(Payment):
    """PayPal payment model"""
    __tablename__ = 'paypal_payment'
    
    paypal_id = db.Column(db.String(100), unique=True)
    paypal_order_id = db.Column(db.String(100))
    paypal_payer_id = db.Column(db.String(100))
    paypal_payer_email = db.Column(db.String(256))
    status = db.Column(db.String(50), default='PENDING')
    payment_source = db.Column(db.String(50))  # paypal, card, bank, etc.
    metadata_json = db.Column(db.Text)
    
    def __repr__(self):
        return f"<PayPalPayment {self.id}: {self.amount} {self.currency}>"

class POSPayment(Payment):
    """Point of Sale payment model"""
    __tablename__ = 'pos_payment'
    
    transaction_id = db.Column(db.String(100), unique=True)
    payment_method = db.Column(db.String(50))  # cash, card, check, etc.
    location = db.Column(db.String(256))
    terminal_id = db.Column(db.String(100))
    cashier_id = db.Column(db.Integer)
    receipt_number = db.Column(db.String(100))
    status = db.Column(db.String(50), default='pending')
    metadata_json = db.Column(db.Text)
    
    def __repr__(self):
        return f"<POSPayment {self.id}: {self.amount} {self.currency}>"