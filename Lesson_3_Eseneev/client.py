import json
import sys
import time
from socket import *

from local.modules import get_message, send_message
from local.settings import (
    ACCOUNT_NAME,
    ACTION,
    DEFAULT_IP,
    DEFAULT_PORT,
    ERROR,
    PRESENCE,
    RESPONSE,
    TIME,
    USER,
)


def create_presence(account_name):
    # Функция генерирует запрос о присутствии клиента
    presence_dict = {
        ACTION: PRESENCE,
        TIME: time.strftime("%d.%m.%Y %H:%M"),
        USER: {ACCOUNT_NAME: account_name},
    }
    # {'action': 'presence', 'time': '24.02.2022 21:02', 'user': {'account_name': 'Guest'}}
    return presence_dict


def process_answer(message):
    # Функция разбирает ответ от сервера
    if RESPONSE in message:
        if message[RESPONSE] == 200:
            return "200 : OK"
        return f"400 : {message[ERROR]}"
    raise ValueError


def main():
    # Загружаем параметры командной строки
    # client.py 192.168.31.83 8079
    try:
        server_ip = sys.argv[1]
        server_port = int(sys.argv[2])
        if server_port < 1024 or server_port > 65535:
            raise ValueError
    except IndexError:
        server_ip = DEFAULT_IP
        server_port = DEFAULT_PORT
    except ValueError:
        print("Порт должен быть в диапазоне от 1024 до 65535.")
        sys.exit(1)

    # Инициализация сокета и обмен
    client_socket = socket(AF_INET, SOCK_STREAM)
    # <socket.socket fd=4, family=AddressFamily.AF_INET, type=SocketKind.SOCK_STREAM, proto=0, laddr=('0.0.0.0', 0)>
    client_socket.connect((server_ip, server_port))
    message_to_server = create_presence("Guest")
    send_message(client_socket, message_to_server)
    try:
        answer = process_answer(get_message(client_socket))
        print(answer)
    except (ValueError, json.JSONDecodeError):
        print("Не удалось декодировать сообщение сервера.")


if __name__ == "__main__":
    main()
