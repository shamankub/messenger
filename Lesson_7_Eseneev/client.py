import argparse
import json
import logging
import sys
import time
from socket import *

import project_log.configs.client_logger
from decorators import log
from local.modules import get_message, send_message
from local.settings import (
    ACCOUNT_NAME,
    ACTION,
    DEFAULT_IP,
    DEFAULT_PORT,
    ERROR,
    MESSAGE,
    MESSAGE_TEXT,
    PRESENCE,
    RESPONSE,
    SENDER,
    TIME,
    USER,
)

# Получаем объект-логгер с именем client:
LOG = logging.getLogger("client")


@log
def create_presence(account_name):
    # Функция генерирует запрос о присутствии клиента
    presence_dict = {
        ACTION: PRESENCE,
        TIME: time.strftime("%d.%m.%Y %H:%M"),
        USER: {ACCOUNT_NAME: account_name},
    }
    LOG.debug(f"Сформировано {PRESENCE} сообщение для пользователя {account_name}")
    # {'action': 'presence', 'time': '24.02.2022 21:02', 'user': {'account_name': 'Guest'}}
    return presence_dict


@log
def process_answer(message):
    # Функция разбирает ответ от сервера
    LOG.debug(f"Разбор сообщения от сервера: {message}")
    if RESPONSE in message:
        if message[RESPONSE] == 200:
            return "200 : OK"
        return f"400 : {message[ERROR]}"
    raise ValueError


@log
def create_argparser():
    # Создаём парсер аргументов командной строки (sys.argv):
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("ip", default=DEFAULT_IP, nargs="?")
    arg_parser.add_argument("port", default=DEFAULT_PORT, type=int, nargs="?")
    arg_parser.add_argument("-m", "--mode", default="listen", nargs="?")
    return arg_parser


@log
def incoming_message(message):
    # Обрабатываем сообщения пользователей, получаемые с сервера.
    if (
        ACTION in message
        and message[ACTION] == MESSAGE
        and SENDER in message
        and MESSAGE_TEXT in message
    ):
        print(f"{message[SENDER]}: {message[MESSAGE_TEXT]}")
        LOG.info(f"Получено сообщение от {message[SENDER]}: {message[MESSAGE_TEXT]}")
    else:
        LOG.error(f"Получено некорректное сообщение с сервера: {message}")


@log
def create_message(sock, account_name):
    # Вводим текст сообщения и возвращаем на его основе словарь.
    message = input("Напишите текст сообщения. Для выхода введите 'q':")
    if message == "q":
        sock.close()
        LOG.info("Завершение работы.")
        print("Спасибо за пользование нашим мессенджером!")
        sys.exit(0)
    message_dict = {
        ACTION: MESSAGE,
        TIME: time.strftime("%d.%m.%Y %H:%M"),
        ACCOUNT_NAME: account_name,
        MESSAGE_TEXT: message,
    }
    LOG.debug(f"Сформирован словарь сообщения: {message_dict}")
    return message_dict


def main():
    # Загружаем параметры командной строки
    # client.py 192.168.31.83 8079
    parser = create_argparser()
    namespace = parser.parse_args(sys.argv[1:])
    server_ip = namespace.ip
    server_port = namespace.port
    client_mode = namespace.mode

    # Проверяем входит ли номер порта в диапазон:
    if not 1023 < server_port < 65536:
        LOG.critical(
            f"Клиент остановлен. port: {server_port} не входит в диапазон от 1024 до 65535."
        )
        sys.exit(1)

    # Валидация режима работы клиента:
    if client_mode not in ("listen", "send"):
        LOG.critical(f"Выберите режим работы 'listen' или 'send'")
        sys.exit(1)

    LOG.info(
        f"Клиент запущен. ip_address: {server_ip}, port: {server_port}, mode: {client_mode}"
    )

    # Инициализация сокета и обмен
    client_socket = socket(AF_INET, SOCK_STREAM)
    # <socket.socket fd=4, family=AddressFamily.AF_INET, type=SocketKind.SOCK_STREAM, proto=0, laddr=('0.0.0.0', 0)>
    client_socket.connect((server_ip, server_port))
    message_to_server = create_presence("Guest")
    send_message(client_socket, message_to_server)
    try:
        answer = process_answer(get_message(client_socket))
        print(f"Ответ сервера: {answer}")
        LOG.info(f"Ответ сервера: {answer}")
    except (ValueError, json.JSONDecodeError):
        print("Не удалось декодировать сообщение сервера.")
        LOG.error("Не удалось декодировать сообщение сервера.")
        sys.exit(1)
    except ConnectionRefusedError:
        print(
            f"Подключение к {server_ip}:{server_port} не установлено, т.к. конечный компьютер отверг запрос на подключение"
        )
        LOG.critical(
            f"Подключение к {server_ip}:{server_port} не установлено, т.к. конечный компьютер отверг запрос на подключение"
        )
        sys.exit(1)
    else:
        # Соединение с сервером установлено. Начинаем обмен сообщениями.
        if client_mode == "send":
            print("Этот клиент работает на отправку сообщений.")
        else:
            print("Этот клиент работает на приём сообщений.")
        while True:
            # Отправка сообщений:
            if client_mode == "send":
                try:
                    send_message(client_socket, create_message(client_socket, "Guest"))
                except (ConnectionAbortedError, ConnectionError, ConnectionResetError):
                    LOG.error(f"Разорвано соединение с сервером: {server_ip}")
                    sys.exit(1)

            # Приём сообщений:
            if client_mode == "listen":
                try:
                    incoming_message(get_message(client_socket))
                except (ConnectionAbortedError, ConnectionError, ConnectionResetError):
                    LOG.error(f"Разорвано соединение с сервером: {server_ip}")
                    sys.exit(1)


if __name__ == "__main__":
    main()
