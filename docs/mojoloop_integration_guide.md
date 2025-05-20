# Mojoloop API Integration Guide

This guide provides detailed information on how to use the Mojoloop API integration in the NVC Banking Platform to process real-time interoperable payments.

## Overview

The Mojoloop API integration allows the NVC Banking Platform to connect with financial institutions that support the Mojoloop protocol, enabling real-time interoperable payments globally. This implementation follows the Level One Principles for financial inclusion.

## Configuration

### Environment Variables

The following environment variables should be configured:

```
MOJOLOOP_API_URL=https://api.mojoloop.io/v1  # Base URL for the Mojoloop API
MOJOLOOP_CLIENT_ID=your_client_id            # Client ID for authentication (if required)
MOJOLOOP_CLIENT_SECRET=your_client_secret    # Client secret for authentication (if required)
MOJOLOOP_DFSP_ID=your_dfsp_id                # Digital Financial Service Provider ID
```

### Access

The Mojoloop dashboard is accessible at:
- Web Interface: `/mojoloop/`
- API Endpoints: `/api/mojoloop/*`

## Creating Transactions

### Using the Web Interface

1. Navigate to `/mojoloop/` in your browser
2. Click the "New Transaction" button
3. Enter all required transaction details
4. Submit the form

### Using the API

#### Python Example

```python
import requests
import json

# Setup API connection
def create_mojoloop_transaction(base_url, token, transaction_data):
    """
    Create a new transaction through Mojoloop API
    
    Args:
        base_url: Base URL of the NVC Banking Platform
        token: JWT authentication token
        transaction_data: Transaction details
        
    Returns:
        Transaction result
    """
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    
    response = requests.post(
        f'{base_url}/api/mojoloop/transactions',
        headers=headers,
        json=transaction_data
    )
    
    response.raise_for_status()
    return response.json()

# Example transaction data
transaction_data = {
    'payer_identifier': '+1234567890',  # Phone number with country code
    'payee_identifier': '+9876543210',  # Phone number with country code
    'amount': 100.50,                   # Transaction amount
    'currency': 'USD',                  # Currency code
    'transaction_type': 'transfer',     # Transaction type
    'note': 'Payment for services'      # Optional note
}

# Execute transaction
result = create_mojoloop_transaction(
    'https://yourdomain.com',
    'your_jwt_token',
    transaction_data
)

# Print result
print(json.dumps(result, indent=2))
```

#### JavaScript/Node.js Example

```javascript
async function createMojolloopTransaction(baseUrl, token, transactionData) {
  try {
    const response = await fetch(`${baseUrl}/api/mojoloop/transactions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(transactionData)
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error creating transaction:', error);
    throw error;
  }
}

// Example transaction data
const transactionData = {
  payer_identifier: '+1234567890',  // Phone number with country code
  payee_identifier: '+9876543210',  // Phone number with country code
  amount: 100.50,                   // Transaction amount
  currency: 'USD',                  // Currency code
  transaction_type: 'transfer',     // Transaction type
  note: 'Payment for services'      // Optional note
};

// Execute transaction
createMojolloopTransaction(
  'https://yourdomain.com',
  'your_jwt_token',
  transactionData
)
  .then(result => console.log(JSON.stringify(result, null, 2)))
  .catch(error => console.error('Failed to create transaction:', error));
```

## Checking Transaction Status

### Using the Web Interface

1. Navigate to `/mojoloop/` in your browser
2. Find your transaction in the list
3. Click the "View" button to see transaction details

### Using the API

#### Python Example

```python
import requests
import json

def get_transaction_status(base_url, token, transaction_id):
    """
    Get status of a Mojoloop transaction
    
    Args:
        base_url: Base URL of the NVC Banking Platform
        token: JWT authentication token
        transaction_id: Transaction ID to check
        
    Returns:
        Transaction status details
    """
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    
    response = requests.get(
        f'{base_url}/api/mojoloop/transactions/{transaction_id}',
        headers=headers
    )
    
    response.raise_for_status()
    return response.json()

# Check transaction status
status = get_transaction_status(
    'https://yourdomain.com',
    'your_jwt_token',
    'ML-c8e7a3d1-f9b4-4c63-9e8b-c5f7b9a1d2e3'
)

# Print status
print(json.dumps(status, indent=2))
```

#### JavaScript/Node.js Example

```javascript
async function getTransactionStatus(baseUrl, token, transactionId) {
  try {
    const response = await fetch(`${baseUrl}/api/mojoloop/transactions/${transactionId}`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error getting transaction status:', error);
    throw error;
  }
}

// Check transaction status
getTransactionStatus(
  'https://yourdomain.com',
  'your_jwt_token',
  'ML-c8e7a3d1-f9b4-4c63-9e8b-c5f7b9a1d2e3'
)
  .then(status => console.log(JSON.stringify(status, null, 2)))
  .catch(error => console.error('Failed to get transaction status:', error));
```

## Transaction Callbacks

The Mojoloop integration supports callbacks from the Mojoloop network when transaction statuses change. These are handled automatically by the system, but you can set up your own callback handling by extending the existing implementation.

### Setting up Callbacks

1. Configure your callback URL in your Mojoloop provider settings to point to:
   - `/api/mojoloop/callbacks/transfers` for transfer status updates
   - `/api/mojoloop/callbacks/quotes` for quote notifications

2. Ensure your callback handler can process the payloads as defined in the API specification

## Error Handling

The Mojoloop API integration provides standardized error responses with the following structure:

```json
{
  "status": "error",
  "message": "Detailed error message"
}
```

Common error scenarios:

- **400 Bad Request**: Invalid transaction data provided
- **401 Unauthorized**: Authentication token is missing or invalid
- **404 Not Found**: Transaction ID not found
- **500 Internal Server Error**: Server-side error processing the request

## Supported Identifiers

The following identifier types are supported for payer and payee:

- **Phone Numbers** (with country code): Example: `+1234567890`
- **IBAN**: Example: `IBAN1234567890`
- **Account IDs**: Example: `account_123456`
- **Email Addresses**: Example: `user@example.com`

## Transaction Status Flow

Transactions will typically flow through the following statuses:

1. **PENDING**: Initial state when transaction is created
2. **PROCESSING**: Transaction is being processed by Mojoloop
3. **COMPLETED**: Transaction has been successfully completed
4. **FAILED**: Transaction has failed or been rejected

## Need Help?

For additional assistance with the Mojoloop API integration, please contact:
- Technical Support: support@nvcbanking.com
- API Integration Team: api-team@nvcbanking.com