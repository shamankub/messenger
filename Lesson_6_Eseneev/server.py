import argparse
import json
import logging
import sys
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
    PRESENCE,
    RESPONSE,
    TIME,
    USER,
)

# Получаем объект-логгер с именем server:
LOG = logging.getLogger("server")


@log
def process_client_message(message):
    # Проверяет корректность сообщения от клиента и возвращает ответ.
    LOG.debug(f"Разбор сообщения от клиента: {message}")
    if (
        ACTION in message
        and message[ACTION] == PRESENCE
        and TIME in message
        and USER in message
        and message[USER][ACCOUNT_NAME] == "Guest"
    ):
        return {RESPONSE: 200}
    return {RESPONSE: 400, ERROR: "Bad Request"}


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

    # Слушаем порт
    server_socket.listen(MAX_CONNECTIONS)

    while True:
        client, client_address = server_socket.accept()
        LOG.info(f"Соединение с {client_address} установлено.")
        try:
            client_message = get_message(client)
            print(f"Получено сообщение от клиента: {client_message}")
            LOG.debug(f"Получено сообщение от клиента: {client_message}")
            response = process_client_message(client_message)
            LOG.info(f"Cформирован ответ клиенту {response}")
            send_message(client, response)
            LOG.debug(f"Соединение с {client_address} закрывается.")
            client.close()
        except (ValueError, json.JSONDecodeError):
            print(
                "Не удалось декодировать сообщение клиента. Соединение с {client_address} закрывается."
            )
            LOG.error(
                "Не удалось декодировать сообщение клиента. Соединение с {client_address} закрывается."
            )
            client.close()


if __name__ == "__main__":
    main()
