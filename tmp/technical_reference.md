# NVC Banking Platform Technical Reference

## Table of Contents
1. [Introduction](#introduction)
2. [System Architecture](#system-architecture)
   - [Component Overview](#component-overview)
   - [Technology Stack](#technology-stack)
   - [Database Schema](#database-schema)
3. [Module Documentation](#module-documentation)
   - [Core Application](#core-application)
   - [Blockchain Integration](#blockchain-integration)
   - [Payment Gateways](#payment-gateways)
   - [Financial Institutions](#financial-institutions)
   - [Authentication and Authorization](#authentication-and-authorization)
   - [API Bridges](#api-bridges)
4. [Blockchain Implementation](#blockchain-implementation)
   - [Smart Contracts](#smart-contracts)
   - [NVC Token (NVCT)](#nvc-token-nvct)
   - [Ethereum Transactions](#ethereum-transactions)
   - [Multi-Signature Wallet](#multi-signature-wallet)
5. [API Reference](#api-reference)
   - [Internal APIs](#internal-apis)
   - [External Integrations](#external-integrations)
   - [Authentication](#api-authentication)
   - [Rate Limiting](#rate-limiting)
6. [Transaction Processing](#transaction-processing)
   - [Transaction Flow](#transaction-flow)
   - [Settlement Logic](#settlement-logic)
   - [Fee Structure](#fee-structure)
   - [Error Handling](#error-handling)
7. [Security Specifications](#security-specifications)
   - [Authentication Mechanisms](#authentication-mechanisms)
   - [Data Encryption](#data-encryption)
   - [Session Management](#session-management)
   - [CSRF Protection](#csrf-protection)
8. [Database Management](#database-management)
   - [Schema Design](#schema-design)
   - [Migration Procedures](#migration-procedures)
   - [Backup Strategy](#backup-strategy)
   - [Performance Optimization](#performance-optimization)
9. [Deployment Guide](#deployment-guide)
   - [Environment Configuration](#environment-configuration)
   - [Deployment Process](#deployment-process)
   - [Testing Procedures](#testing-procedures)
   - [Monitoring Setup](#monitoring-setup)
10. [Troubleshooting](#troubleshooting)
    - [Common Issues](#common-issues)
    - [Diagnostic Tools](#diagnostic-tools)
    - [Recovery Procedures](#recovery-procedures)
11. [Development Guidelines](#development-guidelines)
    - [Coding Standards](#coding-standards)
    - [Version Control](#version-control)
    - [Testing Strategy](#testing-strategy)
    - [Documentation Requirements](#documentation-requirements)

---

## Introduction

This technical reference guide provides in-depth information about the NVC Banking Platform architecture, components, and implementation details. It serves as the authoritative resource for developers, system administrators, and technical staff maintaining and extending the platform.

---

## System Architecture

### Component Overview

The NVC Banking Platform follows a modular architecture with the following primary components:

1. **Web Application Layer:** Flask-based web interface and RESTful APIs
2. **Business Logic Layer:** Transaction processing, validation, and business rules
3. **Data Access Layer:** Database interactions and data management
4. **Blockchain Integration Layer:** Smart contract interaction and blockchain transactions
5. **External Integration Layer:** Payment gateways and financial institution connections
6. **Security Layer:** Authentication, authorization, and data protection

The architecture is designed for high availability, scalability, and security with clear separation of concerns between components.

### Technology Stack

The platform is built on the following technology stack:

- **Backend Framework:** Python 3.11 with Flask
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Authentication:** Flask-Login, Flask-JWT-Extended
- **Form Handling:** Flask-WTF
- **Blockchain Connectivity:** Web3.py
- **XRPL Integration:** XRPL-py
- **Payment Processing:** Stripe, PayPal REST SDK
- **PDF Generation:** WeasyPrint, PDFKit
- **Email Services:** SendGrid
- **Development Tools:** Python virtual environments, Gunicorn for deployment

### Database Schema

The database schema includes the following primary entities:

1. **Users:** User accounts and authentication information
2. **Transactions:** Financial transaction records
3. **Accounts:** Financial accounts associated with users
4. **PaymentGateways:** Configuration for payment processors
5. **FinancialInstitutions:** Partner banking institutions 
6. **BlockchainContracts:** Deployed smart contract information
7. **FormData:** Saved progress on transaction forms
8. **Tokens:** Token balances and transactions
9. **Invitations:** System for inviting new users
10. **AuditLog:** Security and action audit trails

Detailed entity relationship diagrams are available in the database documentation.

---

## Module Documentation

### Core Application

The core application (`app.py`, `main.py`) handles:

- Application initialization and configuration
- Blueprint registration
- Database connection setup
- Error handling
- Session management
- Main route registration

Key components:
- `create_app()`: Factory function for creating Flask application instance
- `db`: SQLAlchemy database instance
- `login_manager`: Flask-Login manager for authentication
- `jwt`: JWT manager for API authentication

### Blockchain Integration

The blockchain module (`blockchain.py`, `blockchain_utils.py`) provides:

- Ethereum network connectivity via Web3.py
- Smart contract deployment and management
- Transaction creation and signing
- Gas price optimization
- Transaction status monitoring
- Error handling and retries

Primary functions:
- `init_web3()`: Initialize blockchain connection
- `get_settlement_contract()`: Get the settlement contract instance
- `get_multisig_wallet()`: Get the multi-signature wallet
- `get_nvc_token()`: Get the NVC token contract
- `settle_payment_via_contract()`: Process payment through smart contract
- `send_ethereum_transaction()`: Send regular Ethereum transaction
- `get_transaction_status()`: Check the status of blockchain transactions

### Payment Gateways

The payment gateways module (`payment_gateways.py`) implements:

- Common interface for all payment processors
- Gateway-specific implementation details
- Transaction routing and processing
- Webhook handling for asynchronous notifications
- Fee calculation and application
- Error handling and resolution

Supported gateways:
- **NVC Global:** Primary internal payment processor
- **PayPal:** Integration with PayPal REST API
- **Stripe:** Credit card processing via Stripe API

### Financial Institutions

The financial institutions module (`financial_institutions.py`) handles:

- Banking partner connections
- SWIFT messaging integration
- Letter of credit processing
- Bank transfer routing
- Compliance checks
- Settlement instructions

Key components:
- `SwiftService`: SWIFT messaging integration
- `FinancialInstitution`: Base class for financial institutions
- `LetterOfCreditService`: LC issuance and management

### Authentication and Authorization

Authentication components (`auth.py`) provide:

- User authentication via username/password
- Role-based access control
- JWT token generation and validation
- Password hashing and verification
- Account recovery mechanisms
- Session management
- API key generation and validation

Key decorators:
- `login_required`: Require authenticated user
- `admin_required`: Require admin privileges
- `api_key_required`: Require valid API key
- `jwt_required`: Require valid JWT token

### API Bridges

API bridges (`api_bridge.py`) facilitate:

- Integration with external systems
- Legacy system connectivity
- Data format transformation
- Authentication between systems
- Error handling and fault tolerance
- Transaction synchronization

The PHP Banking Software bridge provides:
- Request signature verification
- Account synchronization
- Transaction synchronization
- Payment processing
- Status checking
- Callback mechanism

---

## Blockchain Implementation

### Smart Contracts

The platform uses the following Ethereum smart contracts:

1. **SettlementContract:** Handles payment settlement between parties
   - Functions: createSettlement, confirmSettlement, getSettlementStatus
   - Properties: fee percentage, settlement count, owner

2. **MultiSigWallet:** Implements multi-signature authorization
   - Functions: submitTransaction, confirmTransaction, revokeConfirmation, executeTransaction
   - Properties: owners, required confirmations, transaction count

3. **NVCToken:** ERC-20 token implementation for NVCT
   - Functions: transfer, approve, transferFrom, mint, burn
   - Properties: totalSupply, balanceOf, name, symbol, decimals

Contract addresses (Sepolia testnet):
- SettlementContract: 0xE4eA76e830D1A10df277b9D3a1824F216F8F1A5A
- MultiSigWallet: 0xB2C857F7AeCB1dEad987ceB5323f88C3Ef0B7C3E
- NVCToken: 0xA4Bc40DD1f6d56d5EF6EE6D5c8FE6C2fE10CaA4c

### NVC Token (NVCT)

The NVC Token (NVCT) implementation:

- ERC-20 compliant token
- Symbol: NVCT
- Decimals: 18
- USD-pegged (1 NVCT = 1 USD)
- Expandable supply (not fixed maximum)
- Minting controlled by authorized addresses
- Backed by Basel 3 compliant assets
- Transfer fees configurable by admin

### Ethereum Transactions

Ethereum transaction handling includes:

- Transaction creation and signing
- Gas price optimization based on network conditions
- Nonce management to prevent transaction conflicts
- Transaction receipt monitoring
- Resubmission logic for stuck transactions
- Error handling for failed transactions
- Event monitoring for contract events

### Multi-Signature Wallet

The multi-signature wallet implementation provides:

- Configurable number of required signatures
- Owner management (add/remove owners)
- Transaction submission and confirmation workflow
- Execution only after threshold of confirmations
- Confirmation revocation
- Transaction execution
- Daily transaction limits
- Comprehensive event logging

---

## API Reference

### Internal APIs

Internal APIs for platform functionality:

1. **Authentication API:**
   - `POST /api/auth/login`: Generate authentication token
   - `POST /api/auth/refresh`: Refresh an existing token
   - `GET /api/auth/verify`: Verify token validity

2. **User API:**
   - `GET /api/users/<id>`: Get user details
   - `PATCH /api/users/<id>`: Update user details
   - `GET /api/users/me`: Get current user details

3. **Transaction API:**
   - `GET /api/transactions`: List transactions
   - `GET /api/transactions/<id>`: Get transaction details
   - `POST /api/transactions`: Create new transaction
   - `PATCH /api/transactions/<id>`: Update transaction status

4. **Blockchain API:**
   - `GET /api/blockchain/status`: Get blockchain connection status
   - `GET /api/blockchain/balances`: Get token balances
   - `POST /api/blockchain/transfer`: Transfer tokens
   - `GET /api/blockchain/contracts`: Get contract status

5. **Form Data API:**
   - `GET /api/form-data/<transaction_id>`: Get saved form data
   - `POST /api/form-data/<transaction_id>`: Save form data
   - `DELETE /api/form-data/<transaction_id>`: Delete saved form data

### External Integrations

APIs for external system integration:

1. **PHP Bridge API:**
   - `POST /api/bridge/php/sync-accounts`: Synchronize accounts
   - `POST /api/bridge/php/sync-transactions`: Synchronize transactions
   - `POST /api/bridge/php/process-payment`: Process a payment
   - `GET /api/bridge/php/payment-status/<id>`: Check payment status
   - `POST /api/bridge/php/callback`: Receive callbacks

2. **Payment Gateway Webhooks:**
   - `POST /payments/return`: Handle payment return
   - `POST /payments/cancel`: Handle payment cancellation
   - `POST /nvc-callback`: Handle NVC Global callbacks

3. **SWIFT Integration:**
   - `POST /api/swift/send-message`: Send SWIFT message
   - `POST /api/swift/receive-message`: Receive SWIFT message
   - `GET /api/swift/message-status/<id>`: Check message status

### API Authentication

API authentication methods:

1. **JWT Authentication:**
   - Token Generation: `POST /api/auth/login`
   - Header Format: `Authorization: Bearer <token>`
   - Expiration: 1 hour with refresh capability
   - Claims: user_id, username, role, exp, iat

2. **API Key Authentication:**
   - Header Format: `X-API-Key: <api_key>`
   - Suitable for server-to-server integrations
   - Keys managed in the admin dashboard

3. **HMAC Signature Authentication:**
   - Used for PHP Bridge API
   - Request signed with shared secret
   - Verification using request body and timestamp

### Rate Limiting

API rate limiting implementation:

- Default limit: 100 requests per minute per IP
- Admin API: 300 requests per minute per IP
- Public endpoints: 60 requests per minute per IP
- Rate limit headers included in responses
- X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
- Configuration customizable in environment settings

---

## Transaction Processing

### Transaction Flow

Standard transaction processing flow:

1. **Initiation:**
   - User creates transaction through UI or API
   - System validates transaction details
   - Transaction saved in PENDING status

2. **Processing:**
   - Transaction routed to appropriate payment gateway
   - Status updated to PROCESSING
   - User redirected to payment method if needed

3. **Completion:**
   - Gateway processes payment
   - Callback received with status update
   - Transaction marked as COMPLETED or FAILED
   - Notifications sent to relevant parties

4. **Settlement:**
   - Completed transactions marked for settlement
   - Settlement processed through blockchain or traditional means
   - Settlement confirmation recorded
   - Final status updated

### Settlement Logic

Settlement mechanisms:

1. **Blockchain Settlement:**
   - Transaction details submitted to SettlementContract
   - Settlement fee calculated and applied
   - Funds transferred through smart contract
   - Transaction hash recorded
   - Receipt and confirmation provided

2. **Traditional Settlement:**
   - Transaction routed through banking partner
   - Settlement instructions generated
   - Confirmation received from banking partner
   - Settlement status recorded

3. **Token-Based Settlement:**
   - NVCT tokens transferred between parties
   - ERC-20 transfer executed and confirmed
   - Token transaction hash recorded
   - Balance updates reflected in user accounts

### Fee Structure

Transaction fee implementation:

- Base fee: Configurable percentage per transaction type
- Gateway-specific fees: Added based on gateway used
- Volume discounts: Applied based on user transaction history
- Minimum fee: Enforced to ensure processing viability
- Maximum fee: Capped to prevent excessive charges
- Fee splitting: Distribution between platform and partners

### Error Handling

Transaction error handling:

- Validation errors: Returned immediately with clear messages
- Gateway errors: Logged, categorized, and handled based on error type
- Network errors: Automatic retry with exponential backoff
- Timeout handling: Configurable timeouts with status updates
- Manual resolution: Admin interface for resolving stuck transactions
- Notification system: Alerts for critical transaction failures

---

## Security Specifications

### Authentication Mechanisms

User authentication methods:

1. **Username/Password:**
   - Password hashing: Werkzeug security, SHA256 algorithm
   - Password policy: 8+ chars, mixed case, numbers, special chars
   - Brute force protection: Account locking after failed attempts
   - Password rotation: Optional enforcement of password changes

2. **API Authentication:**
   - JWT tokens: RS256 signed tokens with expiration
   - API keys: Securely generated and stored with permissions
   - HMAC signatures: For external system integration

3. **Session Management:**
   - Session duration: 30 days maximum
   - Secure cookies: HTTPOnly, Secure flags
   - Session invalidation: On password change or suspicious activity

### Data Encryption

Data protection mechanisms:

1. **At Rest:**
   - Database encryption: Sensitive fields encrypted before storage
   - File encryption: Documents and exported data encrypted
   - Key management: Segregated key storage with rotation

2. **In Transit:**
   - TLS 1.3 requirement for all connections
   - Certificate validation and pinning
   - Secure cookie transmission
   - Encrypted payload for sensitive API calls

3. **Payload Encryption:**
   - Additional encryption layer for highly sensitive data
   - End-to-end encryption for specific message types
   - Key exchange protocols for secure communication

### Session Management

Session security implementation:

- Session creation: Secure random generation
- Storage: Server-side session storage with secure references
- Timeout: Configurable idle and absolute timeouts
- Revocation: Immediate session invalidation capability
- Tracking: Comprehensive session activity logging
- Cross-device management: View and terminate sessions across devices

### CSRF Protection

Cross-Site Request Forgery protection:

- CSRF token generation: Per-session tokens with rotation
- Form protection: Automatic inclusion in all forms via WTForms
- API protection: Custom headers for AJAX requests
- Token validation: Server-side validation on all state-changing requests
- Expiration: Time-limited tokens with transparent renewal

---

## Database Management

### Schema Design

Database design principles:

- Normalization: Third normal form (3NF) for most tables
- Relationship modeling: Foreign key constraints for referential integrity
- Indexing strategy: Strategic indexes on frequently queried columns
- Migrations: Version-controlled schema evolution
- Audit fields: Creation and modification timestamps on all records

Primary tables and relationships documented in the Model classes.

### Migration Procedures

Database migration process:

1. **Development Migrations:**
   - Create migration script: Flask-Migrate with Alembic
   - Test migration: Apply to development environment
   - Validate changes: Automated tests for data integrity
   - Commit migration: Version control with descriptive naming

2. **Production Migrations:**
   - Backup: Full database backup before migration
   - Downtime assessment: Evaluate need for maintenance window
   - Apply migration: Run with transaction support
   - Verification: Validate successful application
   - Rollback plan: Documented recovery procedure

### Backup Strategy

Database backup implementation:

- Full backups: Daily database dumps
- Incremental backups: Hourly transaction log backups
- Retention policy: 30 days of daily backups, 24 hours of hourly backups
- Encryption: All backups encrypted at rest
- Testing: Regular restoration testing to verify integrity
- Off-site storage: Geographical redundancy for disaster recovery

### Performance Optimization

Database optimization techniques:

- Query optimization: Analyze and optimize frequent queries
- Indexing strategy: Create and maintain appropriate indexes
- Connection pooling: Efficient connection management
- Read replicas: Separate read traffic when scale requires
- Statement timeout: Prevent long-running queries
- Monitoring: Performance metrics with alerting

---

## Deployment Guide

### Environment Configuration

Environment setup requirements:

1. **Server Requirements:**
   - Python 3.11+ runtime environment
   - PostgreSQL 14+ database server
   - 4+ CPU cores recommended
   - 8GB+ RAM recommended
   - 50GB+ disk space for application and database

2. **Environment Variables:**
   - Required variables documented in .env.example
   - Sensitive credentials stored in secure environment
   - Separate configurations for dev/test/prod

3. **Network Configuration:**
   - Outbound access to Ethereum nodes (Infura)
   - Access to payment gateway APIs
   - Email (SMTP/API) connectivity
   - XRPL node connectivity

### Deployment Process

Standard deployment procedure:

1. **Preparation:**
   - Verify all tests pass in staging environment
   - Create deployment package with version tag
   - Backup current production environment
   - Schedule deployment window if needed

2. **Deployment:**
   - Apply database migrations if required
   - Deploy updated application code
   - Update static assets and configuration
   - Restart application services
   - Verify health checks and monitoring

3. **Verification:**
   - Run deployment verification tests
   - Confirm critical functionality
   - Monitor for unexpected errors
   - Verify external integrations

4. **Rollback Plan:**
   - Documented procedure for emergency rollback
   - Database restoration process
   - Previous version redeployment steps

### Testing Procedures

Pre-deployment testing requirements:

1. **Unit Tests:**
   - Coverage requirement: 80%+ of core functionality
   - All critical paths tested
   - Mocked external dependencies

2. **Integration Tests:**
   - API contract verification
   - External system integration testing
   - Database interaction verification

3. **End-to-End Tests:**
   - Critical user journeys
   - Payment processing flows
   - Authentication and authorization scenarios

4. **Performance Testing:**
   - Load testing for expected traffic
   - Stress testing for peak conditions
   - Endurance testing for stability

### Monitoring Setup

Production monitoring configuration:

1. **Application Monitoring:**
   - Error rate tracking
   - Response time metrics
   - Endpoint usage statistics
   - Background task performance

2. **Infrastructure Monitoring:**
   - Server resource utilization
   - Database performance
   - Network connectivity
   - Disk usage and I/O

3. **Business Metrics:**
   - Transaction volume and value
   - User activity and growth
   - Conversion rates
   - Error rates by category

4. **Alerting:**
   - Critical error notifications
   - Performance degradation alerts
   - Security incident alerts
   - Integration failure notifications

---

## Troubleshooting

### Common Issues

Frequently encountered problems and solutions:

1. **Blockchain Connectivity:**
   - Issue: Failed to connect to Ethereum node
   - Diagnosis: Check Infura project ID and network status
   - Resolution: Update credentials or use fallback provider

2. **Payment Gateway Errors:**
   - Issue: Gateway returns error code
   - Diagnosis: Check API logs for specific error message
   - Resolution: Address based on error type (credentials, limits, etc.)

3. **Database Connection Pool Exhaustion:**
   - Issue: "Too many connections" errors
   - Diagnosis: Check active connections and query duration
   - Resolution: Optimize queries, increase pool size, or implement connection release

4. **Transaction Processing Delays:**
   - Issue: Transactions stuck in PROCESSING state
   - Diagnosis: Check gateway callback logs and webhook delivery
   - Resolution: Implement manual status check or admin intervention

### Diagnostic Tools

Tools for troubleshooting:

1. **Log Analysis:**
   - Application logs with configurable verbosity
   - Transaction processing logs
   - Integration endpoint logs
   - Authentication audit logs

2. **Database Tools:**
   - SQL query interface for direct database inspection
   - Transaction analysis queries
   - Performance monitoring queries
   - Integrity checking tools

3. **API Testing:**
   - Endpoint testing tool for direct API access
   - Request/response inspection
   - Authentication token generation
   - Webhook simulation

4. **Blockchain Inspection:**
   - Transaction status checker
   - Smart contract interaction tool
   - Gas price analysis
   - Token balance viewer

### Recovery Procedures

Procedures for recovering from system failures:

1. **Database Recovery:**
   - Identify point of failure or corruption
   - Stop application services
   - Restore from most recent valid backup
   - Apply transaction logs if applicable
   - Verify data integrity
   - Restart services

2. **Blockchain Transaction Recovery:**
   - Identify failed or stuck transactions
   - Check transaction status on blockchain explorer
   - Determine appropriate action (cancel, resend, or update)
   - Execute recovery action
   - Update local transaction records

3. **Payment Gateway Reconciliation:**
   - Identify discrepancies between gateway and platform
   - Generate reconciliation report
   - Update transaction statuses as needed
   - Document resolution for audit purposes

---

## Development Guidelines

### Coding Standards

Development standards for consistency:

1. **Python Style Guide:**
   - Follow PEP 8 standards
   - Maximum line length: 100 characters
   - Docstrings: Google style format
   - Type hints: Used for all public functions
   - Comments: Explanatory comments for complex logic

2. **Flask Best Practices:**
   - Blueprints for modular organization
   - Flask-SQLAlchemy for database access
   - Flask-Login for authentication
   - Flask-WTF for form handling
   - RESTful API design principles

3. **JavaScript Standards:**
   - ES6+ syntax
   - Consistent indentation (2 spaces)
   - Semicolons required
   - Camel case for variables and functions
   - JSDoc comments for APIs

### Version Control

Version control procedures:

1. **Git Workflow:**
   - Feature branches for new development
   - Pull request process for code review
   - Squash merging to maintain clean history
   - Semantic versioning for releases
   - Protected main branch with CI checks

2. **Commit Messages:**
   - Subject line: Concise description (50 chars max)
   - Body: Detailed explanation if needed
   - Reference issue numbers when applicable
   - Conventional commits format preferred

3. **Branch Naming:**
   - feature/descriptive-name
   - bugfix/issue-description
   - hotfix/critical-issue
   - release/vX.Y.Z

### Testing Strategy

Testing expectations for developers:

1. **Test Coverage:**
   - Unit tests for all business logic
   - Integration tests for APIs and services
   - UI tests for critical user flows
   - Coverage targets: 80%+ for core functionality

2. **Test Environment:**
   - Isolated test database
   - Mocked external dependencies
   - Reproducible test setup
   - Automated test execution in CI/CD

3. **Test Types:**
   - Unit: pytest for individual functions and classes
   - Integration: End-to-end API tests
   - Security: Regular vulnerability scanning
   - Performance: Load and stress testing

### Documentation Requirements

Documentation standards:

1. **Code Documentation:**
   - Function docstrings with parameters and return values
   - Class docstrings explaining purpose and usage
   - Module-level documentation
   - Complex algorithm explanations

2. **API Documentation:**
   - OpenAPI/Swagger specification
   - Request/response examples
   - Error codes and handling
   - Authentication requirements

3. **Architecture Documentation:**
   - Component diagrams
   - Sequence diagrams for key flows
   - Data models and relationships
   - Integration points and dependencies

4. **Operational Documentation:**
   - Deployment procedures
   - Configuration options
   - Monitoring instructions
   - Troubleshooting guides

---

*This technical reference is maintained by the NVC Banking Platform development team. Last updated: April 22, 2025.*