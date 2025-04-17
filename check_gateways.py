import os
import sys
from app import db, create_app
from models import PaymentGateway, PaymentGatewayType
from payment_gateways import init_payment_gateways

app = create_app()
with app.app_context():
    # Initialize payment gateways
    init_payment_gateways()
    
    # Print available gateways
    print('Available Payment Gateways:')
    gateways = PaymentGateway.query.all()
    for g in gateways:
        print(f'- {g.name} (Type: {g.gateway_type.value})')