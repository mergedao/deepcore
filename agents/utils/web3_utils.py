import secrets
from eth_account.messages import encode_defunct
from eth_account import Account

def generate_nonce() -> str:
    """Generate random nonce for wallet signature"""
    return secrets.token_hex(16)

def get_message_to_sign(address: str, nonce: str) -> str:
    """Get message for wallet to sign"""
    return f"Sign this message to login to DeepCore\nAddress: {address}\nNonce: {nonce}"

def verify_signature(message: str, signature: str, address: str) -> bool:
    """Verify wallet signature"""
    try:
        message_hash = encode_defunct(text=message)
        recovered_address = Account.recover_message(message_hash, signature=signature)
        return recovered_address.lower() == address.lower()
    except Exception:
        return False 