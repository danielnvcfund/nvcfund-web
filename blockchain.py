import os
import json
import logging
from web3 import Web3, HTTPProvider
# Use the appropriate middleware for Web3.py v7+
from web3 import middleware
from eth_account import Account
from app import app, db
from models import BlockchainTransaction, SmartContract, Transaction, TransactionStatus

logger = logging.getLogger(__name__)

# Global Web3 instance
w3 = None

# Smart contract ABIs
SETTLEMENT_CONTRACT_ABI = json.loads('''
[
    {
        "constant": false,
        "inputs": [
            {
                "name": "recipient",
                "type": "address"
            },
            {
                "name": "amount",
                "type": "uint256"
            },
            {
                "name": "transactionId",
                "type": "string"
            }
        ],
        "name": "settlePayment",
        "outputs": [
            {
                "name": "success",
                "type": "bool"
            }
        ],
        "payable": true,
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [
            {
                "name": "transactionId",
                "type": "string"
            }
        ],
        "name": "getSettlementStatus",
        "outputs": [
            {
                "name": "status",
                "type": "string"
            },
            {
                "name": "timestamp",
                "type": "uint256"
            }
        ],
        "payable": false,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "anonymous": false,
        "inputs": [
            {
                "indexed": true,
                "name": "sender",
                "type": "address"
            },
            {
                "indexed": true,
                "name": "recipient",
                "type": "address"
            },
            {
                "indexed": false,
                "name": "amount",
                "type": "uint256"
            },
            {
                "indexed": false,
                "name": "transactionId",
                "type": "string"
            }
        ],
        "name": "PaymentSettled",
        "type": "event"
    }
]
''')

# Smart contract bytecode - this would be the compiled bytecode for the settlement contract
SETTLEMENT_CONTRACT_BYTECODE = "0x608060405234801561001057600080fd5b50610b4a806100206000396000f3006080604052600436106100325763ffffffff60e060020a6000350416637325731181146100375780638f86ffa914610092575b600080fd5b61007e6004803603606081101561004d57600080fd5b5073ffffffffffffffffffffffffffffffffffffffff81351690602081013590604001356100f7565b604080519115158252519081900360200190f35b6100d5600480360360208110156100a857600080fd5b8101906020810181356401000000008111156100c357600080fd5b8201836020820111156100d557600080fd5b50356100f7565b60408051918252519081900360200190f35b60008054600101905593925050505600a165627a7a72305820e8728975c8357a8ed8ab057382c149e69d208dce1383bd7fe0a54ffbf71b868c0029"


def init_web3():
    """Initialize Web3 connection to Ethereum node"""
    global w3
    
    # Get Ethereum node URL from environment variable or use Sepolia testnet as default
    # Note: Ropsten is deprecated, using Sepolia instead
    infura_project_id = os.environ.get("INFURA_PROJECT_ID", "9aa3d95b3bc440fa88ea12eaa4456161") # Default public key, limited usage
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
    
    if w3.is_connected():
        logger.info(f"Successfully connected to Ethereum node. Network version: {w3.net.version}")
        
        # Initialize settlement contract if it doesn't exist
        with app.app_context():
            initialize_settlement_contract()
    else:
        logger.error("Failed to connect to Ethereum node")


def initialize_settlement_contract():
    """Deploy the settlement contract if it doesn't exist"""
    contract = SmartContract.query.filter_by(name="SettlementContract").first()
    
    if not contract:
        try:
            # Get admin account for contract deployment
            admin_private_key = os.environ.get("ADMIN_ETH_PRIVATE_KEY")
            
            if not admin_private_key:
                logger.error("Admin private key not found. Cannot deploy settlement contract.")
                return
            
            admin_account = Account.from_key(admin_private_key)
            
            # Build contract
            settlement_contract = w3.eth.contract(
                abi=SETTLEMENT_CONTRACT_ABI,
                bytecode=SETTLEMENT_CONTRACT_BYTECODE
            )
            
            # Deploy contract
            construct_txn = settlement_contract.constructor().build_transaction({
                'from': admin_account.address,
                'nonce': w3.eth.get_transaction_count(admin_account.address),
                'gas': 2000000,
                'gasPrice': w3.to_wei('50', 'gwei')
            })
            
            signed_txn = w3.eth.account.sign_transaction(construct_txn, admin_private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
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
        except Exception as e:
            logger.error(f"Error deploying settlement contract: {str(e)}")
    else:
        logger.info(f"Settlement contract already exists at address: {contract.address}")


def get_settlement_contract():
    """Get the settlement contract instance"""
    contract = SmartContract.query.filter_by(name="SettlementContract").first()
    
    if not contract:
        logger.error("Settlement contract not found in database")
        return None
    
    return w3.eth.contract(address=contract.address, abi=json.loads(contract.abi))


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
        
        # Sign and send transaction
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
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
        
        # Sign and send transaction
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
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


def generate_ethereum_account():
    """
    Generate a new Ethereum account
    
    Returns:
        tuple: (address, private_key)
    """
    try:
        account = Account.create()
        return account.address, account.key.hex()
    
    except Exception as e:
        logger.error(f"Error generating Ethereum account: {str(e)}")
        return None, None
