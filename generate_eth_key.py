from eth_account import Account
import secrets

def generate_ethereum_account():
    """
    Generate a new Ethereum account
    
    Returns:
        tuple: (address, private_key)
    """
    try:
        # Generate a random private key
        private_key = secrets.token_hex(32)
        account = Account.from_key(private_key)
        return account.address, private_key
    
    except Exception as e:
        print(f"Error generating Ethereum account: {str(e)}")
        return None, None

if __name__ == "__main__":
    address, private_key = generate_ethereum_account()
    print(f"Address: {address}")
    print(f"Private Key: {private_key}")
    print(f"Private Key Length (hex chars): {len(private_key)}")
    print(f"Private Key Length (bytes): {len(bytes.fromhex(private_key))}")
    print("\nTo use this key, add it to your environment variables:")
    print(f"ADMIN_ETH_PRIVATE_KEY={private_key}")