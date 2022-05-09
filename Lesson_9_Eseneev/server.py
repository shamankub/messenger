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
    DESTINATION,
    ERROR,
    EXIT,
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
def process_client_message(message, messages_list, client, clients, names):
    # Проверяем корректность сообщения от клиента и возвращаем ответ:
    LOG.debug(f"Разбор сообщения от клиента: {message}")
    # Если получаем корректное сообщение о присутствии - отправляем клиенту ответ.
    if (
        ACTION in message
        and message[ACTION] == PRESENCE
        and TIME in message
        and USER in message
    ):
        # Если пользователь существует, то завершаем соединение, иначе регистрируем пользователя.
        if message[USER][ACCOUNT_NAME] not in names.keys():
            names[message[USER][ACCOUNT_NAME]] = client
            send_message(client, {RESPONSE: 200})
        else:
            send_message(
                client, {RESPONSE: 400, ERROR: "Уже есть пользователь с таким именем."}
            )
            clients.remove(client)
            client.close()
        return

    # Если получаем текстовое сообщение, то добавляем его в очередь на отправку.
    elif (
        ACTION in message
        and message[ACTION] == MESSAGE
        and DESTINATION in message
        and TIME in message
        and SENDER in message
        and MESSAGE_TEXT in message
    ):
        messages_list.append(message)
        return

    # Если клиент выходит:
    elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message:
        clients.remove(names[message[ACCOUNT_NAME]])
        names[message[ACCOUNT_NAME]].close()
        del names[message[ACCOUNT_NAME]]
        return

    # В остальных случаях отправляем клиенту ошибку Bad request.
    else:
        send_message(client, {RESPONSE: 400, ERROR: "Bad Request"})
        return


@log
def process_message(message, names, listen_socks):
    # Отправляем сообщение указанному клиенту.
    if message[DESTINATION] in names and names[message[DESTINATION]] in listen_socks:
        send_message(names[message[DESTINATION]], message)
        LOG.info(
            f"Отправлено сообщение для {message[DESTINATION]} от {message[SENDER]}."
        )
    elif (
        message[DESTINATION] in names
        and names[message[DESTINATION]] not in listen_socks
    ):
        raise ConnectionError
    else:
        LOG.error(
            f"Невозможно отправить сообщение. {message[DESTINATION]} не зарегистрирован на сервере."
        )


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

    # Словарь, содержащий имена пользователей и соответствующие им сокеты.
    names = {}

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
                        get_message(client_sender),
                        messages,
                        client_sender,
                        clients,
                        names,
                    )
                except Exception:
                    LOG.info(
                        f"Клиент {client_sender.getpeername()} отключился от сервера."
                    )
                    clients.remove(client_sender)

        # Обрабатываем каждое сообщение.
        for i in messages:
            try:
                process_message(i, names, writest)
            except Exception:
                LOG.info(f"Связь с {i[DESTINATION]} потеряна")
                clients.remove(names[i[DESTINATION]])
                del names[i[DESTINATION]]
        messages.clear()


if __name__ == "__main__":
    main()
