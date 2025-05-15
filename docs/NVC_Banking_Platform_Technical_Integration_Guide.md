# NVC Banking Platform Technical Integration Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Stripe Integration](#stripe-integration)
3. [Card Issuance](#card-issuance)
4. [Correspondent Banking](#correspondent-banking)
5. [API Reference](#api-reference)
6. [Integration Testing](#integration-testing)
7. [Security Requirements](#security-requirements)
8. [Getting Started](#getting-started)

<a name="introduction"></a>
## 1. Introduction

This document provides technical details on the NVC Banking Platform's payment processing capabilities, card issuance infrastructure, and correspondent banking services. It is intended for developers integrating with our systems.

### Platform Overview
- **Core Banking System**: Flask-based application with SQLAlchemy ORM
- **Database**: PostgreSQL for transaction storage and account management
- **Security**: JWT authentication, role-based access controls
- **API Structure**: RESTful API design with versioned endpoints
- **Blockchain Integration**: Ethereum-based token infrastructure (NVCT)

<a name="stripe-integration"></a>
## 2. Stripe Integration Technical Details

### Implementation Architecture
- **Integration Type**: Server-side API implementation using Stripe's Python SDK
- **Authentication**: Stripe Secret Key stored securely in environment variables
- **API Version**: Latest stable (2023-10-16)
- **Environment**: Live mode for production transactions

### Core Payment Processing
- **Endpoint Implementation**: `/api/v1/payments/stripe/create-checkout-session`
- **Parameters**:
  ```json
  {
    "amount": 1000,  // Amount in cents
    "currency": "USD",
    "description": "Payment for Invoice #12345",
    "customer_email": "customer@example.com",
    "metadata": {
      "order_id": "6735",
      "account_id": "ACC-12345"
    }
  }
  ```
- **Response**: Redirect URL to Stripe-hosted checkout page

### Server-Side Workflow
1. Payment request received and validated
2. Stripe session created with specified parameters
3. Session URL returned to client for redirect
4. Customer completes payment on Stripe's hosted page
5. Webhook receives payment completion notification
6. Settlement account updated with transaction details
7. Customer redirected to success/cancel page based on outcome

### Webhook Processing
- **Endpoint**: `/api/v1/webhooks/stripe`
- **Events Handled**:
  - `payment_intent.succeeded`
  - `payment_intent.payment_failed`
  - `charge.refunded`
  - `charge.dispute.created`
- **Security**: Signature verification using `stripe.Webhook.construct_event()`

### Settlement Account Integration
- **Account ID**: Dedicated "Stripe Settlement Account" in treasury system
- **Reconciliation**: Automated daily reconciliation process
- **Transaction Mapping**: One-to-one mapping between Stripe payment_intent and internal transaction ID

### API Key Management
- **Storage**: Environment variables with restricted access
- **Rotation Policy**: 90-day rotation schedule
- **Permissions**: Restricted to payment processing capabilities only

<a name="card-issuance"></a>
## 3. Card Issuance Against NVC Bank Accounts

### Card Program Structure
- **Issuance Partners**: Integration capability with third-party card issuers
- **Card Types**: Debit, Credit, and Prepaid virtual/physical cards
- **Technology**: EMV chip and contactless enabled
- **Currencies**: Multi-currency support with USD as base currency

### Technical Implementation
- **Account Linkage**:
  ```python
  class CardAccount(db.Model):
      id = db.Column(db.Integer, primary_key=True)
      account_id = db.Column(db.Integer, db.ForeignKey('treasury_account.id'), nullable=False)
      card_program_id = db.Column(db.Integer, db.ForeignKey('card_program.id'), nullable=False)
      card_number_hash = db.Column(db.String(128), nullable=False)
      card_status = db.Column(db.Enum(CardStatus), default=CardStatus.PENDING, nullable=False)
      daily_limit = db.Column(db.Numeric(15, 2), nullable=False, default=1000.00)
      expiration_date = db.Column(db.Date, nullable=False)
      is_virtual = db.Column(db.Boolean, default=False)
  ```

### Card Issuance Flow
1. Customer requests card linked to NVC Bank Account
2. System verifies account eligibility and KYC status
3. Card issuance request sent to card issuer API
4. Card details received and securely stored (PCI compliant)
5. Card activated through verification process
6. Account-to-card linkage established for transaction processing

### Transaction Processing
- **Authorization Flow**:
  1. Card authorization request received from payment network
  2. Verification against account balance and limits
  3. Hold placed on funds in linked account
  4. Authorization response sent to network
  5. Transaction settled within 24-48 hours

### Security Features
- **Tokenization**: Card numbers tokenized for secure storage
- **3D Secure**: Support for 3DS 2.0 authentication
- **Fraud Monitoring**: Real-time transaction analysis and risk scoring
- **Controls**: Customer-managed spending controls and limits

<a name="correspondent-banking"></a>
## 4. Correspondent Banking for SWIFT/Telex Access

### Correspondent Network Architecture
- **Network Structure**: Multi-tier correspondent relationship model
- **Primary Correspondents**: Established relationships with 5+ Tier 1/2 banks
- **Account Types**: Nostro/Vostro account support
- **Geographical Coverage**: Global with emphasis on African financial networks

### SWIFT Integration Technical Details
- **Message Types Supported**:
  - MT103: Single Customer Credit Transfer
  - MT202: General Financial Institution Transfer
  - MT950: Statement Message
  - MT199: Free Format Message
- **BIC Code**: Registered SWIFT/BIC code integration capability
  
### SWIFT Message Processing
- **Generation**:
  ```python
  def generate_mt103(sender_bic, receiver_bic, amount, currency, sender_account, 
                     receiver_account, reference, value_date):
      """Generate formatted MT103 message content"""
      message = {
          "block1": {
              "application_id": "F",
              "service_id": "01",
              "receiver_address": receiver_bic,
              "message_priority": "N",
              "delivery_monitoring": "3"
          },
          "block2": {
              "input_output": "I",
              "message_type": "103"
          },
          "block4": {
              "20": reference,                    # Reference
              "23B": "CRED",                      # Bank Operation Code
              "32A": f"{value_date}{currency}{amount}",  # Value Date/Currency/Amount
              "50K": f"/{sender_account}",        # Sender Account + Details
              "59": f"/{receiver_account}",       # Beneficiary Account + Details
              "71A": "SHA"                        # Details of Charges
          }
      }
      return format_swift_message(message)
  ```

### Telex System Integration
- **Format Support**: Standard Telex message formatting
- **Authentication**: Test key verification system
- **Routing**: Direct routing through correspondent banking network
- **Message Priority**: Normal and Urgent priority levels supported

### Liquidity Access Mechanisms
- **Credit Lines**: Pre-established credit facilities with correspondent banks
- **Intraday Liquidity**: Real-time liquidity monitoring and management
- **FX Swap Lines**: Currency swap arrangements for major pairs
- **Settlement Process**:
  1. Outgoing payment instruction created and validated
  2. Message formatted according to SWIFT/Telex standards
  3. Message transmitted through secure channel to correspondent
  4. Status tracking through confirmation process
  5. Settlement in correspondent account
  6. Internal account updated with transaction details

### Compliance Framework
- **Sanctions Screening**: Automated screening against OFAC, UN, EU lists
- **AML Monitoring**: Transaction monitoring with risk-based approach
- **Regulatory Reporting**: Automated reporting for regulatory requirements
- **Documentation**: Full audit trail of all correspondent transactions

<a name="api-reference"></a>
## 5. API Reference

### Authentication
All API requests require authentication using JWT tokens.

**Token Request**:
```
POST /api/v1/auth/token
Content-Type: application/json

{
  "api_key": "your_api_key",
  "api_secret": "your_api_secret"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### Stripe Payment Endpoints

**Create Checkout Session**:
```
POST /api/v1/payments/stripe/create-checkout-session
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "amount": 1000,
  "currency": "USD",
  "description": "Payment for Order #12345",
  "success_url": "https://example.com/success",
  "cancel_url": "https://example.com/cancel",
  "metadata": {
    "order_id": "12345"
  }
}
```

**Get Payment Status**:
```
GET /api/v1/payments/stripe/{payment_id}
Authorization: Bearer {access_token}
```

### Card Issuance Endpoints

**Request Card Issuance**:
```
POST /api/v1/cards/issue
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "account_id": "ACC-12345",
  "card_type": "DEBIT",
  "holder_name": "JOHN DOE",
  "is_virtual": false,
  "daily_limit": 1000.00,
  "currency": "USD"
}
```

**Get Card Details**:
```
GET /api/v1/cards/{card_id}
Authorization: Bearer {access_token}
```

### Correspondent Banking Endpoints

**Create SWIFT Message**:
```
POST /api/v1/correspondent/swift/create
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "message_type": "MT103",
  "sender_bic": "NVCGABC1XXX",
  "receiver_bic": "CHASUS33XXX",
  "amount": 10000.00,
  "currency": "USD",
  "sender_account": "CH9300762011623852957",
  "receiver_account": "GB29NWBK60161331926819",
  "reference": "INVOICE/2025/05/15",
  "value_date": "20250515"
}
```

**Check Message Status**:
```
GET /api/v1/correspondent/swift/status/{reference}
Authorization: Bearer {access_token}
```

<a name="integration-testing"></a>
## 6. Integration Testing

### Test Environment
- **URL**: `https://sandbox.nvcbanking.com/api/v1/`
- **Test Accounts**: Contact administrator for test credentials
- **Simulated Services**: All production services have sandbox equivalents

### Test Data
- **Test BIC Codes**:
  - Sending BIC: `NVCGTEST1XX`
  - Receiving BIC: `TESTBIC1XXX`
- **Test Card Numbers**:
  - Test Visa: `4242 4242 4242 4242`
  - Test Mastercard: `5555 5555 5555 4444`
- **Test Account Numbers**:
  - Source Account: `TEST-SOURCE-ACCOUNT-001`
  - Destination Account: `TEST-DEST-ACCOUNT-001`

### Test Scenarios
1. **Payment Processing**: Complete payment flow from initiation to settlement
2. **Card Issuance**: Request card, activate, and simulate transactions
3. **SWIFT Messaging**: Generate and validate SWIFT message formats
4. **Settlement**: Test end-to-end settlement process

<a name="security-requirements"></a>
## 7. Security Requirements

### Data Protection
- All sensitive data must be encrypted in transit and at rest
- PCI DSS compliance required for handling card data
- Personal information must be handled according to relevant privacy laws

### Authentication & Authorization
- All API requests must be authenticated using valid JWT tokens
- Access control based on role and permission levels
- Multi-factor authentication for administrative functions

### Communication Security
- TLS 1.2+ required for all API communication
- Certificate validation enforced
- Regular security scanning and penetration testing

<a name="getting-started"></a>
## 8. Getting Started

### Developer Onboarding Process
1. Request access credentials from the NVC Banking Platform administrator
2. Confirm receipt of sandbox API keys and documentation
3. Set up development environment with required dependencies
4. Run test API calls to verify access
5. Begin integration development
6. Schedule regular check-ins with technical support team

### Support Resources
- **Developer Portal**: https://developer.nvcbanking.com
- **API Status**: https://status.nvcbanking.com
- **Technical Support**: developer-support@nvcbanking.com

### Integration Timeline
- **Sandbox Testing**: Typically 2-4 weeks
- **Certification**: 1-2 weeks for review and approval
- **Production Deployment**: Scheduled with release management team

---

## Contact Information

For questions or additional information regarding this integration guide, please contact:

Technical Support: developer-support@nvcbanking.com  
Phone: +1 (555) 123-4567