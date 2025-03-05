from agents.agent.entity.inner.finish import FinishOutput
from agents.agent.entity.inner.wallet_output import WalletOutput


async def sign_with_wallet(unsignedTransaction: str):
    """
    Sign a transaction with the wallet.
    Args:
        unsignedTransaction (str): The unsigned transaction to be signed.
    Returns:
        str: The signed transaction.
    """
    print("signing", unsignedTransaction)
    # return "signed"
    yield WalletOutput({"type": "sign", "unsignedTransaction": "AQAAAA....."})
    yield FinishOutput()
