import time

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
)
from sqlalchemy.orm import mapper, sessionmaker

from local.settings import *


class ServerStorage:
    # Пользователи
    class AllUsers:
        def __init__(self, username):
            self.id = None
            self.username = username
            self.last_login = time.strftime("%d.%m.%Y %H:%M")

    # Активные пользователи
    class ActiveUsers:
        def __init__(self, user_id, ip_address, port, login_time):
            self.id = None
            self.user_id = user_id
            self.ip_address = ip_address
            self.port = port
            self.login_time = login_time

    # История входов
    class LoginHistory:
        def __init__(self, name, date, ip_address, port):
            self.id = None
            self.name = name
            self.date = date
            self.ip_address = ip_address
            self.port = port

    # Таблица контактов пользователей
    class UsersContacts:
        def __init__(self, user, contact):
            self.id = None
            self.user = user
            self.contact = contact

    # Таблица истории действий
    class UsersHistory:
        def __init__(self, user):
            self.id = None
            self.user = user
            self.sent = 0
            self.accepted = 0

    def __init__(self, path):
        # Соединение с базой данных
        print(path)
        self.engine = create_engine(
            f"sqlite:///{path}",
            echo=False,
            pool_recycle=7200,
            connect_args={"check_same_thread": False},
        )

        # Создание таблиц
        self.metadata = MetaData()

        # Таблица пользователей
        users_table = Table(
            "Users",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("username", String, unique=True),
            Column("last_login", String),
        )

        # Таблица активных пользователей
        active_users_table = Table(
            "Active_users",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("user_id", ForeignKey("Users.id"), unique=True),
            Column("ip_address", String),
            Column("port", Integer),
            Column("login_time", String),
        )

        # Таблица истории входов
        login_history_table = Table(
            "Login_history",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("name", ForeignKey("Users.id")),
            Column("date", String),
            Column("ip_address", String),
            Column("port", Integer),
        )

        # Создаём таблицу контактов пользователей
        users_contacts_table = Table(
            "Users_contacts",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("user", ForeignKey("Users.id")),
            Column("contact", ForeignKey("Users.id")),
        )

        # Создаём таблицу истории пользователей
        users_history_table = Table(
            "Users_history",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("user", ForeignKey("Users.id")),
            Column("sent", Integer),
            Column("accepted", Integer),
        )

        # Делаем миграции
        self.metadata.create_all(self.engine)

        # Создаём отображения
        mapper(self.AllUsers, users_table)
        mapper(self.ActiveUsers, active_users_table)
        mapper(self.LoginHistory, login_history_table)
        mapper(self.UsersContacts, users_contacts_table)
        mapper(self.UsersHistory, users_history_table)

        # Создаём сессию
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        # При установке соединения очищаем таблицу активных пользователей
        self.session.query(self.ActiveUsers).delete()
        self.session.commit()

    # При входе пользователя, записываем в базу факт входа
    def user_login(self, username, ip_address, port):
        print(f"Вход выполнен: {username}, {ip_address}, {port}")
        # Ищем в таблице пользователя с таким именем
        res = self.session.query(self.AllUsers).filter_by(username=username)
        # Если находим, то обновляем время последнего входа
        if res.count():
            user = res.first()
            user.last_login = time.strftime("%d.%m.%Y %H:%M")
        # Если нет, то создаём нового пользователя
        else:
            # Создаём объект класса AllUsers
            user = self.AllUsers(username)
            # Передаём данные в таблицу
            self.session.add(user)
            # Сохраняем транзакцию
            self.session.commit()

        # Создаём запись в таблице активных пользователей о факте входа.
        # Создаём экземпляр класса ActiveUsers
        new_active_user = self.ActiveUsers(
            user.id, ip_address, port, time.strftime("%d.%m.%Y %H:%M")
        )
        # Передаём данные в таблицу
        self.session.add(new_active_user)

        # Создаём запись в таблице истории входов
        # Создаём экземпляр класса LoginHistory
        history = self.LoginHistory(
            user.id, time.strftime("%d.%m.%Y %H:%M"), ip_address, port
        )
        # Передаём данные в таблицу
        self.session.add(history)

        # Создаём запись в таблице истории пользователей
        # Проверяем есть ли пользователь в таблице UsersHistory. Если нет, то добавляем.
        if not self.session.query(self.UsersHistory).filter_by(user=user.id).count():
            users_history = self.UsersHistory(user.id)
            # Передаём данные в таблицу
            self.session.add(users_history)

        # Сохраняем изменения
        self.session.commit()

    # При выходе пользователя, записываем в базу факт выхода
    def user_logout(self, username):
        # Ищем в таблице пользователя с таким именем
        user = self.session.query(self.AllUsers).filter_by(username=username).first()
        # Удаляем запись из таблицы ActiveUsers
        self.session.query(self.ActiveUsers).filter_by(user_id=user.id).delete()
        # Сохраняем изменения
        self.session.commit()
        print(f"Пользователь '{username}' отключён")

    # Отображаем список пользователей со временем последнего входа
    def users_list(self):
        query = self.session.query(
            self.AllUsers.username,
            self.AllUsers.last_login,
        )
        # Возвращаем список
        return query.all()

    # Отображаем список активных пользователей
    def active_users_list(self):
        query = self.session.query(
            self.AllUsers.username,
            self.ActiveUsers.ip_address,
            self.ActiveUsers.port,
            self.ActiveUsers.login_time,
        ).join(self.AllUsers)
        # Возвращаем список кортежей (имя, IP-адрес, порт, время)
        return query.all()

    # Возвращаем историю входов
    def login_history(self, username=None):
        # Запрашиваем историю входа
        query = self.session.query(
            self.AllUsers.username,
            self.LoginHistory.date,
            self.LoginHistory.ip_address,
            self.LoginHistory.port,
        ).join(self.AllUsers)
        # Если было указано имя пользователя, то фильтруем по нему
        if username:
            query = query.filter(self.AllUsers.username == username)
        return query.all()

    # Фиксируем передачу сообщения и делаем соответствующие отметки в БД
    def process_message(self, sender, recipient):
        # Получаем из сообщения ID отправителя и получателя
        sender = self.session.query(self.AllUsers).filter_by(username=sender).first().id
        recipient = (
            self.session.query(self.AllUsers).filter_by(username=recipient).first().id
        )
        # Запрашиваем строки из истории и увеличиваем счётчики
        sender_row = (
            self.session.query(self.UsersHistory).filter_by(user=sender).first()
        )
        sender_row.sent += 1
        recipient_row = (
            self.session.query(self.UsersHistory).filter_by(user=recipient).first()
        )
        recipient_row.accepted += 1

        # Сохраняем изменения
        self.session.commit()

    # Добавляем контакт для пользователя
    def add_contact(self, user, contact):
        # Получаем ID пользователей
        user = self.session.query(self.AllUsers).filter_by(username=user).first()
        contact = self.session.query(self.AllUsers).filter_by(username=contact).first()

        print(
            f"Добавление контакта: {self.session.query(self.AllUsers.username).filter_by(id=contact.id).first()[0]}"
        )

        # Проверяем, что нет дублей
        if (
            not contact
            or self.session.query(self.UsersContacts)
            .filter_by(user=user.id, contact=contact.id)
            .count()
        ):
            return

        # Создаём объект и заносим его в БД
        contact_row = self.UsersContacts(user.id, contact.id)
        self.session.add(contact_row)

        # Сохраняем изменения
        self.session.commit()

    # Удаляем контакт из БД
    def remove_contact(self, user, contact):
        # Получаем ID пользователей
        user = self.session.query(self.AllUsers).filter_by(username=user).first()
        contact = self.session.query(self.AllUsers).filter_by(username=contact).first()
        print(
            f"Удаление контакта: {self.session.query(self.AllUsers.username).filter_by(id=contact.id).first()[0]}"
        )
        # Проверяем что контакт может существовать (полю пользователь мы доверяем)
        if not contact:
            return

        # Удаляем требуемое
        self.session.query(self.UsersContacts).filter(
            self.UsersContacts.user == user.id,
            self.UsersContacts.contact == contact.id,
        ).delete()

        # Сохраняем изменения
        self.session.commit()

    # Возвращаем список контактов пользователя
    def get_contacts(self, username):
        # Запрашивааем указанного пользователя
        user = self.session.query(self.AllUsers).filter_by(username=username).one()
        # Запрашиваем его список контактов
        query = (
            self.session.query(self.UsersContacts, self.AllUsers.username)
            .filter_by(user=user.id)
            .join(self.AllUsers, self.UsersContacts.contact == self.AllUsers.id)
        )

        # Выбираем только имена пользователей и возвращаем их.
        return [contact[1] for contact in query.all()]

    # Возвращаем количество переданных и полученных сообщений
    def message_history(self):
        query = self.session.query(
            self.AllUsers.username,
            self.AllUsers.last_login,
            self.UsersHistory.sent,
            self.UsersHistory.accepted,
        ).join(self.AllUsers)
        # Возвращаем список кортежей
        return query.all()


# Отладка
if __name__ == "__main__":
    # Создаём тестовую БД
    test_db = ServerStorage()
    # выполняем "подключение" пользователя
    test_db.user_login("client_1", "192.168.1.4", 8888)
    test_db.user_login("client_2", "192.168.1.5", 7777)
    test_db.user_login("client_3", "192.168.1.6", 6666)

    # Выводим активных пользователей
    # print(f"Активные пользователи: {test_db.active_users_list()}")
    # Выполянем "отключение" пользователя "client_1"
    # test_db.user_logout("client_1")
    # Выводим активных пользователей
    # print(f"Активные пользователи: {test_db.active_users_list()}")
    # Запрашиваем историю входов пользователя "client_1"
    # print(f"История входов: {test_db.login_history('client_1')}")
    # Выводим список логинившихся пользователей
    # print(f"Известные пользователи: {test_db.users_list()}")

    test_db.process_message("client_1", "client_2")
    # test_db.process_message("client_2", "client_1")
    test_db.add_contact("client_1", "client_2")
    print(f"Получение контактов: {test_db.get_contacts('client_1')}")
    test_db.remove_contact("client_1", "client_2")
    print(f"Получение контактов: {test_db.get_contacts('client_1')}")
    print(f"История сообщений: {test_db.message_history()}")


"""
Результат:

Вход выполнен: client_1, 192.168.1.4, 8888
Вход выполнен: client_2, 192.168.1.5, 7777
Вход выполнен: client_3, 192.168.1.6, 6666
Добавление контакта: client_2
Получение контактов: ['client_2']
Удаление контакта: client_2
Получение контактов: []
История сообщений: [('client_1', '21.04.2022 23:03', 1, 0), ('client_2', '21.04.2022 23:03', 0, 1), ('client_3', '21.04.2022 23:03', 0, 0)]
"""
