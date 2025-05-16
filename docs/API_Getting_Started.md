# NVC Banking Platform API - Getting Started

This guide provides step-by-step instructions for accessing and using the NVC Banking Platform API, with specific focus on Stripe integration, card issuance, and SWIFT/Telex access.

## Authentication

All API requests require authentication using JWT tokens:

```
POST /api/v1/auth/token
Content-Type: application/json

{
  "api_key": "your_api_key",
  "api_secret": "your_api_secret"
}
```

The response will include your access token:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

Use this token in the Authorization header for all subsequent requests:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Stripe Integration Quick Start

### Creating a Checkout Session

```
POST /api/v1/payments/stripe/create-checkout-session
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "amount": 1000,
  "currency": "USD",
  "description": "Payment for Order #12345",
  "success_url": "https://your-return-url.com/success",
  "cancel_url": "https://your-return-url.com/cancel",
  "metadata": {
    "order_id": "12345"
  }
}
```

### Retrieving Payment Status

```
GET /api/v1/payments/stripe/{payment_id}
Authorization: Bearer {access_token}
```

## Card Issuance API

### Request Card Issuance

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

### Retrieve Card Details

```
GET /api/v1/cards/{card_id}
Authorization: Bearer {access_token}
```

## SWIFT/Telex Integration

### Create SWIFT Message

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

### Check Message Status

```
GET /api/v1/correspondent/swift/status/{reference}
Authorization: Bearer {access_token}
```

## Liquidity Access API

### Check Available Credit Lines

```
GET /api/v1/liquidity/credit-lines
Authorization: Bearer {access_token}
```

### Request Liquidity Access

```
POST /api/v1/liquidity/request
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "amount": 1000000.00,
  "currency": "USD",
  "purpose": "PAYMENT_SETTLEMENT",
  "duration_hours": 24,
  "correspondent_id": "CORR-123"
}
```

## Error Handling

All API responses follow a standard format for error messages:

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The request was invalid due to missing required fields",
    "details": {
      "field": "amount",
      "issue": "must be greater than 0"
    }
  }
}
```

Common error codes:
- `AUTHENTICATION_ERROR` - Invalid or expired token
- `AUTHORIZATION_ERROR` - Insufficient permissions
- `VALIDATION_ERROR` - Request validation failed
- `RESOURCE_NOT_FOUND` - Requested resource does not exist
- `RATE_LIMIT_EXCEEDED` - Too many requests

## Next Steps

1. Request your sandbox API credentials from our developer support team
2. Use the sandbox environment to test your integration
3. Review the complete API documentation in the Technical Integration Guide
4. Contact our developer support team with any questions

For detailed information on all available endpoints, request/response formats, and implementation examples, please refer to the full Technical Integration Guide included in this documentation package.