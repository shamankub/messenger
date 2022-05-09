import time

from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
)
from sqlalchemy.orm import mapper, sessionmaker

from local.settings import *


class ClientDatabase:
    # Пользователи
    class KnownUsers:
        def __init__(self, username):
            self.id = None
            self.username = username

    # История сообщений
    class MessageHistory:
        def __init__(self, from_user, to_user, message):
            self.id = None
            self.from_user = from_user
            self.to_user = to_user
            self.message = message
            self.date = time.strftime("%d.%m.%Y %H:%M")

    # Список контактов
    class Contacts:
        def __init__(self, contact):
            self.id = None
            self.contact = contact

    def __init__(self, name):
        # Соединение с базой данных
        # Необходимо создать для каждого клиента свою БД, чтобы осуществить многопоточность
        self.engine = create_engine(
            f"sqlite:///client_{name}.sqlite3",
            echo=False,
            pool_recycle=7200,
            connect_args={"check_same_thread": False},
        )

        # Создание таблиц
        self.metadata = MetaData()

        # Таблица известных пользователей
        users = Table(
            "known_users",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("username", String),
        )

        # Таблица истории сообщений
        history = Table(
            "message_history",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("from_user", String),
            Column("to_user", String),
            Column("message", Text),
            Column("date", String),
        )

        # Таблица контактов
        contacts = Table(
            "contacts",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("contact", String, unique=True),
        )

        # Делаем миграции
        self.metadata.create_all(self.engine)

        # Создаём отображения
        mapper(self.KnownUsers, users)
        mapper(self.MessageHistory, history)
        mapper(self.Contacts, contacts)

        # Создаём сессию
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        # При установке соединения необходимо очистить таблицу контактов,
        # т.к. при запуске они подгружаются с сервера.
        self.session.query(self.Contacts).delete()
        self.session.commit()

    # Добавляем контакты
    def add_contact(self, contact):
        if not self.session.query(self.Contacts).filter_by(contact=contact).count():
            contact_row = self.Contacts(contact)
            self.session.add(contact_row)
            self.session.commit()
            print(f"Добавление контакта: {contact}")

    # Удаляем контакты
    def del_contact(self, contact):
        if not self.session.query(self.Contacts).filter_by(contact=contact).count():
            print(f"Контакт {contact} не найден")
        else:
            self.session.query(self.Contacts).filter_by(contact=contact).delete()
            self.session.commit()
            print(f"Удаление контакта: {contact}")

    # Возвращаем контакты
    def get_contacts(self):
        return [
            contact[0] for contact in self.session.query(self.Contacts.contact).all()
        ]

    # Проверяем наличие пользователя в контактах
    def check_contact(self, contact):
        if self.session.query(self.Contacts).filter_by(contact=contact).count():
            return True
        else:
            return False

    # Добавляем известных пользователей
    # Пользователи подгружаются с сервера, поэтому очищаем таблицу
    def add_users(self, users_list):
        self.session.query(self.KnownUsers).delete()
        for user in users_list:
            user_row = self.KnownUsers(user)
            self.session.add(user_row)
        self.session.commit()
        print(f"Добавление пользователей: {users_list}")

    # Возвращаем список известных пользователей
    def get_users(self):
        return [user[0] for user in self.session.query(self.KnownUsers.username).all()]

    # Проверяем наличие пользователя в таблице известных пользователей
    def check_user(self, user):
        if self.session.query(self.KnownUsers).filter_by(username=user).count():
            return True
        else:
            return False

    # Сохраняем сообщения
    def save_message(self, from_user, to_user, message):
        message_row = self.MessageHistory(from_user, to_user, message)
        self.session.add(message_row)
        self.session.commit()

    # Возвращаем историю переписки
    def get_history(self, from_user=None, to_user=None):
        query = self.session.query(self.MessageHistory)
        if from_user:
            query = query.filter_by(from_user=from_user)
        if to_user:
            query = query.filter_by(to_user=to_user)
        return [
            (
                history_row.from_user,
                history_row.to_user,
                history_row.message,
                history_row.date,
            )
            for history_row in query.all()
        ]


# Отладка
if __name__ == "__main__":
    test_db = ClientDatabase("user_1")
    for i in range(2, 6):
        test_db.add_contact(f"user_{i}")
    print(f"Существующие контакты: {test_db.get_contacts()}")
    test_db.del_contact("user_2")
    test_db.del_contact("user_6")
    print(f"Существующие контакты: {test_db.get_contacts()}")
    print(f"Проверка наличия контакта: {test_db.check_contact('user_5')}")
    test_db.add_users(["user_1", "user_2", "user_3"])
    print(f"Существующие пользователи: {test_db.get_users()}")
    print(f"Проверка наличия пользователя: {test_db.check_user('user_3')}")
    print(f"Проверка наличия пользователя: {test_db.check_user('superuser')}")
    test_db.save_message("user_1", "user_2", "Сообщение для user_2")
    test_db.save_message("user_2", "user_1", "Сообщение для user_1")
    print(test_db.get_history(to_user="user_2"))
    print(test_db.get_history("user_2"))
    print(test_db.get_history("superuser"))

"""
Результат:

Добавление контакта: user_2
Добавление контакта: user_3
Добавление контакта: user_4
Добавление контакта: user_5
Существующие контакты: ['user_2', 'user_3', 'user_4', 'user_5']
Удаление контакта: user_2
Контакт user_6 не найден
Существующие контакты: ['user_3', 'user_4', 'user_5']
Проверка наличия контакта: True
Добавление пользователей: ['user_1', 'user_2', 'user_3']
Существующие пользователи: ['user_1', 'user_2', 'user_3']
Проверка наличия пользователя: True
Проверка наличия пользователя: False
[('user_1', 'user_2', 'Сообщение для user_2', '21.04.2022 22:10')]
[('user_2', 'user_1', 'Сообщение для user_1', '21.04.2022 22:10')]
[]
"""
