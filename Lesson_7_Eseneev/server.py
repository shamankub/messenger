import argparse
import json
import logging
import select
import sys
import time
from socket import *

import project_log.configs.server_logger
from decorators import log
from local.modules import get_message, send_message
from local.settings import (
    ACCOUNT_NAME,
    ACTION,
    DEFAULT_PORT,
    ERROR,
    MAX_CONNECTIONS,
    MESSAGE,
    MESSAGE_TEXT,
    PRESENCE,
    RESPONSE,
    SENDER,
    TIME,
    USER,
)

# Получаем объект-логгер с именем server:
LOG = logging.getLogger("server")


@log
def process_client_message(message, messages_list, client):
    # Проверяем корректность сообщения от клиента и возвращаем ответ:

    # Если получаем корректное сообщение о присутствии - отправляем клиенту ответ.
    if (
        ACTION in message
        and message[ACTION] == PRESENCE
        and TIME in message
        and USER in message
        and message[USER][ACCOUNT_NAME] == "Guest"
    ):
        send_message(client, {RESPONSE: 200})
        return

    # Если получаем текстовое сообщение, то добавляем его в очередь на отправку.
    elif (
        ACTION in message
        and message[ACTION] == MESSAGE
        and TIME in message
        and MESSAGE_TEXT in message
    ):
        messages_list.append((message[ACCOUNT_NAME], message[MESSAGE_TEXT]))
        return

    # В остальных случаях отправляем клиенту ошибку Bad request.
    else:
        send_message(client, {RESPONSE: 400, ERROR: "Bad Request"})
        return


@log
def create_argparser():
    # Создаём парсер аргументов командной строки (sys.argv):
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-p", default=DEFAULT_PORT, type=int, nargs="?")
    arg_parser.add_argument("-a", default="", nargs="?")
    return arg_parser


def main():
    # Параметры конфигурации файла: -p 8079 -a 192.168.31.83
    # Валидация прослушиваемого порта:

    parser = create_argparser()
    namespace = parser.parse_args(sys.argv[1:])
    listen_ip = namespace.a
    listen_port = namespace.p

    # Проверяем входит ли номер порта в диапазон:
    if not 1023 < listen_port < 65536:
        LOG.critical(
            f"Сервер остановлен. port: {listen_port} не входит в диапазон от 1024 до 65535."
        )
        sys.exit(1)
    LOG.info(f"Сервер запущен. ip_address: {listen_ip}, port: {listen_port}.")

    # Готовим сокет
    server_socket = socket(AF_INET, SOCK_STREAM)
    server_socket.bind((listen_ip, listen_port))
    server_socket.settimeout(0.5)

    # Список клиентов, очередь сообщений на отправку.
    clients = []
    messages = []

    # Слушаем порт:
    server_socket.listen(MAX_CONNECTIONS)

    while True:
        # Ждём подключения, если таймаут вышел - ловим исключение.
        try:
            client, client_address = server_socket.accept()
        except OSError:
            pass
        else:
            LOG.info(f"Установлено соединение с {client_address}")
            clients.append(client)

        readst = []  # отправители
        writest = []  # получатели (ожидающие клиенты)
        errorst = []

        # Проверяем на наличие ожидающих клиентов:
        try:
            if clients:
                readst, writest, errorst = select.select(clients, clients, [], 0)
        except OSError:
            pass

        # Полученные сообщения кладём в словарь, если ошибка - то исключаем клиента из списка отправителей.
        if readst:
            for client_sender in readst:
                try:
                    process_client_message(
                        get_message(client_sender), messages, client_sender
                    )
                except:
                    LOG.info(
                        f"Клиент {client_sender.getpeername()} отключился от сервера."
                    )
                    clients.remove(client_sender)

        # Отправляем сообщения ожидающим клиентам, если ошибка - то исключаем клиента из списка получателей.
        if messages and writest:
            # [(message[ACCOUNT_NAME], message[MESSAGE_TEXT])]
            message = {
                ACTION: MESSAGE,
                SENDER: messages[0][0],
                TIME: time.strftime("%d.%m.%Y %H:%M"),
                MESSAGE_TEXT: messages[0][1],
            }
            del messages[0]
            for client_receiver in writest:
                try:
                    send_message(client_receiver, message)
                except:
                    LOG.info(
                        f"Клиент {client_receiver.getpeername()} отключился от сервера."
                    )
                    clients.remove(client_receiver)


if __name__ == "__main__":
    main()
