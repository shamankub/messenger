import json
import sys
from socket import *

from local.modules import get_message, send_message
from local.settings import (
    ACCOUNT_NAME,
    ACTION,
    DEFAULT_PORT,
    ERROR,
    MAX_CONNECTIONS,
    PRESENCE,
    RESPONSE,
    TIME,
    USER,
)


def process_client_message(message):
    # Проверяет корректность сообщения от клиента и возвращает ответ.
    if (
        ACTION in message
        and message[ACTION] == PRESENCE
        and TIME in message
        and USER in message
        and message[USER][ACCOUNT_NAME] == "Guest"
    ):
        return {RESPONSE: 200}
    return {RESPONSE: 400, ERROR: "Bad Request"}


def main():
    # Параметры конфигурации файла: -p 8079 -a 192.168.31.83
    # Валидация прослушиваемого порта:
    try:
        if "-p" in sys.argv:
            listen_port = int(sys.argv[sys.argv.index("-p") + 1])
        else:
            listen_port = DEFAULT_PORT
        if listen_port < 1024 or listen_port > 65535:
            raise ValueError
    except IndexError:
        print("После параметра '-p' необходимо указать порт.")
        sys.exit(1)
    except ValueError:
        print("Порт должен быть в диапазоне от 1024 до 65535.")
        sys.exit(1)

    # Валидация прослушиваемого IP-адреса:
    try:
        if "-a" in sys.argv:
            listen_address = sys.argv[sys.argv.index("-a") + 1]
        else:
            listen_address = ""

    except IndexError:
        print("После параметра '-a' необходимо указать IP-адрес.")
        sys.exit(1)

    # Готовим сокет
    server_socket = socket(AF_INET, SOCK_STREAM)
    server_socket.bind((listen_address, listen_port))

    # Слушаем порт
    server_socket.listen(MAX_CONNECTIONS)

    while True:
        client, client_address = server_socket.accept()
        try:
            client_message = get_message(client)
            print(client_message)
            response = process_client_message(client_message)
            send_message(client, response)
            client.close()
        except (ValueError, json.JSONDecodeError):
            print("Принято некорректное сообщение от клиента.")
            client.close()


if __name__ == "__main__":
    main()
