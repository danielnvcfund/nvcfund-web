import os
import json
import logging
from web3 import Web3, HTTPProvider
# Use the appropriate middleware for Web3.py v7+
from web3 import middleware
from eth_account import Account

logger = logging.getLogger(__name__)

# Import db from app within functions to avoid circular imports
def get_db():
    from app import db
    return db

def get_models():
    from models import BlockchainTransaction, SmartContract, Transaction, TransactionStatus
    return BlockchainTransaction, SmartContract, Transaction, TransactionStatus

# Global Web3 instance
w3 = None

def get_web3():
    """Get the Web3 instance, initializing it if necessary"""
    global w3
    if w3 is None:
        try:
            init_web3()
        except Exception as e:
            logger.error(f"Error initializing Web3: {str(e)}")
            return None
    return w3

# Contract compilation would normally be done separately
# These are placeholders that would be replaced with actual ABI and bytecode
# from Solidity compiler or Truffle/Hardhat build artifacts

# For now we'll use simplified placeholder ABIs that will be replaced
# with the actual ABI from the compiled contract during deployment

SETTLEMENT_CONTRACT_ABI = json.loads('''
[
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "_feePercentage",
                "type": "uint256"
            },
            {
                "internalType": "address",
                "name": "_feeCollector",
                "type": "address"
            }
        ],
        "stateMutability": "nonpayable",
        "type": "constructor"
    },
    {
        "inputs": [
            {
                "internalType": "string",
                "name": "transactionId",
                "type": "string"
            },
            {
                "internalType": "address",
                "name": "to",
                "type": "address"
            },
            {
                "internalType": "string",
                "name": "metadata",
                "type": "string"
            }
        ],
        "name": "createSettlement",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "settlementId",
                "type": "uint256"
            }
        ],
        "name": "completeSettlement",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "settlementId",
                "type": "uint256"
            }
        ],
        "name": "cancelSettlement",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "settlementId",
                "type": "uint256"
            },
            {
                "internalType": "string",
                "name": "reason",
                "type": "string"
            }
        ],
        "name": "disputeSettlement",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "settlementId",
                "type": "uint256"
            },
            {
                "internalType": "bool",
                "name": "completeSettlement",
                "type": "bool"
            }
        ],
        "name": "resolveDispute",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "settlementId",
                "type": "uint256"
            }
        ],
        "name": "getSettlement",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "id",
                "type": "uint256"
            },
            {
                "internalType": "string",
                "name": "transactionId",
                "type": "string"
            },
            {
                "internalType": "address",
                "name": "from",
                "type": "address"
            },
            {
                "internalType": "address",
                "name": "to",
                "type": "address"
            },
            {
                "internalType": "uint256",
                "name": "amount",
                "type": "uint256"
            },
            {
                "internalType": "uint256",
                "name": "fee",
                "type": "uint256"
            },
            {
                "internalType": "uint256",
                "name": "timestamp",
                "type": "uint256"
            },
            {
                "internalType": "uint8",
                "name": "status",
                "type": "uint8"
            },
            {
                "internalType": "string",
                "name": "metadata",
                "type": "string"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]
''')

MULTISIG_WALLET_ABI = json.loads('''
[
    {
        "inputs": [
            {
                "internalType": "address[]",
                "name": "_owners",
                "type": "address[]"
            },
            {
                "internalType": "uint256",
                "name": "_requiredConfirmations",
                "type": "uint256"
            }
        ],
        "stateMutability": "nonpayable",
        "type": "constructor"
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "destination",
                "type": "address"
            },
            {
                "internalType": "uint256",
                "name": "value",
                "type": "uint256"
            },
            {
                "internalType": "bytes",
                "name": "data",
                "type": "bytes"
            }
        ],
        "name": "submitTransaction",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "transactionId",
                "type": "uint256"
            }
        ],
        "name": "confirmTransaction",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "transactionId",
                "type": "uint256"
            }
        ],
        "name": "revokeConfirmation",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "transactionId",
                "type": "uint256"
            }
        ],
        "name": "executeTransaction",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]
''')

NVC_TOKEN_ABI = json.loads('''
[
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "initialSupply",
                "type": "uint256"
            },
            {
                "internalType": "address",
                "name": "initialOwner",
                "type": "address"
            }
        ],
        "stateMutability": "nonpayable",
        "type": "constructor"
    },
    {
        "inputs": [],
        "name": "totalSupply",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "account",
                "type": "address"
            }
        ],
        "name": "balanceOf",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "recipient",
                "type": "address"
            },
            {
                "internalType": "uint256",
                "name": "amount",
                "type": "uint256"
            }
        ],
        "name": "transfer",
        "outputs": [
            {
                "internalType": "bool",
                "name": "",
                "type": "bool"
            }
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "to",
                "type": "address"
            },
            {
                "internalType": "uint256",
                "name": "amount",
                "type": "uint256"
            }
        ],
        "name": "mint",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "from",
                "type": "address"
            },
            {
                "internalType": "uint256",
                "name": "amount",
                "type": "uint256"
            }
        ],
        "name": "burn",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]
''')

# Smart contract bytecodes - would be replaced with actual compiled bytecode
# For MVP purposes, these are placeholder values
SETTLEMENT_CONTRACT_BYTECODE = "0x608060405234801561001057600080fd5b5060405161001e90610046565b604051809103906000f080158015610039573d6000803e3d6000fd5b50506100529050565b6071806100606000396000f3fe608060405260043610601c5760003560e01c80635c60da1b146021575b600080fd5b60273660046056565b602f565b604080519115158252519081900360200190f35b6000602052806000526040600020600091509056fea26469706673582212200e12794d1d4bc268b81d108eb5c28ff5ae52eccccc6513daa83af985e688c5c064736f6c634300080f0033"
MULTISIG_WALLET_BYTECODE = "0x608060405234801561001057600080fd5b5060405161001e90610046565b604051809103906000f080158015610039573d6000803e3d6000fd5b50506100529050565b6071806100606000396000f3fe608060405260043610601c5760003560e01c80635c60da1b146021575b600080fd5b60273660046056565b602f565b604080519115158252519081900360200190f35b6000602052806000526040600020600091509056fea26469706673582212200e12794d1d4bc268b81d108eb5c28ff5ae52eccccc6513daa83af985e688c5c064736f6c634300080f0033"
NVC_TOKEN_BYTECODE = "0x608060405234801561001057600080fd5b5060405161001e90610046565b604051809103906000f080158015610039573d6000803e3d6000fd5b50506100529050565b6071806100606000396000f3fe608060405260043610601c5760003560e01c80635c60da1b146021575b600080fd5b60273660046056565b602f565b604080519115158252519081900360200190f35b6000602052806000526040600020600091509056fea26469706673582212200e12794d1d4bc268b81d108eb5c28ff5ae52eccccc6513daa83af985e688c5c064736f6c634300080f0033"


def init_web3():
    """Initialize Web3 connection to Ethereum node"""
    global w3
    
    # Get Ethereum node URL from environment variable or use Sepolia testnet as default
    # Note: Ropsten is deprecated, using Sepolia instead
    infura_project_id = os.environ.get("INFURA_PROJECT_ID", "e1159d2eed8f4c4fafa3f2053b612f9b") # Updated project ID
    
    # Remove '0x' prefix if present in the project ID as Infura doesn't expect it
    if infura_project_id and infura_project_id.startswith('0x'):
        infura_project_id = infura_project_id[2:]
        
    eth_node_url = os.environ.get("ETHEREUM_NODE_URL", f"https://sepolia.infura.io/v3/{infura_project_id}")
    
    logger.info(f"Connecting to Ethereum node: {eth_node_url}")
    
    # Initialize Web3 instance
    w3 = Web3(HTTPProvider(eth_node_url))
    
    # Add middleware for compatibility with PoA networks
    try:
        # For Web3.py version 7.x
        from web3.exceptions import ExtraDataLengthError
        
        # Use direct access to avoid attribute errors
        if hasattr(middleware, 'geth_poa_middleware'):
            w3.middleware_onion.inject(middleware.geth_poa_middleware, layer=0)
            logger.info("Added geth_poa_middleware from middleware module")
        else:
            logger.warning("geth_poa_middleware not found in middleware module")
    except Exception as e:
        logger.error(f"Error setting up PoA middleware: {str(e)}")
        logger.warning("Web3 functionality may be limited")
    
    if w3 and w3.is_connected():
        logger.info(f"Successfully connected to Ethereum node. Network version: {w3.net.version}")
        
        # Initialize contracts if they don't exist - will be done later in the app context
        # Moved contract initialization to outside this function to avoid circular imports
        
        return w3
    else:
        logger.error("Failed to connect to Ethereum node")
        
        # Return None to indicate connection failure
        # This will allow the application to handle the error gracefully
        # and implement fallback behavior
        return None


def initialize_settlement_contract():
    """Deploy the settlement contract if it doesn't exist"""
    db = get_db()
    BlockchainTransaction, SmartContract, Transaction, TransactionStatus = get_models()
    contract = SmartContract.query.filter_by(name="SettlementContract").first()
    
    if not contract:
        try:
            # Get admin account for contract deployment
            admin_private_key = os.environ.get("ADMIN_ETH_PRIVATE_KEY")
            
            if not admin_private_key:
                logger.error("Admin private key not found. Cannot deploy settlement contract.")
                return None, None
            
            admin_account = Account.from_key(admin_private_key)
            
            # Build contract
            settlement_contract = w3.eth.contract(
                abi=SETTLEMENT_CONTRACT_ABI,
                bytecode=SETTLEMENT_CONTRACT_BYTECODE
            )
            
            # Deploy contract with constructor arguments
            # Set fee percentage to 100 basis points (1%) and fee collector to admin account
            fee_percentage = 100  # 1% fee in basis points
            fee_collector = admin_account.address

            # Deploy contract with constructor arguments
            construct_txn = settlement_contract.constructor(
                fee_percentage,
                fee_collector
            ).build_transaction({
                'from': admin_account.address,
                'nonce': w3.eth.get_transaction_count(admin_account.address),
                'gas': 2000000,
                'gasPrice': w3.to_wei('50', 'gwei')
            })
            
            # Sign transaction with the updated Web3.py API (v7+)
            account = Account.from_key(admin_private_key)
            signed_txn = account.sign_transaction(construct_txn)
            
            # Get raw transaction bytes from the signed transaction
            raw_txn = signed_txn.raw_transaction
            
            # Send the raw transaction
            tx_hash = w3.eth.send_raw_transaction(raw_txn)
            
            # Wait for transaction receipt
            tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            contract_address = tx_receipt.contractAddress
            
            # Save contract to database
            new_contract = SmartContract(
                name="SettlementContract",
                address=contract_address,
                abi=json.dumps(SETTLEMENT_CONTRACT_ABI),
                bytecode=SETTLEMENT_CONTRACT_BYTECODE,
                description="Smart contract for handling payment settlements on Ethereum"
            )
            
            db.session.add(new_contract)
            db.session.commit()
            
            logger.info(f"Settlement contract deployed at address: {contract_address}")
            return contract_address, tx_hash.hex()
        except Exception as e:
            logger.error(f"Error deploying settlement contract: {str(e)}")
            return None, None
    else:
        logger.info(f"Settlement contract already exists at address: {contract.address}")
        return contract.address, None


def initialize_multisig_wallet(owner_addresses=None, required_confirmations=None):
    """Deploy the multi-signature wallet contract if it doesn't exist"""
    db = get_db()
    BlockchainTransaction, SmartContract, Transaction, TransactionStatus = get_models()
    contract = SmartContract.query.filter_by(name="MultiSigWallet").first()
    
    if not contract:
        try:
            # Get admin account for contract deployment
            admin_private_key = os.environ.get("ADMIN_ETH_PRIVATE_KEY")
            
            if not admin_private_key:
                logger.error("Admin private key not found. Cannot deploy MultiSigWallet contract.")
                return None, None
            
            admin_account = Account.from_key(admin_private_key)
            
            # For MultiSigWallet, we need initial owners (default to just admin for now)
            # In a production system, this would likely include multiple administrators or partners
            if not owner_addresses:
                owner_addresses = [admin_account.address]
                
            if not required_confirmations:
                required_confirmations = 1  # Single confirmation for now, would be higher in production
            
            # Build contract
            multisig_contract = w3.eth.contract(
                abi=MULTISIG_WALLET_ABI,
                bytecode=MULTISIG_WALLET_BYTECODE
            )
            
            # Deploy contract with constructor arguments
            construct_txn = multisig_contract.constructor(
                owner_addresses, 
                required_confirmations
            ).build_transaction({
                'from': admin_account.address,
                'nonce': w3.eth.get_transaction_count(admin_account.address),
                'gas': 5000000,  # Higher gas limit for more complex contract
                'gasPrice': w3.to_wei('50', 'gwei')
            })
            
            # Sign transaction with the updated Web3.py API (v7+)
            account = Account.from_key(admin_private_key)
            signed_txn = account.sign_transaction(construct_txn)
            
            # Get raw transaction bytes from the signed transaction
            raw_txn = signed_txn.raw_transaction
            
            # Send the raw transaction
            tx_hash = w3.eth.send_raw_transaction(raw_txn)
            
            # Wait for transaction receipt
            tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            contract_address = tx_receipt.contractAddress
            
            # Save contract to database
            new_contract = SmartContract(
                name="MultiSigWallet",
                address=contract_address,
                abi=json.dumps(MULTISIG_WALLET_ABI),
                bytecode=MULTISIG_WALLET_BYTECODE,
                description="Multi-signature wallet for secure high-value transactions"
            )
            
            db.session.add(new_contract)
            db.session.commit()
            
            logger.info(f"MultiSigWallet contract deployed at address: {contract_address}")
            return contract_address, tx_hash.hex()
        except Exception as e:
            logger.error(f"Error deploying MultiSigWallet contract: {str(e)}")
            return None, None
    else:
        logger.info(f"MultiSigWallet contract already exists at address: {contract.address}")
        return contract.address, None


def initialize_nvc_token():
    """Deploy the NVC token contract if it doesn't exist"""
    db = get_db()
    BlockchainTransaction, SmartContract, Transaction, TransactionStatus = get_models()
    contract = SmartContract.query.filter_by(name="NVCToken").first()
    
    if not contract:
        try:
            # Get admin account for contract deployment
            admin_private_key = os.environ.get("ADMIN_ETH_PRIVATE_KEY")
            
            if not admin_private_key:
                logger.error("Admin private key not found. Cannot deploy NVCToken contract.")
                return None, None
            
            admin_account = Account.from_key(admin_private_key)
            
            # Initial supply of 10,000,000,000,000 tokens (10 trillion - with 18 decimals)
            # This matches the NVCTokenomics document specification
            initial_supply = 10_000_000_000_000
            
            # Build contract
            token_contract = w3.eth.contract(
                abi=NVC_TOKEN_ABI,
                bytecode=NVC_TOKEN_BYTECODE
            )
            
            # Deploy contract with constructor arguments
            construct_txn = token_contract.constructor(
                initial_supply, 
                admin_account.address
            ).build_transaction({
                'from': admin_account.address,
                'nonce': w3.eth.get_transaction_count(admin_account.address),
                'gas': 3000000,
                'gasPrice': w3.to_wei('50', 'gwei')
            })
            
            # Sign transaction with the updated Web3.py API (v7+)
            account = Account.from_key(admin_private_key)
            signed_txn = account.sign_transaction(construct_txn)
            
            # Get raw transaction bytes from the signed transaction
            raw_txn = signed_txn.raw_transaction
            
            # Send the raw transaction
            tx_hash = w3.eth.send_raw_transaction(raw_txn)
            
            # Wait for transaction receipt
            tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            contract_address = tx_receipt.contractAddress
            
            # Save contract to database
            new_contract = SmartContract(
                name="NVCToken",
                address=contract_address,
                abi=json.dumps(NVC_TOKEN_ABI),
                bytecode=NVC_TOKEN_BYTECODE,
                description="NVC Banking Token for platform transactions"
            )
            
            db.session.add(new_contract)
            db.session.commit()
            
            logger.info(f"NVCToken contract deployed at address: {contract_address}")
            return contract_address, tx_hash.hex()
        except Exception as e:
            logger.error(f"Error deploying NVCToken contract: {str(e)}")
            return None, None
    else:
        logger.info(f"NVCToken contract already exists at address: {contract.address}")
        return contract.address, None


def get_settlement_contract():
    """Get the settlement contract instance"""
    try:
        db = get_db()
        BlockchainTransaction, SmartContract, Transaction, TransactionStatus = get_models()
        contract = SmartContract.query.filter_by(name="SettlementContract").first()
        
        if not contract:
            logger.error("Settlement contract not found in database")
            return None
        
        # Fix contract address format - ensure 0x is present and it's the right length
        address = contract.address
        if not address.startswith('0x'):
            address = '0x' + address
            
        # Use the ABI from our predefined constants to ensure compatibility
        return w3.eth.contract(address=address, abi=SETTLEMENT_CONTRACT_ABI)
    except Exception as e:
        logger.error(f"Error getting settlement contract: {str(e)}")
        return None


def get_multisig_wallet():
    """Get the MultiSigWallet contract instance"""
    try:
        db = get_db()
        BlockchainTransaction, SmartContract, Transaction, TransactionStatus = get_models()
        contract = SmartContract.query.filter_by(name="MultiSigWallet").first()
        
        if not contract:
            logger.error("MultiSigWallet contract not found in database")
            return None
        
        # Fix contract address format - ensure 0x is present and it's the right length
        address = contract.address
        if not address.startswith('0x'):
            address = '0x' + address
            
        # Use the ABI from our predefined constants to ensure compatibility
        return w3.eth.contract(address=address, abi=MULTISIG_WALLET_ABI)
    except Exception as e:
        logger.error(f"Error getting multisig wallet contract: {str(e)}")
        return None


def get_nvc_token():
    """Get the NVCToken contract instance"""
    try:
        db = get_db()
        BlockchainTransaction, SmartContract, Transaction, TransactionStatus = get_models()
        contract = SmartContract.query.filter_by(name="NVCToken").first()
        
        if not contract:
            logger.error("NVCToken contract not found in database")
            return None
        
        # Fix contract address format - ensure 0x is present and it's the right length
        address = contract.address
        if not address.startswith('0x'):
            address = '0x' + address
            
        # Use the ABI from our predefined constants to ensure compatibility
        return w3.eth.contract(address=address, abi=NVC_TOKEN_ABI)
    except Exception as e:
        logger.error(f"Error getting NVC token contract: {str(e)}")
        return None


def send_ethereum_transaction(from_address, to_address, amount_in_eth, private_key, transaction_id):
    """
    Send an Ethereum transaction
    
    Args:
        from_address (str): Sender's Ethereum address
        to_address (str): Recipient's Ethereum address
        amount_in_eth (float): Amount in ETH to send
        private_key (str): Sender's private key
        transaction_id (str): Associated application transaction ID
    
    Returns:
        str: Transaction hash if successful, None otherwise
    """
    try:
        db = get_db()
        BlockchainTransaction, SmartContract, Transaction, TransactionStatus = get_models()
        
        # Convert ETH to Wei
        amount_in_wei = w3.to_wei(amount_in_eth, 'ether')
        
        # Prepare transaction
        nonce = w3.eth.get_transaction_count(from_address)
        tx = {
            'nonce': nonce,
            'to': to_address,
            'value': amount_in_wei,
            'gas': 21000,
            'gasPrice': w3.to_wei('50', 'gwei'),
            'chainId': int(w3.net.version)
        }
        
        # Sign transaction with the updated Web3.py API (v7+)
        account = Account.from_key(private_key)
        signed_tx = account.sign_transaction(tx)
        
        # Get raw transaction bytes from the signed transaction
        raw_txn = signed_tx.raw_transaction
        
        # Send the raw transaction
        tx_hash = w3.eth.send_raw_transaction(raw_txn)
        
        # Wait for transaction receipt
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Record transaction in database
        blockchain_tx = BlockchainTransaction(
            transaction_id=transaction_id,
            eth_tx_hash=tx_hash.hex(),
            from_address=from_address,
            to_address=to_address,
            amount=amount_in_eth,
            gas_used=tx_receipt.gasUsed,
            gas_price=w3.from_wei(w3.to_wei('50', 'gwei'), 'ether'),
            block_number=tx_receipt.blockNumber,
            status="confirmed" if tx_receipt.status else "failed"
        )
        
        db.session.add(blockchain_tx)
        db.session.commit()
        
        # Update transaction status
        transaction = Transaction.query.filter_by(id=transaction_id).first()
        if transaction:
            transaction.eth_transaction_hash = tx_hash.hex()
            transaction.status = TransactionStatus.COMPLETED if tx_receipt.status else TransactionStatus.FAILED
            db.session.commit()
        
        logger.info(f"Ethereum transaction sent: {tx_hash.hex()}")
        return tx_hash.hex()
    
    except Exception as e:
        logger.error(f"Error sending Ethereum transaction: {str(e)}")
        
        db = get_db()
        BlockchainTransaction, SmartContract, Transaction, TransactionStatus = get_models()
        
        # Update transaction status to failed
        transaction = Transaction.query.filter_by(id=transaction_id).first()
        if transaction:
            transaction.status = TransactionStatus.FAILED
            db.session.commit()
        
        return None


def settle_payment_via_contract(from_address, to_address, amount_in_eth, private_key, transaction_id):
    """
    Settle a payment using the settlement smart contract
    
    Args:
        from_address (str): Sender's Ethereum address
        to_address (str): Recipient's Ethereum address
        amount_in_eth (float): Amount in ETH to send
        private_key (str): Sender's private key
        transaction_id (str): Associated application transaction ID
    
    Returns:
        str: Transaction hash if successful, None otherwise
    """
    try:
        db = get_db()
        BlockchainTransaction, SmartContract, Transaction, TransactionStatus = get_models()
        
        contract = get_settlement_contract()
        
        if not contract:
            logger.error("Settlement contract not available")
            return None
        
        # Convert ETH to Wei
        amount_in_wei = w3.to_wei(amount_in_eth, 'ether')
        
        # Build transaction
        nonce = w3.eth.get_transaction_count(from_address)
        
        # Get transaction function
        tx = contract.functions.settlePayment(
            to_address,
            amount_in_wei,
            str(transaction_id)
        ).build_transaction({
            'from': from_address,
            'value': amount_in_wei,
            'gas': 200000,
            'gasPrice': w3.to_wei('50', 'gwei'),
            'nonce': nonce,
            'chainId': int(w3.net.version)
        })
        
        # Sign transaction with the updated Web3.py API (v7+)
        account = Account.from_key(private_key)
        signed_tx = account.sign_transaction(tx)
        
        # Get raw transaction bytes from the signed transaction
        raw_txn = signed_tx.raw_transaction
        
        # Send the raw transaction
        tx_hash = w3.eth.send_raw_transaction(raw_txn)
        
        # Wait for transaction receipt
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Record transaction in database
        blockchain_tx = BlockchainTransaction(
            transaction_id=transaction_id,
            eth_tx_hash=tx_hash.hex(),
            from_address=from_address,
            to_address=to_address,
            amount=amount_in_eth,
            gas_used=tx_receipt.gasUsed,
            gas_price=w3.from_wei(w3.to_wei('50', 'gwei'), 'ether'),
            block_number=tx_receipt.blockNumber,
            status="confirmed" if tx_receipt.status else "failed"
        )
        
        db.session.add(blockchain_tx)
        db.session.commit()
        
        # Update transaction status
        transaction = Transaction.query.filter_by(id=transaction_id).first()
        if transaction:
            transaction.eth_transaction_hash = tx_hash.hex()
            transaction.status = TransactionStatus.COMPLETED if tx_receipt.status else TransactionStatus.FAILED
            db.session.commit()
        
        logger.info(f"Payment settled via contract: {tx_hash.hex()}")
        return tx_hash.hex()
    
    except Exception as e:
        logger.error(f"Error settling payment via contract: {str(e)}")
        
        db = get_db()
        BlockchainTransaction, SmartContract, Transaction, TransactionStatus = get_models()
        
        # Update transaction status to failed
        transaction = Transaction.query.filter_by(id=transaction_id).first()
        if transaction:
            transaction.status = TransactionStatus.FAILED
            db.session.commit()
        
        return None


def get_transaction_status(eth_tx_hash):
    """
    Get the status of an Ethereum transaction
    
    Args:
        eth_tx_hash (str): Ethereum transaction hash
    
    Returns:
        dict: Transaction details and status
    """
    try:
        tx_receipt = w3.eth.get_transaction_receipt(eth_tx_hash)
        tx = w3.eth.get_transaction(eth_tx_hash)
        
        result = {
            "hash": eth_tx_hash,
            "from": tx["from"],
            "to": tx["to"],
            "value": w3.from_wei(tx["value"], 'ether'),
            "block_number": tx_receipt["blockNumber"],
            "gas_used": tx_receipt["gasUsed"],
            "status": "confirmed" if tx_receipt["status"] else "failed"
        }
        
        return result
    
    except Exception as e:
        logger.error(f"Error getting transaction status: {str(e)}")
        return {"error": str(e)}


def submit_multisig_transaction(from_address, to_address, amount_in_eth, data, private_key, transaction_id):
    """
    Submit a transaction to the MultiSigWallet
    
    Args:
        from_address (str): Sender's Ethereum address (must be an owner)
        to_address (str): Recipient's Ethereum address
        amount_in_eth (float): Amount in ETH to send
        data (bytes): Transaction data payload
        private_key (str): Sender's private key
        transaction_id (str): Associated application transaction ID
        
    Returns:
        str: Transaction hash if successful, None otherwise
    """
    try:
        db = get_db()
        BlockchainTransaction, SmartContract, Transaction, TransactionStatus = get_models()
        
        contract = get_multisig_wallet()
        
        if not contract:
            logger.error("MultiSigWallet contract not available")
            return None
        
        # Convert ETH to Wei
        amount_in_wei = w3.to_wei(amount_in_eth, 'ether')
        
        # Build transaction
        nonce = w3.eth.get_transaction_count(from_address)
        
        # Submit transaction to multisig wallet
        tx = contract.functions.submitTransaction(
            to_address,
            amount_in_wei,
            data
        ).build_transaction({
            'from': from_address,
            'gas': 300000,
            'gasPrice': w3.to_wei('50', 'gwei'),
            'nonce': nonce,
            'chainId': int(w3.net.version)
        })
        
        # Sign transaction with the updated Web3.py API (v7+)
        account = Account.from_key(private_key)
        signed_tx = account.sign_transaction(tx)
        
        # Get raw transaction bytes from the signed transaction
        raw_txn = signed_tx.raw_transaction
        
        # Send the raw transaction
        tx_hash = w3.eth.send_raw_transaction(raw_txn)
        
        # Wait for transaction receipt
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Record transaction in database
        blockchain_tx = BlockchainTransaction(
            transaction_id=transaction_id,
            eth_tx_hash=tx_hash.hex(),
            from_address=from_address,
            to_address=to_address,
            amount=amount_in_eth,
            gas_used=tx_receipt.gasUsed,
            gas_price=w3.from_wei(w3.to_wei('50', 'gwei'), 'ether'),
            block_number=tx_receipt.blockNumber,
            contract_address=contract.address,
            status="confirmed" if tx_receipt.status else "failed"
        )
        
        db.session.add(blockchain_tx)
        db.session.commit()
        
        # Update transaction status
        transaction = Transaction.query.filter_by(id=transaction_id).first()
        if transaction:
            transaction.eth_transaction_hash = tx_hash.hex()
            transaction.status = TransactionStatus.PENDING  # MultiSig requires confirmations
            db.session.commit()
        
        logger.info(f"MultiSig transaction submitted: {tx_hash.hex()}")
        return tx_hash.hex()
    
    except Exception as e:
        logger.error(f"Error submitting MultiSig transaction: {str(e)}")
        
        db = get_db()
        BlockchainTransaction, SmartContract, Transaction, TransactionStatus = get_models()
        
        # Update transaction status to failed
        transaction = Transaction.query.filter_by(id=transaction_id).first()
        if transaction:
            transaction.status = TransactionStatus.FAILED
            db.session.commit()
        
        return None


def confirm_multisig_transaction(transaction_id, from_address, private_key, multisig_tx_id):
    """
    Confirm a transaction in the MultiSigWallet
    
    Args:
        transaction_id (str): Associated application transaction ID
        from_address (str): Owner address confirming the transaction
        private_key (str): Owner's private key
        multisig_tx_id (int): MultiSigWallet transaction ID to confirm
        
    Returns:
        str: Transaction hash if successful, None otherwise
    """
    try:
        db = get_db()
        BlockchainTransaction, SmartContract, Transaction, TransactionStatus = get_models()
        
        contract = get_multisig_wallet()
        
        if not contract:
            logger.error("MultiSigWallet contract not available")
            return None
        
        # Build transaction
        nonce = w3.eth.get_transaction_count(from_address)
        
        # Confirm transaction
        tx = contract.functions.confirmTransaction(
            multisig_tx_id
        ).build_transaction({
            'from': from_address,
            'gas': 100000,
            'gasPrice': w3.to_wei('50', 'gwei'),
            'nonce': nonce,
            'chainId': int(w3.net.version)
        })
        
        # Sign transaction with the updated Web3.py API (v7+)
        account = Account.from_key(private_key)
        signed_tx = account.sign_transaction(tx)
        
        # Get raw transaction bytes from the signed transaction
        raw_txn = signed_tx.raw_transaction
        
        # Send the raw transaction
        tx_hash = w3.eth.send_raw_transaction(raw_txn)
        
        # Wait for transaction receipt
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Record confirmation in database
        blockchain_tx = BlockchainTransaction(
            transaction_id=transaction_id,
            eth_tx_hash=tx_hash.hex(),
            from_address=from_address,
            to_address=contract.address,
            amount=0,  # Confirmation doesn't transfer value
            gas_used=tx_receipt.gasUsed,
            gas_price=w3.from_wei(w3.to_wei('50', 'gwei'), 'ether'),
            block_number=tx_receipt.blockNumber,
            contract_address=contract.address,
            status="confirmed" if tx_receipt.status else "failed"
        )
        
        db.session.add(blockchain_tx)
        db.session.commit()
        
        # Log confirmation
        logger.info(f"MultiSig transaction confirmed: {tx_hash.hex()}")
        return tx_hash.hex()
    
    except Exception as e:
        logger.error(f"Error confirming MultiSig transaction: {str(e)}")
        return None


def transfer_nvc_tokens(from_address, to_address, amount, private_key, transaction_id):
    """
    Transfer NVC tokens from one address to another
    
    Args:
        from_address (str): Sender's Ethereum address
        to_address (str): Recipient's Ethereum address
        amount (float): Amount of tokens to send
        private_key (str): Sender's private key
        transaction_id (str): Associated application transaction ID
        
    Returns:
        str: Transaction hash if successful, None otherwise
    """
    try:
        db = get_db()
        BlockchainTransaction, SmartContract, Transaction, TransactionStatus = get_models()
        
        contract = get_nvc_token()
        
        if not contract:
            logger.error("NVCToken contract not available")
            return None
        
        # Convert to token units (with 18 decimals)
        amount_in_units = int(amount * 10**18)
        
        # Build transaction
        nonce = w3.eth.get_transaction_count(from_address)
        
        # Transfer tokens
        tx = contract.functions.transfer(
            to_address,
            amount_in_units
        ).build_transaction({
            'from': from_address,
            'gas': 100000,
            'gasPrice': w3.to_wei('50', 'gwei'),
            'nonce': nonce,
            'chainId': int(w3.net.version)
        })
        
        # Sign transaction with the updated Web3.py API (v7+)
        account = Account.from_key(private_key)
        signed_tx = account.sign_transaction(tx)
        
        # Get raw transaction bytes from the signed transaction
        raw_txn = signed_tx.raw_transaction
        
        # Send the raw transaction
        tx_hash = w3.eth.send_raw_transaction(raw_txn)
        
        # Wait for transaction receipt
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Record transaction in database
        blockchain_tx = BlockchainTransaction(
            transaction_id=transaction_id,
            eth_tx_hash=tx_hash.hex(),
            from_address=from_address,
            to_address=to_address,
            amount=amount,
            gas_used=tx_receipt.gasUsed,
            gas_price=w3.from_wei(w3.to_wei('50', 'gwei'), 'ether'),
            block_number=tx_receipt.blockNumber,
            contract_address=contract.address,
            status="confirmed" if tx_receipt.status else "failed"
        )
        
        db.session.add(blockchain_tx)
        db.session.commit()
        
        # Update transaction status
        transaction = Transaction.query.filter_by(id=transaction_id).first()
        if transaction:
            transaction.eth_transaction_hash = tx_hash.hex()
            transaction.status = TransactionStatus.COMPLETED if tx_receipt.status else TransactionStatus.FAILED
            db.session.commit()
        
        logger.info(f"NVC tokens transferred: {tx_hash.hex()}")
        return tx_hash.hex()
    
    except Exception as e:
        logger.error(f"Error transferring NVC tokens: {str(e)}")
        
        db = get_db()
        BlockchainTransaction, SmartContract, Transaction, TransactionStatus = get_models()
        
        # Update transaction status to failed
        transaction = Transaction.query.filter_by(id=transaction_id).first()
        if transaction:
            transaction.status = TransactionStatus.FAILED
            db.session.commit()
        
        return None


def get_nvc_token_balance(address):
    """
    Get NVC token balance for an address
    
    Args:
        address (str): Ethereum address to check
        
    Returns:
        float: Token balance
    """
    try:
        contract = get_nvc_token()
        
        if not contract:
            logger.error("NVCToken contract not available")
            return 0
        
        # Call balanceOf function
        balance_in_units = contract.functions.balanceOf(address).call()
        
        # Convert to human-readable format (with 18 decimals)
        balance = balance_in_units / 10**18
        
        return balance
    
    except Exception as e:
        logger.error(f"Error getting NVC token balance: {str(e)}")
        return 0


def create_new_settlement(from_address, to_address, amount_in_eth, private_key, transaction_id, tx_metadata=""):
    """
    Create a new settlement using the SettlementContract
    
    Args:
        from_address (str): Sender's Ethereum address
        to_address (str): Recipient's Ethereum address
        amount_in_eth (float): Amount in ETH to send
        private_key (str): Sender's private key
        transaction_id (str): Associated application transaction ID
        metadata (str): Additional settlement data
        
    Returns:
        str: Transaction hash if successful, None otherwise
    """
    try:
        db = get_db()
        BlockchainTransaction, SmartContract, Transaction, TransactionStatus = get_models()
        
        contract = get_settlement_contract()
        
        if not contract:
            logger.error("Settlement contract not available")
            return None
        
        # Convert ETH to Wei
        amount_in_wei = w3.to_wei(amount_in_eth, 'ether')
        
        # Build transaction
        nonce = w3.eth.get_transaction_count(from_address)
        
        # Create settlement
        tx = contract.functions.createSettlement(
            str(transaction_id),
            to_address,
            tx_metadata
        ).build_transaction({
            'from': from_address,
            'value': amount_in_wei,
            'gas': 300000,
            'gasPrice': w3.to_wei('50', 'gwei'),
            'nonce': nonce,
            'chainId': int(w3.net.version)
        })
        
        # Sign transaction with the updated Web3.py API (v7+)
        account = Account.from_key(private_key)
        signed_tx = account.sign_transaction(tx)
        
        # Get raw transaction bytes from the signed transaction
        raw_txn = signed_tx.raw_transaction
        
        # Send the raw transaction
        tx_hash = w3.eth.send_raw_transaction(raw_txn)
        
        # Wait for transaction receipt
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Record transaction in database
        blockchain_tx = BlockchainTransaction(
            transaction_id=transaction_id,
            eth_tx_hash=tx_hash.hex(),
            from_address=from_address,
            to_address=to_address,
            amount=amount_in_eth,
            gas_used=tx_receipt.gasUsed,
            gas_price=w3.from_wei(w3.to_wei('50', 'gwei'), 'ether'),
            block_number=tx_receipt.blockNumber,
            contract_address=contract.address,
            status="confirmed" if tx_receipt.status else "failed"
        )
        
        db.session.add(blockchain_tx)
        db.session.commit()
        
        # Update transaction status
        transaction = Transaction.query.filter_by(id=transaction_id).first()
        if transaction:
            transaction.eth_transaction_hash = tx_hash.hex()
            transaction.status = TransactionStatus.PENDING  # Settlement is pending until completed
            db.session.commit()
        
        logger.info(f"Settlement created: {tx_hash.hex()}")
        return tx_hash.hex()
    
    except Exception as e:
        logger.error(f"Error creating settlement: {str(e)}")
        
        db = get_db()
        BlockchainTransaction, SmartContract, Transaction, TransactionStatus = get_models()
        
        # Update transaction status to failed
        transaction = Transaction.query.filter_by(id=transaction_id).first()
        if transaction:
            transaction.status = TransactionStatus.FAILED
            db.session.commit()
        
        return None


# This function has been moved to blockchain_utils.py to prevent circular imports
