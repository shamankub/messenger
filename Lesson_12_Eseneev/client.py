import argparse
import json
import logging
import socket
import sys
import threading
import time

import project_log.configs.client_logger
from decorators import log
from errors import *
from local.modules import *
from local.settings import *
from metaclasses import ClientVerifier

# Получаем объект-логгер с именем client:
LOG = logging.getLogger("client")

# Объект блокировки сокета и работы с БД
sock_lock = threading.Lock()
database_lock = threading.Lock()

# Класс формировки и отправки сообщений на сервер и взаимодействия с пользователем.
class ClientSender(threading.Thread, metaclass=ClientVerifier):
    def __init__(self, account_name, sock, database):
        self.account_name = account_name
        self.sock = sock
        self.database = database
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

        # Проверим, что получатель существует
        with database_lock:
            if not self.database.check_user(to_user):
                LOG.error(
                    f"Попытка отправить сообщение незарегистрированому получателю: {to_user}"
                )
                return

        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.account_name,
            DESTINATION: to_user,
            TIME: time.strftime("%d.%m.%Y %H:%M"),
            MESSAGE_TEXT: message,
        }
        LOG.debug(f"Сформирован словарь сообщения: {message_dict}")

        # Сохраняем сообщения для истории
        with database_lock:
            self.database.save_message(self.account_name, to_user, message)

        # Необходимо дождаться освобождения сокета для отправки сообщения
        with sock_lock:
            try:
                send_message(self.sock, message_dict)
                LOG.info(f"Отправлено сообщение для {to_user}")
            except OSError as err:
                if err.errno:
                    LOG.critical("Потеряно соединение с сервером.")
                    exit(1)
                else:
                    LOG.error("Не удалось передать сообщение. Таймаут соединения")

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
                with sock_lock:
                    try:
                        send_message(self.sock, self.create_exit_message())
                    except:
                        pass
                    print("Завершение работы по команде пользователя.")
                    LOG.info("Завершение работы по команде пользователя.")
                # Задержка для того, чтобы сообщение о выходе успело уйти.
                time.sleep(0.5)
                break
            elif command == "contacts":
                with database_lock:
                    contacts_list = self.database.get_contacts()
                for contact in contacts_list:
                    print(contact)
            elif command == "edit":
                self.edit_contacts()
            elif command == "history":
                self.print_history()
            else:
                print(
                    "Такой команды не существует, попробуйте ещё раз. Введите 'help', чтобы вывести поддерживаемые команды."
                )

    def edit_contacts(self):
        # Редактируем контакты
        ans = input("Для удаления введите del, для добавления add: ")
        if ans == "del":
            edit = input("Введите имя удаляемного контакта: ")
            with database_lock:
                if self.database.check_contact(edit):
                    self.database.del_contact(edit)
                else:
                    LOG.error("Попытка удаления несуществующего контакта.")
        elif ans == "add":
            # Проверка на возможность такого контакта
            edit = input("Введите имя создаваемого контакта: ")
            if self.database.check_user(edit):
                with database_lock:
                    self.database.add_contact(edit)
                with sock_lock:
                    try:
                        add_contact(self.sock, self.account_name, edit)
                    except ServerError:
                        LOG.error("Не удалось отправить информацию на сервер.")

    # Функция выводящяя историю сообщений
    def print_history(self):
        ask = input(
            "Показать входящие сообщения - in, исходящие - out, все - просто Enter: "
        )
        with database_lock:
            if ask == "in":
                history_list = self.database.get_history(to_who=self.account_name)
                for message in history_list:
                    print(
                        f"\nСообщение от пользователя: {message[0]} от {message[3]}:\n{message[2]}"
                    )
            elif ask == "out":
                history_list = self.database.get_history(from_who=self.account_name)
                for message in history_list:
                    print(
                        f"\nСообщение пользователю: {message[1]} от {message[3]}:\n{message[2]}"
                    )
            else:
                history_list = self.database.get_history()
                for message in history_list:
                    print(
                        f"\nСообщение от пользователя: {message[0]}, пользователю {message[1]} от {message[3]}\n{message[2]}"
                    )

    def print_help(self):
        # Выводим справку.
        print("Справка по программе:")
        print("message - отправить сообщение")
        print("history - история сообщений")
        print("contacts - список контактов")
        print("edit - редактирование списка контактов")
        print("help - вывести подсказки по командам")
        print("exit - выход из программы")


# Класс-приёмник сообщений с сервера. Принимает сообщения, выводит в консоль.
class ClientReader(threading.Thread, metaclass=ClientVerifier):
    def __init__(self, account_name, sock, database):
        self.account_name = account_name
        self.sock = sock
        self.database = database
        super().__init__()

    def run(self):
        # Обрабатываем сообщения пользователей, получаемые с сервера.
        while True:
            # Отдыхаем секунду и снова пробуем захватить сокет.
            # Если не сделать тут задержку, то второй поток может достаточно долго ждать освобождения сокета.
            time.sleep(1)
            with sock_lock:
                try:
                    message = get_message(self.sock)
                # Вышел таймаут соединения если errno = None, иначе обрыв соединения.
                except OSError as err:
                    if err.errno:
                        LOG.critical(f"Потеряно соединение с сервером.")
                        break
                # Проблемы с соединением
                except (
                    ConnectionError,
                    ConnectionAbortedError,
                    ConnectionResetError,
                    json.JSONDecodeError,
                ):
                    LOG.critical(f"Потеряно соединение с сервером.")
                    break
                # Если пакет корретно получен выводим в консоль и записываем в базу.
                else:
                    if (
                        ACTION in message
                        and message[ACTION] == MESSAGE
                        and SENDER in message
                        and DESTINATION in message
                        and MESSAGE_TEXT in message
                        and message[DESTINATION] == self.account_name
                    ):
                        print(f"\n{message[SENDER]}: {message[MESSAGE_TEXT]}")
                        with database_lock:
                            try:
                                self.database.save_message(
                                    message[SENDER],
                                    self.account_name,
                                    message[MESSAGE_TEXT],
                                )
                            except:
                                LOG.error("Ошибка взаимодействия с базой данных")
                        LOG.info(
                            f"Получено сообщение от {message[SENDER]}: {message[MESSAGE_TEXT]}"
                        )
                    else:
                        LOG.error(
                            f"Получено некорректное сообщение с сервера: {message}"
                        )


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


# Запрос контактов
def contacts_list_request(sock, name):
    LOG.debug(f"Запрос контактов для пользователя {name}")
    req = {ACTION: GET_CONTACTS, TIME: time.strftime("%d.%m.%Y %H:%M"), USER: name}
    LOG.debug(f"Сформирован запрос: {req}")
    send_message(sock, req)
    ans = get_message(sock)
    LOG.debug(f"Получен ответ: {ans}")
    if RESPONSE in ans and ans[RESPONSE] == 202:
        return ans[LIST_INFO]
    else:
        raise ServerError


# Добавление пользователя в контакты
def add_contact(sock, username, contact):
    LOG.debug(f"Создание контакта '{contact}'")
    req = {
        ACTION: ADD_CONTACT,
        TIME: time.strftime("%d.%m.%Y %H:%M"),
        USER: username,
        ACCOUNT_NAME: contact,
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 200:
        pass
    else:
        raise ServerError("Ошибка создания контакта")
    print("Контакт создан")


# Запрос списка известных пользователей
def user_list_request(sock, username):
    LOG.debug(f"Запрос списка известных пользователей {username}")
    req = {
        ACTION: USERS_REQUEST,
        TIME: time.strftime("%d.%m.%Y %H:%M"),
        ACCOUNT_NAME: username,
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 202:
        return ans[LIST_INFO]
    else:
        raise ServerError


# Удаление пользователя из контактов
def remove_contact(sock, username, contact):
    LOG.debug(f"Удаление контакта '{contact}'")
    req = {
        ACTION: REMOVE_CONTACT,
        TIME: time.strftime("%d.%m.%Y %H:%M"),
        USER: username,
        ACCOUNT_NAME: contact,
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 200:
        pass
    else:
        raise ServerError("Ошибка удаления контакта")
    print("Контакт удалён")


# Функция инициализатор БД. Запускается при старте, загружает данные в БД с сервера.
def database_load(sock, database, username):
    # Загружаем список известных пользователей
    try:
        users_list = user_list_request(sock, username)
    except ServerError:
        LOG.error("Ошибка запроса списка известных пользователей")
    else:
        database.add_users(users_list)

    # Загружаем список контактов
    try:
        contacts_list = contacts_list_request(sock, username)
    except ServerError:
        LOG.error("Ошибка запроса списка контактов")
    else:
        for contact in contacts_list:
            database.add_contact(contact)


def main():
    # Загружаем параметры командной строки
    # client.py 192.168.31.83 8079
    server_ip, server_port, client_name = create_argparser()

    if not client_name:
        client_name = input("Введите имя пользователя: ")
    else:
        # Выводим в консоль имя пользователя.
        print(f"-----{client_name}-----")

    LOG.info(
        f"Клиент запущен. IP адрес сервера: {server_ip}, порт: {server_port}, имя пользователя: {client_name}"
    )

    # Инициализация сокета и обмен
    try:
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # <socket.socket fd=4, family=AddressFamily.AF_INET, type=SocketKind.SOCK_STREAM, proto=0, laddr=('0.0.0.0', 0)>
        # Таймаут 1 секунда, необходим для освобождения сокета.
        transport.settimeout(1)
        transport.connect((server_ip, server_port))
        send_message(transport, create_presence(client_name))
        answer = process_answer(get_message(transport))
        print(f"Ответ сервера: {answer}")
        LOG.info(f"Ответ сервера: {answer}")
    except json.JSONDecodeError:
        print("Не удалось декодировать сообщение сервера.")
        LOG.error("Не удалось декодировать сообщение сервера.")
        exit(1)
    except ServerError as error:
        LOG.error(f"При установке соединения сервер вернул ошибку: {error.text}")
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
        # Инициализация БД
        database = ClientVerifier(client_name)
        database_load(transport, database, client_name)

        # Соединение с сервером установлено. Начинаем обмен сообщениями.
        receiver = ClientReader(client_name, transport, database)
        receiver.daemon = True
        receiver.start()

        # Отправка сообщений:
        sender = ClientSender(client_name, transport, database)
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
