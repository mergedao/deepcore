# Supported scenarios for agent context storage
# This list can be extended in the future
SUPPORTED_CONTEXT_SCENARIOS = [
    "wallet_signature",  # Wallet signature data
]

sensitive_config_map = {
    "wallet_signature":{
      "parameters": {
        "nested_fields": [
          {
            "path": "signedTransaction",
            "description": "Nested password field in body"
          }
        ]
      }
    }
}