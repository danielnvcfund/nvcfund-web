#!/usr/bin/env python3
"""
Check Contract Status Script
This script checks the database for deployed smart contracts and their addresses.
"""

import logging
from app import app
from models import SmartContract

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('contract_checker')

def check_contracts():
    """Check for deployed contracts in the database"""
    with app.app_context():
        contracts = SmartContract.query.all()
        
        if not contracts:
            logger.info("No contracts found in database")
            print("No contracts have been deployed yet.")
            return
            
        print("\nDeployed Contracts:")
        print("==================")
        
        for contract in contracts:
            print(f"Name: {contract.name}")
            print(f"Address: {contract.address}")
            print(f"Description: {contract.description}")
            print("------------------")
        
        # Check for specific contracts
        settlement = SmartContract.query.filter_by(name="SettlementContract").first()
        multisig = SmartContract.query.filter_by(name="MultiSigWallet").first()
        token = SmartContract.query.filter_by(name="NVCToken").first()
        
        print("\nContract Status Summary:")
        print("======================")
        print(f"Settlement Contract: {'✅ Deployed' if settlement else '❌ Not Deployed'}")
        print(f"MultiSig Wallet: {'✅ Deployed' if multisig else '❌ Not Deployed'}")
        print(f"NVC Token: {'✅ Deployed' if token else '❌ Not Deployed'}")
        
if __name__ == "__main__":
    check_contracts()