import argparse
import logging
import select
import socket
import sys
import threading

import project_log.configs.server_logger
from decorators import log
from descriptors import Port
from local.modules import *
from local.settings import *
from metaclasses import ServerVerifier
from server_db import ServerStorage

# Получаем объект-логгер с именем server:
LOG = logging.getLogger("server")


@log
def create_argparser():
    # Создаём парсер аргументов командной строки (sys.argv):
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-p", default=DEFAULT_PORT, type=int, nargs="?")
    arg_parser.add_argument("-a", default="", nargs="?")
    namespace = arg_parser.parse_args(sys.argv[1:])
    listen_ip = namespace.a
    listen_port = namespace.p
    return listen_ip, listen_port


# Основной класс сервера
class Server(threading.Thread, metaclass=ServerVerifier):
    port = Port()

    def __init__(self, listen_ip, listen_port, database):
        # Параметры конфигурации файла: -p 8079 -a 192.168.31.83
        # Валидация прослушиваемого порта:
        self.addr = listen_ip
        self.port = listen_port
        self.database = database

        # Список клиентов, очередь сообщений на отправку.
        self.clients = []
        self.messages = []

        # Словарь, содержащий имена пользователей и соответствующие им сокеты.
        self.names = {}

        super().__init__()

    def init_socket(self):
        LOG.info(f"Сервер запущен. ip_address: {self.addr}, port: {self.port}.")
        # Готовим сокет
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.bind((self.addr, self.port))
        transport.settimeout(0.5)

        # Слушаем порт:
        self.sock = transport
        self.sock.listen()

    def run(self):
        # Инициализация сокета
        self.init_socket()

        # Основной цикл программы сервера
        while True:
            # Ждём подключения, если таймаут вышел - ловим исключение.
            try:
                client, client_address = self.sock.accept()
            except OSError:
                pass
            else:
                LOG.info(f"Установлено соединение с {client_address}")
                self.clients.append(client)

            readst = []  # отправители
            writest = []  # получатели (ожидающие клиенты)
            errorst = []

            # Проверяем на наличие ждущих клиентов
            try:
                if self.clients:
                    readst, writest, errorst = select.select(
                        self.clients, self.clients, [], 0
                    )
            except OSError:
                pass

            # Полученные сообщения кладём в словарь, если ошибка - то исключаем клиента из списка отправителей.
            if readst:
                for client_sender in readst:
                    try:
                        self.process_client_message(
                            get_message(client_sender), client_sender
                        )
                    except:
                        LOG.info(
                            f"Клиент {client_sender.getpeername()} отключился от сервера."
                        )
                        self.clients.remove(client_sender)

            # Обрабатываем каждое сообщение.
            for message in self.messages:
                try:
                    self.process_message(message, writest)
                except:
                    LOG.info(f"Связь с {message[DESTINATION]} потеряна")
                    self.clients.remove(self.names[message[DESTINATION]])
                    del self.names[message[DESTINATION]]
            self.messages.clear()

    # Отправляем сообщение указанному клиенту.
    def process_message(self, message, listen_socks):
        if (
            message[DESTINATION] in self.names
            and self.names[message[DESTINATION]] in listen_socks
        ):
            send_message(self.names[message[DESTINATION]], message)
            LOG.info(
                f"Отправлено сообщение для {message[DESTINATION]} от {message[SENDER]}."
            )
        elif (
            message[DESTINATION] in self.names
            and self.names[message[DESTINATION]] not in listen_socks
        ):
            raise ConnectionError
        else:
            LOG.error(
                f"Невозможно отправить сообщение. {message[DESTINATION]} не зарегистрирован на сервере."
            )

    # Проверяем корректность сообщения от клиента и возвращаем ответ:
    def process_client_message(self, message, client):
        LOG.debug(f"Разбор сообщения от клиента: {message}")
        # Если получаем корректное сообщение о присутствии - отправляем клиенту ответ.
        if (
            ACTION in message
            and message[ACTION] == PRESENCE
            and TIME in message
            and USER in message
        ):
            # Если пользователь существует, то завершаем соединение, иначе регистрируем пользователя.
            if message[USER][ACCOUNT_NAME] not in self.names.keys():
                self.names[message[USER][ACCOUNT_NAME]] = client
                client_ip, client_port = client.getpeername()
                self.database.user_login(
                    message[USER][ACCOUNT_NAME], client_ip, client_port
                )
                send_message(client, {RESPONSE: 200})
            else:
                response = {RESPONSE: 400, ERROR: None}
                response[ERROR] = "Уже есть пользователь с таким именем."
                send_message(client, response)
                self.clients.remove(client)
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
            self.messages.append(message)
            return

        # Если клиент выходит:
        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message:
            self.database.user_logout(message[ACCOUNT_NAME])
            self.clients.remove(self.names[message[ACCOUNT_NAME]])
            self.names[message[ACCOUNT_NAME]].close()
            del self.names[message[ACCOUNT_NAME]]
            return

        # В остальных случаях отправляем клиенту ошибку Bad request.
        else:
            response = {RESPONSE: 400, ERROR: None}
            response[ERROR] = "Bad Request."
            send_message(client, response)
            return


def print_help():
    # Выводим справку.
    print("Справка по программе:")
    print("help - вывести подсказки по командам")
    print("exit - выход из программы")

    print("users - список известных пользователей")
    print("connected - список подключенных пользователей")
    print("loghist - история входов пользователя")


def main():
    # Параметры конфигурации файла: -p 8079 -a 192.168.31.83
    # Валидация прослушиваемого порта:
    listen_ip, listen_port = create_argparser()

    # Инициализация базы данных
    database = ServerStorage()

    # Создание экземпляра класса - сервера.
    server = Server(listen_ip, listen_port, database)
    server.daemon = True
    server.start()

    # Печатаем справку:
    print_help()

    # Основной цикл сервера:
    while True:
        command = input("Введите комманду: \n")
        if command == "help":
            print_help()
        elif command == "exit":
            break
        elif command == "users":
            for user in sorted(database.users_list()):
                print(f"Пользователь {user[0]}, последний вход: {user[1]}")
        elif command == "connected":
            for user in sorted(database.active_users_list()):
                print(
                    f"Пользователь {user[0]}, подключен: {user[1]}:{user[2]}, время установки соединения: {user[3]}"
                )
        elif command == "loghist":
            name = input(
                "Введите имя пользователя для просмотра истории. Для вывода всей истории, просто нажмите Enter: "
            )
            for user in sorted(database.login_history(name)):
                print(
                    f"Пользователь: {user[0]} время входа: {user[1]}. Вход с: {user[2]}:{user[3]}"
                )
        else:
            print("Команда не распознана.")


if __name__ == "__main__":
    main()
