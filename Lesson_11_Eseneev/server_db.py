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

    def __init__(self):
        # Соединение с базой данных
        self.engine = create_engine(SERVER_DB, echo=False, pool_recycle=7200)

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

        # Делаем миграции
        self.metadata.create_all(self.engine)

        # Создаём отображения
        mapper(self.AllUsers, users_table)
        mapper(self.ActiveUsers, active_users_table)
        mapper(self.LoginHistory, login_history_table)

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


# Отладка
if __name__ == "__main__":
    # Создаём тестовую БД
    test_db = ServerStorage()
    # выполняем "подключение" пользователя
    test_db.user_login("client_1", "192.168.1.4", 8888)
    test_db.user_login("client_2", "192.168.1.5", 7777)
    # Выводим активных пользователей
    print(f"Активные пользователи: {test_db.active_users_list()}")
    # Выполянем "отключение" пользователя "client_1"
    test_db.user_logout("client_1")
    # Выводим активных пользователей
    print(f"Активные пользователи: {test_db.active_users_list()}")
    # Запрашиваем историю входов пользователя "client_1"
    print(f"История входов: {test_db.login_history('client_1')}")
    # Выводим список логинившихся пользователей
    print(f"Известные пользователи: {test_db.users_list()}")
