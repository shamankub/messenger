import argparse
import json
import logging
import socket
import sys
import threading
import time

import project_log.configs.client_logger
from decorators import log
from local.modules import *
from local.settings import *
from metaclasses import ClientVerifier

# Получаем объект-логгер с именем client:
LOG = logging.getLogger("client")

# Класс формировки и отправки сообщений на сервер и взаимодействия с пользователем.
class ClientSender(threading.Thread, metaclass=ClientVerifier):
    def __init__(self, account_name, sock):
        self.account_name = account_name
        self.sock = sock
        super().__init__()

    def create_exit_message(self):
        # Создаёт словарь с сообщением о выходе.
        return {
            ACTION: EXIT,
            TIME: time.strftime("%d.%m.%Y %H:%M"),
            ACCOUNT_NAME: self.account_name,
        }

    def create_message(self):
        # Вводим получателя и текст сообщения.
        to_user = input("Введите имя получателя: ")
        message = input("Введите текст сообщения: ")
        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.account_name,
            DESTINATION: to_user,
            TIME: time.strftime("%d.%m.%Y %H:%M"),
            MESSAGE_TEXT: message,
        }
        LOG.debug(f"Сформирован словарь сообщения: {message_dict}")
        try:
            send_message(self.sock, message_dict)
            LOG.info(f"Отправлено сообщение для {to_user}")
        except:
            LOG.critical("Потеряно соединение с сервером.")
            exit(1)

    def run(self):
        # Взаимодействуем с пользователем, запрашиваем команды, отправляем сообщения.
        self.print_help()
        while True:
            command = input("Введите команду: ")
            if command == "message":
                self.create_message()
            elif command == "help":
                self.print_help()
            elif command == "exit":
                try:
                    send_message(self.sock, self.create_exit_message())
                except:
                    pass
                print("Завершение работы по команде пользователя.")
                LOG.info("Завершение работы по команде пользователя.")
                # Задержка для того, чтобы сообщение о выходе успело уйти.
                time.sleep(0.5)
                break
            else:
                print(
                    "Такой команды не существует, попробуйте ещё раз. Введите 'help', чтобы вывести поддерживаемые команды."
                )

    def print_help(self):
        # Выводим справку.
        print("Справка по программе:")
        print("message - отправить сообщение")
        print("help - вывести подсказки по командам")
        print("exit - выход из программы")


# Класс-приёмник сообщений с сервера. Принимает сообщения, выводит в консоль.
class ClientReader(threading.Thread, metaclass=ClientVerifier):
    def __init__(self, account_name, sock):
        self.account_name = account_name
        self.sock = sock
        super().__init__()

    def run(self):
        # Обрабатываем сообщения пользователей, получаемые с сервера.
        while True:
            try:
                message = get_message(self.sock)
                if (
                    ACTION in message
                    and message[ACTION] == MESSAGE
                    and SENDER in message
                    and DESTINATION in message
                    and MESSAGE_TEXT in message
                    and message[DESTINATION] == self.account_name
                ):
                    print(f"\n{message[SENDER]}: {message[MESSAGE_TEXT]}")
                    LOG.info(
                        f"Получено сообщение от {message[SENDER]}: {message[MESSAGE_TEXT]}"
                    )
                else:
                    LOG.error(f"Получено некорректное сообщение с сервера: {message}")
            except (
                OSError,
                ConnectionError,
                ConnectionAbortedError,
                ConnectionResetError,
                json.JSONDecodeError,
            ):
                LOG.critical(f"Потеряно соединение с сервером.")
                break


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
    arg_parser.add_argument("addr", default=DEFAULT_IP, nargs="?")
    arg_parser.add_argument("port", default=DEFAULT_PORT, type=int, nargs="?")
    arg_parser.add_argument("-n", "--name", default=None, nargs="?")
    namespace = arg_parser.parse_args(sys.argv[1:])
    server_ip = namespace.addr
    server_port = namespace.port
    client_name = namespace.name

    # Проверяем входит ли номер порта в диапазон:
    if not 1023 < server_port < 65536:
        LOG.critical(
            f"Клиент остановлен. port: {server_port} не входит в диапазон от 1024 до 65535."
        )
        exit(1)

    return server_ip, server_port, client_name


def main():
    # Загружаем параметры командной строки
    # client.py 192.168.31.83 8079
    server_ip, server_port, client_name = create_argparser()

    if not client_name:
        client_name = input("Введите имя пользователя: ")

    LOG.info(
        f"Клиент запущен. IP адрес сервера: {server_ip}, порт: {server_port}, имя пользователя: {client_name}"
    )

    # Инициализация сокета и обмен
    try:
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # <socket.socket fd=4, family=AddressFamily.AF_INET, type=SocketKind.SOCK_STREAM, proto=0, laddr=('0.0.0.0', 0)>
        transport.connect((server_ip, server_port))
        send_message(transport, create_presence(client_name))
        answer = process_answer(get_message(transport))
        print(f"-----{client_name}-----")  # Выводим в консоль имя пользователя.
        print(f"Ответ сервера: {answer}")
        LOG.info(f"Ответ сервера: {answer}")
    except json.JSONDecodeError:
        print("Не удалось декодировать сообщение сервера.")
        LOG.error("Не удалось декодировать сообщение сервера.")
        exit(1)
    except (ConnectionRefusedError, ConnectionError):
        print(
            f"Подключение к {server_ip}:{server_port} не установлено, т.к. конечный компьютер отверг запрос на подключение"
        )
        LOG.critical(
            f"Подключение к {server_ip}:{server_port} не установлено, т.к. конечный компьютер отверг запрос на подключение"
        )
        exit(1)
    else:
        # Соединение с сервером установлено. Начинаем обмен сообщениями.
        receiver = ClientReader(client_name, transport)
        receiver.daemon = True
        receiver.start()

        # Отправка сообщений:
        sender = ClientSender(client_name, transport)
        sender.daemon = True
        sender.start()
        LOG.debug("Запущены процессы")

        # Основной цикл. Если один из потоков завершён, то значит или потеряно соединение
        # или пользователь ввёл 'exit'. Поскольку все события обрабатываются в потоках,
        # достаточно просто завершить цикл.
        while True:
            time.sleep(1)
            if receiver.is_alive() and sender.is_alive():
                continue
            break


if __name__ == "__main__":
    main()
