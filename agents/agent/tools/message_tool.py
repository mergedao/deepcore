import json


def send_message(event: str, message: dict) -> str:
    """
    Send a message to the client.
    """
    return f'event: {event}\ndata: {json.dumps(message, ensure_ascii=False)}\n\n'
