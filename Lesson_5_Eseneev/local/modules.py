import json
from local.settings import MAX_PACKAGE_LENGTH


def get_message(client):
    encoded_response = client.recv(MAX_PACKAGE_LENGTH)
    if isinstance(encoded_response, bytes):
        json_response = encoded_response.decode("utf-8")  # {"response": 200}
        response = json.loads(json_response)  # {'response': 200}
        if isinstance(response, dict):
            return response
        raise ValueError
    raise ValueError


def send_message(sock, message):
    json_message = json.dumps(message)  # {"response": 200}
    encoded_message = json_message.encode("utf-8")  # b'{"response": 200}'
    sock.send(encoded_message)
