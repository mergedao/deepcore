import base64
import logging
from typing import Union

import base58
import nacl.exceptions
import nacl.signing
from eth_account import Account
from eth_account.messages import encode_defunct

from agents.protocol.schemas import ChainType

logger = logging.getLogger(__name__)

def generate_nonce() -> str:
    """Generate a random nonce for wallet signature"""
    import random
    import string
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))

def get_message_to_sign(address: str, nonce: str) -> str:
    """Get message to sign for wallet authentication"""
    return f"Sign this message to authenticate with your wallet address: {address}\nNonce: {nonce}"

def verify_signature(message: str, signature: str, address: str, chain_type: Union[ChainType, str] = ChainType.ETHEREUM) -> bool:
    """
    Verify wallet signature based on chain type
    
    :param message: Message that was signed
    :param signature: Signature to verify
    :param address: Wallet address
    :param chain_type: Blockchain type (ChainType enum or string)
    :return: True if signature is valid, False otherwise
    """
    try:
        # Convert string to enum if needed
        if isinstance(chain_type, str):
            try:
                chain_type = ChainType(chain_type.lower())
            except ValueError:
                logger.warning(f"Unsupported chain type: {chain_type}")
                return False
        
        if chain_type == ChainType.ETHEREUM:
            return verify_ethereum_signature(message, signature, address)
        elif chain_type == ChainType.SOLANA:
            return verify_solana_signature(message, signature, address)
        else:
            logger.warning(f"Unsupported chain type: {chain_type}")
            return False
    except Exception as e:
        logger.error(f"Error verifying signature: {str(e)}", exc_info=True)
        return False

def verify_ethereum_signature(message: str, signature: str, address: str) -> bool:
    """Verify Ethereum wallet signature"""
    try:
        message_hash = encode_defunct(text=message)
        recovered_address = Account.recover_message(message_hash, signature=signature)
        return recovered_address.lower() == address.lower()
    except Exception as e:
        logger.error(f"Error verifying Ethereum signature: {str(e)}", exc_info=True)
        return False

def verify_solana_signature(message: str, signature: str, address: str) -> bool:
    """
    Verify Solana wallet signature
    
    :param message: Message that was signed
    :param signature: Signature in base58 or base64 format
    :param address: Solana wallet address (public key in base58 format)
    :return: True if signature is valid, False otherwise
    """
    try:
        # Convert message to bytes
        message_bytes = message.encode('utf-8')
        
        # Try to decode the signature (could be base58 or base64)
        try:
            # First try base58 decoding (common in Solana wallets)
            signature_bytes = base58.b58decode(signature)
        except Exception:
            try:
                # If base58 fails, try base64 decoding
                signature_bytes = base64.b64decode(signature)
            except Exception as e:
                logger.error(f"Failed to decode Solana signature: {str(e)}")
                return False
        
        # Decode the public key from base58
        try:
            public_key_bytes = base58.b58decode(address)
            if len(public_key_bytes) != 32:
                logger.error(f"Invalid Solana public key length: {len(public_key_bytes)}")
                return False
        except Exception as e:
            logger.error(f"Failed to decode Solana public key: {str(e)}")
            return False
            
        # Create a VerifyKey from the public key bytes
        verify_key = nacl.signing.VerifyKey(public_key_bytes)
        
        # Verify the signature
        try:
            verify_key.verify(message_bytes, signature_bytes)
            return True
        except nacl.exceptions.BadSignatureError:
            logger.warning(f"Invalid Solana signature for address: {address}")
            return False
        
    except Exception as e:
        logger.error(f"Error verifying Solana signature: {str(e)}", exc_info=True)
        return False

# Test function for Solana signature verification
def test_solana_signature_verification():
    """
    Test function for Solana signature verification
    
    This is for development/testing purposes only and should be removed in production.
    """
    try:
        # Example Solana keypair (DO NOT USE IN PRODUCTION)
        # This is just for testing the verification logic
        from nacl.signing import SigningKey
        
        # Generate a new random keypair for testing
        signing_key = SigningKey.generate()
        verify_key = signing_key.verify_key
        
        # Get the public key in bytes and convert to base58
        public_key_bytes = bytes(verify_key)
        public_key_base58 = base58.b58encode(public_key_bytes).decode('utf-8')
        
        # Create a test message
        test_message = "Test message for Solana signature verification"
        message_bytes = test_message.encode('utf-8')
        
        # Sign the message
        signature_bytes = signing_key.sign(message_bytes).signature
        signature_base58 = base58.b58encode(signature_bytes).decode('utf-8')
        
        # Verify the signature
        result = verify_solana_signature(test_message, signature_base58, public_key_base58)
        
        # Log the result
        if result:
            logger.info("Solana signature verification test passed!")
        else:
            logger.error("Solana signature verification test failed!")
            
        return result
    except Exception as e:
        logger.error(f"Error in Solana signature verification test: {str(e)}", exc_info=True)
        return False 