from agents.agent.tools.function.wallet_tool import sign_with_wallet, get_public_key

LOCAL_TOOL = [sign_with_wallet, get_public_key]

def get_local_tool():
    return LOCAL_TOOL