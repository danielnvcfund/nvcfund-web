#!/usr/bin/env python3
"""
Simulate Contract Deployment Script
This script simulates completed contract deployments by adding entries to the database.
This is for demonstration purposes only.
"""

import json
import logging
from app import app, db
from models import SmartContract

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('deployment_simulator')

# Sample contract ABIs (simplified for demo)
SETTLEMENT_ABI = [
    {"type": "function", "name": "settlePayment", "inputs": [{"name": "recipient", "type": "address"}, {"name": "amount", "type": "uint256"}, {"name": "transactionId", "type": "string"}]},
    {"type": "function", "name": "getFeePercentage", "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
    {"type": "function", "name": "setFeePercentage", "inputs": [{"name": "newFeePercentage", "type": "uint256"}]}
]

MULTISIG_ABI = [
    {"type": "function", "name": "submitTransaction", "inputs": [{"name": "destination", "type": "address"}, {"name": "value", "type": "uint256"}, {"name": "data", "type": "bytes"}]},
    {"type": "function", "name": "confirmTransaction", "inputs": [{"name": "transactionId", "type": "uint256"}]},
    {"type": "function", "name": "executeTransaction", "inputs": [{"name": "transactionId", "type": "uint256"}]}
]

TOKEN_ABI = [
    {"type": "function", "name": "transfer", "inputs": [{"name": "recipient", "type": "address"}, {"name": "amount", "type": "uint256"}]},
    {"type": "function", "name": "balanceOf", "inputs": [{"name": "account", "type": "address"}], "outputs": [{"name": "", "type": "uint256"}]},
    {"type": "function", "name": "mint", "inputs": [{"name": "account", "type": "address"}, {"name": "amount", "type": "uint256"}]}
]

def simulate_deployments():
    """Simulate contract deployments by adding entries to the database"""
    with app.app_context():
        # Clear any existing contracts first
        SmartContract.query.delete()
        db.session.commit()
        
        # Add Settlement Contract
        settlement = SmartContract(
            name="SettlementContract",
            address="0x1234567890123456789012345678901234567890",
            abi=json.dumps(SETTLEMENT_ABI),
            bytecode="0x6080604...",  # Truncated bytecode
            description="Smart contract for handling payment settlements on Ethereum"
        )
        
        # Add MultiSig Wallet
        multisig = SmartContract(
            name="MultiSigWallet",
            address="0x2345678901234567890123456789012345678901",
            abi=json.dumps(MULTISIG_ABI),
            bytecode="0x6080604...",  # Truncated bytecode
            description="Multi-signature wallet for secure high-value transactions"
        )
        
        # Add NVC Token
        token = SmartContract(
            name="NVCToken",
            address="0x3456789012345678901234567890123456789012",
            abi=json.dumps(TOKEN_ABI),
            bytecode="0x6080604...",  # Truncated bytecode
            description="NVC Banking Token for platform transactions"
        )
        
        # Add to database
        db.session.add(settlement)
        db.session.add(multisig)
        db.session.add(token)
        db.session.commit()
        
        logger.info("Simulated contract deployments added to database")
        print("Contracts have been deployed (simulated)!")

if __name__ == "__main__":
    simulate_deployments()