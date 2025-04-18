# PHP Bridge Integration Testing Guide

## Overview
This guide explains how to test the integration between the PHP banking software and the NVC Global Payment system through the PHP Bridge API.

## Prerequisites
- Python 3.x installed
- Requests library installed (`pip install requests`)
- Access to the NVC Banking Platform with a running server

## API Authentication
The PHP Bridge API uses API key authentication. The test client is already configured with:
- API Key: `php_test_api_key`
- Shared Secret: `php_bridge_shared_secret`

These are automatically set up when the application starts.

## Running the Test Client

### 1. Synchronizing Accounts
This simulates PHP banking software sending user account data to the NVC platform:

```bash
python php_bridge_test_client.py sync_accounts
```

Expected Result:
- The system should create or update the user accounts
- You should see a success response with counts of created/updated accounts

### 2. Synchronizing Transactions
This simulates PHP banking software sending transaction data to the NVC platform:

```bash
python php_bridge_test_client.py sync_transactions
```

Expected Result:
- The system should create or update transactions
- You should see a success response with counts of created/updated transactions

### 3. Processing a Payment
This simulates the PHP banking software requesting a payment through NVC Global:

```bash
python php_bridge_test_client.py process_payment
```

Expected Result:
- The system should create a new payment transaction
- You should receive a transaction ID for the payment
- The payment should initially be in "pending" status

### 4. Checking Payment Status
Once you have a transaction ID from processing a payment, you can check its status:

```bash
python php_bridge_test_client.py check_status NVC-12345-67890
```
(Replace NVC-12345-67890 with your actual transaction ID)

Expected Result:
- The system should return the current status of the transaction
- You should see details about the transaction including status, amount, and user information

## API Documentation

For detailed API documentation, log in as an administrator and visit the PHP Bridge Documentation page from the admin menu. This documentation provides:

- Comprehensive API endpoint information
- Request and response formats
- Authentication details
- Signature verification examples
- Integration best practices

## Troubleshooting

1. **API Key Issues**: Ensure the server is properly generating the PHP test user with API key `php_test_api_key`. Check server logs for confirmation.

2. **Connection Problems**: Verify that the BASE_URL in the test client is correct, especially if running on Replit or other hosted environments.

3. **Request Format Errors**: Compare your request format with the examples in the API documentation.

4. **Signature Verification**: Ensure the shared secret is consistent between the client and server.

5. **Missing Users**: Run the account sync operation before attempting payment processing.

## Production Integration

For production integration:
1. Use a secure API key and shared secret management system
2. Implement proper error handling and retry mechanisms
3. Set up monitoring for the integration points
4. Secure all communications with TLS/HTTPS
5. Implement comprehensive logging for troubleshooting

For any additional questions or support, contact the NVC Platform support team.