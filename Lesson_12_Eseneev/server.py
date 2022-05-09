import argparse
import configparser
import logging
import os
import select
import socket
import sys
import threading

from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QApplication, QMessageBox

import project_log.configs.server_logger
from decorators import log
from descriptors import Port
from local.modules import *
from local.settings import *
from metaclasses import ServerVerifier
from server_db import ServerStorage
from server_gui import (
    ConfigWindow,
    HistoryWindow,
    MainWindow,
    create_stat_model,
    gui_create_model,
)

# Получаем объект-логгер с именем server:
LOG = logging.getLogger("server")

# Чтобы каждый раз не обновлять базу, ставим флаг, что новый пользователь подключён
new_connection = False
conflag_lock = threading.Lock()


@log
def create_argparser(default_port, default_address):
    # Создаём парсер аргументов командной строки (sys.argv):
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-p", default=default_port, type=int, nargs="?")
    arg_parser.add_argument("-a", default=default_address, nargs="?")
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
            except OSError as err:
                LOG.error(f"Ошибка работы с сокетами: {err}")

            # Полученные сообщения кладём в словарь, если ошибка - то исключаем клиента из списка отправителей.
            if readst:
                for client_sender in readst:
                    try:
                        self.process_client_message(
                            get_message(client_sender), client_sender
                        )
                    except OSError:
                        LOG.info(
                            f"Клиент {client_sender.getpeername()} отключился от сервера."
                        )
                        for name in self.names:
                            if self.names[name] == client_sender:
                                self.database.user_logout(name)
                                del self.names[name]
                                break
                        self.clients.remove(client_sender)

            # Обрабатываем каждое сообщение.
            for message in self.messages:
                try:
                    self.process_message(message, writest)
                except (
                    ConnectionAbortedError,
                    ConnectionError,
                    ConnectionResetError,
                    ConnectionRefusedError,
                ):
                    LOG.info(f"Связь с {message[DESTINATION]} потеряна")
                    self.clients.remove(self.names[message[DESTINATION]])
                    self.database.user_logout(message[DESTINATION])
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
        global new_connection
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
                with conflag_lock:
                    new_connection = True
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
            and self.names[message[SENDER]] == client
        ):
            self.messages.append(message)
            self.database.process_message(message[SENDER], message[DESTINATION])
            return

        # Если клиент выходит:
        elif (
            ACTION in message
            and message[ACTION] == EXIT
            and ACCOUNT_NAME in message
            and self.names[message[ACCOUNT_NAME]] == client
        ):
            self.database.user_logout(message[ACCOUNT_NAME])
            LOG.info(f"Клиент {message[ACCOUNT_NAME]} корректно отключился от сервера.")
            self.clients.remove(self.names[message[ACCOUNT_NAME]])
            self.names[message[ACCOUNT_NAME]].close()
            del self.names[message[ACCOUNT_NAME]]
            with conflag_lock:
                new_connection = True
            return

        # Если это добавление контакта
        elif (
            ACTION in message
            and message[ACTION] == ADD_CONTACT
            and ACCOUNT_NAME in message
            and USER in message
            and self.names[message[USER]] == client
        ):
            self.database.add_contact(message[USER], message[ACCOUNT_NAME])
            send_message(client, {RESPONSE: 200})

        # Если это удаление контакта
        elif (
            ACTION in message
            and message[ACTION] == REMOVE_CONTACT
            and ACCOUNT_NAME in message
            and USER in message
            and self.names[message[USER]] == client
        ):
            self.database.remove_contact(message[USER], message[ACCOUNT_NAME])
            send_message(client, {RESPONSE: 200})

        # Если это запрос известных пользователей
        elif (
            ACTION in message
            and message[ACTION] == USERS_REQUEST
            and ACCOUNT_NAME in message
            and self.names[message[ACCOUNT_NAME]] == client
        ):
            response = {RESPONSE: 202, LIST_INFO: None}
            response[LIST_INFO] = [user[0] for user in self.database.users_list()]
            send_message(client, response)

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
    # Загрузка файла конфигурации сервера
    config = configparser.ConfigParser()

    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(f"{dir_path}/{SERVER_CONFIG}")

    # Параметры конфигурации файла: -p 8079 -a 192.168.31.83
    # Валидация прослушиваемого порта:
    listen_ip, listen_port = create_argparser(
        config["SETTINGS"]["Default_port"], config["SETTINGS"]["Listen_Address"]
    )

    # Инициализация базы данных
    database = ServerStorage(
        os.path.join(
            config["SETTINGS"]["Database_path"], config["SETTINGS"]["Database_file"]
        )
    )

    # Выполняем "подключение" пользователей
    database.user_login("client_1", "192.168.1.4", 8888)
    database.user_login("client_2", "192.168.1.5", 7777)
    database.user_login("client_3", "192.168.1.6", 6666)

    # Создание экземпляра класса - сервера.
    server = Server(listen_ip, listen_port, database)
    server.daemon = True
    server.start()

    # Создаём графическое окружение для сервера
    server_app = QApplication(sys.argv)
    main_window = MainWindow()

    # Инициализируем параметры окна
    main_window.statusBar().showMessage("Server Working")
    main_window.active_clients_table.setModel(gui_create_model(database))
    main_window.active_clients_table.resizeColumnsToContents()
    main_window.active_clients_table.resizeRowsToContents()

    # Обновляем список подключённых клиентов,
    # Проверяем флаг подключения, и если надо обновляем список
    def list_update():
        global new_connection
        if new_connection:
            main_window.active_clients_table.setModel(gui_create_model(database))
            main_window.active_clients_table.resizeColumnsToContents()
            main_window.active_clients_table.resizeRowsToContents()
            with conflag_lock:
                new_connection = False

    # Создаём окно со статистикой клиентов
    def show_statistics():
        global stat_window
        stat_window = HistoryWindow()
        stat_window.history_table.setModel(create_stat_model(database))
        stat_window.history_table.resizeColumnsToContents()
        stat_window.history_table.resizeRowsToContents()
        stat_window.show()

    # Создаём окно с настройками сервера
    def server_config():
        global config_window
        # Заносим текущие параметры
        config_window = ConfigWindow()
        config_window.db_path.insert(config["SETTINGS"]["Database_path"])
        config_window.db_file.insert(config["SETTINGS"]["Database_file"])
        config_window.port.insert(config["SETTINGS"]["Default_port"])
        config_window.ip.insert(config["SETTINGS"]["Listen_Address"])
        config_window.save_btn.clicked.connect(save_server_config)

    # Сохраняем настройки
    def save_server_config():
        global config_window
        message = QMessageBox()
        config["SETTINGS"]["Database_path"] = config_window.db_path.text()
        config["SETTINGS"]["Database_file"] = config_window.db_file.text()
        try:
            port = int(config_window.port.text())
        except ValueError:
            message.warning(config_window, "Ошибка", "Порт должен быть числом")
        else:
            config["SETTINGS"]["Listen_Address"] = config_window.ip.text()
            if 1023 < port < 65536:
                config["SETTINGS"]["Default_port"] = str(port)
                print(port)
                with open("server.ini", "w") as conf:
                    config.write(conf)
                    message.information(
                        config_window, "OK", "Настройки успешно сохранены!"
                    )
            else:
                message.warning(
                    config_window, "Ошибка", "Порт должен быть от 1024 до 65536"
                )

    # Таймер, обновляющий список клиентов 1 раз в секунду
    timer = QTimer()
    timer.timeout.connect(list_update)
    timer.start(1000)

    # Связываем кнопки с процедурами
    main_window.refresh_button.triggered.connect(list_update)
    main_window.show_history_button.triggered.connect(show_statistics)
    main_window.config_btn.triggered.connect(server_config)

    # Запускаем GUI
    server_app.exec_()


if __name__ == "__main__":
    main()
